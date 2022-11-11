from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime, Float,Numeric,BigInteger, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


from .database import Base




class Protocol(Base):
    __tablename__ = "stimulus_protocol"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"))

    title = Column(String(500))
    desc = Column(String(3500), nullable=True)
    manager = Column(String(500), nullable=True)
    regdate = Column(DateTime(timezone=True), server_default=func.now())


class ProtocolExp(Base):
    __tablename__ = "stimulus_protocol_exp"
    id = Column(Integer, primary_key=True, index=True)
    proto_id = Column(Integer, ForeignKey("stimulus_protocol.id"))
    name = Column(String(500))
    gender = Column(String(1))
    birth = Column(String(8))
    diagnosis = Column(String(500))
    maxstimulus= Column(Integer)
    deviceinfo = Column(String(3500), nullable=True)
    desc = Column(String(3500), nullable=True)

    survey_link = Column(String(1500), nullable=True)
    agree_filename = Column(String(1500), nullable=True)
    exp_duration = Column(String(1500), nullable=True)
    regdate = Column(DateTime(timezone=True), server_default=func.now())


class ProtocolExpStimulus(Base):
    __tablename__ = "stimulus_protocol_exp_stimulus"
    serial = Column(BigInteger, primary_key=True)
    proto_exp_id = Column(Integer, ForeignKey("stimulus_protocol_exp.id"))
    intensity= Column(Integer)
    interval= Column(Integer)
    height= Column(Integer)
    long = Column(Integer)
    time = Column(BigInteger, index=True)
    regdate = Column(DateTime(timezone=True), server_default=func.now())


class ProtocolExpSignal(Base):
    __tablename__ = "stimulus_protocol_exp_signals"
    serial = Column(Integer, primary_key=True)
    proto_exp_id = Column(Integer, ForeignKey("stimulus_protocol_exp.id"))
    code = Column(String(10), index=True)
    time = Column(BigInteger, index=True)
    v = Column(Float)




class ProtocolExpEvent(Base):
    __tablename__ = "stimulus_protocol_exp_event"
    serial = Column(Integer, primary_key=True)
    proto_exp_id = Column(Integer, ForeignKey("stimulus_protocol_exp.id"))
    memo = Column(String(500), nullable=True)
    time = Column(BigInteger, index=True)
    regtime=Column(BigInteger)

class ProtocolExpTrigger(Base):
    __tablename__ = "stimulus_protocol_exp_trigger"
    serial = Column(Integer, primary_key=True)
    proto_exp_id = Column(Integer, ForeignKey("stimulus_protocol_exp.id"))
    time = Column(BigInteger, index=True)



"""
class StimulusSetting(Base):
    __tablename__ = "stimulus_protocol_exp_setting"
    serial = Column(BigInteger, primary_key=True)
    proto_exp_id = Column(Integer, ForeignKey("stimulus_protocol_exp.id"))
    intensity= Column(Integer)
    interval= Column(Integer)
    height= Column(Integer)
    regdate = Column(DateTime(timezone=True), server_default=func.now())

"""




class LicenseKey(Base):
    __tablename__ = "member_license"
    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String(200), unique=True)
    is_used = Column(Boolean, default=False)
    username = Column(String(200), nullable=True)
    used_from = Column(DateTime, nullable=True)
    regdate= Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(255), unique=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    hashed_password = Column(String(555))
    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)

    patients = relationship("Patient", back_populates="doctor")


class Signal(Base):
    __tablename__ = "infusion_signals"
    serial = Column(Integer, primary_key=True)
    exp_id = Column(Integer, ForeignKey("infusion_exp.id"), index=True)
    code = Column(String(10), index=True)
    time = Column(BigInteger, index=True)
    v = Column(Float)
    memo = Column(String(500), nullable=True)


class Artifact(Base):
    __tablename__ = "infusion_artifact"
    serial = Column(BigInteger, primary_key=True)
    exp_id = Column(Integer, ForeignKey("infusion_exp.id"))
    code = Column(String(10))
    s_time = Column(BigInteger)
    e_time = Column(BigInteger)


class Experiment(Base):
    __tablename__ = "infusion_exp"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"))
    patient_id = Column(Integer, ForeignKey("patient.id"))
    title = Column(String(500))
    start_time = Column(DateTime(timezone=True), nullable=True)
    signal_codes = Column(String(1000))
    duration = Column(Integer, default=0)

    baseline_start = Column(String(50), nullable=True)
    baseline_end = Column(String(50), nullable=True)
    transient_start = Column(String(50), nullable=True)
    transient_end = Column(String(50), nullable=True)
    plateau_start = Column(String(50), nullable=True)
    plateau_end = Column(String(50), nullable=True)
    result_json=Column(Text(4294000000), nullable=True)
    regdate = Column(DateTime(timezone=True), server_default=func.now())
    patient = relationship("Patient", back_populates="experiments")


class Patient(Base):
    __tablename__ = "patient"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(200))
    gender = Column(String(1))
    age = Column(Integer)
    weight = Column(Float)
    height = Column(Float)
    patient_object= Column(String(200))
    regdate= Column(DateTime(timezone=True), server_default=func.now())
    experiments = relationship("Experiment", back_populates="patient")
    doctor = relationship("User", back_populates="patients")