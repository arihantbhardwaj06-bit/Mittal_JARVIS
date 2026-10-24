# JARVIS Campus AI — public web app

A deployable, responsive campus copilot with:
- Chat-style JARVIS assistant
- Tasks CRUD (create, view, update/complete, delete)
- Lost & Found CRUD (create, view, edit status/details, delete)
- Campus resources directory (create, view, delete)
- REST API documented at `/docs`
- Render deployment configuration

## Run locally (optional)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Open `http://127.0.0.1:8000`.

## Deploy publicly on Render
1. Push this folder to a new GitHub repository.
2. Open https://render.com and create **New → Web Service**.
3. Connect the repository. Render can also use `render.yaml`.
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy, then share the public `https://<service-name>.onrender.com` URL.

## Important data note
This starter uses SQLite for a quick demo. A hosted service's local filesystem may be temporary, so data may not survive restarts/redeploys and the free service may sleep. Before using this with real students, connect a managed PostgreSQL/Supabase database and add authentication/authorization. The starter is a hackathon demo and currently has no login; do not post private phone numbers, student IDs, or sensitive information.

## Current scope / honest limitation
The chat uses built-in campus workflows and the records in this app; it is not yet connected to a paid/free LLM API, live campus timetable, student portal, or the existing uAgents runtime. The agent runtime can remain a separate process/service until its tools are connected to this API.
