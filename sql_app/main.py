from typing import List
import uvicorn
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException,status, File, UploadFile, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from sql_app import crud, models, schemas
from database import SessionLocal, engine
import json

from fastapi.responses import StreamingResponse


import io
import pandas
import database
import pymysql
origins = ["*"]

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")





models.Base.metadata.create_all(bind=engine)



app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 99999

@app.get("/get_csv/{protocol_exp_id}")
async def get_csv(protocol_exp_id:int):



    conn = pymysql.connect(host=database.DB_IP,port=3306, user=database.DB_ID, passwd=database.DB_PASS, db=database.DB_BASE, charset='utf8')
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    #cursor.execute('SELECT code,time,v FROM stimulus_protocol_exp_signals where proto_exp_id=' + str(protocol_exp_id) + '   order by time')
    cursor.execute('(SELECT code, time, v FROM stimulus_protocol_exp_signals where proto_exp_id=' + str(protocol_exp_id) + ') UNION(SELECT "TRIGGER" as code, time, 1 as V FROM test.stimulus_protocol_exp_trigger where proto_exp_id = ' + str(protocol_exp_id) + ') order by time')

    cursorData=cursor.fetchall()

    conn.close()


    df = pandas.DataFrame.from_records(cursorData)
    df2=df.pivot(index="time", columns="code", values="v").reset_index('time')
    stream = io.StringIO()

    df2.to_csv(stream, index=False)

    response = StreamingResponse(iter([stream.getvalue()]),
                                 media_type="text/csv"
                                 )

    response.headers["Content-Disposition"] = "attachment; filename=export.csv"

    return response

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str):
    user = crud.get_user_by_username(db, username)

    if not user:
        return False
    if user.username!=username:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=99999)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user




@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    if access_token == user.tokens or user.tokens == "NULL":
        db_user_update = db.query(models.User).filter(models.User.id == user.id).first()
        db_user_update.tokens = access_token
        db.add(db_user_update)
        db.commit()
        db.refresh(db_user_update)
        return {"access_token": access_token, "token_type": "bearers"}
    else:
        db_user_update = db.query(models.User).filter(models.User.id == user.id).first()
        db_user_update.tokens = "NULL"
        db.add(db_user_update)
        db.commit()
        db.refresh(db_user_update)
        return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(license_key: str, user: schemas.UserCreate, db: Session = Depends(get_db)):

    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    return crud.create_user(db=db, user=user,license_key=license_key, hashed_password=hashed_password)


