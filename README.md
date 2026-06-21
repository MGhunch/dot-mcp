# dot-mcp

Remote MCP server for **Dot**. A thin relay that exposes Dot's job-setup and
todo actions to Claude (claude.ai, Desktop, mobile) over Streamable HTTP.

It holds **no logic** — every tool just POSTs to the Hub. Job-number
reservation, the Tracker line, the Todo, and the Dropbox folder all happen in
the Hub's `/api/new-job` and `/api/todos`, so single-writer integrity stays in
the Hub. dot-mcp never touches Airtable directly.

## Tools

| Tool | Hub endpoint | Does |
|------|--------------|------|
| `create_job` | `POST /api/new-job` | Reserves the next number, creates Project + live Tracker line + Todo + Dropbox folder. Returns the per-step receipt. |
| `add_todo` | `POST /api/todos` | Adds a todo (bucket CLIENTS/OTHER, optional client link). |

## Run locally

```bash
pip install -r requirements.txt
HUB_URL=https://dot.hunch.co.nz python server.py   # serves http://localhost:8000/mcp
```

## Deploy (Railway)

New service from this repo. Set env vars:

| Var | Value |
|-----|-------|
| `HUB_URL` | `https://dot.hunch.co.nz` |
| `MISE_PYTHON_GITHUB_ATTESTATIONS` | `false` |

`PORT` is provided by Railway. Start command comes from the `Procfile`
(`web: python server.py`). The connector URL is `https://<service>.up.railway.app/mcp`.

## Connect to Claude

claude.ai → Settings → Connectors → **Add custom connector** →
paste the `…/mcp` URL → transport **Streamable HTTP** → no auth.

## Auth

None (v1). The Hub endpoints are open; lock both down together later if needed.
Note: Claude doesn't support pasted bearer tokens or tokens in the URL — the
real options are authless (now) or OAuth (later).
