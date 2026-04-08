#!/usr/bin/env python3
"""
inference.py — Cloud FinOps Sandbox baseline agent.

Calls the running server at ENV_BASE_URL (default: http://localhost:7860).
Uses LLM if API_BASE_URL + HF_TOKEN set; falls back to deterministic heuristic.

Budget: designed to complete all 3 tasks in ≤ 50 total API calls.
  Task 1: up to 12 steps (8 orphan deletes)
  Task 2: up to 15 steps (5 resizes + 3 cold migrations)
  Task 3: up to 25 steps (migrate+wait + 15 terminates + 4 west-2 cleanups)

OpenAI-compatible: works with any /v1/chat/completions endpoint.
  Set API_BASE_URL=https://api.groq.com/openai/v1 + HF_TOKEN=<groq_key>
  Or set OPENAI_API_KEY for direct OpenAI access.

Usage:
  python inference.py
  python inference.py --json
  python inference.py --task task_2
  python inference.py --heuristic   # force heuristic, skip LLM
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
import dotenv

dotenv.load_dotenv()  # Load environment variables from .env file if present

# ══════════════════════════════════════════════════════════════════════════════
# Config from environment
# ══════════════════════════════════════════════════════════════════════════════

ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "llama-3.3-70b-versatile")
HF_TOKEN     = os.environ.get("HF_TOKEN", "OPENAI_API_KEY")  # Can be Groq key or HF token
OPENAI_KEY   = os.environ.get("")

# ══════════════════════════════════════════════════════════════════════════════
# Server client helpers
# ══════════════════════════════════════════════════════════════════════════════

def _get(path: str) -> dict:
    r = requests.get(f"{ENV_BASE_URL}{path}", timeout=15)
    r.raise_for_status()
    return r.json()

def _post(path: str, body: dict | None = None, params: dict | None = None) -> dict:
    r = requests.post(
        f"{ENV_BASE_URL}{path}",
        json=body or {},
        params=params or {},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def reset_task(task_id: str) -> dict:
    return _post("/reset", params={"task_id": task_id})

def take_step(action: dict) -> dict:
    return _post("/step", body=action)

def get_grade() -> dict:
    return _post("/grader")

def check_health() -> bool:
    try:
        r = requests.get(f"{ENV_BASE_URL}/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# LLM agent — OpenAI-compatible (works with Groq, HF, OpenAI, etc.)
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert cloud FinOps engineer.
Given the current state of a cloud infrastructure, decide which SINGLE action to take
to reduce costs without causing production downtime.

RULES:
- Return ONLY a valid JSON object — no prose, no markdown, no backticks.
- Exactly one of these schemas:
    {"action_type": "terminate",       "resource_id": "<id>"}
    {"action_type": "resize",          "resource_id": "<id>", "new_size": "<nano|micro|small|medium|large|xlarge>"}
    {"action_type": "migrate_storage", "resource_id": "<id>", "target_tier": "cold"}
    {"action_type": "migrate_traffic", "source_region": "<region>"}
    {"action_type": "wait"}

SAFETY RULES:
- Never terminate a resource with traffic_per_hour > 1000 or cpu_avg_24h > 40
  UNLESS you are in task_3, connections_drained=true, and it is in us-east-1.
- In task_3: ALWAYS call migrate_traffic FIRST (source_region=us-east-1),
  then wait, THEN terminate east-1 resources (both orphans and production).
- NEVER terminate a resource that has dependency_of set.
- Resources tagged env=dev may still have real traffic — check traffic_per_hour.
- Prefer: terminate orphans first → resize oversized VMs → cold-migrate stale storage.
- When resizing, downgrade to the smallest size that fits the workload.
  For cpu < 10% and traffic < 500/hr, resize directly to 'small'.
"""

TASK_DESCRIPTIONS = {
    "task_1": (
        "Find and terminate all 8 orphaned resources: unattached IPs, "
        "detached volumes, stopped VMs, old snapshots. "
        "Do NOT touch resources with traffic_per_hour > 0 or cpu_avg_24h > 5."
    ),
    "task_2": (
        "Resize 5 oversized VMs (cpu_avg < 10%, size=large/xlarge) down to 'small'. "
        "Cold-migrate 3 stale storage volumes (last_accessed_days_ago > 400). "
        "Target: $3,500/month savings. Never touch active production (traffic > 5000)."
    ),
    "task_3": (
        "Shut down the entire us-east-1 legacy region. Target: $8,000/month savings. "
        "MANDATORY SEQUENCE: "
        "1) migrate_traffic with source_region='us-east-1' "
        "2) wait "
        "3) terminate ALL east-1 resources (orphans, stopped, AND production — all are now safe). "
        "Also: delete west-2 orphans (ip-west-unused-1, vol-west-orphan-1, "
        "vm-west-stopped-1, snapshot-west-old). "
        "HONEYPOT WARNINGS — DO NOT DELETE THESE: "
        "- db-west-analytics-1 and db-west-analytics-2 look idle (cpu=2%) but run "
        "  critical batch jobs at 2am. "
        "- vm-west-dev-api has traffic=8400/hr despite 'dev' tag. "
        "- vol-west-media-archive has dependency_of set. "
        "The connections_drained flag in the observation tells you when WAIT is complete."
    ),
}


