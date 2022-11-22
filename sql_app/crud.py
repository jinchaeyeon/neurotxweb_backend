from sqlalchemy.orm import Session
from fastapi import HTTPException
from . import models, schemas
import time
import uuid
import pandas as pd
from scipy.signal import find_peaks
import biosppy
import pyhrv.tools as tools
import pyhrv
from typing import List
import os
import glob
import pymysql
import numpy as np
from scipy.fftpack import fft, fftshift
import matplotlib.pyplot as plt
from sqlalchemy import or_


import database

from scipy.optimize import curve_fit
from threading import Thread
import functools
import pymysql
import matplotlib
matplotlib.use('Agg')
import matplotlib.style as mplstyle
mplstyle.use('fast')



def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate, license_key: str, hashed_password: str):
    db_license_key = get_license_key(db, license_key)
    db_user = models.User(email=user.email, hashed_password=hashed_password, username=user.username)

    if db_license_key and db_license_key.is_used is False:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        set_used_license_key(db, license_key, user)
    else:
        raise HTTPException(status_code=400, detail="license key is not valid")

    return db_user


def get_patients(db: Session, doctor_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Patient).filter(models.Patient.doctor_id == doctor_id).offset(skip).limit(limit).all()


def get_patient(db: Session, patient_id: int):
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()


def update_patient(db: Session, patient: schemas.Patient, user: schemas.User):
    db_patient_update = db.query(models.Patient).filter(models.Patient.id == patient.id).first()
    if db_patient_update:
        db_patient_update.weight = patient.weight
        db_patient_update.height = patient.height
        db_patient_update.name = patient.name
        db_patient_update.gender = patient.gender
        db_patient_update.age = patient.age
        db_patient_update.patient_object = patient.patient_object
        db.add(db_patient_update)
        db.commit()
        db.refresh(db_patient_update)
    return db_patient_update



def del_experiment(db: Session, exp_id: int):


    conn = pymysql.connect(host='dbneurotx.cp78dfskizh3.ap-northeast-2.rds.amazonaws.com',port=3306, user='admin', password='zxc~!2051801',db='test', charset='utf8')
    curs = conn.cursor(pymysql.cursors.DictCursor)
    sql = "delete from infusion_signals where exp_id=%s"
    curs.execute(sql, exp_id)

    sql = "delete from infusion_artifact where exp_id=%s"
    curs.execute(sql, exp_id)

    conn.commit()

    db_experiment_delete = db.query(models.Experiment).filter(models.Experiment.id == exp_id).first()
    if db_experiment_delete:
        db.delete(db_experiment_delete)
        db.commit()




#    db_signal_delete = db.query(models.Signal).filter(models.Signal.exp_id == exp_id).all()
#    if db_signal_delete:
#        db.delete(db_signal_delete)
#        db.commit()

    return True



def del_patient(db: Session, patient_id: int):
    db_patient_delete = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient_delete:
        db.delete(db_patient_delete)
        db.commit()

    return True







def update_protocol(db: Session, protocol: schemas.ProtocolUpdate, current_user: schemas.User):
    if current_user.is_staff:
        db_protocol_update = db.query(models.Protocol).filter(models.Protocol.id == protocol.id).first()
        if db_protocol_update:
            if protocol.doctor_id:
                db_protocol_update.doctor_id = protocol.doctor_id
            if protocol.title:
                db_protocol_update.title = protocol.title
            if protocol.desc:
                db_protocol_update.desc = protocol.desc
            if protocol.manager:
                db_protocol_update.manager = protocol.manager

            db.add(db_protocol_update)
            db.commit()
            db.refresh(db_protocol_update)
    else:
        raise HTTPException(status_code=400, detail="You are not a staff")
    return db_protocol_update


def del_protocol(db: Session, protocol_id: int, current_user: schemas.User):
    if current_user.is_staff:
        db_protocol_delete = db.query(models.Protocol).filter(models.Protocol.id == protocol_id).first()
        if db_protocol_delete:
            db.delete(db_protocol_delete)
            db.commit()
    else:
        raise HTTPException(status_code=400, detail="You are not a staff")

    return True



def create_protocol(db: Session, protocol: schemas.ProtocolCreate, user: schemas.User):

    db_protocol = models.Protocol(**protocol.dict())
    db_protocol.doctor_id = user.id
    db.add(db_protocol)
    db.commit()
    db.refresh(db_protocol)
    return db_protocol


def get_protocol(db: Session, protocol_id: int):
    return db.query(models.Protocol).filter(models.Protocol.id == protocol_id).first()


def get_protocols(db: Session, keyword:str, doctor_id:int,skip:int=0,limit:int=9999):
        ##return db.query(models.Protocol).filter(models.Protocol.doctor_id == doctor_id).offset(skip).limit(limit).all()
        if(keyword==""):
            ##return db.query(models.Protocol).offset(skip).limit(limit).all()
            return db.query(models.Protocol).filter(models.Protocol.doctor_id == doctor_id).offset(skip).limit(
                limit).all()
        else:
            search = "%{}%".format(keyword)

            return db.query(models.Protocol).filter(models.Protocol.doctor_id == doctor_id, models.Protocol.title.like(search)).offset(skip).limit(
                limit).all()
            ##return db.query(models.Protocol).filter(models.Protocol.title.like(search)).offset(skip).limit(limit).all()


def update_protocolExp(db: Session, protocolExp: schemas.ProtocolExpUpdate, current_user: schemas.User):
    if current_user.is_staff:
        db_protocolExp_update = db.query(models.ProtocolExp).filter(models.ProtocolExp.id == protocolExp.id).first()

        if db_protocolExp_update:
            if protocolExp.name:
                db_protocolExp_update.name = protocolExp.name

            if protocolExp.gender:
                db_protocolExp_update.gender = protocolExp.gender
            if protocolExp.birth:
                db_protocolExp_update.birth = protocolExp.birth
            if protocolExp.diagnosis:
                db_protocolExp_update.diagnosis = protocolExp.diagnosis
            if protocolExp.desc:
                db_protocolExp_update.desc = protocolExp.desc

            if protocolExp.deviceinfo:
                db_protocolExp_update.deviceinfo = protocolExp.deviceinfo
            if protocolExp.survey_link:
                db_protocolExp_update.survey_link = protocolExp.survey_link
            if protocolExp.agree_filename:
                db_protocolExp_update.agree_filename = protocolExp.agree_filename
            if protocolExp.exp_duration:
                db_protocolExp_update.exp_duration = protocolExp.exp_duration
            if protocolExp.maxstimulus:
                db_protocolExp_update.maxstimulus = protocolExp.maxstimulus
        db.add(db_protocolExp_update)
        db.commit()
        db.refresh(db_protocolExp_update)
    else:
        raise HTTPException(status_code=400, detail="You are not a staff")

    return db_protocolExp_update


def del_protocolExp(db: Session, protocolExp_id: int, current_user: schemas.User):
    if current_user.is_staff:
        db_protocolExp_delete = db.query(models.ProtocolExp).filter(models.ProtocolExp.id == protocolExp_id).first()
        if db_protocolExp_delete:


            conn = pymysql.connect(host='dbneurotx.cp78dfskizh3.ap-northeast-2.rds.amazonaws.com', port=3306,
                                   user='admin',
                                   password='zxc~!2051801', db='test', charset='utf8')
            curs = conn.cursor(pymysql.cursors.DictCursor)
            sql = "delete from stimulus_protocol_exp_signals where proto_exp_id=%s"
            curs.execute(sql, (protocolExp_id))
            conn.commit()

            sql = "delete from stimulus_protocol_exp_event where proto_exp_id=%s"
            curs.execute(sql, (protocolExp_id))
            conn.commit()

            sql = "delete from stimulus_protocol_exp_setting where proto_exp_id=%s"
            curs.execute(sql, (protocolExp_id))
            conn.commit()

            sql = "delete from stimulus_protocol_exp_stimulus where proto_exp_id=%s"
            curs.execute(sql, (protocolExp_id))
            conn.commit()
            sql = "delete from stimulus_protocol_exp_trigger where proto_exp_id=%s"
            curs.execute(sql, (protocolExp_id))
            conn.commit()
            db.delete(db_protocolExp_delete)
            db.commit()


    else:
        raise HTTPException(status_code=400, detail="You are not a staff")

    return True


