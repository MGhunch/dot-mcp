"""
dot-mcp — remote MCP server for Dot.

Thin relay between Claude (claude.ai / Desktop / mobile) and the Dot Hub.
Exposes Dot's job-setup and todo actions as MCP tools over Streamable HTTP.

"Brain thinks, Workers work, Airtable remembers." dot-mcp just carries the
message — it holds no logic. Job-number reservation, the Tracker line, the
Todo, and the Dropbox folder all live in the Hub's /api/new-job and
/api/todos. This server NEVER writes to Airtable directly, so single-writer
integrity for job numbers stays in the Hub where it belongs.

Transport : Streamable HTTP, mounted at /mcp (the URL you paste into claude.ai).
Auth      : none (v1). The Hub endpoints are open; lock both down together later.
"""

import os

import requests
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

HUB_URL = os.environ.get("HUB_URL", "https://dot.hunch.co.nz").rstrip("/")
REQUEST_TIMEOUT = 30  # seconds

mcp = FastMCP("dot-mcp")


def _post(path: str, payload: dict) -> dict:
    """POST to a Hub endpoint and return its JSON, or a clean error dict.

    Always returns a dict so Claude can narrate the outcome in natural
    language — it never raises into the transport.
    """
    url = f"{HUB_URL}{path}"
    try:
        r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        return {"success": False, "error": f"Couldn't reach the Hub: {e}"}

    try:
        data = r.json()
    except ValueError:
        return {
            "success": False,
            "error": f"Hub returned non-JSON ({r.status_code}): {r.text[:200]}",
        }

    # Surface HTTP-level failures even when there's a JSON body.
    if not r.ok and "error" not in data:
        data = {"success": False, "error": f"Hub {r.status_code}", "detail": data}
    return data


@mcp.tool
def create_job(
    client_code: str,
    job_name: str,
    description: str = "",
    owner: str = "",
    cost: float = 5000,
    is_ballpark: bool = False,
    live: str = "Tbc",
) -> dict:
    """Create a new Dot job.

    Reserves the next job number, creates the Project and a live Tracker line,
    adds a Todo, and makes the Dropbox folder — all in one call.

    Args:
        client_code: Client code, e.g. "TOW", "SKY", "HUN". Required.
        job_name: The job's name, e.g. "EOFY email campaign". Required.
        description: The brief / what the job is ("The Job"). Optional.
        owner: Client-side owner — the client contact, NOT a Hunch person. Optional.
        cost: Budget in dollars. Defaults to 5000.
        is_ballpark: False = live/confirmed spend (default). True = estimate.
        live: Expected live month, e.g. "Jun", or "Tbc" (default).

    Returns the Hub's per-step receipt: jobNumber, filesUrl, and a `steps` map
    {project, tracker, todo, folder}, each "created" or "failed: <reason>".
    Narrate this back to the user in plain language — do NOT dump the raw JSON.
    """
    if not client_code or not job_name:
        return {"success": False, "error": "client_code and job_name are both required."}

    return _post(
        "/api/new-job",
        {
            "clientCode": client_code,
            "jobName": job_name,
            "description": description,
            "owner": owner,
            "cost": cost,
            "isBallpark": is_ballpark,
            "live": live,
        },
    )


@mcp.tool
def add_todo(
    title: str,
    bucket: str = "OTHER",
    client: str = "",
    urgent: bool = False,
) -> dict:
    """Add a todo to Dot's todo list.

    Args:
        title: The todo text. Required.
        bucket: "CLIENTS" (client work) or "OTHER" (default).
        client: Client code or name to link, e.g. "TOW". Optional.
        urgent: Mark as urgent. Default False.

    Returns the created todo, or an error dict. Narrate the outcome in plain
    language — do NOT dump the raw JSON.
    """
    if not title:
        return {"success": False, "error": "title is required."}

    payload = {"title": title, "bucket": bucket, "urgent": urgent}
    if client:
        payload["client"] = client
    return _post("/api/todos", payload)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "dot-mcp", "hub": HUB_URL})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
