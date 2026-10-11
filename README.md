# UndoProof

**Policy first. Execute only within scope. Verify the resulting state.**

UndoProof is a prototype demonstrating policy-gated automated actions, scoped execution, verification of database changes, and snapshot-based recovery.

## Demo scenarios

- **ALLOW:** Update a permitted customer record and verify the change.
- **BLOCK:** Reject an oversized request before it modifies records.
- **RECOVER:** Restore a saved SQLite demo snapshot and verify the final state.

## Technology

- Python
- FastAPI
- SQLite
- Pytest

## Run locally

Install Python, then open PowerShell in the project directory.

Create a virtual environment:

```powershell
python -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the application:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Open http://127.0.0.1:8000 in your browser.

Run the tests in another PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Prototype limitations

This is a local demonstration using synthetic data and SQLite. Recovery applies to the demo database snapshot; it is not a universal rollback mechanism for external systems. The current prototype does not claim integration with production AI agents or external business systems.
