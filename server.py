# server.py
# Cloud FinOps Sandbox — OpenEnv submission
# FastAPI server.  Runs on port 7860 (Hugging Face Spaces requirement).
#
# Endpoints:
#   GET  /           — health check
#   POST /reset      — start episode (query param: task_id)
#   POST /step       — submit one action (JSON body: Action)
#   GET  /state      — current observation snapshot
#   GET  /tasks      — task metadata + action schemas
#   POST /grader     — score the current episode
#   POST /baseline   — run baseline.py as subprocess, return all scores
from __future__ import annotations

import subprocess
import sys
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from environment import FinOpsEnv
from graders import run_grader
from models import (
    Action,
    ActionSchema,
    ActionType,
    BaselineResult,
    GraderResult,
    Observation,
    StepResult,
    StorageTier,
    TaskBaselineResult,
    TaskInfo,
)
from resources import TASK_META

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Cloud FinOps Cost Optimization Sandbox",
    description=(
        "OpenEnv-compliant RL environment simulating cloud infrastructure "
        "cost optimization for a fictional e-commerce company (NovaCart). "
        "An AI agent acts as an automated FinOps/DevOps engineer."
    ),
    version="1.0.0",
)

# Single shared environment instance (stateful across requests in one session).
# For multi-agent parallelism you would instantiate per-session; single-instance
# is sufficient for the hackathon evaluation loop.
_env = FinOpsEnv()


# ══════════════════════════════════════════════════════════════════════════════
# Action schema definitions (static — used by GET /tasks)
# ══════════════════════════════════════════════════════════════════════════════

_ALL_ACTION_SCHEMAS: List[ActionSchema] = [
    ActionSchema(
        action_type=ActionType.TERMINATE,
        required_fields=["resource_id"],
        description=(
            "Permanently delete a resource. Saves its full monthly_cost. "
            "Risky if the resource is active — causes downtime and large penalty."
        ),
    ),
    ActionSchema(
        action_type=ActionType.RESIZE,
        required_fields=["resource_id", "new_size"],
        description=(
            "Downgrade a VM or database to a smaller instance_size tier. "
            "new_size must be strictly smaller than the current size. "
            "Saves the cost delta. Safe on low-CPU resources."
        ),
    ),
    ActionSchema(
        action_type=ActionType.MIGRATE_STORAGE,
        required_fields=["resource_id", "target_tier"],
        description=(
            "Move a hot storage volume to cold tier. "
            "target_tier must be 'cold'. "
            "Reduces monthly_cost by 80%. "
            "Penalty if last_accessed_days_ago < 30."
        ),
    ),
    ActionSchema(
        action_type=ActionType.MIGRATE_TRAFFIC,
        required_fields=["source_region"],
        description=(
            "[Task 3 only] Migrate all live traffic away from source_region. "
            "Must be called BEFORE terminating any production resource in that region. "
            "Call WAIT after this to drain connections."
        ),
    ),
    ActionSchema(
        action_type=ActionType.WAIT,
        required_fields=[],
        description=(
            "[Task 3 only] Wait for connection drain after MIGRATE_TRAFFIC. "
            "Must be called after migrate_traffic — otherwise incurs a sequence violation. "
            "After this completes, east-1 production resources become safe to terminate."
        ),
    ),
]

_TASK_1_ACTIONS = [s for s in _ALL_ACTION_SCHEMAS if s.action_type in (
    ActionType.TERMINATE, ActionType.RESIZE, ActionType.MIGRATE_STORAGE
)]
_TASK_2_ACTIONS = _TASK_1_ACTIONS  # same three
_TASK_3_ACTIONS = _ALL_ACTION_SCHEMAS  # all five


def _build_task_info(task_id: str) -> TaskInfo:
    meta = TASK_META[task_id]
    actions = {
        "task_1": _TASK_1_ACTIONS,
        "task_2": _TASK_2_ACTIONS,
        "task_3": _TASK_3_ACTIONS,
    }[task_id]

    return TaskInfo(
        task_id=task_id,
        name=meta["name"],
        difficulty=meta["difficulty"],
        description=meta["description"],
        monthly_bill=meta.get("monthly_bill", 0.0),
        savings_target=meta["savings_target"],
        max_steps=meta["max_steps"],
        regions=meta["regions"],
        available_actions=actions,
        grading_notes=meta["grading_notes"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

# ── GET / ─────────────────────────────────────────────────────────────────────

@app.get("/", summary="Health check")
def health_check() -> dict:
    """
    Required by OpenEnv Phase 1 gate.
    Returns 200 with environment metadata.
    """
    return {
        "status": "ok",
        "name": "cloud-finops-env",
        "version": "1.0.0",
        "tasks": ["task_1", "task_2", "task_3"],
        "current_task": _env._task_id,
    }


# ── POST /reset ───────────────────────────────────────────────────────────────

@app.post("/reset", response_model=Observation, summary="Start a new episode")
def reset(task_id: str = Query(..., description="One of: task_1, task_2, task_3")) -> Observation:
    """
    Reset the environment and start a fresh episode.
    Returns the initial Observation (resources as agent-safe views).
    """
    try:
        obs = _env.reset(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return obs


# ── POST /step ────────────────────────────────────────────────────────────────

@app.post("/step", response_model=StepResult, summary="Submit one action")
def step(action: Action) -> StepResult:
    """
    Apply one agent action and return reward, done flag, and new observation.
    Must call /reset first.
    """
    try:
        result = _env.step(action)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Action error: {exc}")
    return result


# ── GET /state ────────────────────────────────────────────────────────────────

@app.get("/state", response_model=Observation, summary="Current state snapshot")
def state() -> Observation:
    """
    Return the current environment observation without advancing the step counter.
    """
    try:
        return _env.state()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── GET /tasks ────────────────────────────────────────────────────────────────

@app.get("/tasks", response_model=List[TaskInfo], summary="All task definitions")
def tasks() -> List[TaskInfo]:
    """
    Return metadata for all 3 tasks including action schemas, savings targets,
    max steps, and grading rubrics.  Use this to build your agent prompt.
    """
    return [_build_task_info(tid) for tid in ("task_1", "task_2", "task_3")]


# ── POST /grader ──────────────────────────────────────────────────────────────

@app.post("/grader", response_model=GraderResult, summary="Score the current episode")
def grader() -> GraderResult:
    """
    Compute the final score for the current episode using the task-specific
    grader.  Can be called at any point after /reset.
    """
    try:
        return run_grader(_env)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── POST /baseline ────────────────────────────────────────────────────────────

@app.post("/baseline", response_model=BaselineResult, summary="Run baseline agent")
def baseline() -> BaselineResult:
    """
    Runs baseline.py as a subprocess (GPT-4o or heuristic fallback).
    Returns scores for all 3 tasks.  This may take 60–120 seconds.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "baseline.py", "--json"],
            capture_output=True,
            text=True,
            timeout=300,  # 5-minute hard cap
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Baseline timed out after 300s.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Baseline subprocess error: {exc}")

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline failed (rc={proc.returncode}): {proc.stderr[:500]}",
        )

    # baseline.py --json writes a JSON blob to stdout
    import json
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline returned non-JSON output: {proc.stdout[:300]}",
        )

    try:
        result = BaselineResult(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline output did not match BaselineResult schema: {exc}",
        )

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Exception handlers
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
    )


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860, reload=False)
