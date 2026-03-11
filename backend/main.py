from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import sqlite3
import json

from backend.auth import router as auth_router
from backend.database import get_db_connection, save_message, get_history
from backend.data_utils import clean_uploaded_csv, clean_column_names, generate_schema, generate_kpi_cards
from backend.llm_engine import generate_query, validate_sql

app = FastAPI(title="Lakshya BI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# In-memory storage for datasets across sessions
user_sessions = {}

class ChatRequest(BaseModel):
    username: str
    session_id: str
    message: str
    last_sql: Optional[str] = None

class SwitchDatasetRequest(BaseModel):
    username: str
    filename: str

class SummaryRequest(BaseModel):
    username: str
    filename: str

@app.post("/api/upload")
async def upload_file(username: str = Form(...), file: UploadFile = File(...)):
    contents = await file.read()
    df = clean_uploaded_csv(contents)
    
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")
    df = clean_column_names(df)
    
    if username not in user_sessions:
        user_sessions[username] = {"datasets": {}, "current": None, "schema": None, "kpis": None}
        
    user_sessions[username]["datasets"][file.filename] = df
    user_sessions[username]["current"] = file.filename
    
    # Load into SQLite
    conn = get_db_connection()
    df.to_sql(f"data_{username}", conn, index=False, if_exists="replace")
    conn.close()
    
    schema = generate_schema(df)
    kpis = generate_kpi_cards(df)
    
    user_sessions[username]["schema"] = schema
    user_sessions[username]["kpis"] = kpis
    
    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "kpis": kpis,
        "datasets": list(user_sessions[username]["datasets"].keys())
    }

@app.get("/api/datasets/{username}")
def get_datasets(username: str):
    if username not in user_sessions:
        return {"current": None, "datasets": [], "kpis": []}
    
    return {
        "current": user_sessions[username]["current"],
        "datasets": list(user_sessions[username]["datasets"].keys()),
        "kpis": user_sessions[username].get("kpis", [])
    }

@app.post("/api/datasets/switch")
def switch_dataset(req: SwitchDatasetRequest):
    if req.username not in user_sessions or req.filename not in user_sessions[req.username]["datasets"]:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    df = user_sessions[req.username]["datasets"][req.filename]
    user_sessions[req.username]["current"] = req.filename
    
    conn = get_db_connection()
    df.to_sql(f"data_{req.username}", conn, index=False, if_exists="replace")
    conn.close()
    
    schema = generate_schema(df)
    kpis = generate_kpi_cards(df)
    
    user_sessions[req.username]["schema"] = schema
    user_sessions[req.username]["kpis"] = kpis
    
    return {"message": "Switched successfully", "current": req.filename, "kpis": kpis}

@app.post("/api/summary")
def get_summary_charts(req: SummaryRequest):
    if req.username not in user_sessions or req.filename not in user_sessions[req.username]["datasets"]:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    schema = user_sessions[req.username]["schema"]
    msg = "Give me an overview dashboard of this dataset. Generate EXACTLY 3 queries: 1 pie chart for distribution, 1 bar chart for comparison, and 1 line chart for a trend. I need them to be highly informative."
    
    result = generate_query(req.username, f"User: {msg}", schema)
    
    if not result or "queries" not in result:
        return {"queries": [], "error": "Could not generate summary charts"}
        
    queries = result.get("queries", [])
    processed_queries = []
    conn = get_db_connection()
    
    for q_obj in queries:
        title = q_obj.get("title", "Overview Chart")
        sql = q_obj.get("sql", "")
        
        if not validate_sql(sql):
            continue
            
        try:
            df_result = pd.read_sql(sql, conn)
            err = None
        except Exception as e:
            err = str(e)
            
        if err is None and not df_result.empty:
            c_type = q_obj.get("chart_type", "none")
            x = q_obj.get("x_axis")
            y = q_obj.get("y_axis")
            group = q_obj.get("group_by")
            
            processed_queries.append({
                "title": title,
                "data": df_result.to_dict(orient="records"),
                "chart_type": c_type,
                "x_axis": x,
                "y_axis": y,
                "group_by": group
            })

    conn.close()
    return {"queries": processed_queries}

