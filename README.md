# UndoProof

**Policy-gated automated actions with verification and snapshot-based recovery.**

## About

UndoProof is a local prototype that demonstrates how automated actions can be checked against policy, executed within a defined scope, verified after execution, and recovered using a saved snapshot.

## Demo scenarios

- **ALLOW:** Execute a permitted action and verify the resulting record.
- **BLOCK:** Reject a prohibited action before it changes records.
- **RECOVER:** Restore a record to its saved snapshot and verify the final state.

The demo uses synthetic customer records and a local SQLite database.

## Tech stack

- Python
- FastAPI
- SQLite
- Pytest

## Run locally on Windows

Open PowerShell in the project folder:

```powershell
cd C:\Users\acer\UndoProof
.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Open the dashboard at http://127.0.0.1:8000.

Open the audit view at http://127.0.0.1:8000/audit.

## Run tests

In a separate PowerShell window:

```powershell
cd C:\Users\acer\UndoProof
.\.venv\Scripts\python.exe -m pytest -q
```

## Current limitations

This is a local proof of concept using synthetic data. Recovery is snapshot-based for the demo database; it is not a universal rollback mechanism. The prototype is not yet integrated with a live AI agent or external business systems. Its policy decisions are deterministic and should not be described as a trained AI model.
