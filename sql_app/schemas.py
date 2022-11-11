from typing import List, Optional
from datetime import datetime, time, timedelta
from typing import Dict

from pydantic import BaseModel



class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None



class ProtocolExpBase(BaseModel):
    name: str
    gender: Optional[str]
    birth: Optional[str]
    diagnosis: Optional[str]
    deviceinfo: Optional[str]
    survey_link: Optional[str]
    agree_filename: Optional[str]
    exp_duration: Optional[str]

class ProtocolExpCreate(ProtocolExpBase):
    pass

class ProtocolExp(ProtocolExpBase):
    id: int
    proto_id: int
    regdate: Optional[datetime]


    class Config:
        orm_mode = True



class ProtocolBase(BaseModel):
    title: str
    desc: Optional[str]
    manager: Optional[str]

class ProtocolCreate(ProtocolBase):
    pass

class Protocol(ProtocolBase):
    id: int
    doctor_id: int
    regdate: Optional[datetime]


    class Config:
        orm_mode = True

class ProtocolUpdate(BaseModel):
    id: int
    title: Optional[str]
    desc: Optional[str]
    manager: Optional[str]
    doctor_id: Optional[int]


class ProtocolExpUpdate(BaseModel):
    id: int
    name: Optional[str]
    gender: Optional[str]
    birth: Optional[str]
    diagnosis: Optional[str]
    desc: Optional[str]
    deviceinfo: Optional[str]
    survey_link: Optional[str]
    agree_filename: Optional[str]
    exp_duration: Optional[str]
    maxstimulus: Optional[int]


class ProtocolExpBase(BaseModel):
    proto_id: int
    name: Optional[str]
    gender: Optional[str]
    birth: Optional[str]
    diagnosis: Optional[str]
    desc: Optional[str]
    deviceinfo: Optional[str]
    survey_link: Optional[str]
    agree_filename: Optional[str]
    exp_duration: Optional[str]
    maxstimulus: Optional[int]


class ProtocolExpCreate(ProtocolExpBase):
    pass


class ProtocolExp(ProtocolExpBase):
    id: int
    regdate: Optional[datetime]

    class Config:
        orm_mode = True



class ProtocolExpStimulusBase(BaseModel):
    proto_exp_id: int
    intensity: int
    interval: int
    height: int
    long: int
    time: int

    class Config:
        orm_mode = True


class ProtocolExpStimulusCreate(ProtocolExpStimulusBase):
    pass


class ProtocolExpStimulus(ProtocolExpStimulusBase):
    serial: int
    regdate: Optional[datetime]
    class Config:
        orm_mode = True


class ProtocolExpSignalBase(BaseModel):
    proto_exp_id: int
    code: str
    time: int
    v: float
    class Config:
        orm_mode = True


class ProtocolExpSignalCreate(ProtocolExpSignalBase):
    pass

class ProtocolExpSignal(ProtocolExpSignalBase):
    serial: int
    class Config:
        orm_mode = True

class ProtocolExpSignal_Simple(BaseModel):
    k: str
    v: str
    class Config:
        orm_mode = True


class ProtocolExpTriggerBase(BaseModel):
    proto_exp_id: int
    time : int
    class Config:
        orm_mode = True


class ProtocolExpTriggerCreate(ProtocolExpTriggerBase):
    pass


class ProtocolExpTrigger(ProtocolExpTriggerBase):
    serial: int
    regdate: Optional[datetime]
    class Config:
        orm_mode = True



class ProtocolExpEventBase(BaseModel):
    proto_exp_id: Optional[int]
    time : Optional[int]
    regtime : Optional[int]
    memo: Optional[str]
    class Config:
        orm_mode = True


class ProtocolExpEventCreate(ProtocolExpEventBase):
    pass


class ProtocolExpEvent(ProtocolExpEventBase):
    serial: int
    regdate: Optional[datetime]
    class Config:
        orm_mode = True


class StimulusSettingBase(BaseModel):
    proto_exp_id: int
    intensity: int
    interval: int
    height: int
    class Config:
        orm_mode = True


class StimulusSettingCreate(StimulusSettingBase):
    pass


