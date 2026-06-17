import time
from fastapi import FastAPI, HTTPException,Depends,status
from datetime import datetime
from schemas import *
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

@app.get("/fetch/categories")
def get_categories(user:dict = Depends(get_current_user)):
    if user.get("user_role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )
    try:
        with get_db_connection() as cur:
            cur.execute("SELECT * FROM categories")
            result=cur.fetchall()
            if result:
                categories = []
                for row in result:
                    categories.append({
                        "category_id": row[0],
                        "user_id": row[1],
                        "name": row[2],
                        "description": row[3],
                        "is_active": row[4],
                        "created_at": row[5],
                        "updated_at": row[6]
                    })

                return categories
    except HTTPException as e:
        raise e

@app.post("/generate/ticket")
def create_ticket(ticket:Ticket, user:dict = Depends(get_current_user)):
    try:
        if get_current_user and user.get("user_role")== "customer":
                with get_db_connection() as cur:
                    cur.execute(""
                                "Insert into tickets (title,description,customer_id,category_id,priority)" \
                                " VALUES (%s,%s,%s,%s,%s) RETURNING id"""
                                ,(ticket.title,ticket.description,user["user_id"],ticket.category_id,ticket.priority))
                    result = cur.fetchone()
                    if result:
                        return {"message": "Ticket created successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action")
    except HTTPException as e:
        raise e
       
@app.get("/view/ticket")
def view_ticket(user:dict = Depends(get_current_user)):
    if user.get("user_role") != "admin":
       raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action")
    try:
        with get_db_connection() as cur:
            cur.execute("SELECT * FROM tickets")
            result=cur.fetchall()
            if result:
                tickets=[]
                for res in result:
                    tickets.append({
                        "ticket_id":res[0],
                        "title":res[1],
                        "description":res[2],
                        "customer_id":res[3],
                        "assigned_to":res[4],
                        "category_id":res[5],
                        "priority":res[6],
                        "status":res[7],
                        "created_at":res[8],
                        "updated_at":res[9],
                        "resolved_at":res[10]
                    })
                return tickets
    except HTTPException as e:
        raise e

@app.patch("/assign/ticket")
def assign_ticket(assign:AssignTicket,user:dict = Depends(get_current_user)):
    if user.get("user_role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action")
    try:
        with get_db_connection() as cur:
            cur.execute("UPDATE tickets SET assigned_to = %s WHERE id = %s RETURNING id",(assign.assigned_to, assign.ticket_id))
            result=cur.fetchone()
            if result:
                return {"message": "Ticket assigned successfully to","agent_id":result}
    except HTTPException as e:
        raise e

@app.patch("/update/status")
def update_status(us:UpdateStatus,user:dict = Depends(get_current_user)):
    if user.get("user_role") == "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You do not have permission to perform this action")
    try:
        with get_db_connection() as cur:
            if us.status=="resolved":
                cur.execute("UPDATE tickets SET status = %s, resolved_at = %s, updated_at=%s WHERE id = %s and assigned_to =%s RETURNING id",(us.status,datetime.now(),datetime.now(),us.ticket_id,user["user_id"]))

            cur.execute("UPDATE tickets SET status = %s, updated_at=%s WHERE id = %s and assigned_to =%s  RETURNING id",(us.status,datetime.now(),us.ticket_id,user["user_id"]))
            result=cur.fetchone()
            if result:
                return {"message": "Status updated successfully","status":us.status}
    except HTTPException as e:
        raise e


                  

