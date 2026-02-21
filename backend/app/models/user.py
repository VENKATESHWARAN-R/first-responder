from pydantic import BaseModel
from typing import List, Optional

class UserBase(BaseModel):
    email: str
    role: str = "viewer" # admin | viewer
    allowed_namespaces: List[str] = []
    theme_pref: str = "minimal" # minimal | neo-brutal

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str

    class Config:
        from_attributes = True

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