class StimulusSetting(StimulusSettingBase):
    serial: int
    regdate: Optional[datetime]
    class Config:
        orm_mode = True


class SignalBase(BaseModel):
    exp_id: int
    code: str
    time: int
    v: float
    memo: Optional[str]
    class Config:
        orm_mode = True

class SignalCreate(SignalBase):
    pass



class Signal(SignalBase):
    serial: int

    class Config:
        orm_mode = True


class ArtifactBase(BaseModel):
    exp_id: int
    code: str
    s_time: int
    e_time: int


class ArtifactCreate(ArtifactBase):
    pass


class Artifact(ArtifactBase):
    serial: int

    class Config:
        orm_mode = True

class ArtifactUpdate(BaseModel):
    serial: int
    loc: Optional[str]
    new_value: Optional[str]

class PatientBase(BaseModel):

    name: str
    gender: str
    age: int
    weight: float
    height: float
    patient_object: str


class PatientCreate(PatientBase):
    pass


class Patient(PatientBase):
    id: int
    doctor_id: int
    regdate: Optional[datetime]


    class Config:
        orm_mode = True


class ExperimentRegionUpdate(BaseModel):
    kind: Optional[str]
    loc: Optional[str]
    new_value: Optional[str]

class ExperimentBase(BaseModel):
    title: str

    patient_id: int
    baseline_start: Optional[str]
    baseline_end: Optional[str]
    transient_start: Optional[str]
    transient_end: Optional[str]
    plateau_start: Optional[str]
    plateau_end: Optional[str]
    result_json: Optional[str]
    start_time: Optional[datetime]
    signal_codes: Optional[str]
    duration: Optional[int]

class ExperimentCreate(ExperimentBase):
    pass

class Experiment(ExperimentBase):
    id: int
    doctor_id: int
    regdate: Optional[datetime]


    class Config:
        orm_mode = True

class ExperimentList(Experiment):
    patient: Patient
    class Config:
        orm_mode = True



class UserUpdate(BaseModel):
    id: int
    email: Optional[str]
    is_staff: Optional[bool]
    first_name: Optional[str]
    last_name: Optional[str]

class UserBase(BaseModel):
    email: str
    username: str
    is_staff: bool
    first_name: Optional[str]
    last_name: Optional[str]


class UserResponse(UserBase):

    class Config:
        orm_mode = True

class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    #hashed_password: str

    class Config:
        orm_mode = True


class LicenseKey(BaseModel):
    id: int
    license_key: str
    is_used: bool
    username: Optional[str]
    used_from: Optional[datetime]
    regdate: Optional[datetime]

    class Config:
        orm_mode = True


class SimpleSignal(BaseModel):
    x: int
    y: float


class TwoSignalList(BaseModel):
    signalList1: List[Dict[str, float]]
    signalList2: List[Dict[str, float]]


class OneSignalList(BaseModel):
    signalList: List[Dict[str, float]]


class InfusionInput(BaseModel):
    exp_id: int
    ABP_list: List[Dict[str, float]]
    ICP_list: List[Dict[str, float]]
    ABP_atf_list: List[Optional[List[int]]]
    ICP_atf_list: List[Optional[List[int]]]

    baseline_start: Optional[str]
    baseline_end: Optional[str]
    transient_start: Optional[str]
    transient_end: Optional[str]
    plateau_start: Optional[str]
    plateau_end: Optional[str]

    resistance_of_shunt: str
    shunt_operating_pressure: str

    infusion_rate: str
    infusion_duration: str
    infusion_start: int


class InfusionOutput(BaseModel):
    RAP_arr: List[SimpleSignal]
    AMP_arr: List[SimpleSignal]
    baseline_mean_ICP: float
    baseline_mean_AMP: float
    plateau_mean_ICP: float
    plateau_mean_AMP: float
    Rcsf: float
    Pss: float
    csf_production_rate: float
    infused_volume: float
    elasticity: float
    PVI: float
    ICP_AMP_point_obj_list: List[SimpleSignal]
    ICP_AMP_a: float
    ICP_AMP_b: float
    vol_pss_point_obj_list: List[SimpleSignal]
    a: float
    b: float
    c: float