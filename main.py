import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DB_PATH = os.getenv("DB_PATH", str(ROOT / "jarvis.db"))

app = FastAPI(title="JARVIS Campus AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            title TEXT NOT NULL,
            due_date TEXT DEFAULT '',
            category TEXT DEFAULT 'General',
            done INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lost_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('Lost','Found')),
            item TEXT NOT NULL,
            location TEXT DEFAULT '',
            details TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            status TEXT DEFAULT 'Open',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            details TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

init_db()

class TaskIn(BaseModel):
    owner: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    due_date: str = ""
    category: str = "General"
    done: bool = False

class LostFoundIn(BaseModel):
    owner: str = Field(min_length=1, max_length=80)
    kind: str
    item: str = Field(min_length=1, max_length=160)
    location: str = ""
    details: str = ""
    contact: str = ""
    status: str = "Open"

class ResourceIn(BaseModel):
    owner: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    category: str = "General"
    details: str = ""
    contact: str = ""

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    owner: str = "Student"

@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")

@app.get("/api/health")
def health():
    return {"ok": True, "app": "JARVIS Campus AI"}

def rows(query, params=()):
    with db() as c:
        return [dict(r) for r in c.execute(query, params).fetchall()]

@app.get("/api/tasks")
def list_tasks(owner: str = ""):
    if owner:
        return rows("SELECT * FROM tasks WHERE owner=? ORDER BY done, due_date, id DESC", (owner,))
    return rows("SELECT * FROM tasks ORDER BY done, due_date, id DESC")

@app.post("/api/tasks")
def add_task(t: TaskIn):
    with db() as c:
        cur = c.execute("INSERT INTO tasks(owner,title,due_date,category,done) VALUES(?,?,?,?,?)",
                         (t.owner.strip(), t.title.strip(), t.due_date, t.category, int(t.done)))
        return dict(c.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone())