@app.get("/users/", response_model=List[schemas.User])
async def read_users(token: str = Depends(oauth2_scheme), skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/findid/{email}", response_model=str)
def read_user_by_email(email: str, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=email)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User id not found")
    return db_user.username

@app.patch("/users/", response_model=schemas.User)
def update_user(user: schemas.UserUpdate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.update_user(db, user=user, current_user=current_user)


@app.delete("/users/{user_id}", response_model=bool)
def remove_user(user_id: int, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.del_user(db, user_id=user_id, current_user=current_user)



@app.delete("/protocols/{protocol_id}", response_model=bool)
def remove_protocol(protocol_id: int, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.del_protocol(db, protocol_id=protocol_id, current_user=current_user)

@app.patch("/protocols/", response_model=schemas.Protocol)
def update_protocol(protocol: schemas.ProtocolUpdate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):

    return crud.update_protocol(db, protocol=protocol, current_user=current_user)


@app.post("/protocols/", response_model=schemas.Protocol)
def create_protocol(protocol: schemas.ProtocolCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.create_protocol(db=db, protocol=protocol, user=current_user)


@app.get("/protocols/{protocol_id}", response_model=schemas.Protocol)
def read_protocol(protocol_id:int, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    item = crud.get_protocol(db, protocol_id=protocol_id)
    return item


@app.get("/protocols/", response_model=List[schemas.Protocol])
def read_protocols(keyword:str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    items = crud.get_protocols(db, keyword=keyword, doctor_id=current_user.id, skip=skip, limit=limit)
    return items


@app.patch("/protocolExps/", response_model=schemas.ProtocolExp)
def update_protocolExp(protocolExp: schemas.ProtocolExp, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.update_protocolExp(db, protocolExp=protocolExp, current_user=current_user)


@app.delete("/protocolExps/{id}", response_model=bool)
def remove_protocolExp(id: int, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.del_protocolExp(db, protocolExp_id=id, current_user=current_user)


@app.post("/protocolExps/", response_model=schemas.ProtocolExp)
def create_protocolExp(protocolExp: schemas.ProtocolExpCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.create_protocolExp(db=db, protocolExp=protocolExp, user=current_user)


@app.get("/protocolExps/", response_model=List[schemas.ProtocolExp])
def read_protocolExps(protocol_id: int, skip: int = 0,  limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    items = crud.get_protocolExps(db, protocol_id=protocol_id, skip=skip, limit=limit)
    return items


@app.get("/protocolExps/{protocolExp_id}", response_model=schemas.ProtocolExp)
def read_protocol(protocolExp_id:int, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    item = crud.get_protocolExp(db, protocolExp_id=protocolExp_id)
    return item

#################################
@app.delete("/protocolExpsEvent/{id}", response_model=bool)
def remove_protocolExpEvent(id: int, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.del_protocolExpEvent(db, protocolExpEvent_id=id, current_user=current_user)


@app.post("/protocolExpsEvent/", response_model=schemas.ProtocolExpEvent)
def create_protocolExpEvent(protocolExpEvent: schemas.ProtocolExpEventCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.create_protocolExpEvent(db=db, protocolExpEvent=protocolExpEvent, user=current_user)

@app.patch("/protocolExpsEvent/{protocol_exp_id}", response_model=schemas.ProtocolExpEvent)
def update_protocolExpEvent(protocol_exp_id: int,protocolExpEvent: schemas.ProtocolExpEventCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.update_protocolExpEvent(db=db,protocol_exp_id=protocol_exp_id, protocolExpEvent=protocolExpEvent, user=current_user)


@app.get("/protocolExpsEvent/{protocol_exp_id}", response_model=List[schemas.ProtocolExpEvent])
def read_protocolExpEvents(protocol_exp_id: int, skip: int = 0,  limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    items = crud.get_protocolExpEvents(db=db, protocol_exp_id=protocol_exp_id, skip=skip, limit=limit)
    return items


@app.post("/protocolExpSignal/", response_model=bool)
def create_protocolExpSignal(protocolExpSignals: List[schemas.ProtocolExpSignalCreate] , db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.create_protocolExpSignal(db=db, protocolExpSignals=protocolExpSignals, user=current_user)


@app.get("/protocolExpSignal/{protocol_exp_id}", response_model=List[schemas.ProtocolExpSignal])
def read_protocolExpSignals(protocol_exp_id: int, skip: int = 0,  limit: int = 1000000, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    items = crud.get_protocolExpSignals(db=db, protocol_exp_id=protocol_exp_id, skip=skip, limit=limit)
    return items


@app.post("/signals/{protocol_exp_id}/{code}/{m}", response_model=bool)
async def write_signals(code: str, protocol_exp_id: int,m: int, request: Request):
    data: bytes = await request.body()
    return crud.create_protocolExpSignalsSimple(k=str(protocol_exp_id).rjust(6, '0')+code.rjust(4, '0')+str(m).rjust(4, '0'), data=data)


@app.get("/signals_bin/{protocol_exp_id}/{code}")
async def read_signals_bin(code: str, protocol_exp_id: int):
    data=crud.get_protocolExpSignalsBin(k=str(protocol_exp_id).rjust(6, '0')+code.rjust(4, '0'))
    return Response(content=data, media_type="application/octet-stream")

@app.get("/signals/{protocol_exp_id}/{code}", response_model=str)
def read_signals(code: str, protocol_exp_id: int):
    items = crud.get_protocolExpSignalsSimple(k=str(protocol_exp_id).rjust(6, '0')+code.rjust(4, '0'))
    rtn=""
    for item in items:
        if rtn=="":
            rtn += item["v"]
        else:
            rtn+=","+item["v"]
    return rtn


@app.get("/protocolExpSignal/all/{protocol_exp_id}/{code}")
def read_protocolExpAllSignals(protocol_exp_id: int, code: str, db: Session = Depends(get_db)):
    items = crud.get_protocolExpAllSignals(code=code, db=db, protocol_exp_id=protocol_exp_id)

    jsonStr='['
    #serial,proto_exp_id,code,time,v
    idx=0
    for item in items:
        if jsonStr!='[':
            jsonStr += ','
        jsonStr+='{"time":'+str(idx)+',' #item["time"]
        jsonStr+='"code":"'+item["code"]+'",'
        jsonStr+='"v":'+str(item["v"])+'}'
        idx=idx+1
    jsonStr += ']'

    return Response(content=jsonStr, media_type="application/json")


@app.delete("/protocolExpSignal/{protocol_exp_id}", response_model=bool)
def delete_protocolExpSignals(protocol_exp_id: int,start_time:int,end_time:int, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    is_ok = crud.delete_protocolExpSignals(db=db, protocol_exp_id=protocol_exp_id,start_time=start_time,end_time=end_time)
    return is_ok



@app.get("/protocolExpSignal/{protocol_exp_id}/{code}", response_model=List[schemas.Signal])
def read_protocol_exp_signal(code: str, protocol_exp_id: int, skip: int = 0, limit: int = 3000000, db: Session = Depends(get_db)):
    items = crud.get_protocolExpSignal(db, code=code, protocol_exp_id=protocol_exp_id,  skip=skip, limit=limit)
    return items



@app.get("/protocolExpSignal/{protocol_exp_id}/{signal}/lasttime", response_model=int)
def read_protocol_exp_signal_lasttime(protocol_exp_id: int, signal: str, db: Session = Depends(get_db)):
    return crud.get_protocolExpSignal_lasttime(db, protocol_exp_id=protocol_exp_id, signal=signal)

@app.get("/protocolExpSignal/{protocol_exp_id}/{signal}/firsttime", response_model=int)
def read_protocol_exp_signal_firsttime(protocol_exp_id: int, signal: str, db: Session = Depends(get_db)):
    return crud.get_protocolExpSignal_firsttime(db, protocol_exp_id=protocol_exp_id, signal=signal)


@app.post("/protocolExpStimulus/", response_model=schemas.ProtocolExpStimulus)
def create_protocolExpStimulus(protocolExpStimulus: schemas.ProtocolExpStimulusCreate , db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.create_protocolExpStimulus(db=db, protocolExpStimulus=protocolExpStimulus, user=current_user)


@app.get("/protocolExpStimulus/{protocol_exp_id}", response_model=List[schemas.ProtocolExpStimulus])
def read_protocolExpStimulus(protocol_exp_id: int, skip: int = 0,  limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    items = crud.get_protocolExpStimulus(db=db, protocol_exp_id=protocol_exp_id, skip=skip, limit=limit)
    return items

@app.post("/protocolExpTrigger/", response_model=schemas.ProtocolExpTrigger)
def create_protocolExpTrigger(protocolExpTrigger: schemas.ProtocolExpTriggerCreate , db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.create_protocolExpTrigger(db=db, protocolExpTrigger=protocolExpTrigger, user=current_user)


@app.get("/protocolExpTrigger/{protocol_exp_id}", response_model=List[schemas.ProtocolExpTrigger])
def read_protocolExpTrigger(protocol_exp_id: int, skip: int = 0,  limit: int = 5, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    items = crud.get_protocolExpTrigger(db=db, protocol_exp_id=protocol_exp_id, skip=skip, limit=limit)
    return items


#################################


@app.get("/files/{path}", response_class=FileResponse)
async def file_down(path:str):
    npath=os.getcwd() +"\\files\\"+ path;
    return FileResponse(path=npath,  filename=path)




@app.post("/upload/")
async def file_upload(fileData: UploadFile = File(...)):
    print(fileData.file)
    # print('../'+os.path.isdir(os.getcwd()+"images"),"*************")
    try:
        os.mkdir("files")
        print(os.getcwd())
    except Exception as e:
        print(e)

    file_name = os.getcwd()+"/files/"+fileData.filename.replace(" ", "-")
    file_name_short = fileData.filename.replace(" ", "-")
    with open(file_name,'wb+') as f:
        f.write(fileData.file.read())
        f.close()

    file = {"filePath": file_name}

    #new_file = await add_file(file)
    return {"filename": file_name_short}




@app.post("/patients/", response_model=schemas.Patient)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.create_patient(db=db, patient=patient, user=current_user)


@app.get("/patients/", response_model=List[schemas.Patient])
def read_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    patients = crud.get_patients(db, current_user.id, skip=skip, limit=limit)
    return patients


@app.get("/patients/{patient_id}", response_model=schemas.Patient)
def read_patient(patient_id: int, db: Session = Depends(get_db)):
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient


@app.patch("/patients/", response_model=schemas.Patient)
def set_patient(patient: schemas.Patient, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.update_patient(db, patient=patient, user=current_user)


@app.delete("/patients/{patient_id}", response_model=bool)
def remove_patient(patient_id: int, db: Session = Depends(get_db)):
    return crud.del_patient(db, patient_id=patient_id)


@app.get("/experiments/{exp_id}", response_model=schemas.Experiment)
def get_experiment(exp_id: int, db: Session = Depends(get_db)):
    return crud.get_experiment(db=db, exp_id=exp_id)



@app.patch("/experiments/{exp_id}/region", response_model=schemas.Experiment)
def update_experiment_region(exp_id: int, experiment_region: schemas.ExperimentRegionUpdate, db: Session = Depends(get_db)):
    return crud.update_experiment_region(db=db, exp_id=exp_id, experiment_region=experiment_region)


@app.delete("/experiments/{exp_id}", response_model=bool)
def remove_experiment(exp_id: int, db: Session = Depends(get_db)):
    return crud.del_experiment(db, exp_id=exp_id)


@app.post("/experiments/", response_model=schemas.Experiment)
def create_experiment(experiment: schemas.ExperimentCreate, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.create_experiment(db=db, experiment=experiment, user=current_user)


@app.get("/experiments/", response_model=List[schemas.ExperimentList])
def read_experiment(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    items = crud.get_experiments(db, user_id=current_user.id, skip=skip, limit=limit)
    return items


@app.post("/artifacts/", response_model=schemas.Artifact)
def create_artifact(artifact: schemas.ArtifactCreate, db: Session = Depends(get_db)):
    return crud.create_artifact(db=db, artifact=artifact)


@app.patch("/artifacts/", response_model=schemas.Artifact)
def update_artifact(artifact_update: schemas.ArtifactUpdate, db: Session = Depends(get_db)):
    return crud.update_artifact(db=db, artifact_update=artifact_update)

@app.delete("/artifacts/", response_model=bool)
def delete_artifact(serial: int, db: Session = Depends(get_db)):
    return crud.delete_artifact(db=db, serial=serial)


@app.get("/artifacts/{exp_id}", response_model=List[schemas.Artifact])
def read_artifacts(exp_id: int, time_s: int = 0, time_e: int = 9613651596456, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud.get_artifacts(db, exp_id=exp_id, time_s=time_s, time_e=time_e, skip=skip, limit=limit)
    return items


@app.get("/signals/{exp_id}", response_model=List[schemas.Signal])
def read_signals(exp_id: int, time_s: int = 0, time_e: int = 9613651596456,  skip_v:int=1,  skip: int = 0, limit: int = 80000, db: Session = Depends(get_db)):
    items = crud.get_signals(db, exp_id=exp_id, time_s=time_s, time_e=time_e,skip_v=skip_v, skip=skip, limit=limit)
    return items


@app.get("/signals/{exp_id}/{code}", response_model=List[schemas.Signal])
def read_signal(code: str, exp_id: int, time_s: int = 0, time_e: int = 9613651596456, skip_v:int=1, skip: int = 0, limit: int = 30000, db: Session = Depends(get_db)):
    items = crud.get_signal(db, code=code, exp_id=exp_id, time_s=time_s, time_e=time_e ,skip_v=skip_v, skip=skip, limit=limit)
    return items

@app.get("/signals/{exp_id}/{signal}/lasttime", response_model=int)
def read_signal_lasttime(exp_id: int, signal: str, db: Session = Depends(get_db)):
    return crud.get_signal_lasttime(db, exp_id=exp_id, signal=signal)

@app.get("/signals/{exp_id}/{signal}/firsttime", response_model=int)
def read_signal_firsttime(exp_id: int, signal: str, db: Session = Depends(get_db)):
    return crud.get_signal_firsttime(db, exp_id=exp_id, signal=signal)


@app.delete("/licenses/{license_id}", response_model=bool)
def del_license_key(license_id: int, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.del_license_key(db, license_id, current_user)


@app.get("/licenseKey/", response_model=str)
def get_license_key(db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    rtn = crud.generate_license_key(db,current_user)
    return rtn.license_key


@app.get("/licenses/", response_model=List[schemas.LicenseKey])
def get_license_keys(skip: int = 0, limit: int = 99999, db: Session = Depends(get_db), current_user: schemas.User = Depends(get_current_user)):
    return crud.get_license_keys(db, skip=skip, limit=limit, current_user=current_user)


@app.post("/signals/", response_model=bool)
def create_signals(signal_list: List[schemas.SignalCreate], db: Session = Depends(get_db)):
    return crud.create_signal(db, signal_list)

@app.post("/api_CPP/", response_model=schemas.SimpleSignal)
def create_signals(two_signal_list: schemas.TwoSignalList):
    return crud.get_CPP_func(two_signal_list.signalList1,two_signal_list.signalList2)


@app.post("/api_AMP/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_AMP_func(one_signal_list.signalList)


@app.post("/api_PRx/", response_model=schemas.SimpleSignal)
def create_signals(two_signal_list: schemas.TwoSignalList):
    return crud.get_PRx_func(two_signal_list.signalList1, two_signal_list.signalList2)


@app.post("/api_RAP/", response_model=schemas.SimpleSignal)
def create_signals(two_signal_list: schemas.TwoSignalList):
    return crud.get_RAP_func(two_signal_list.signalList1, two_signal_list.signalList2)


@app.post("/api_RAC/", response_model=schemas.SimpleSignal)
def create_signals(two_signal_list: schemas.TwoSignalList):
    return crud.get_RAC_func(two_signal_list.signalList1, two_signal_list.signalList2)


@app.post("/api_wICP/", response_model=schemas.SimpleSignal)
def create_signals(two_signal_list: schemas.TwoSignalList):
    return crud.get_wICP_func(two_signal_list.signalList1, two_signal_list.signalList2)


@app.post("/api_MRR/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_nni_mean_func(one_signal_list.signalList)


@app.post("/api_SDNN/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_sdnn_func(one_signal_list.signalList)


@app.post("/api_RMSSD/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_rmssd_func(one_signal_list.signalList)


@app.post("/api_pNN50/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_pnn50_func(one_signal_list.signalList)


@app.post("/api_pNN20/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_pnn20_func(one_signal_list.signalList)


@app.post("/api_VLF/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_vlf_abs_func(one_signal_list.signalList)


@app.post("/api_LF/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_lf_abs_func(one_signal_list.signalList)


@app.post("/api_HF/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_hf_abs_func(one_signal_list.signalList)

@app.post("/api_SD1/", response_model=schemas.SimpleSignal)
def create_signals(one_signal_list: schemas.OneSignalList):
    return crud.get_sd1_func(one_signal_list.signalList)


@app.post("/api_INFUSION/", response_model=schemas.InfusionOutput)
def create_signals(data: schemas.InfusionInput,db: Session = Depends(get_db)):
    exp_id = data.exp_id
    ABP_list = data.ABP_list
    ICP_list = data.ICP_list
    ABP_atf_list = data.ABP_atf_list
    ICP_atf_list = data.ICP_atf_list

    baseline_start = data.baseline_start
    baseline_end = data.baseline_end
    transient_start = data.transient_start
    transient_end = data.transient_end
    plateau_start = data.plateau_start
    plateau_end = data.plateau_end
    resistance_of_shunt = data.resistance_of_shunt
    shunt_operating_pressure = data.shunt_operating_pressure

    infusion_rate = data.infusion_rate
    infusion_duration = data.infusion_duration
    infusion_start = data.infusion_start


    rtn= crud.infusion_test_analyzer(ABP_list, ICP_list,
                                          int(baseline_start), int(baseline_end), int(transient_start),
                                          int(transient_end), int(plateau_start), int(plateau_end),
                                          float(resistance_of_shunt), float(shunt_operating_pressure),
                                          float(infusion_rate), int(infusion_start), int(infusion_duration),
                                          ABP_atf_list, ICP_atf_list)

    result_json= json.dumps(rtn)

    crud.set_experiment_region(db, exp_id, baseline_start, baseline_end, transient_start,transient_end, plateau_start, plateau_end)
    crud.set_experiment_result(db, exp_id, result_json)

    return rtn




if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
