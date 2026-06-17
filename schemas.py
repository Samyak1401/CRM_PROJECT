from pydantic import BaseModel
from typing import Optional



class Register(BaseModel):
    username: str
    email: str
    password: str
    role: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Login(BaseModel):
    email: str
    password: str