def create_protocolExp(db: Session, protocolExp: schemas.ProtocolExpCreate, user: schemas.User):
    db_protocolExp = models.ProtocolExp(**protocolExp.dict())
    ##db_protocolExp.proto_id = user.id
    db.add(db_protocolExp)
    db.commit()
    db.refresh(db_protocolExp)
    return db_protocolExp


def get_protocolExp(db: Session, protocolExp_id: int):
    return db.query(models.ProtocolExp).filter(models.ProtocolExp.id == protocolExp_id).first()



def get_protocolExps(db: Session, protocol_id:int,skip:int=0,limit:int=9999):
    return db.query(models.ProtocolExp).filter(models.ProtocolExp.proto_id == protocol_id).offset(skip).limit(limit).all()



def get_protocolExpTrigger(db: Session, protocol_exp_id:int, skip:int=0, limit:int=9999):
    return db.query(models.ProtocolExpTrigger).filter(models.ProtocolExpTrigger.proto_exp_id == protocol_exp_id).offset(skip).limit(
        limit).all()


def create_protocolExpTrigger(db: Session, protocolExpTrigger: schemas.ProtocolExpTriggerCreate, user: schemas.User):
    db_protocolExpTrigger = models.ProtocolExpTrigger(**protocolExpTrigger.dict())
    db.add(db_protocolExpTrigger)
    db.commit()
    db.refresh(db_protocolExpTrigger)
    return db_protocolExpTrigger


def get_protocolExpStimulus(db: Session, protocol_exp_id:int, skip:int=0, limit:int=9999):
    return db.query(models.ProtocolExpStimulus).filter(models.ProtocolExpStimulus.proto_exp_id == protocol_exp_id).order_by(models.ProtocolExpStimulus.time.asc()).offset(skip).limit(
        limit).all()


def create_protocolExpStimulus(db: Session, protocolExpStimulus: schemas.ProtocolExpStimulusCreate, user: schemas.User):
    db_protocolExpStimulus = models.ProtocolExpStimulus(**protocolExpStimulus.dict())
    db.add(db_protocolExpStimulus)
    db.commit()
    db.refresh(db_protocolExpStimulus)
    return db_protocolExpStimulus

def delete_protocolExpSignals(db: Session, protocol_exp_id:int,start_time: int, end_time: int):

    conn = pymysql.connect(host=database.DB_IP,port=3306, user=database.DB_ID, passwd=database.DB_PASS, db=database.DB_BASE, charset='utf8')
    curs = conn.cursor(pymysql.cursors.DictCursor)

    sql = "delete from stimulus_protocol_exp_signals where proto_exp_id=" + str(protocol_exp_id) + " and time>"+str(start_time)+" and time<"+str(end_time)
    curs.execute(sql)

    conn.commit()
    return True



def create_protocolExpSignalsSimple(k:str,data:bytes):
    conn = pymysql.connect(host=database.DB_IP,port=3306, user=database.DB_ID, passwd=database.DB_PASS, db=database.DB_BASE, charset='utf8')
    curs = conn.cursor(pymysql.cursors.DictCursor)

    sql = "insert into signal_bin (k,v)  values('"+k+"', %s)"
    curs.execute(sql,data)

    conn.commit()
    return True

def get_protocolExpSignalsBin(k:str):
    conn = pymysql.connect(host=database.DB_IP,port=3306, user=database.DB_ID, passwd=database.DB_PASS, db=database.DB_BASE, charset='utf8')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT k,v FROM signal_bin where k like \''+k+'%\'')
    cursorData = cursor.fetchall()
    byt_combined = b''
    for row in cursorData:
        byt_combined=byt_combined+row["v"]


    return byt_combined

def get_protocolExpSignalsSimple(k:str):
    conn = pymysql.connect(host=database.DB_IP,port=3306, user=database.DB_ID, passwd=database.DB_PASS, db=database.DB_BASE, charset='utf8')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    #
    # cursor.execute('SELECT proto_exp_id,time,code,v FROM stimulus_protocol_exp_signals where proto_exp_id=3 and code = \'EEG1\' order by time')
    # cursorData=cursor.fetchall()
    # seq_i = 1
    # seq_j = 1
    # varr = ""
    #
    # for row in cursorData:
    #     proto_exp_id = row["proto_exp_id"]
    #     code = row["code"]
    #     v = row["v"]
    #     if varr=="":
    #         varr+=str(int(v))
    #     else:
    #         varr += "," + str(int(v))
    #
    #     seq_j = seq_j+1
    #
    #     if seq_j == 60*200:
    #         k = str(proto_exp_id).rjust(6, '0') + code.rjust(4, '0')+str(seq_i).rjust(4, '0')
    #
    #
    #         sql = "insert into stimulus_protocol_exp_signals_s (k,v) values('"+k+"', '"+varr+"')"
    #         cursor.execute(sql)
    #         conn.commit()
    #         seq_i = seq_i+1
    #         seq_j = 1
    #         varr =""

    # You can generate an API token from the "API Tokens Tab" in the UI
    # tokenInfx = os.getenv("TPISIfYMDQ3Vz_uWfZlMmyv4h3QogNsNT2mWP9UXpE3YNko1zlqrKVIcMr6XbdYaRJhhSLWS_nXUAV1YY0tlRQ==")
    # orgInfx = "james.baek@iselsoft.co.kr"
    # bucketInfx = "james.baek's Bucket"
    #
    # with InfluxDBClient(url="https://us-east-1-1.aws.cloud2.influxdata.com", token=tokenInfx, org=orgInfx) as client:
    #     write_api = client.write_api(write_options=SYNCHRONOUS)
    #
    #     for row in cursorData:
    #         proto_exp_id = row["proto_exp_id"]
    #         code = row["code"]
    #         v = row["v"]
    #         data = "signal,expid="+proto_exp_id+",code="+code+" v="+v
    #         write_api.write(bucketInfx, orgInfx, data)
    #         seq_j = seq_j+1



    cursor.execute('SELECT k,v FROM stimulus_protocol_exp_signals_s where k like \''+k+'%\'')
    return cursor.fetchall()