@app.get("/api/history/{username}/{session_id}")
def get_chat_history(username: str, session_id: str):
    return {"messages": get_history(session_id, username)}

@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.username not in user_sessions or not user_sessions[req.username]["schema"]:
        raise HTTPException(status_code=400, detail="No active dataset.")
        
    save_message(req.session_id, req.username, "user", req.message)
    
    history_list = get_history(req.session_id, req.username)
    formatted_history = []
    for m in history_list:
        role = "User" if m["role"] == "user" else "Assistant"
        formatted_history.append(f"{role}:\n{m['content']}")
    history_text = "\n".join(formatted_history)
    
    schema = user_sessions[req.username]["schema"]
    
    result = generate_query(req.username, history_text, schema, req.last_sql)
    
    if not result:
        err_msg = "I couldn't understand the AI response. Please try asking differently."
        save_message(req.session_id, req.username, "assistant", err_msg)
        return {"error": err_msg}
        
    if "error" in result and result["error"]:
        save_message(req.session_id, req.username, "assistant", result["error"])
        return {"error": result["error"]}
        
    if "conversational_reply" in result:
        assistant_content = result["conversational_reply"]
        follow_ups = result.get("follow_up_questions", [])
        save_message(req.session_id, req.username, "assistant", assistant_content, follow_ups)
        return {
            "content": assistant_content,
            "queries": [],
            "follow_ups": follow_ups,
            "last_sql": req.last_sql
        }
        
    queries = result.get("queries", [])
    if not queries and "sql" in result:
        queries = [result]
        
    if not queries:
        err_msg = "Could not find any queries in the response."
        save_message(req.session_id, req.username, "assistant", err_msg)
        return {"error": err_msg}

    assistant_content = ""
    processed_queries = []
    conn = get_db_connection()
    successful_sql = None
    
    for q_obj in queries:
        title = q_obj.get("title", "Result")
        sql = q_obj.get("sql", "")
        
        assistant_content += f"**{title}**\n\n<details>\n<summary>View Technical Details</summary>\n\n```sql\n{sql}\n```\n\n</details>\n\n"
        
        if not validate_sql(sql):
            continue
            
        try:
            df_result = pd.read_sql(sql, conn)
            err = None
        except Exception as e:
            err = str(e)
            
        # Optional: Implement auto-correction logic here as done in streamlit app
        # For brevity in React conversion, if it fails we just pass the error
        if err is not None:
            # Simple retry loop
            correction_prompt = f"The following SQL query failed with this error:\nERROR: {err}\nFAILED QUERY:\n```sql\n{sql}\n```\nPlease fix."
            retry_result = generate_query(req.username, history_text + "\n" + correction_prompt, schema)
            if retry_result and "queries" in retry_result and len(retry_result["queries"]) > 0:
                sql = retry_result["queries"][0].get("sql", "")
                try:
                    df_result = pd.read_sql(sql, conn)
                    err = None
                    q_obj = retry_result["queries"][0]
                except Exception as e:
                    err = str(e)
                    
        if err is None and not df_result.empty:
            successful_sql = sql
            
            # Auto detect axes logic from Streamlit
            c_type = q_obj.get("chart_type", "none")
            x = q_obj.get("x_axis")
            y = q_obj.get("y_axis")
            group = q_obj.get("group_by")
            
            processed_queries.append({
                "title": title,
                "data": df_result.to_dict(orient="records"),
                "chart_type": c_type,
                "x_axis": x,
                "y_axis": y,
                "group_by": group
            })

    conn.close()
    
    follow_ups = result.get("follow_up_questions", [])
    save_message(req.session_id, req.username, "assistant", assistant_content, follow_ups)
    
    return {
        "content": assistant_content,
        "queries": processed_queries,
        "follow_ups": follow_ups,
        "last_sql": successful_sql
    }
