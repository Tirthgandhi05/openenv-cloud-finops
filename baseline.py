#!/usr/bin/env python3
# Cloud FinOps Sandbox heuristic baseline.

"""
  python baseline.py               → pretty-print scores
  python baseline.py --json        → JSON to stdout
  python baseline.py --task task_2 → one task only
"""
from __future__ import annotations
import argparse, json, sys
from typing import Optional
from environment import FinOpsEnv
from graders import run_grader
from models import (
    Action, ActionType, InstanceSize, StorageTier,
    BaselineResult, TaskBaselineResult,
)
from resources import EAST_1_PRODUCTION_IDS

def _heuristic_action(obs_dict: dict) -> Optional[dict]:
    task = obs_dict.get("task_id", "")
    resources = obs_dict.get("resources", [])
    migrated = obs_dict.get("traffic_migrated_from")
    drained = obs_dict.get("connections_drained", False)

    if task == "task_3":
        if migrated is None:
            for r in resources:
                if r["region"] == "us-east-1" and _is_orphan(r):
                    return {"action_type": "terminate", "resource_id": r["id"]}
            return {"action_type": "migrate_traffic", "source_region": "us-east-1"}
        if not drained:
            return {"action_type": "wait"}
        for r in resources:
            if r["region"] == "us-east-1":
                return {"action_type": "terminate", "resource_id": r["id"]}

    for r in resources:
        if _is_orphan(r) and not _has_dependency(r) and not _is_risky(r):
            return {"action_type": "terminate", "resource_id": r["id"]}

    for r in resources:
        if _is_cold_candidate(r):
            return {"action_type": "migrate_storage", "resource_id": r["id"], "target_tier": "cold"}

    for r in resources:
        if _is_oversized(r) and not _is_risky(r):
            return {"action_type": "resize", "resource_id": r["id"], "new_size": "small"}

    return None

def _is_orphan(r: dict) -> bool:
    status = str(r.get("status", "")).replace("ResourceStatus.", "")
    rtype = str(r.get("resource_type", "")).replace("ResourceType.", "")
    traffic = r.get("traffic_per_hour") or 0
    queries = r.get("queries_per_hour") or 0
    attached = r.get("attached_to")
    if _has_dependency(r): return False
    if rtype == "ip_address": return traffic == 0 and not attached
    if rtype == "snapshot": return True
    if status in ("stopped", "orphaned"): return traffic == 0 and queries == 0
    return False

def _is_cold_candidate(r: dict) -> bool:
    rtype = str(r.get("resource_type", "")).replace("ResourceType.", "")
    tier = str(r.get("storage_tier", "")).replace("StorageTier.", "")
    days = r.get("last_accessed_days_ago")
    if _has_dependency(r): return False
    if r.get("attached_to"): return False
    return rtype == "storage" and tier == "hot" and days is not None and days >= 400

def _is_oversized(r: dict) -> bool:
    rtype = str(r.get("resource_type", "")).replace("ResourceType.", "")
    size = str(r.get("instance_size", "")).replace("InstanceSize.", "")
    cpu = r.get("cpu_avg_24h")
    if _has_dependency(r): return False
    return rtype in ("vm", "database") and size in ("large", "xlarge") and cpu is not None and cpu < 10.0

def _has_dependency(r: dict) -> bool:
    dep = r.get("dependency_of")
    return bool(dep)

def _is_risky(r: dict) -> bool:
    tags = r.get("tags") or {}
    traffic = r.get("traffic_per_hour") or 0
    queries = r.get("queries_per_hour") or 0
    if tags.get("env") == "dev" and traffic > 1000: return True
    if tags.get("env") == "dr" or tags.get("role") == "standby": return True
    if tags.get("compliance") or tags.get("audit"): return True
    if tags.get("schedule") == "nightly": return True
    return False


def run_baseline(task_id: str) -> dict:
    env = FinOpsEnv()
    obs = env.reset(task_id)
    obs_dict = obs.model_dump()
    steps = 0

    while steps < obs_dict.get("max_steps", 20):
        action_dict = _heuristic_action(obs_dict)
        if action_dict is None:
            break
        action = Action(**action_dict)
        result = env.step(action)
        obs_dict = result.observation.model_dump()
        steps += 1
        if result.done:
            break

    grade = run_grader(env)
    return {
        "task_id": task_id,
        "score": grade.score,
        "money_saved": grade.money_saved,
        "steps_taken": steps,
        "downtime_events": grade.downtime_events,
        "notes": grade.message,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--task", type=str, default=None)
    args = parser.parse_args()

    tasks = [args.task] if args.task else ["task_1", "task_2", "task_3"]
    results = []

    for tid in tasks:
        r = run_baseline(tid)
        results.append(r)
        if not args.json:
            print(f"  {tid}: score={r['score']:.4f} saved=${r['money_saved']:,.0f} steps={r['steps_taken']}")

    mean = sum(r["score"] for r in results) / len(results) if results else 0.0

    output = {
        "model_used": "heuristic",
        "results": [TaskBaselineResult(**r).model_dump() for r in results],
        "mean_score": round(mean, 4),
    }

    if args.json:
        print(json.dumps(output))
    else:
        print(f"\n  Mean: {mean:.4f}")
        print(json.dumps(output))


if __name__ == "__main__":
    main()
