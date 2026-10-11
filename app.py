import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "undoproof.db"
MAX_SCOPE = 1


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                balance INTEGER NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                scenario TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                details TEXT NOT NULL
            )
        """)
        count = db.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]
        if count == 0:
            db.executemany(
                "INSERT INTO customers(id, name, status, balance) VALUES (?, ?, ?, ?)",
                [
                    (i, f"Demo Customer {i:03d}", "active", 1000 + i)
                    for i in range(1, 101)
                ],
            )


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(
    title="UndoProof",
    description="Policy-gated actions with state verification and recovery demo",
    version="1.0.0",
    lifespan=lifespan,
)


class ActionRequest(BaseModel):
    customer_id: int = Field(default=42, ge=1, le=100)
    new_status: str = Field(default="review", pattern="^(active|review|suspended)$")


def snapshot():
    with connect() as db:
        rows = db.execute(
            "SELECT id, name, status, balance FROM customers ORDER BY id"
        ).fetchall()
    return {str(row["id"]): dict(row) for row in rows}


def audit(scenario, decision, reason, details):
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario,
        "decision": decision,
        "reason": reason,
        "details": details,
    }
    with connect() as db:
        db.execute(
            """INSERT INTO audit_log
            (id, timestamp, scenario, decision, reason, details)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event["id"], event["timestamp"], scenario, decision,
                reason, json.dumps(details),
            ),
        )
    return event


def update_customer(customer_id, new_status):
    with connect() as db:
        db.execute(
            "UPDATE customers SET status = ? WHERE id = ?",
            (new_status, customer_id),
        )


def reset_demo():
    with connect() as db:
        db.execute(
            "UPDATE customers SET status = 'active', balance = 1000 + id"
        )


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!doctype html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>UndoProof | Safety Before Execution</title>
      <style>
        body{font-family:Arial,sans-serif;background:#101827;color:#edf2f7;
        max-width:900px;margin:35px auto;padding:0 18px}
        h1{font-size:38px;margin-bottom:6px}
        .muted{color:#aab8ca}
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
        .card{background:#1b293b;border:1px solid #34445a;border-radius:14px;padding:20px}
        button{background:#65e0bd;color:#10202a;border:0;border-radius:8px;
        padding:12px 16px;font-weight:bold;cursor:pointer;margin:5px 4px 5px 0}
        pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b1220;
        border-radius:10px;padding:16px;min-height:100px}
        .tag{color:#65e0bd;font-weight:bold}
      </style>
    </head>
    <body>
      <p class="tag">CODEMATRIX 2026 · ROUND 2 MVP</p>
      <h1>UndoProof</h1>
      <p class="muted">Policy first. Execute only within scope. Verify the resulting state.</p>
      <div class="grid">
        <div class="card"><h3>01 · ALLOW</h3><p>Change only customer #42.</p>
          <button onclick="run('allow')">Run ALLOW</button></div>
        <div class="card"><h3>02 · BLOCK</h3><p>Attempt a bulk update across 100 records.</p>
          <button onclick="run('block')">Run BLOCK</button></div>
        <div class="card"><h3>03 · RECOVER</h3><p>Inject an unexpected change, detect it, and restore the snapshot.</p>
          <button onclick="run('recover')">Run RECOVER</button></div>
      </div>
      <div class="card" style="margin-top:16px">
        <button onclick="run('reset')">Reset demo data</button>
        <button onclick="loadState()">Inspect database</button>
        <h3>Live execution report</h3>
        <pre id="out">Ready. Select a scenario.</pre>
      </div>
      <script>
        async function run(s){
          const out=document.getElementById('out');
          out.textContent='Running '+s.toUpperCase()+'...';
          try{
            const r=await fetch('/demo/'+s,{method:'POST'});
            const data=await r.json();
            out.textContent=JSON.stringify(data,null,2);
          }catch(e){out.textContent='Request failed: '+e}
        }
        async function loadState(){
          const r=await fetch('/state');
          document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2);
        }
      </script>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "ok", "product": "UndoProof"}


