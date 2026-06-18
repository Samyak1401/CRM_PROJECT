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

@app.get("/")
def root():
    return {"message": "API is running"}


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
    try:
        with get_db_connection() as cur:
            cur.execute("SELECT * FROM categories where is_active = True")
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
def update_status(us: UpdateStatus, user: dict = Depends(get_current_user)):
    if user.get("user_role") == "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action")
    try:
        with get_db_connection() as cur:
            cur.execute(
                "SELECT status FROM tickets WHERE id = %s AND assigned_to = %s",
                (us.ticket_id, user["user_id"])
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Ticket not found or not assigned to you")
            old_status = row[0]

            if old_status == us.status:
                raise HTTPException(status_code=400, detail="Ticket already has this status")

            now = datetime.now()
            if us.status == "resolved":
                cur.execute(
                    "UPDATE tickets SET status = %s, resolved_at = %s, updated_at = %s WHERE id = %s AND assigned_to = %s RETURNING id",
                    (us.status, now, now, us.ticket_id, user["user_id"])
                )
            else:
                cur.execute(
                    "UPDATE tickets SET status = %s, updated_at = %s WHERE id = %s AND assigned_to = %s RETURNING id",
                    (us.status, now, us.ticket_id, user["user_id"])
                )
            updated = cur.fetchone()
            if updated is None:
                raise HTTPException(status_code=404, detail="Ticket update failed")

            cur.execute(
                "INSERT INTO ticket_status_history (ticket_id, old_status, new_status, changed_by_id, changed_at, note) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (us.ticket_id, old_status, us.status, user["user_id"], now, us.note)
            )
            history_row = cur.fetchone()
            if history_row is None:
                raise HTTPException(status_code=500, detail="Failed to log status history")

            return {"message": "Status updated successfully", "status": us.status}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comments")
def create_comment(comment: CommentCreate, user: dict = Depends(get_current_user)):
    try:
        with get_db_connection() as cur:
            cur.execute(
                "SELECT customer_id, assigned_to FROM tickets WHERE id = %s",
                (comment.ticket_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Ticket not found")
            user_id, assigned_to = row

            if user["user_role"] == "customer":
                raise HTTPException(status_code=403, detail="You do not have permission to perform this action")

            cur.execute(
                "INSERT INTO ticket_comments (ticket_id, user_id, body, created_at) "
                "VALUES (%s, %s, %s, %s) RETURNING id, ticket_id, user_id, body, created_at",
                (comment.ticket_id, user["user_id"], comment.body, datetime.now())
            )
            result = cur.fetchone()
            if result is None:
                raise HTTPException(status_code=500, detail="Failed to create comment")

            return {
                "message": "Comment added successfully",
                "comment": {
                    "id": result[0],
                    "ticket_id": result[1],
                    "user_id": result[2],
                    "body": result[3],
                    "created_at": result[4]
                }
            }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/comments/{ticket_id}")
def get_comments(ticket_id: int, user: dict = Depends(get_current_user)):
    try:
        with get_db_connection() as cur:
            cur.execute("SELECT customer_id FROM tickets WHERE id = %s", (ticket_id,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Ticket not found")

            if user["user_role"] == "customer":
                raise HTTPException(status_code=403, detail="You do not have permission to perform this action")

            cur.execute(
                "SELECT id, ticket_id, user_id, body, created_at FROM ticket_comments "
                "WHERE ticket_id = %s ORDER BY created_at ASC",
                (ticket_id,)
            )
            rows = cur.fetchall()

            comments = [
                {"id": r[0], "ticket_id": r[1], "agent_id": r[2], "body": r[3], "created_at": r[4]}
                for r in rows
            ]
            return comments
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/profile")
def get_user_profile(user: dict = Depends(get_current_user)):
    try:
        with get_db_connection() as cur:
            cur.execute("SELECT name, email FROM users WHERE id = %s", (user["user_id"],))
            profile = cur.fetchone()
            if profile is None:
                raise HTTPException(status_code=404, detail="User not found")

            if user.get("user_role") == "admin":
                return {
                    "name": profile[0],
                    "email": profile[1]
                }

            if user.get("user_role") == "customer":
                cur.execute(
                    "SELECT id, title, description, status, priority FROM tickets WHERE customer_id = %s",
                    (user["user_id"],)
                )
            elif user.get("user_role") == "agent":
                cur.execute(
                    "SELECT id, title, description, status, priority FROM tickets WHERE assigned_to = %s",
                    (user["user_id"],)
                )
            else:
                raise HTTPException(status_code=403, detail="Unknown role")

            tickets = cur.fetchall()

            ticket_list = []
            for t in tickets:
                ticket_id = t[0]
                cur.execute(
                    "SELECT id, user_id, body, created_at FROM ticket_comments "
                    "WHERE ticket_id = %s ORDER BY created_at ASC",
                    (ticket_id,)
                )
                comment_rows = cur.fetchall()
                comments = [
                    {"id": c[0], "author_id": c[1], "body": c[2], "created_at": c[3]}
                    for c in comment_rows
                ]
                ticket_list.append({
                    "id": ticket_id,
                    "title": t[1],
                    "description": t[2],
                    "status": t[3],
                    "priority": t[4],
                    "comments": comments
                })

            return {
                "name": profile[0],
                "email": profile[1],
                "tickets": ticket_list
            }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.patch("/update/category", status_code=status.HTTP_200_OK)
def update_category(category: Category, user: dict = Depends(get_current_user)):
    if user.get("user_role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )

    try:
        with get_db_connection() as cur:
            cur.execute(
                """
                UPDATE categories
                SET name = %s, description = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (category.name, category.description, category.id)
            )
            result = cur.fetchone()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category with id {category.id} not found"
                )

            return {"message": "Category updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the category"
        )


@app.delete("/delete/category/{category_id}", status_code=status.HTTP_200_OK)
def delete_category(category_id: int, user: dict = Depends(get_current_user)):
    if user.get("user_role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )

    try:
        with get_db_connection() as cur:
            cur.execute(
                """
                UPDATE categories
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (category_id,)
            )
            result = cur.fetchone()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category with id {category_id} not found"
                )

            return {"message": "Category deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the category"
        )
@app.patch("/reactivate/category/{category_id}", status_code=status.HTTP_200_OK)
def reactivate_category(category_id: int, user: dict = Depends(get_current_user)):
    if user.get("user_role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )

    try:
        with get_db_connection() as cur:
            cur.execute(
                """
                UPDATE categories
                SET is_active = TRUE, updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (category_id,)
            )
            result = cur.fetchone()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category with id {category_id} not found"
                )

            return {"message": "Category reactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while reactivating the category"
        )