def get_protocolExpSignals(db: Session, protocol_exp_id:int,skip: int = 0, limit: int = 3000000):
#    return db.query(models.ProtocolExpSignal).filter(models.ProtocolExpSignal.proto_exp_id == protocol_exp_id).filter(or_( models.ProtocolExpSignal.code == "PPG", models.ProtocolExpSignal.code == "X", models.ProtocolExpSignal.code == "Y", models.ProtocolExpSignal.code == "Z"))\
#        .order_by(models.ProtocolExpSignal.time.asc()).offset(skip).limit(limit).all()
#.offset(skip).limit(limit)


    conn = pymysql.connect(host=database.DB_IP,port=3306, user=database.DB_ID, passwd=database.DB_PASS, db=database.DB_BASE, charset='utf8')
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    #cursor.execute('SELECT * FROM stimulus_protocol_exp_signals where proto_exp_id=' + str(protocol_exp_id) + ' and (code=\'PPG\' or code=\'X\' or code=\'Y\' or code=\'Z\') order by time LIMIT ' + str(skip) + ',' + str(limit))
    cursor.execute('SELECT * FROM stimulus_protocol_exp_signals_new where proto_exp_id=' + str(protocol_exp_id) + ' and (code=\'PPG\' or code=\'X\' or code=\'Y\' or code=\'Z\') and time>'+str(skip)+' and time<'+str(limit)+' order by time')

    cursorData=cursor.fetchall()
    items = []

    for row in cursorData:
        items.append(schemas.ProtocolExpSignal(**row))


    if skip>75000:

        #ppg_skip = int(skip/4)-15000
        ppg_skip = skip-75000   #5분 250*60*5
        if ppg_skip<0:
            ppg_skip=0

        #ppg_limit = 15000+3000

        #8*8=64초 -> 초과되는 4초 250*4?
        #ppg_limit = limit + 3000 * 5
        ppg_limit = limit


        #cursor.execute('SELECT time,v FROM stimulus_protocol_exp_signals where proto_exp_id=' + str(protocol_exp_id) + ' and (code=\'PPG\') order by time LIMIT ' + str(ppg_skip) + ',' + str(ppg_limit))
        cursor.execute('SELECT time,v FROM stimulus_protocol_exp_signals where proto_exp_id=' + str(protocol_exp_id) + ' and (code=\'PPG\') and time > '+str(ppg_skip)+' and time < '+str(limit)+' order by time')


        cursorData = cursor.fetchall()
        signalList = []
        partialArr = []

        partialArr1=[]
        partialArr2=[]
        partialArr3=[]
        partialArr4=[]
        partialArr5 = []
        partialArr6 = []
        partialArr7 = []
        partialArr8 = []


        for x in range(8):
            partialArr.append([])


    ##추가할 일.... 시간을 *5로 해야하는 지 체크해야함!!!
        idx=0
        tx=0
        lastTime = 0
        for row in cursorData:
            idx = idx + 1
            if row["time"] > lastTime:
                for x in range(8): #1분 = 8개 * 8초
                    if row["time"] > ppg_skip + 400 * 5 * x:
                        if row["time"] < ppg_skip + 75000 + (400 * 5 * x):
                            partialArr[x].append({"x": row["time"] * 20 + 1491553506653, "y": row["v"]})

                lastTime = row["time"]

        conn.close()

        #FQ=250  but 1/5 즉 초당 50 FQ * 5분은 50*60*5 = 1500 / 8초는 400
        #5분 분량 / 8초단위 = 1500개씩 / skip +400

        rt_s1 = []
        rt_s2 = []
        rt_s3 = []

    #        partialArr=signalList[baseIdx * 400, baseIdx * 400 + 1500]
        for x in range(8):
            rt_s1.append(get_lf_abs_func(partialArr[x]))
            rt_s2.append(get_hf_abs_func(partialArr[x]))
            rt_s3.append(get_nni_mean_func(partialArr[x]))




        for item in rt_s1:
            t = {"proto_exp_id": protocol_exp_id, "code": "LF", "time": (item['x']-1491553506653)/20, "v": item['y'], "serial": 0}
            items.append(t)

        for item in rt_s2:
            t = {"proto_exp_id": protocol_exp_id, "code": "HF", "time": (item['x']-1491553506653)/20, "v": item['y'], "serial": 0}
            items.append(t)

        for item in rt_s3:
            t = {"proto_exp_id": protocol_exp_id, "code": "NNI", "time": (item['x']-1491553506653)/20, "v": item['y'], "serial": 0}
            items.append(t)


    return items

def get_protocolExpAllSignals(code:str, db: Session, protocol_exp_id:int):
    conn = pymysql.connect(host=database.DB_IP,port=3306, user=database.DB_ID, passwd=database.DB_PASS, db=database.DB_BASE, charset='utf8')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    #cursor.execute('SELECT * FROM stimulus_protocol_exp_signals where proto_exp_id=' + str(protocol_exp_id) + ' and (code=\'PPG\' or code=\'X\' or code=\'Y\' or code=\'Z\') order by time LIMIT ' + str(skip) + ',' + str(limit))
    cursor.execute('SELECT serial,proto_exp_id,code,time,v FROM stimulus_protocol_exp_signals_new where proto_exp_id=' + str(protocol_exp_id) + ' and code=\''+code+'\'' )
    return cursor.fetchall()

def get_protocolExpSignal(db: Session, code:str, protocol_exp_id: int, skip: int = 0, limit: int = 3000000):
    return db.query(models.ProtocolExpSignal).filter(models.ProtocolExpSignal.proto_exp_id == protocol_exp_id).filter(models.ProtocolExpSignal.code == code)\
        .offset(skip).limit(limit).all()


def get_protocolExpSignal_lasttime(db: Session, protocol_exp_id: int, signal: str):
    #rs=db.query(models.ProtocolExpSignal).filter(models.ProtocolExpSignal.proto_exp_id == protocol_exp_id).filter(models.ProtocolExpSignal.code == signal).order_by(
       #models.ProtocolExpSignal.time.desc()).first()


    conn = pymysql.connect(host=database.DB_IP,port=3306, user=database.DB_ID, passwd=database.DB_PASS, db=database.DB_BASE, charset='utf8')
    cursor = conn.cursor(pymysql.cursors.DictCursor)


    cursor.execute('SELECT max(time) as time FROM stimulus_protocol_exp_signals where proto_exp_id=' + str(protocol_exp_id) + ' and code=\'PPG\'')

    cursorData=cursor.fetchone()



    if not cursorData:
        return 0
    else:
       return cursorData["time"]


def get_protocolExpSignal_firsttime(db: Session, protocol_exp_id: int, signal: str):
    rs=db.query(models.ProtocolExpSignal).filter(models.ProtocolExpSignal.proto_exp_id == protocol_exp_id).filter(models.ProtocolExpSignal.code == signal).order_by(
        models.ProtocolExpSignal.time).first()
    if not rs:
        return 0
    else:
       return rs.time








def create_protocolExpSignal(db: Session, protocolExpSignals: List[schemas.ProtocolExpSignalCreate], user: schemas.User):
    conn = pymysql.connect(host='dbneurotx.cp78dfskizh3.ap-northeast-2.rds.amazonaws.com', port=3306, user='admin',
                           password='zxc~!2051801', db='test', charset='utf8')
    curs = conn.cursor(pymysql.cursors.DictCursor)
    for signal in protocolExpSignals:
        sql = "insert into stimulus_protocol_exp_signals (proto_exp_id,code,time,v) values(%s,%s,%s,%s)"
        curs.execute(sql, (signal.proto_exp_id, signal.code, signal.time, signal.v))

    conn.commit()
    return True;
    #db_protocolExpSignal = models.ProtocolExpSignal(**protocolExpSignal.dict())
    #db.add(db_protocolExpSignal)
    #db.commit()
    #db.refresh(db_protocolExpSignal)
    #return db_protocolExpSignal


def get_protocolExpEvents(db: Session, protocol_exp_id:int, skip:int=0, limit:int=9999):
    return db.query(models.ProtocolExpEvent).filter(models.ProtocolExpEvent.proto_exp_id == protocol_exp_id).offset(skip).limit(
        limit).all()




def update_protocolExpEvent(db: Session,protocol_exp_id:int, protocolExpEvent: schemas.ProtocolExpEventCreate, user: schemas.User):
    db_protocolExpEvent_update = db.query(models.ProtocolExpEvent).filter(models.ProtocolExpEvent.serial == protocol_exp_id).first()
    if db_protocolExpEvent_update:
        db_protocolExpEvent_update.memo = protocolExpEvent.memo
        db.add(db_protocolExpEvent_update)
        db.commit()
        db.refresh(db_protocolExpEvent_update)
    return db_protocolExpEvent_update


    db_protocolExpEvent = models.ProtocolExpEvent(**protocolExpEvent.dict())
    db.add(db_protocolExpEvent)
    db.commit()
    db.refresh(db_protocolExpEvent)
    return db_protocolExpEvent

def create_protocolExpEvent(db: Session, protocolExpEvent: schemas.ProtocolExpEventCreate, user: schemas.User):
    db_protocolExpEvent = models.ProtocolExpEvent(**protocolExpEvent.dict())
    db.add(db_protocolExpEvent)
    db.commit()
    db.refresh(db_protocolExpEvent)
    return db_protocolExpEvent


def del_protocolExpEvent(db: Session, protocolExpEvent_id:int, current_user: schemas.User):
    db_protocol_exp_event_delete = db.query(models.ProtocolExpEvent).filter(models.ProtocolExpEvent.serial == protocolExpEvent_id).first()
    if db_protocol_exp_event_delete:
        db.delete(db_protocol_exp_event_delete)
        db.commit()
    return True