@app.get("/state")
def state():
    data = snapshot()
    return {
        "record_count": len(data),
        "sample": [data[str(i)] for i in (1, 2, 42, 99, 100)],
    }


@app.get("/audit")
def get_audit():
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 30"
        ).fetchall()
    return [
        {
            **dict(row),
            "details": json.loads(row["details"]),
        }
        for row in rows
    ]


@app.post("/demo/allow")
def demo_allow(request: ActionRequest = ActionRequest()):
    before = snapshot()
    # Policy checks are performed before the mutation.
    if request.customer_id not in range(1, 101):
        raise HTTPException(status_code=403, detail="Customer outside permitted dataset")
    decision = "ALLOW"
    customer_key = str(request.customer_id)
    target_status = request.new_status

    # Make the demo produce a real state change on repeated runs.
    if before[customer_key]["status"] == target_status:
        target_status = "active" if target_status != "active" else "review"

    update_customer(request.customer_id, target_status)
    after = snapshot()
    changed = [
        key for key in before
        if before[key] != after[key]
    ]
    verified = (
        changed == [customer_key]
        and after[customer_key]["status"] == target_status
    )
    event = audit(
        "allow", decision, "Single-record change is within policy scope",
        {"requested_id": request.customer_id, "changed_ids": changed,
         "verified": verified},
    )
    return {
        "scenario": "ALLOW", "decision": decision,
        "verified": verified, "changed_record_count": len(changed),
        "changed_ids": changed, "audit_id": event["id"],
        "message": "Single-record scope verified" if verified else "Unexpected state difference",
    }


@app.post("/demo/block")
def demo_block():
    before = snapshot()
    requested_scope = list(before.keys())  # Simulated agent proposal: all 100 records.
    if len(requested_scope) > MAX_SCOPE:
        event = audit(
            "block", "BLOCK", "Requested scope exceeds policy maximum",
            {"requested_count": len(requested_scope), "maximum": MAX_SCOPE},
        )
        after = snapshot()
        return {
            "scenario": "BLOCK", "decision": "BLOCK",
            "requested_record_count": len(requested_scope),
            "changed_record_count": sum(before[k] != after[k] for k in before),
            "verified_no_mutation": before == after,
            "audit_id": event["id"],
            "message": "Bulk action rejected before execution",
        }
    raise HTTPException(status_code=500, detail="Demo policy configuration unexpected")


@app.post("/demo/recover")
def demo_recover():
    before = snapshot()

    # Simulate an unexpected side effect by a faulty executor.
    update_customer(42, "review")
    update_customer(43, "suspended")
    observed = snapshot()
    changed_before_recovery = [
        key for key in before if before[key] != observed[key]
    ]
    unexpected = [key for key in changed_before_recovery if key != "42"]

    # Recovery is attempted only after comparing the observed state to the snapshot.
    # This local demo can restore the full synthetic dataset from its snapshot.
    with connect() as db:
        db.executemany(
            "UPDATE customers SET status = ?, balance = ? WHERE id = ?",
            [
                (row["status"], row["balance"], int(key))
                for key, row in before.items()
            ],
        )

    final = snapshot()
    restored = final == before
    event = audit(
        "recover", "RECOVER" if restored else "RECOVERY_FAILED",
        "Unexpected changed records detected; snapshot restoration attempted",
        {"changed_before_recovery": changed_before_recovery,
         "unexpected_ids": unexpected, "restored": restored},
    )
    return {
        "scenario": "RECOVER",
        "decision": "RECOVER" if restored else "RECOVERY_FAILED",
        "changed_before_recovery": changed_before_recovery,
        "unexpected_ids": unexpected,
        "restored": restored,
        "final_state_matches_snapshot": restored,
        "audit_id": event["id"],
        "message": "Snapshot restoration verified" if restored else "Restoration verification failed",
    }


@app.post("/demo/reset")
def demo_reset():
    reset_demo()
    data = snapshot()
    return {"reset": True, "record_count": len(data), "message": "Demo data reset"}