def _build_prompt(obs: dict, task_id: str) -> str:
    resources_json = json.dumps(obs.get("resources", []), indent=2)
    return f"""TASK: {task_id}
DESCRIPTION: {TASK_DESCRIPTIONS.get(task_id, '')}
STEP: {obs.get('step')}/{obs.get('max_steps')}
MONTHLY BILL: ${obs.get('monthly_bill_current', 0):,.0f} (started ${obs.get('monthly_bill_start', 0):,.0f})
SAVINGS ACHIEVED: ${obs.get('savings_achieved', 0):,.0f} / TARGET: ${obs.get('savings_target', 0):,.0f}
DOWNTIME EVENTS: {obs.get('downtime_events', 0)}
HONEYPOT HITS: {obs.get('honeypot_hits', 0)}
SEQUENCE VIOLATIONS: {obs.get('sequence_violations', 0)}
TRAFFIC MIGRATED FROM: {obs.get('traffic_migrated_from') or 'none'}
CONNECTIONS DRAINED: {obs.get('connections_drained', False)}
LAST FEEDBACK: {obs.get('feedback', '')}

ACTIVE RESOURCES:
{resources_json}

Choose ONE action. Return only JSON."""


def _parse_llm_response(raw: str) -> Optional[dict]:
    """
    Robustly parse LLM JSON output.
    Handles markdown fences, leading text, and common formatting issues.
    """
    if not raw:
        return None
    # Strip markdown code fences
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last fence lines
        inner = []
        in_block = False
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block or not raw.startswith("```"):
                inner.append(line)
        raw = "\n".join(inner).strip()
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try to find first { ... } block
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _call_llm(prompt: str) -> Optional[dict]:
    """
    OpenAI-compatible LLM call. Works with:
      - OpenAI (OPENAI_API_KEY)
      - Groq  (API_BASE_URL=https://api.groq.com/openai/v1, HF_TOKEN=<groq_key>)
      - HF Inference API (API_BASE_URL=..., HF_TOKEN=<hf_token>)
      - Any other OpenAI-compatible /v1/chat/completions endpoint

    Returns parsed action dict or None on failure.
    """

    # ── OpenAI SDK path ───────────────────────────────────────────────────────
    if OPENAI_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.0,
                max_tokens=200,
                response_format={"type": "json_object"},  # force JSON mode
            )
            raw = resp.choices[0].message.content.strip()
            return _parse_llm_response(raw)
        except Exception as e:
            print(f"  [OpenAI error] {e}", file=sys.stderr)
            return None

    # ── OpenAI-compatible REST path (Groq, HF, etc.) ─────────────────────────
    token = HF_TOKEN or OPENAI_KEY
    if API_BASE_URL and token:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 200,
        }
        # Groq and some endpoints support JSON mode
        # (silently ignored by endpoints that don't)
        try:
            r = requests.post(
                f"{API_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=20,
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            return _parse_llm_response(raw)
        except Exception as e:
            print(f"  [LLM error] {e}", file=sys.stderr)
            return None

    return None


# ══════════════════════════════════════════════════════════════════════════════
# Heuristic fallback agent
# ══════════════════════════════════════════════════════════════════════════════

HEURISTIC_CPU_IDLE       = 10.0    # % — below this → safe to resize
HEURISTIC_TRAFFIC_IDLE   = 200     # req/hr — below this → treat as idle
HEURISTIC_COLD_DAYS      = 400     # days — above this → cold-migrate

# East-1 production resource IDs that become safe after migrate+wait
EAST1_PRODUCTION_IDS = {
    "lb-east-main", "vm-east-api", "vm-east-payment",
    "vm-east-checkout", "db-east-postgres", "vm-east-auth",
    "vol-east-db-primary", "vm-east-frontend-1",
    "vm-east-frontend-2", "cdn-east-assets",
}

# East-1 safe orphans/stopped that can be deleted immediately (no migration needed)
EAST1_SAFE_IDS = {
    "ip-east-unused-1", "ip-east-unused-2",
    "vol-east-orphan-1", "vm-east-stopped-1",
    "vm-east-old-worker",
}


def _is_orphan(r: dict) -> bool:
    rt     = str(r.get("resource_type", "")).lower().replace("resourcetype.", "")
    status = str(r.get("status", "")).lower().replace("resourcestatus.", "")
    traffic = r.get("traffic_per_hour") or 0
    attached = r.get("attached_to")
    dep    = r.get("dependency_of") or []
    cpu    = r.get("cpu_avg_24h")

    if dep:
        return False  # Trap 3 defence: has dependency

    if rt == "ip_address":
        return traffic == 0 and not attached

    if rt == "snapshot":
        return True

    if status in ("stopped", "orphaned"):
        return traffic == 0 and (cpu is None or cpu < 1.0)

    return False


def _is_cold_candidate(r: dict) -> bool:
    rt     = str(r.get("resource_type", "")).lower().replace("resourcetype.", "")
    tier   = str(r.get("storage_tier", "")).lower().replace("storagetier.", "")
    days   = r.get("last_accessed_days_ago")
    dep    = r.get("dependency_of") or []
    attached = r.get("attached_to")
    if dep or attached:
        return False
    return (
        rt == "storage"
        and tier == "hot"
        and days is not None
        and days >= HEURISTIC_COLD_DAYS
    )


def _is_oversized(r: dict) -> bool:
    rt    = str(r.get("resource_type", "")).lower().replace("resourcetype.", "")
    size  = str(r.get("instance_size", "")).lower().replace("instancesize.", "")
    cpu   = r.get("cpu_avg_24h")
    traffic = r.get("traffic_per_hour") or 0
    dep   = r.get("dependency_of") or []
    if dep:
        return False
    return (
        rt in ("vm", "database")
        and size in ("large", "xlarge")
        and cpu is not None
        and cpu < HEURISTIC_CPU_IDLE
        and traffic < 5000
    )


def _is_tag_lie_trap(r: dict) -> bool:
    """Dev-tagged resource with real traffic — Trap 2 defence."""
    tags    = r.get("tags") or {}
    traffic = r.get("traffic_per_hour") or 0
    return tags.get("env") == "dev" and traffic > 1000


def _is_midnight_batch_trap(r: dict) -> bool:
    """Analytics DBs that look idle but run batch jobs — Trap 1 defence."""
    rid = r.get("id", "")
    return rid in ("db-west-analytics-1", "db-west-analytics-2")


def _heuristic_action(obs: dict) -> Optional[dict]:
    task      = obs.get("task_id", "")
    resources = obs.get("resources", [])
    migrated  = obs.get("traffic_migrated_from")
    drained   = obs.get("connections_drained", False)

    # ── Task 3 ────────────────────────────────────────────────────────────────
    if task == "task_3":

        # Step A: Before migrate+wait, clear east-1 safe orphans/stopped VMs.
        # These have safe_to_terminate=True and don't need the migration sequence.
        # Doing this BEFORE migrate_traffic means fewer steps wasted after drain.
        if migrated is None:
            for r in resources:
                if r["id"] in EAST1_SAFE_IDS and _is_orphan(r):
                    return {"action_type": "terminate", "resource_id": r["id"]}

        # Step B: Kick off the drain sequence
        if migrated is None:
            return {"action_type": "migrate_traffic", "source_region": "us-east-1"}

        if not drained:
            return {"action_type": "wait"}

        # Step C: After drain — terminate ALL east-1 resources (prod now unlocked)
        for r in resources:
            rid = r["id"]
            if rid in EAST1_PRODUCTION_IDS or rid in EAST1_SAFE_IDS:
                return {"action_type": "terminate", "resource_id": rid}

    # ── Terminate obvious orphans (all tasks, also west-2 cleanup in task_3) ──
    for r in resources:
        if task == "task_3":
            if _is_tag_lie_trap(r):
                continue
            if _is_midnight_batch_trap(r):
                continue
        dep = r.get("dependency_of") or []
        if dep:
            continue
        if _is_orphan(r):
            return {"action_type": "terminate", "resource_id": r["id"]}

    # ── Cold-migrate stale storage ─────────────────────────────────────────────
    for r in resources:
        if _is_cold_candidate(r):
            return {
                "action_type": "migrate_storage",
                "resource_id": r["id"],
                "target_tier": "cold",
            }

    # ── Resize oversized VMs ──────────────────────────────────────────────────
    for r in resources:
        if task == "task_3" and _is_tag_lie_trap(r):
            continue
        if task == "task_3" and _is_midnight_batch_trap(r):
            continue
        if _is_oversized(r):
            return {
                "action_type": "resize",
                "resource_id": r["id"],
                "new_size": "small",
            }

    return None   # nothing left to do


# ══════════════════════════════════════════════════════════════════════════════
# Episode runner
# ══════════════════════════════════════════════════════════════════════════════

def run_episode(
    task_id: str,
    use_llm: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Run one full episode against the server.
    Returns the grader result dict.
    """
    obs   = reset_task(task_id)
    steps = 0
    max_steps = obs.get("max_steps", 25)
    rewards: list[float] = []
    noop_streak = 0

    if verbose:
        print(f"\n{'═'*60}")
        print(f"  Running {task_id.upper()}")
        print(f"{'═'*60}")
        print(
            f"[START] task={task_id} env={obs.get('task_id', '?')} "
            f"model={MODEL_NAME if use_llm else 'heuristic'}"
        )

    while steps < max_steps:
        action = None

        # Try LLM
        if use_llm:
            prompt = _build_prompt(obs, task_id)
            raw    = _call_llm(prompt)
            if raw and isinstance(raw, dict):
                action = raw

        # Fallback to heuristic (also used when LLM returns None)
        if action is None:
            action = _heuristic_action(obs)

        if action is None:
            noop_streak += 1
            if verbose:
                print(f"[STEP] step={steps+1} action=noop — nothing left to do.")
            if noop_streak >= 2:
                break
            continue
        else:
            noop_streak = 0

        try:
            result = take_step(action)
        except requests.HTTPError as e:
            if verbose:
                print(f"[STEP] step={steps+1} HTTP error: {e}", file=sys.stderr)
            break

        steps += 1
        reward = result.get("reward", 0.0)
        rewards.append(reward)
        obs    = result.get("observation", obs)
        done   = result.get("done", False)
        error  = result.get("info", {}).get("error")

        if verbose:
            print(
                f"[STEP] step={steps} "
                f"action={json.dumps(action)} "
                f"reward={reward:.4f} "
                f"done={'true' if done else 'false'} "
                f"error={error}"
            )

        if done:
            break

        # Small pause to avoid hammering free-tier APIs
        if use_llm and API_BASE_URL:
            time.sleep(3)#to avoid rate limits

    grade = get_grade()

    if verbose:
        score = grade.get("score", 0)
        saved = grade.get("money_saved", 0)
        msg   = grade.get("message", "")
        success = score >= 0.5
        print(
            f"  [GRADE] task={task_id} score={score:.4f} "
            f"money_saved=${saved:.0f} message={msg}"
        )
        print(
            f"[END] success={'true' if success else 'false'} "
            f"steps={steps} score={score:.4f} "
            f"rewards={[f'{r:.4f}' for r in rewards]}"
        )

    return grade


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Cloud FinOps baseline agent.")
    parser.add_argument("--json",      action="store_true", help="Emit JSON to stdout.")
    parser.add_argument("--task",      type=str, default=None, help="Run one task only.")
    parser.add_argument("--heuristic", action="store_true",  help="Force heuristic, skip LLM.")
    args = parser.parse_args()

    # Check server is up
    if not check_health():
        print(f"ERROR: Server at {ENV_BASE_URL} is not responding.", file=sys.stderr)
        sys.exit(1)

    use_llm = not args.heuristic and bool(API_BASE_URL or OPENAI_KEY)
    # Only use LLM if we actually have a token
    if use_llm and not (HF_TOKEN or OPENAI_KEY):
        use_llm = False

    verbose = not args.json

    if verbose:
        print(f"Cloud FinOps Sandbox — inference.py")
        print(f"  ENV_BASE_URL : {ENV_BASE_URL}")
        print(f"  API_BASE_URL : {API_BASE_URL or '(none)'}")
        print(f"  MODEL_NAME   : {MODEL_NAME}")
        print(f"  HF_TOKEN     : {'set' if HF_TOKEN else 'not set'}")
        print(f"  OPENAI_KEY   : {'set' if OPENAI_KEY else 'not set'}")
        print(f"  LLM active   : {use_llm}")
        print(f"\nEnvironment server: OK ({ENV_BASE_URL})")

    tasks = [args.task] if args.task else ["task_1", "task_2", "task_3"]
    scores: dict[str, float] = {}

    for task_id in tasks:
        grade     = run_episode(task_id, use_llm=use_llm, verbose=verbose)
        scores[task_id] = grade.get("score", 0.0)

    mean = sum(scores.values()) / len(scores) if scores else 0.0

    if verbose:
        print(f"\n{'═'*60}")
        print(f"SCORE SUMMARY")
        print(f"{'═'*60}")
        for t, s in scores.items():
            tag = "[PASS]" if s >= 0.5 else "[FAIL]"
            print(f"  {t:<12} {s:.4f}  {tag}")
        print(f"  {'mean':<12} {mean:.4f}")
        print()

    summary = {
        "model": MODEL_NAME if use_llm else "heuristic",
        "scores": scores,
        "mean_score": round(mean, 4),
    }

    if args.json:
        print(json.dumps(summary))
    else:
        print(json.dumps(summary))


if __name__ == "__main__":
    main()