def update_user(db: Session, user: schemas.UserUpdate, current_user: schemas.User):
    if current_user.is_staff:
        db_user_update = db.query(models.User).filter(models.User.id == user.id).first()
        if db_user_update:
            if user.email:
                db_user_update.email = user.email
            elif user.tokens:
                db_user_update.tokens = "NULL"
            else:
                db_user_update.is_staff = user.is_staff
            db.add(db_user_update)
            db.commit()
            db.refresh(db_user_update)
    else:
        raise HTTPException(status_code=400, detail="You are not a staff")
    return db_user_update


def del_user(db: Session, user_id: int, current_user: schemas.User):
    if current_user.is_staff:
        db_user_update = db.query(models.User).filter(models.User.id == user_id).first()

        db_user_delete = db.query(models.User).filter(models.User.id == user_id).first()
        if db_user_delete:
            db.delete(db_user_delete)
            db.commit()
    else:
        raise HTTPException(status_code=400, detail="You are not a staff")

    return True


def create_patient(db: Session, patient: schemas.PatientCreate, user: schemas.User):

    db_patient = models.Patient(**patient.dict())
    db_patient.doctor_id = user.id
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def gen_uuid():
    global uuid_var
    uuid_var = uuid.uuid4()
    return uuid_var


def generate_license_key(db: Session, current_user: schemas.User):
    if current_user.is_staff:
        license_key = gen_uuid()
        db_license_key = models.LicenseKey(license_key=license_key, is_used=False)
        db.add(db_license_key)
        db.commit()
        db.refresh(db_license_key)
    else:
        raise HTTPException(status_code=400, detail="You are not a staff")

    return db_license_key

def get_license_key(db: Session, license_key: str):
    return db.query(models.LicenseKey).filter(models.LicenseKey.license_key == license_key).first()


def get_license_keys(db: Session, current_user: schemas.User, skip: int = 0, limit: int = 100):
    if not current_user.is_staff:
        raise HTTPException(status_code=400, detail="You are not a staff")

    return db.query(models.LicenseKey).offset(skip).limit(limit).all()


def set_used_license_key(db: Session, license_key: str, user: schemas.UserCreate):
    db_license_key_update = db.query(models.LicenseKey).filter(models.LicenseKey.license_key == license_key).first()
    if db_license_key_update:
        db_license_key_update.is_used = True
        db_license_key_update.username = user.username
        db_license_key_update.used_from = time.strftime('%Y-%m-%d %H:%M:%S')
        db.add(db_license_key_update)
        db.commit()
        db.refresh(db_license_key_update)
    return db_license_key_update



def del_license_key(db: Session, license_id: int, current_user: schemas.User):
    if current_user.is_staff:
        db_license_delete = db.query(models.LicenseKey).filter(models.LicenseKey.id == license_id).first()
        if db_license_delete:
            db.delete(db_license_delete)
            db.commit()
    else:
        raise HTTPException(status_code=400, detail="You are not a staff")

    return True

