import time
from fastapi import FastAPI, HTTPException,Depends,status
from datetime import datetime
from schemas import Register,Login,Category
from database import get_db_connection
from database import init_db
from auth import create_token, get_current_user, hash_password, verify_password

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
            cur.execute("SELECT id, password ,role FROM users WHERE email=%s", (user.email,))
            result = cur.fetchone()
            if not result or not verify_password(user.password, result[1]):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            user_id = result[0]
            user_role = result[2]
            token = create_token(user_id,user_role)
            return {"message": "Login successful", "token": token}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/categories")
def create_category(category:Category, user:dict = Depends(get_current_user)):
    if user.get("user_role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )
    try:
        with get_db_connection() as cur:
            cur.execute(
                    """
                    INSERT INTO categories (user_id, name, description, is_active) 
                    VALUES (%s, %s, %s, %s) 
                    RETURNING id;
                    """, 
                    (
                        user["user_id"], 
                        category.name, 
                        category.description, 
                        True  
                    )
                )
            result = cur.fetchone()
            if result:
                return {"message": "Category created successfully", "id": result[0]}
            else:
                raise HTTPException(status_code=500, detail="Failed to create category")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   



