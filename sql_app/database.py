from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


#SQLALCHEMY_DATABASE_URL = "mysql+pymysql://admin:zxc~!2051801@dbneurotx.cp78dfskizh3.ap-northeast-2.rds.amazonaws.com:3306/test"
DB_IP="34.64.140.125"
DB_ID="root"
DB_PASS="neurotx1!"
DB_BASE="test"
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://"+DB_ID+":"+DB_PASS+"@"+DB_IP+":3306/"+DB_BASE





engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()