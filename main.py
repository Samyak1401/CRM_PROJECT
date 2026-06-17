import time
from fastapi import FastAPI, HTTPException,Depends
from datetime import datetime
from schemas import Register,Login
from database import get_db_connection
from database import init_db
from auth import create_token, hash_password, verify_password

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/register")
def register_user(user:Register):
    hashed_password=hash_password(user.password)
    try:
        with get_db_connection() as cur:
            cur.execute("INSERT INTO users (name, email,password,role,created_at,updated_at) VALUES (%s, %s, %s,%s,%s,%s) Returning id", (user.username, user.email, hashed_password,user.role,
                                                                                                                     datetime.now(),datetime.now()))
            return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
def login_user(user: Login):
    try:
        with get_db_connection() as cur:
            cur.execute("SELECT id, password FROM users WHERE email=%s", (user.email,))
            result = cur.fetchone()
            if not result or not verify_password(user.password, result[1]):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            user_id = result[0]
            token = create_token(user_id)
            return {"message": "Login successful", "token": token}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



