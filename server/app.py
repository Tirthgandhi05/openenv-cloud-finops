# server.py — Cloud FinOps Sandbox — FastAPI server (port 7860)
from __future__ import annotations
import os
import json, subprocess, sys
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from environment import FinOpsEnv
from graders import run_grader
from models import (
    Action, ActionSchema, ActionType, BaselineResult, GraderResult,
    Observation, StepResult, StorageTier, TaskBaselineResult, TaskInfo,
)
from resources import TASK_META

app = FastAPI(
    title="Cloud FinOps Cost Optimization Sandbox",
    description=(
        "OpenEnv-compliant RL environment simulating cloud infrastructure "
        "cost optimization for NovaCart (fictional e-commerce)."
    ),
    version="1.0.0",
)

_env = FinOpsEnv()

_ALL_ACTION_SCHEMAS: List[ActionSchema] = [
    ActionSchema(action_type=ActionType.TERMINATE, required_fields=["resource_id"],
        description="Permanently delete a resource. Saves full monthly_cost. Risky if active."),
    ActionSchema(action_type=ActionType.RESIZE, required_fields=["resource_id", "new_size"],
        description="Downgrade a VM/DB to smaller instance_size. Saves cost delta."),
    ActionSchema(action_type=ActionType.MIGRATE_STORAGE, required_fields=["resource_id", "target_tier"],
        description="Move hot storage to cold tier. Reduces cost by 80%."),
    ActionSchema(action_type=ActionType.MIGRATE_TRAFFIC, required_fields=["source_region"],
        description="[Task 3] Migrate traffic from source_region. Must call before terminating prod."),
    ActionSchema(action_type=ActionType.WAIT, required_fields=[],
        description="[Task 3] Drain connections after migrate_traffic. Unlocks safe termination."),
]

_T12_ACTIONS = [s for s in _ALL_ACTION_SCHEMAS if s.action_type in (
    ActionType.TERMINATE, ActionType.RESIZE, ActionType.MIGRATE_STORAGE)]

def _build_task_info(task_id: str) -> TaskInfo:
    meta = TASK_META[task_id]
    actions = _ALL_ACTION_SCHEMAS if task_id == "task_3" else _T12_ACTIONS
    return TaskInfo(
        task_id=task_id, name=meta["name"], difficulty=meta["difficulty"],
        description=meta["description"], monthly_bill=meta.get("monthly_bill", 0.0),
        savings_target=meta["savings_target"], max_steps=meta["max_steps"],
        regions=meta["regions"], available_actions=actions,
        grading_notes=meta["grading_notes"],
    )

@app.get("/", summary="Health check")
def health_check() -> dict:
    return {"status": "ok", "name": "cloud-finops-env", "version": "1.0.0",
            "tasks": ["task_1", "task_2", "task_3"], "current_task": _env._task_id}

@app.get("/health", summary="Health check with version")
def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}

@app.post("/reset", response_model=Observation, summary="Start a new episode")
def reset(task_id: Optional[str] = None) -> Observation:
    if task_id is None:
        task_id = "task_1" 
    try: return _env.reset(task_id)
    except KeyError as e: raise HTTPException(status_code=400, detail=str(e))

@app.post("/step", response_model=StepResult, summary="Submit one action")
def step(action: Action) -> StepResult:
    try: return _env.step(action)
    except RuntimeError as e: raise HTTPException(status_code=400, detail=str(e))
    except Exception as e: raise HTTPException(status_code=422, detail=f"Action error: {e}")

@app.get("/state", response_model=Observation, summary="Current state snapshot")
def state() -> Observation:
    try: return _env.state()
    except RuntimeError as e: raise HTTPException(status_code=400, detail=str(e))

@app.get("/tasks", response_model=List[TaskInfo], summary="All task definitions")
def tasks() -> List[TaskInfo]:
    return [_build_task_info(tid) for tid in ("task_1", "task_2", "task_3")]

@app.post("/grader", response_model=GraderResult, summary="Score current episode")
def grader() -> GraderResult:
    try: return run_grader(_env)
    except (RuntimeError, ValueError) as e: raise HTTPException(status_code=400, detail=str(e))

@app.post("/baseline", response_model=BaselineResult, summary="Run baseline agent")
def baseline() -> BaselineResult:
    try:
        proc = subprocess.run([sys.executable, "baseline.py", "--json"],
            capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Baseline timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Baseline error: {e}")
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Baseline failed: {proc.stderr[:500]}")
    try: data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Non-JSON output: {proc.stdout[:300]}")
    try: return BaselineResult(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema mismatch: {e}")

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(status_code=500,
        content={"detail": f"Internal error: {type(exc).__name__}: {exc}"})

def main():
    import uvicorn
    # Make sure this points to server.app:app since we moved it into the server folder
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()