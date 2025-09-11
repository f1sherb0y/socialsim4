from typing import Optional, List

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    disabled: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_sso: Optional[bool] = None

    class Config:
        orm_mode = True


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
        orm_mode = True


class ProfilePlanReq(BaseModel):
    scenario: str
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

class StartReq(BaseModel):
    sim_code: str
    template_id: int
    providers: List[LLMConfig]

class LoadReq(BaseModel):
    sim_code: str
    providers: Optional[List[LLMConfig]] = None