@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, payload: dict):
    allowed = {"title", "due_date", "category", "done"}
    changes = {k: v for k, v in payload.items() if k in allowed}
    if not changes:
        raise HTTPException(400, "No editable fields supplied")
    if "done" in changes:
        changes["done"] = int(bool(changes["done"]))
    with db() as c:
        if not c.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone():
            raise HTTPException(404, "Task not found")
        sql = ", ".join(f"{k}=?" for k in changes)
        c.execute(f"UPDATE tasks SET {sql} WHERE id=?", (*changes.values(), task_id))
        return dict(c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    with db() as c:
        cur = c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Task not found")
    return {"deleted": True}

@app.get("/api/lost-found")
def list_lost_found(kind: Optional[str] = None):
    if kind in ("Lost", "Found"):
        return rows("SELECT * FROM lost_found WHERE kind=? ORDER BY id DESC", (kind,))
    return rows("SELECT * FROM lost_found ORDER BY id DESC")

@app.post("/api/lost-found")
def add_lost_found(item: LostFoundIn):
    if item.kind not in ("Lost", "Found"):
        raise HTTPException(400, "kind must be Lost or Found")
    with db() as c:
        cur = c.execute("""INSERT INTO lost_found(owner,kind,item,location,details,contact,status)
                           VALUES(?,?,?,?,?,?,?)""",
                        (item.owner.strip(), item.kind, item.item.strip(), item.location,
                         item.details, item.contact, item.status))
        return dict(c.execute("SELECT * FROM lost_found WHERE id=?", (cur.lastrowid,)).fetchone())

@app.patch("/api/lost-found/{item_id}")
def update_lost_found(item_id: int, payload: dict):
    allowed = {"item", "location", "details", "contact", "status"}
    changes = {k: v for k, v in payload.items() if k in allowed}
    if not changes:
        raise HTTPException(400, "No editable fields supplied")
    with db() as c:
        if not c.execute("SELECT id FROM lost_found WHERE id=?", (item_id,)).fetchone():
            raise HTTPException(404, "Item not found")
        sql = ", ".join(f"{k}=?" for k in changes)
        c.execute(f"UPDATE lost_found SET {sql} WHERE id=?", (*changes.values(), item_id))
        return dict(c.execute("SELECT * FROM lost_found WHERE id=?", (item_id,)).fetchone())

@app.delete("/api/lost-found/{item_id}")
def delete_lost_found(item_id: int):
    with db() as c:
        cur = c.execute("DELETE FROM lost_found WHERE id=?", (item_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Item not found")
    return {"deleted": True}

@app.get("/api/resources")
def list_resources():
    return rows("SELECT * FROM resources ORDER BY id DESC")

@app.post("/api/resources")
def add_resource(r: ResourceIn):
    with db() as c:
        cur = c.execute("INSERT INTO resources(owner,title,category,details,contact) VALUES(?,?,?,?,?)",
                        (r.owner.strip(), r.title.strip(), r.category, r.details, r.contact))
        return dict(c.execute("SELECT * FROM resources WHERE id=?", (cur.lastrowid,)).fetchone())

@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int):
    with db() as c:
        cur = c.execute("DELETE FROM resources WHERE id=?", (resource_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Resource not found")
    return {"deleted": True}

@app.post("/api/chat")
def chat(data: ChatIn):
    q = data.message.lower().strip()
    if any(w in q for w in ["lost", "found", "wallet", "phone", "id card", "keys"]):
        items = rows("SELECT kind,item,location,details,status FROM lost_found WHERE status!='Resolved' ORDER BY id DESC LIMIT 8")
        if items:
            lines = [f"• {x['kind']}: {x['item']} — {x['location'] or 'location not specified'} ({x['status']})" for x in items]
            return {"reply": "Here are current lost-and-found posts:\n" + "\n".join(lines) + "\n\nOpen Lost & Found to post or update an item. Share contact details privately when possible."}
        return {"reply": "I can help with lost & found. There are no posts yet—open Lost & Found and add a Lost or Found report."}
    if any(w in q for w in ["task", "todo", "to-do", "deadline", "plan my day", "assignment"]):
        tasks = rows("SELECT title,due_date,category,done FROM tasks WHERE owner=? ORDER BY done,due_date LIMIT 10", (data.owner,))
        if tasks:
            lines = [f"• {'✓' if x['done'] else '○'} {x['title']} — due {x['due_date'] or 'date not set'} [{x['category']}]" for x in tasks]
            return {"reply": "Your task list:\n" + "\n".join(lines) + "\n\nYou can add, complete, edit, or delete tasks in the Tasks panel."}
        return {"reply": "Let's make a plan. Add your exams, assignments, and deadlines in Tasks; I can then summarize them here."}
    if any(w in q for w in ["exam", "study", "prepare", "revision", "quiz"]):
        return {"reply": "Quick study plan: 1) list the syllabus and exam date, 2) split topics into 30–45 minute blocks, 3) solve past questions before rereading notes, 4) keep an error log, 5) reserve the final session for timed practice. Add each block as a task. Tell me the subject, exam date, and topics for a more specific plan."}
    if any(w in q for w in ["resource", "club", "society", "room", "lab", "library", "canteen", "office"]):
        resources = rows("SELECT title,category,details,contact FROM resources ORDER BY id DESC LIMIT 8")
        if resources:
            lines = [f"• {x['title']} [{x['category']}] — {x['details']}" for x in resources]
            return {"reply": "Campus resource directory:\n" + "\n".join(lines) + "\n\nYou can add or remove entries in Campus Resources."}
        return {"reply": "The campus directory is empty so far. Add verified campus offices, clubs, labs, facilities, and useful contacts in Campus Resources."}
    return {"reply": "Hi! I'm JARVIS, your campus copilot. I can help organize study plans and tasks, search campus resources, and manage Lost & Found. Use the panels to create, view, edit, and delete records. For a tailored study plan, tell me your subject, exam date, and syllabus."}
