from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    institution: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    disabled: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_sso: Optional[bool] = None
    registration_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class SSOLoginRequest(BaseModel):
    appId: str
    username: str
    time: str
    sign: str


class ProviderBase(BaseModel):
    usage: str
    kind: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stream: Optional[bool] = None


class ProviderCreate(ProviderBase):
    pass


class Provider(ProviderBase):
    class Config:
        from_attributes = True


class ProfilePlanReq(BaseModel):
    scene: str
    request: str
    agent_count: int


class ProfilesReq(BaseModel):
    plan: str


class FeedbackCreate(BaseModel):
    feedback: str


class FeedbackAdminResponse(BaseModel):
    id: int
    user_username: str
    user_email: str
    feedback_text: str
    timestamp: str


class LLMConfig(BaseModel):
    name: str
    kind: str
    model: str
    dialect: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stream: Optional[bool] = False


class Agent(BaseModel):
    name: str
    user_profile: str
    style: str
    initial_instruction: str
    role_prompt: str
    action_space: List[str]
    max_repeat: Optional[int] = None
    properties: Optional[dict] = {}


class Template(BaseModel):
    simCode: str
    events: List[dict]
    personas: List[Agent]
    meta: dict
    workflow: dict
    template_json: str


class StartReq(BaseModel):
    sim_code: str
    template: Template
    providers: List[LLMConfig]
    initial_rounds: Optional[int] = 1


class LoadReq(BaseModel):
    sim_code: str
    providers: Optional[List[LLMConfig]] = None
