import os
import time
from dotenv import load_dotenv
from typing import Dict
from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException,FastAPI, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

#password hashing 
pwd_context= CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password:str) -> str:
    return pwd_context.hash(password)

def verify_password(user_password:str,db_hashed_password:str) -> bool:
    return pwd_context.verify(user_password,db_hashed_password)

def create_token(user_id:int) -> str:
              # colname: value  
    payload = {"user_id": user_id,"exp":time.time()+3600}
    token= jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return  token

def decode_jwt(token:str)->Dict[str, str]:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token if decoded_token["exp"]>=time.time() else None
    except:
        return None
        


security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    payload = decode_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["user_id"]