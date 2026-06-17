from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Register(BaseModel):
    username: str
    email: str
    password: str
    role: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Login(BaseModel):
    email: str
    password: str

class Category(BaseModel):
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Ticket(BaseModel):
    title: str
    description: str
    category_id: int
    priority: str = "medium"
    status: str = "open"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class AssignTicket(BaseModel):
    assigned_to: int
    ticket_id: int

class UpdateStatus(BaseModel):
    status:str
    ticket_id:int