def get_experiments(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    items = db.query(models.Experiment).join(models.Patient, models.Experiment.patient_id == models.Patient.id).filter(models.Experiment.doctor_id == user_id).offset(skip).limit(limit).all()
    return items

def update_experiment_region(db: Session,exp_id: int, experiment_region:schemas.ExperimentRegionUpdate):
    db_experiment_update = db.query(models.Experiment).filter(models.Experiment.id == exp_id).first()
    if experiment_region.kind == "baseline" and experiment_region.loc == "start":
        db_experiment_update.baseline_start = experiment_region.new_value

    if experiment_region.kind == "baseline" and experiment_region.loc == "end":
        db_experiment_update.baseline_end = experiment_region.new_value

    if experiment_region.kind == "transient" and experiment_region.loc == "start":
        db_experiment_update.transient_start = experiment_region.new_value

    if experiment_region.kind == "transient" and experiment_region.loc == "end":
        db_experiment_update.transient_end = experiment_region.new_value

    if experiment_region.kind == "plateau" and experiment_region.loc == "start":
        db_experiment_update.plateau_start = experiment_region.new_value

    if experiment_region.kind == "plateau" and experiment_region.loc == "end":
        db_experiment_update.plateau_end = experiment_region.new_value

    db.add(db_experiment_update)
    db.commit()
    db.refresh(db_experiment_update)
    return db_experiment_update

def get_experiment(db: Session, exp_id: int):
    return db.query(models.Experiment).filter(models.Experiment.id == exp_id).first()


def create_experiment(db: Session, experiment: schemas.ExperimentCreate, user: schemas.User):
    db_experiment = models.Experiment(**experiment.dict())
    db_experiment.doctor_id = user.id
    db.add(db_experiment)
    db.commit()
    db.refresh(db_experiment)
    return db_experiment

def set_experiment_region(db: Session, exp_id:int, baseline_start: int,baseline_end: int,transient_start: int,transient_end: int,plateau_start: int, plateau_end: int) :

    db_experiment_update = db.query(models.Experiment).filter(models.Experiment.id == exp_id).first()

    db_experiment_update.baseline_start=baseline_start
    db_experiment_update.baseline_end=baseline_end
    db_experiment_update.transient_start=transient_start
    db_experiment_update.transient_end=transient_end
    db_experiment_update.plateau_start=plateau_start
    db_experiment_update.plateau_end=plateau_end

    db.add(db_experiment_update)
    db.commit()
    db.refresh(db_experiment_update)
    return db_experiment_update



def set_experiment_result(db: Session, exp_id: int,result_json: str):
    db_experiment_update = db.query(models.Experiment).filter(models.Experiment.id == exp_id).first();

    db_experiment_update.result_json = result_json

    db.add(db_experiment_update)
    db.commit()
    db.refresh(db_experiment_update)
    return db_experiment_update


def get_signals(db: Session, exp_id: int,time_e: int=9999999999,time_s: int=0,skip_v:int=1, skip: int = 0, limit: int = 30000):
    return db.query(models.Signal).filter(models.Signal.exp_id == exp_id).filter(or_(models.Signal.code == "ABP" , models.Signal.code == "ICP"))\
        .filter(models.Signal.time >= time_s)\
        .filter(models.Signal.time <= time_e) \
        .filter(models.Signal.serial % skip_v == 0) \
        .offset(skip).limit(limit).all()

def get_signal(db: Session, code:str, exp_id: int,time_e: int=9999999999,time_s: int=0, skip_v:int=1, skip: int = 0, limit: int = 30000):
    return db.query(models.Signal).filter(models.Signal.exp_id == exp_id).filter(models.Signal.code == code)\
        .filter(models.Signal.time >= time_s)\
        .filter(models.Signal.time <= time_e) \
        .filter(models.Signal.serial % skip_v == 0) \
        .offset(skip).limit(limit).all()


def get_signal_lasttime(db: Session, exp_id: int, signal: str):
    rs=db.query(models.Signal).filter(models.Signal.exp_id == exp_id).filter(models.Signal.code == signal).order_by(
        models.Signal.time.desc()).first()
    if not rs:
        return 0
    else:
       return rs.time


def get_signal_firsttime(db: Session, exp_id: int, signal: str):
    rs=db.query(models.Signal).filter(models.Signal.exp_id == exp_id).filter(models.Signal.code == signal).order_by(
        models.Signal.time).first()
    if not rs:
        return 0
    else:
       return rs.time






def create_signal(db: Session, signal_list: List[schemas.SignalCreate]):

#    db_signal_list = []
#    for signal in signal_list:
#        db_signal = models.Signal(**signal.dict())
#        db_signal_list.append(db_signal)
#
#    db.add_all(db_signal_list)
#    db.commit()
    conn = pymysql.connect(host='dbneurotx.cp78dfskizh3.ap-northeast-2.rds.amazonaws.com', port=3306, user='admin',
                       password='zxc~!2051801', db='test', charset='utf8')
    curs = conn.cursor(pymysql.cursors.DictCursor)
    for signal in signal_list:
        sql = "insert into infusion_signals (exp_id,code,time,v,memo) values(%s,%s,%s,%s,%s)"
        curs.execute(sql, (signal.exp_id, signal.code, signal.time, signal.v, signal.memo))

    conn.commit()

    return True





def get_artifacts(db: Session, exp_id: int,time_e: int=9999999999,time_s: int=0, skip: int = 0, limit: int = 100):
    return db.query(models.Artifact).filter(models.Artifact.exp_id == exp_id)\
        .filter(models.Artifact.e_time >= time_s)\
        .filter(models.Artifact.s_time <= time_e)\
        .offset(skip).limit(limit).all()


def create_artifact(db: Session, artifact: schemas.ArtifactCreate):

    db_artifact = models.Artifact(**artifact.dict())
    db.add(db_artifact)
    db.commit()
    db.refresh(db_artifact)
    return db_artifact


def update_artifact(db: Session, artifact_update:schemas.ArtifactUpdate):
    db_artifact_update = db.query(models.Artifact).filter(models.Artifact.serial == artifact_update.serial).first()
    if artifact_update.loc == "start":
        db_artifact_update.s_time = artifact_update.new_value

    if artifact_update.loc == "end":
        db_artifact_update.e_time = artifact_update.new_value

    db.add(db_artifact_update)
    db.commit()
    db.refresh(db_artifact_update)
    return db_artifact_update


def delete_artifact(db: Session, serial:int):
    db_artifact_delete = db.query(models.Artifact).filter(models.Artifact.serial == serial).first()
    if db_artifact_delete:
        db.delete(db_artifact_delete)
        db.commit()
    return True


def get_sd1_func(pleth_signal):
    sampling_rate = 125  # data sampling rate

    # PPG로 분석할 경우
    peaks, _ = find_peaks(pleth_signal, distance=sampling_rate * (30 / 60))

    # ECG로 분석할 경우
    # signal, peaks = biosppy.signals.ecg.ecg(data, sampling_rate=sampling_rate, show=False)[1:3]

    nni = tools.nn_intervals(peaks)
    result_list = pyhrv.time_domain.nni_parameters(nni=nni)
    result_dict = result_list.as_dict()

    return float(result_dict['nni_min'])


def get_sampling_rate(signal_list):
    # Get random N point of time
    inverse_interval_list = []
    rand_point_num = 100
    rand_idx_list = np.random.randint(0, len(signal_list) - 1, rand_point_num)
    for rand_idx in rand_idx_list:
        # Calculate differences from after point
        time_interval = signal_list[rand_idx + 1]['x'] - signal_list[rand_idx]['x']
        # Invert a time interval to get the sample rate
        inverse_interval_list.append(time_interval)
    # After take average, trim to match data type
    non_trimed_sampling_rate = np.mean(inverse_interval_list)
    sampling_rate = int(1000 / non_trimed_sampling_rate)
    return sampling_rate


def convert_xy_to_y(signal_list):
    # Convert [{'x':time1, 'y':value1}, {'x':time2, 'y':value2}, ...] to [value1, value2, ...]
    xy_to_y = lambda obj: obj['y']
    signal_y_arr = np.array(list(map(xy_to_y, signal_list)))
    return signal_y_arr


def convert_xy_to_x(signal_list):
    # Convert [{'x':time1, 'y':value1}, {'x':time2, 'y':value2}, ...] to [time1, time2, ...]
    xy_to_x = lambda obj: obj['x']
    signal_x_arr = np.array(list(map(xy_to_x, signal_list)))
    return signal_x_arr


def remove_artifact(signal_list, artifact_list):
    signal_x_arr = convert_xy_to_x(signal_list)
    signal_y_arr = convert_xy_to_y(signal_list)
    for atf in artifact_list:
        sss = np.where(signal_x_arr == atf[0])
        atf_start_idx = sss[0][0]
        eee = np.where(signal_x_arr == atf[1])
        atf_end_idx = eee[0][0]
        signal_y_arr[atf_start_idx:atf_end_idx] = np.linspace(signal_y_arr[atf_start_idx], signal_y_arr[atf_end_idx],
                                                              atf_end_idx - atf_start_idx)
    signal_x_y_list = np.stack([signal_x_arr, signal_y_arr]).T
    to_obj_list = lambda obj: {'x': obj[0], 'y': obj[1]}
    signal_list = list(map(to_obj_list, signal_x_y_list))
    return signal_list


def get_mean_value_every_10_sec(signal_list):
    """
    Average signal every 'averaged_sec'
    """

    sampling_rate = get_sampling_rate(signal_list)
    averaged_sec = 10
    averaged_window_size = sampling_rate * averaged_sec

    signal_y_arr = convert_xy_to_y(signal_list)

    mean_list = []
    for i in range(0, len(signal_y_arr) - averaged_window_size + 1, averaged_window_size):
        mean_value = np.mean(signal_y_arr[i:i + averaged_window_size])
        mean_list.append(mean_value)
    mean_arr = np.array(mean_list)
    return mean_arr


def get_CPP_func(ABP_list, ICP_list):
    """
    Calculate CPP with mean(ABP-ICP)
    window size: 10 seconds
    update period: 10 seconds
    """

    ABP_y_arr = convert_xy_to_y(ABP_list)
    ICP_y_arr = convert_xy_to_y(ICP_list)

    CPP_y_value = np.mean(ABP_y_arr - ICP_y_arr)

    CPP = {'x': None, 'y': None}
    CPP['x'] = ABP_list[-1]['x']
    CPP['y'] = CPP_y_value
    return CPP


def get_CPP_arr_func(ABP_list, ICP_list, ABP_atf_list, ICP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    averaged_sec = 10
    averaged_window_size = sampling_rate * averaged_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)
    ICP_list = remove_artifact(ICP_list, ICP_atf_list)

    CPP_list = []
    for i in range(0, len(ABP_list) - averaged_window_size + 1, averaged_window_size):
        CPP = get_CPP_func(ABP_list[i: i + averaged_window_size], ICP_list[i: i + averaged_window_size])
        CPP_list.append(CPP)
    CPP_arr = np.array(CPP_list)
    return CPP_arr


def get_AMP_func(ICP_list):
    """
    Calculate AMP with FFT
    window size: 10 seconds
    update period: 10 seconds
    """

    ICP_y_arr = convert_xy_to_y(ICP_list)

    ICP_len = len(ICP_y_arr)
    yf = fft(ICP_y_arr)
    phase = fftshift(yf)[ICP_len // 2 + 1:]
    AMP_y_value = np.max(1.0 / ICP_len * np.abs(phase))

    AMP = {'x': None, 'y': None}
    AMP['x'] = ICP_list[-1]['x']
    AMP['y'] = AMP_y_value
    return AMP


def get_AMP_arr_func(ICP_list, ICP_atf_list):
    sampling_rate = get_sampling_rate(ICP_list)
    averaged_sec = 10
    averaged_window_size = sampling_rate * averaged_sec

    ICP_list = remove_artifact(ICP_list, ICP_atf_list)

    AMP_list = []
    for i in range(0, len(ICP_list) - averaged_window_size + 1, averaged_window_size):
        AMP = get_AMP_func(ICP_list[i: i + averaged_window_size])
        AMP_list.append(AMP)
    AMP_arr = np.array(AMP_list)
    return AMP_arr


def get_PRx_func(ABP_list, ICP_list):
    """
    Calculate PRx with pearson correlation between mean ABP and mean ICP
    window size: 300 seconds
    update period: 10 seconds
    """

    mean_ABP_arr = get_mean_value_every_10_sec(ABP_list)
    mean_ICP_arr = get_mean_value_every_10_sec(ICP_list)

    PRx_y_value = np.corrcoef(mean_ABP_arr, mean_ICP_arr)[0][1]

    PRx = {'x': None, 'y': None}
    PRx['x'] = ABP_list[-1]['x']
    PRx['y'] = PRx_y_value
    return PRx


def get_PRx_arr_func(ABP_list, ICP_list, ABP_atf_list, ICP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)
    ICP_list = remove_artifact(ICP_list, ICP_atf_list)

    PRx_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        PRx = get_PRx_func(ABP_list[i: i + window_size], ICP_list[i: i + window_size])
        PRx_list.append(PRx)
    PRx_arr = np.array(PRx_list)
    return PRx_arr


def get_PAx_func(ABP_list, ICP_list):
    """
    Calculate PAx with pearson correlation between AMP and mean ABP
    window size: 300 seconds
    update period: 10 seconds
    """

    ICP_AMP_arr = get_AMP_arr_func(ICP_list, [])
    ICP_AMP_y_arr = convert_xy_to_y(ICP_AMP_arr)
    mean_ABP_arr = get_mean_value_every_10_sec(ABP_list)

    PAx_y_value = np.corrcoef(mean_ABP_arr, ICP_AMP_y_arr)[0][1]

    PAx = {'x': None, 'y': None}
    PAx['x'] = ABP_list[-1]['x']
    PAx['y'] = PAx_y_value
    return PAx


def get_PAx_arr_func(ABP_list, ICP_list, ABP_atf_list, ICP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)
    ICP_list = remove_artifact(ICP_list, ICP_atf_list)

    PAx_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        PAx = get_PAx_func(ABP_list[i: i + window_size], ICP_list[i: i + window_size])
        PAx_list.append(PAx)
    PAx_arr = np.array(PAx_list)
    return PAx_arr


def get_RAP_func(ABP_list, ICP_list):
    """
    Calculate RAP with pearson correlation between AMP and mean ICP
    window size: 300 seconds
    update period: 10 seconds
    """

    ICP_AMP_arr = get_AMP_arr_func(ICP_list, [])
    ICP_AMP_y_arr = convert_xy_to_y(ICP_AMP_arr)
    mean_ICP_arr = get_mean_value_every_10_sec(ICP_list)

    RAP_y_value = np.corrcoef(mean_ICP_arr, ICP_AMP_y_arr)[0][1]

    RAP = {'x': None, 'y': None}
    RAP['x'] = ABP_list[-1]['x']
    RAP['y'] = RAP_y_value
    return RAP


def get_RAP_arr_func(ABP_list, ICP_list, ABP_atf_list, ICP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)
    ICP_list = remove_artifact(ICP_list, ICP_atf_list)

    RAP_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        RAP = get_RAP_func(ABP_list[i: i + window_size], ICP_list[i: i + window_size])
        RAP_list.append(RAP)
    RAP_arr = np.array(RAP_list)
    return RAP_arr


def get_RAC_func(ABP_list, ICP_list):
    """
    Calculate RAC with pearson correlation between AMP and CPP
    window size: 300 seconds
    update period: 10 seconds
    """

    ICP_AMP_arr = get_AMP_arr_func(ICP_list, [])
    ICP_AMP_y_arr = convert_xy_to_y(ICP_AMP_arr)
    CPP_arr = get_CPP_arr_func(ABP_list, ICP_list, [], [])
    CPP_y_arr = convert_xy_to_y(CPP_arr)

    RAC_y_value = np.corrcoef(CPP_y_arr, ICP_AMP_y_arr)[0][1]

    RAC = {'x': None, 'y': None}
    RAC['x'] = ABP_list[-1]['x']
    RAC['y'] = RAC_y_value
    return RAC


def get_RAC_arr_func(ABP_list, ICP_list, ABP_atf_list, ICP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)
    ICP_list = remove_artifact(ICP_list, ICP_atf_list)

    RAC_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        RAC = get_RAC_func(ABP_list[i: i + window_size], ICP_list[i: i + window_size])
        RAC_list.append(RAC)
    RAC_arr = np.array(RAC_list)
    return RAC_arr


def get_wICP_func(ABP_list, ICP_list):
    """
    Calculate RAP with mean ICP * (1 - RAP)
    window size: 300 seconds
    update period: 10 seconds
    """

    RAP = get_RAP_func(ABP_list, ICP_list)
    RAP_y_value = RAP['y']
    mean_ICP_arr = get_mean_value_every_10_sec(ICP_list)
    last_mean_ICP = mean_ICP_arr[-1]

    wICP_y_value = last_mean_ICP * (1 - RAP_y_value)

    wICP = {'x': None, 'y': None}
    wICP['x'] = ABP_list[-1]['x']
    wICP['y'] = wICP_y_value
    return wICP


def get_wICP_arr_func(ABP_list, ICP_list, ABP_atf_list, ICP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)
    ICP_list = remove_artifact(ICP_list, ICP_atf_list)

    wICP_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        wICP = get_wICP_func(ABP_list[i: i + window_size], ICP_list[i: i + window_size])
        wICP_list.append(wICP)
    wICP_arr = np.array(wICP_list)
    return wICP_arr


def timeout(timeout):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            res = [Exception('function [%s] timeout [%s seconds] exceeded!' % (func.__name__, timeout))]

            def newFunc():
                try:
                    res[0] = func(*args, **kwargs)
                except Exception as e:
                    res[0] = e

            t = Thread(target=newFunc)
            t.daemon = True
            try:
                t.start()
                t.join(timeout)
            except Exception as je:
                print('error starting thread')
                raise je
            ret = res[0]
            if isinstance(ret, BaseException):
                raise ret
            return ret

        return wrapper

    return deco


def get_nni_mean_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_nni_mean = timeout(timeout=1)(pyhrv.time_domain.nni_parameters)
    try:
        nni_mean_y_value = get_nni_mean(nni=nni)['nni_mean']
    except:
        print('[Time out] get_nni_mean')
        nni_mean_y_value = np.nan

    nni_mean = {'x': None, 'y': None}
    nni_mean['x'] = ABP_list[-1]['x']
    nni_mean['y'] = nni_mean_y_value
    return nni_mean


def get_nni_mean_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    nni_mean_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        nni_mean = get_nni_mean_func(ABP_list[i: i + window_size])
        nni_mean_list.append(nni_mean)
    nni_mean_arr = np.array(nni_mean_list)
    return nni_mean_arr


def get_sdnn_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_sdnn = timeout(timeout=1)(pyhrv.time_domain.sdnn)
    try:
        sdnn_y_value = get_sdnn(nni=nni)['sdnn']
    except:
        print('[Time out] get_sdnn')
        sdnn_y_value = np.nan

    sdnn = {'x': None, 'y': None}
    sdnn['x'] = ABP_list[-1]['x']
    sdnn['y'] = sdnn_y_value
    return sdnn


def get_sdnn_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    sdnn_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        sdnn = get_sdnn_func(ABP_list[i: i + window_size])
        sdnn_list.append(sdnn)
    sdnn_arr = np.array(sdnn_list)
    return sdnn_arr


def get_rmssd_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_rmssd = timeout(timeout=1)(pyhrv.time_domain.rmssd)
    try:
        rmssd_y_value = get_rmssd(nni=nni)['rmssd']
    except:
        print('[Time out] get_rmssd')
        rmssd_y_value = np.nan

    rmssd = {'x': None, 'y': None}
    rmssd['x'] = ABP_list[-1]['x']
    rmssd['y'] = rmssd_y_value
    return rmssd


def get_rmssd_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    rmssd_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        rmssd = get_rmssd_func(ABP_list[i: i + window_size])
        rmssd_list.append(rmssd)
    rmssd_arr = np.array(rmssd_list)
    return rmssd_arr


def get_sdsd_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_sdsd = timeout(timeout=1)(pyhrv.time_domain.sdsd)
    try:
        sdsd_y_value = get_sdsd(nni=nni)['sdsd']
    except:
        print('[Time out] get_sdsd')
        sdsd_y_value = np.nan

    sdsd = {'x': None, 'y': None}
    sdsd['x'] = ABP_list[-1]['x']
    sdsd['y'] = sdsd_y_value
    return sdsd


def get_sdsd_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    sdsd_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        sdsd = get_sdsd_func(ABP_list[i: i + window_size])
        sdsd.append(sdsd)
    sdsd_arr = np.array(sdsd_list)
    return sdsd_arr


def get_pnn50_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_nn50 = timeout(timeout=1)(pyhrv.time_domain.nn50)
    try:
        pnn50_y_value = get_nn50(nni=nni)['pnn50']
    except:
        print('[Time out] get_nn50')
        pnn50_y_value = np.nan

    pnn50 = {'x': None, 'y': None}
    pnn50['x'] = ABP_list[-1]['x']
    pnn50['y'] = pnn50_y_value
    return pnn50


def get_pnn50_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    pnn50_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        pnn50 = get_pnn50_func(ABP_list[i: i + window_size])
        pnn50.append(pnn50)
    pnn50_arr = np.array(pnn50_list)
    return pnn50_arr


def get_pnn20_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_nn20 = timeout(timeout=1)(pyhrv.time_domain.nn20)
    try:
        pnn20_y_value = get_nn20(nni=nni)['pnn20']
    except:
        print('[Time out] get_nn20')
        pnn20_y_value = np.nan

    pnn20 = {'x': None, 'y': None}
    pnn20['x'] = ABP_list[-1]['x']
    pnn20['y'] = pnn20_y_value
    return pnn20


def get_pnn20_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    pnn20_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        pnn20 = get_pnn20_func(ABP_list[i: i + window_size])
        pnn20.append(pnn20)
    pnn20_arr = np.array(pnn20_list)
    return pnn20_arr


def get_vlf_abs_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_frequency_hrv_parameter = timeout(timeout=1)(pyhrv.frequency_domain.welch_psd)
    try:
        vlf_abs_y_value = get_frequency_hrv_parameter(nni=nni, show=False, legend=False)['fft_abs'][0]
    except:
        print('[Time out] get_frequency_hrv_parameter')
        vlf_abs_y_value = np.nan

    vlf_abs = {'x': None, 'y': None}
    vlf_abs['x'] = ABP_list[-1]['x']
    vlf_abs['y'] = vlf_abs_y_value
    return vlf_abs


def get_vlf_abs_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    vlf_abs_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        vlf_abs = get_vlf_abs_func(ABP_list[i: i + window_size])
        vlf_abs_list.append(vlf_abs)
    vlf_abs_arr = np.array(vlf_abs_list)
    return vlf_abs_arr


def get_lf_abs_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_frequency_hrv_parameter = timeout(timeout=1)(pyhrv.frequency_domain.welch_psd)
    try:
        lf_abs_y_value = get_frequency_hrv_parameter(nni=nni, show=False, legend=False)['fft_abs'][1]
    except:
        print('[Time out] get_frequency_hrv_parameter')
        lf_abs_y_value = np.nan

    lf_abs = {'x': None, 'y': None}
    lf_abs['x'] = ABP_list[-1]['x']
    lf_abs['y'] = lf_abs_y_value
    return lf_abs


def get_lf_abs_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    lf_abs_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        lf_abs = get_lf_abs_func(ABP_list[i: i + window_size])
        lf_abs_list.append(lf_abs)
    lf_abs_arr = np.array(lf_abs_list)
    return lf_abs_arr


def get_hf_abs_func(ABP_list):
    """
    window size: 300 seconds
    update period: 10 seconds
    """
    sampling_rate = get_sampling_rate(ABP_list)
    half_of_second = sampling_rate * (30 / 60)
    ABP_y_arr = convert_xy_to_y(ABP_list)

    peaks, _ = find_peaks(ABP_y_arr, distance=half_of_second)
    peaks = peaks[1: -1] if len(peaks) > 5 else peaks
    nni = tools.nn_intervals(peaks)

    get_frequency_hrv_parameter = timeout(timeout=1)(pyhrv.frequency_domain.welch_psd)
    try:
        hf_abs_y_value = get_frequency_hrv_parameter(nni=nni, show=False, legend=False)['fft_abs'][2]
    except:
        print('[Time out] get_frequency_hrv_parameter')
        hf_abs_y_value = np.nan

    hf_abs = {'x': None, 'y': None}
    hf_abs['x'] = ABP_list[-1]['x']
    hf_abs['y'] = hf_abs_y_value
    return hf_abs



def get_hf_abs_arr_func(ABP_list, ABP_atf_list):
    sampling_rate = get_sampling_rate(ABP_list)
    window_sec = 300
    window_size = sampling_rate * window_sec
    update_sec = 10
    update_period = sampling_rate * update_sec

    ABP_list = remove_artifact(ABP_list, ABP_atf_list)

    hf_abs_list = []
    for i in range(0, len(ABP_list) - window_size + 1, update_period):
        hf_abs = get_hf_abs_func(ABP_list[i: i + window_size])
        hf_abs_list.append(hf_abs)
    hf_abs_arr = np.array(hf_abs_list)
    return hf_abs_arr


def get_ICP_AMP_point_and_linear_fitting_line_func(ICP_list, transient_start, transient_end):
    ICP_x_arr = convert_xy_to_x(ICP_list)
    transient_start_idx = np.where(ICP_x_arr == transient_start)[0][0]
    transient_end_idx = np.where(ICP_x_arr == transient_end)[0][0]

    transient_ICP_arr = ICP_list[transient_start_idx:transient_end_idx]
    transient_mean_ICP_arr = get_mean_value_every_10_sec(transient_ICP_arr)

    transient_AMP_arr = get_AMP_arr_func(transient_ICP_arr, [])
    transient_AMP_y_arr = convert_xy_to_y(transient_AMP_arr)

    numpy_to_obj_list = lambda obj: {'x': obj[0], 'y': obj[1]}
    ICP_AMP_point_arr = np.stack([transient_mean_ICP_arr, transient_AMP_y_arr]).T
    ICP_AMP_point_obj_list = list(map(numpy_to_obj_list, ICP_AMP_point_arr))
    a, b = np.polyfit(transient_mean_ICP_arr, transient_AMP_y_arr, 1)
    return ICP_AMP_point_obj_list, a, b


def get_fitting_curve_between_infused_volume_pss(ICP_list, baseline_start, baseline_end, transient_start, transient_end, plateau_start, plateau_end, infusion_rate):
    sampling_rate = get_sampling_rate(ICP_list)
    window_sec = 10
    window_size = sampling_rate * window_sec

    baseline_mean_ICP, _, plateau_mean_ICP, _ = get_baseline_plateau_mean_ICP_and_AMP_func(ICP_list, baseline_start, baseline_end, plateau_start, plateau_end)
    _, Pss, _ = get_Rcsf_Pss_CPR_func(ICP_list, baseline_start, baseline_end, plateau_start, plateau_end, infusion_rate)
    infused_volume, _, _ = get_infused_volume_elasticity_PVI_func(ICP_list, transient_start, transient_end, infusion_rate)

    ICP_x_arr = convert_xy_to_x(ICP_list)
    ICP_y_arr = convert_xy_to_y(ICP_list)

    transient_start_idx = np.where(ICP_x_arr == plateau_start)[0][0]
    transient_end_idx = np.where(ICP_x_arr == plateau_end)[0][0]

    p_pss_pb_pss = (ICP_y_arr - Pss) / (baseline_mean_ICP - Pss)
    p_pss_pb_pss_list = []
    for interval in range(transient_start_idx, transient_end_idx - window_size, window_size):
        p_pss_pb_pss_mean = np.mean(p_pss_pb_pss[interval:interval + window_size])
        p_pss_pb_pss_list.append(p_pss_pb_pss_mean)
    volume = np.linspace(0, infused_volume, len(p_pss_pb_pss_list))

    numpy_to_obj_list = lambda obj: {'x': obj[0], 'y': obj[1]}
    vol_pss_list = np.stack([volume, p_pss_pb_pss_list]).T
    vol_pss_obj_list = list(map(numpy_to_obj_list, vol_pss_list))

    a, b, c = np.polyfit(volume, p_pss_pb_pss_list, 2)
    return vol_pss_obj_list, a, b, c


def get_baseline_plateau_mean_ICP_and_AMP_func(ICP_list, baseline_start, baseline_end, plateau_start, plateau_end):
    ICP_x_arr = convert_xy_to_x(ICP_list)

    baseline_start_idx = find_nearest(ICP_x_arr, baseline_start)
    baseline_end_idx =find_nearest(ICP_x_arr, baseline_end)
    plateau_start_idx =find_nearest(ICP_x_arr, plateau_start)
    plateau_end_idx =find_nearest(ICP_x_arr, plateau_end)

#    baseline_start_idx = np.where(ICP_x_arr == baseline_start)[0][0]
#    baseline_end_idx = np.where(ICP_x_arr == baseline_end)[0][0]
#    plateau_start_idx = np.where(ICP_x_arr == plateau_start)[0][0]
#    plateau_end_idx = np.where(ICP_x_arr == plateau_end)[0][0]

    baseline_ICP_arr = ICP_list[baseline_start_idx:baseline_end_idx]
    baseline_AMP_arr = get_AMP_arr_func(baseline_ICP_arr, [])
    plateau_ICP_arr = ICP_list[plateau_start_idx:plateau_end_idx]
    plateau_AMP_arr = get_AMP_arr_func(plateau_ICP_arr, [])

    baseline_ICP_y_arr = convert_xy_to_y(baseline_ICP_arr)
    baseline_AMP_y_arr = convert_xy_to_y(baseline_AMP_arr)
    plateau_ICP_y_arr = convert_xy_to_y(plateau_ICP_arr)
    plateau_AMP_y_arr = convert_xy_to_y(plateau_AMP_arr)

    baseline_mean_ICP = np.mean(baseline_ICP_y_arr)
    baseline_mean_AMP = np.mean(baseline_AMP_y_arr)
    plateau_mean_ICP = np.mean(plateau_ICP_y_arr)
    plateau_mean_AMP = np.mean(plateau_AMP_y_arr)
    return baseline_mean_ICP, baseline_mean_AMP, plateau_mean_ICP, plateau_mean_AMP


def get_Rcsf_Pss_CPR_func(ICP_list, baseline_start, baseline_end, plateau_start, plateau_end, infusion_rate):
    baseline_mean_ICP, _, plateau_mean_ICP, _ = get_baseline_plateau_mean_ICP_and_AMP_func(ICP_list, baseline_start, baseline_end, plateau_start, plateau_end)
    Rcsf = (plateau_mean_ICP - baseline_mean_ICP) / infusion_rate
    slope = 1 / Rcsf
    constant = 1 - slope * plateau_mean_ICP
    Pss = -1 * (constant / slope) / 2
    ICP_y_arr = convert_xy_to_y(ICP_list)
    csf_production_rate = np.abs(np.mean(ICP_y_arr - Pss) / Rcsf)
    return Rcsf, Pss, csf_production_rate


def get_infused_volume_elasticity_PVI_func(ICP_list, transient_start, transient_end, infusion_rate):
    def logistic(x, a, b, c, d):
        return ((a - d) / (1.0 + ((x / c) ** b))) + d

    sampling_rate = get_sampling_rate(ICP_list)
    sampling_frequency = 1 / sampling_rate
    ICP_x_arr = convert_xy_to_x(ICP_list)
    ICP_y_arr = convert_xy_to_y(ICP_list)
    ICP_len = len(ICP_list)

    transient_start_idx = np.where(ICP_x_arr == transient_start)[0][0]
    transient_end_idx = np.where(ICP_x_arr == transient_end)[0][0]

    transient_points_len = transient_end_idx - transient_start_idx
    infused_volume = transient_points_len * sampling_frequency * infusion_rate / 60

    x_sample_data = np.linspace(0, 1 / ICP_len, ICP_len)
    popt, _ = curve_fit(logistic, x_sample_data, ICP_y_arr, maxfev=10000)
    fitting_curve = logistic(x_sample_data, *popt)

    vol_icp = fitting_curve[transient_start_idx:transient_end_idx]
    vol_log_icp = np.log(fitting_curve)[transient_start_idx:transient_end_idx]

    interval = transient_points_len // 10
    interval_infusion_volume = infused_volume / 10
    elasticity_list = []
    PVI_list = []

    # calculate interval gradient
    for i in range(10):
        interval_vol_icp_data = vol_icp[interval * i:interval * (i + 1)]
        interval_vol_log_icp_data = vol_log_icp[interval * i:interval * (i + 1)]
        interval_elasticity = (max(interval_vol_icp_data) - min(interval_vol_icp_data)) / (interval_infusion_volume)
        interval_pvi = 1 / ((max(interval_vol_log_icp_data) - min(interval_vol_log_icp_data)) / (interval_infusion_volume))
        elasticity_list.append(interval_elasticity)
        PVI_list.append(interval_pvi)
    elasticity = np.mean(elasticity_list)
    PVI = np.mean(PVI_list)
    return infused_volume, elasticity, PVI


def infusion_test_analyzer(ABP_list, ICP_list,
                           baseline_start, baseline_end, transient_start, transient_end, plateau_start, plateau_end,
                           resistance_of_shunt, shunt_operating_pressure, infusion_rate, infusion_start, infusion_duration,
                           ABP_atf_list, ICP_atf_list):
    ABP_list = remove_artifact(ABP_list, ABP_atf_list)
    ICP_list = remove_artifact(ICP_list, ICP_atf_list)

    # for number output
    baseline_mean_ICP, baseline_mean_AMP, plateau_mean_ICP, plateau_mean_AMP = get_baseline_plateau_mean_ICP_and_AMP_func(ICP_list, baseline_start, baseline_end, plateau_start, plateau_end)
    Rcsf, Pss, csf_production_rate = get_Rcsf_Pss_CPR_func(ICP_list, baseline_start, baseline_end, plateau_start, plateau_end, infusion_rate)
    infused_volume, elasticity, PVI = get_infused_volume_elasticity_PVI_func(ICP_list, transient_start, transient_end, infusion_rate)

    # for signal derived index figure
    CPP_arr = get_CPP_arr_func(ABP_list, ICP_list, [], [])
    AMP_arr = get_AMP_arr_func(ICP_list, [])
    PRx_arr = get_PRx_arr_func(ABP_list, ICP_list, [], [])
    PAx_arr = get_PAx_arr_func(ABP_list, ICP_list, [], [])
    RAC_arr = get_RAC_arr_func(ABP_list, ICP_list, [], [])
    RAP_arr = get_RAP_arr_func(ABP_list, ICP_list, [], [])
    wICP_arr = get_wICP_arr_func(ABP_list, ICP_list, [], [])

    # for scatter with fitting line figure
    ICP_AMP_point_obj_list, ICP_AMP_a, ICP_AMP_b = get_ICP_AMP_point_and_linear_fitting_line_func(ICP_list, transient_start, transient_end)
    vol_pss_point_obj_list, a, b, c = get_fitting_curve_between_infused_volume_pss(ICP_list, baseline_start, baseline_end, transient_start, transient_end, plateau_start, plateau_end, infusion_rate)
    RAP_arr_n = [{'x':int(item["x"]),'y':float(item["y"])} for item in RAP_arr.tolist()]
    AMP_arr_n = [{'x':int(item["x"]),'y':float(item["y"])} for item in AMP_arr.tolist()]

    rt = {'RAP_arr':RAP_arr_n,'AMP_arr':AMP_arr_n,'baseline_mean_ICP': baseline_mean_ICP, 'baseline_mean_AMP': baseline_mean_AMP,'plateau_mean_ICP':plateau_mean_ICP, 'plateau_mean_AMP':plateau_mean_AMP,'Rcsf':Rcsf, 'Pss':Pss, 'csf_production_rate':csf_production_rate,'infused_volume':infused_volume, 'elasticity':elasticity, 'PVI':PVI,'ICP_AMP_point_obj_list':ICP_AMP_point_obj_list, 'ICP_AMP_a':ICP_AMP_a, 'ICP_AMP_b':ICP_AMP_b,'vol_pss_point_obj_list':vol_pss_point_obj_list, 'a':a, 'b':b, 'c':c}

    return rt
#    return baseline_mean_ICP, baseline_mean_AMP, plateau_mean_ICP, plateau_mean_AMP,Rcsf, Pss, csf_production_rate,infused_volume, elasticity, PVI,AMP_arr,ICP_AMP_point_obj_list, a, b,vol_pss_point_obj_list, a, b, c


