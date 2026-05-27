"""BioAgent Web UI - FastAPI-based web interface."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import BioAgent
from .config import config

app = FastAPI(
    title="BioAgent API",
    description="AI-Powered Bioinformatics Research Assistant",
    version=config.VERSION,
)

agent = BioAgent()


class QueryRequest(BaseModel):
    message: str


class QueryResponse(BaseModel):
    response: str
    tool_calls: int = 0


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the web UI."""
    html_path = Path(__file__).parent.parent / "static" / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")

    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>BioAgent</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background:#0d1117; color:#c9d1d9; min-height:100vh; display:flex; flex-direction:column; }
        header { background:#161b22; border-bottom:1px solid #30363d; padding:16px 24px; }
        header h1 { font-size:1.3em; color:#58a6ff; }
        header span { font-size:0.85em; color:#8b949e; }
        main { flex:1; max-width:900px; margin:0 auto; width:100%; padding:24px; display:flex; flex-direction:column; }
        #chat { flex:1; overflow-y:auto; margin-bottom:16px; }
        .msg { margin-bottom:16px; padding:12px 16px; border-radius:8px; }
        .msg.user { background:#1f6feb22; border:1px solid #1f6feb44; }
        .msg.agent { background:#23863622; border:1px solid #23863644; }
        .msg .role { font-size:0.75em; font-weight:bold; margin-bottom:6px; color:#8b949e; }
        .msg pre { background:#161b22; padding:8px; border-radius:4px; overflow-x:auto; font-size:0.85em; }
        form { display:flex; gap:8px; }
        input { flex:1; padding:12px; border:1px solid #30363d; border-radius:6px; background:#0d1117; color:#c9d1d9; font-size:0.95em; }
        button { padding:12px 24px; background:#238636; color:#fff; border:none; border-radius:6px; cursor:pointer; font-weight:600; }
        button:hover { background:#2ea043; }
        .loading { color:#8b949e; font-style:italic; }
    </style>
</head>
<body>
<header><h1>BioAgent <span>v{version}</span></h1></header>
<main>
<div id="chat"></div>
<form id="form">
    <input id="input" placeholder="Ask about genes, diseases, or bioinformatics analysis..." autofocus>
    <button type="submit">Send</button>
</form>
</main>
<script>
const chat = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('input');

function addMsg(role, text) {{
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.innerHTML = '<div class="role">' + (role==='user'?'You':'BioAgent') + '</div>' + text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}}

form.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    addMsg('user', msg);
    const loading = document.createElement('div');
    loading.className = 'msg agent loading';
    loading.textContent = 'Thinking...';
    chat.appendChild(loading);

    try {{
        const resp = await fetch('/api/chat', {{
            method:'POST',
            headers: {{'Content-Type':'application/json'}},
            body: JSON.stringify({{message: msg}})
        }});
        const data = await resp.json();
        loading.remove();
        addMsg('agent', data.response.replace(/\\n/g,'<br>'));
    }} catch(err) {{
        loading.remove();
        addMsg('agent', 'Error: ' + err.message);
    }}
}});
</script>
</body>
</html>""".format(version=config.VERSION)


@app.post("/api/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """Chat endpoint for the web UI."""
    try:
        response = agent.chat(request.message)
        return QueryResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset")
async def reset():
    """Reset conversation context."""
    agent.reset()
    return {"status": "ok"}


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": config.VERSION}


def start_server(port: int = 8000):
    """Start the FastAPI web server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
