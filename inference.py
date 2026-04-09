#!/usr/bin/env python3
"""
inference.py — Cloud FinOps Sandbox baseline agent.

MANDATORY STDOUT FORMAT:
  [START] task=<task_name> env=cloud-finops model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

Uses OpenAI client for all LLM calls. Budget: ≤50 total calls across all tasks.
"""
from __future__ import annotations
import json, os, sys, time
from typing import Any, Dict, List, Optional
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
ENV_BASE_URL = os.environ.get("ENV_BASE_URL")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME","llama-3.3-70b-versatile")
API_KEY      = os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY", "")
BENCHMARK    = "cloud-finops"
MAX_TOTAL_CALLS = 50
TEMPERATURE  = 0.2  # Low but not zero — allows score variance

# ── OpenAI Client ─────────────────────────────────────────────────────────────
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

# ── Server helpers ────────────────────────────────────────────────────────────
def _get(path: str) -> dict:
    r = requests.get(f"{ENV_BASE_URL}{path}", timeout=15); r.raise_for_status(); return r.json()

def _post(path: str, body: dict = None, params: dict = None) -> dict:
    r = requests.post(f"{ENV_BASE_URL}{path}", json=body or {}, params=params or {}, timeout=15)
    r.raise_for_status(); return r.json()

def reset_task(task_id: str) -> dict: return _post("/reset", params={"task_id": task_id})
def take_step(action: dict) -> dict: return _post("/step", body=action)
def get_grade() -> dict: return _post("/grader")

# ── System prompt — NO hardcoded resource IDs, NO specific trap names ─────────
SYSTEM_PROMPT = """You are an expert cloud FinOps engineer optimizing NovaCart's cloud infrastructure.
You must reduce costs WITHOUT causing production downtime.

Return ONLY a valid JSON object — no prose, no markdown, no backticks.
Exactly one of these schemas:
  {"action_type": "terminate", "resource_id": "<id>"}
  {"action_type": "resize", "resource_id": "<id>", "new_size": "<nano|micro|small|medium|large|xlarge>"}
  {"action_type": "migrate_storage", "resource_id": "<id>", "target_tier": "cold"}
  {"action_type": "migrate_traffic", "source_region": "<region>"}
  {"action_type": "wait"}

SAFETY ANALYSIS — before EVERY action, verify:
1. Is the resource truly idle? Low 24h CPU average does NOT mean the resource is unused.
   Databases and batch systems often have extreme peak usage at night (2-4am) that
   does not show in 24-hour averages.
2. Does the resource have dependency_of set? If yes, DO NOT touch it.
3. Check traffic_per_hour AND queries_per_hour — either being high means the resource is active.
4. Tags can LIE. A resource tagged "dev" may serve real production traffic. Always verify
   traffic/queries before trusting tags.
5. Stopped VMs with critical tags (dr, standby, failover) may be disaster recovery nodes.
6. Compliance-tagged resources (PCI-DSS, audit, SOX) should never be resized or terminated.
7. For storage: check both last_accessed_days_ago AND dependency_of before cold-migrating.

TASK-SPECIFIC RULES:
- task_1: Find orphaned resources (status=orphaned/stopped, traffic=0, no dependencies).
  Terminate only clearly orphaned ones.
- task_2: Resize oversized VMs (cpu<10%, large/xlarge) and cold-migrate old storage
  (last_accessed>400 days). But verify no dependencies and no batch job indicators.
- task_3: MANDATORY SEQUENCE for us-east-1 shutdown:
  (1) migrate_traffic with source_region="us-east-1"
  (2) wait
  (3) THEN terminate east-1 resources
  Also clean west-2 orphans. NEVER touch west-2 production resources.

PRIORITY ORDER: terminate obvious orphans → migrate_traffic (task_3) → wait (task_3) →
terminate drained east-1 resources → cold-migrate stale storage → resize oversized VMs.

When nothing safe remains, return: {"action_type": "terminate", "resource_id": "DONE"}
"""


def _build_prompt(obs: dict, task_id: str) -> str:
    resources = obs.get("resources", [])
    # Compact resource view — only show active resources with key fields
    compact = []
    for r in resources:
        entry = {
            "id": r["id"], "type": r["resource_type"], "status": r["status"],
            "region": r["region"], "cost": r["monthly_cost"],
        }
        if r.get("cpu_avg_24h") is not None: entry["cpu%"] = r["cpu_avg_24h"]
        if r.get("traffic_per_hour"): entry["traffic/hr"] = r["traffic_per_hour"]
        if r.get("queries_per_hour"): entry["queries/hr"] = r["queries_per_hour"]
        if r.get("instance_size"): entry["size"] = r["instance_size"]
        if r.get("attached_to"): entry["attached_to"] = r["attached_to"]
        if r.get("dependency_of"): entry["dependency_of"] = r["dependency_of"]
        if r.get("storage_tier"): entry["tier"] = r["storage_tier"]
        if r.get("last_accessed_days_ago") is not None: entry["last_access_days"] = r["last_accessed_days_ago"]
        if r.get("tags"): entry["tags"] = r["tags"]
        compact.append(entry)

    return f"""TASK: {task_id} | STEP: {obs.get('step')}/{obs.get('max_steps')}
BILL: ${obs.get('monthly_bill_current', 0):,.0f} (started ${obs.get('monthly_bill_start', 0):,.0f})
SAVINGS: ${obs.get('savings_achieved', 0):,.0f} / TARGET: ${obs.get('savings_target', 0):,.0f}
DOWNTIME: {obs.get('downtime_events', 0)} | HONEYPOTS: {obs.get('honeypot_hits', 0)} | SEQ_VIOLATIONS: {obs.get('sequence_violations', 0)}
TRAFFIC_MIGRATED: {obs.get('traffic_migrated_from') or 'none'} | DRAINED: {obs.get('connections_drained', False)}
FEEDBACK: {obs.get('feedback', '')}

RESOURCES ({len(compact)} active):
{json.dumps(compact, indent=1)}

Choose ONE safe action. Return only JSON."""


def _parse_response(raw: str) -> Optional[dict]:
    if not raw: return None
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        inner = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(inner).strip()
    try: return json.loads(raw)
    except json.JSONDecodeError: pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        try: return json.loads(raw[start:end+1])
        except json.JSONDecodeError: pass
    return None


def _call_llm(prompt: str) -> Optional[dict]:
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        return _parse_response(raw)
    except Exception as e:
        print(f"  [LLM error] {e}", file=sys.stderr)
        return None


# ── Episode runner ────────────────────────────────────────────────────────────
def run_episode(task_id: str, calls_remaining: int) -> tuple[dict, int]:
    """Run one episode. Returns (grade_dict, calls_used)."""
    obs = reset_task(task_id)
    max_steps = obs.get("max_steps", 20)
    steps = 0
    rewards: List[float] = []
    calls_used = 0
    noop_count = 0

    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}")

    while steps < max_steps and calls_used < calls_remaining:
        prompt = _build_prompt(obs, task_id)
        action = _call_llm(prompt)
        calls_used += 1

        if action is None:
            noop_count += 1
            print(f"[STEP] step={steps+1} action=noop reward=0.00 done=false error=llm_parse_failure")
            if noop_count >= 3:
                break
            time.sleep(2)
            continue

        # Check for "DONE" signal
        if action.get("resource_id") == "DONE":
            print(f"[STEP] step={steps+1} action=done reward=0.00 done=true error=null")
            break

        noop_count = 0

        try:
            result = take_step(action)
        except requests.HTTPError as e:
            steps += 1
            print(f"[STEP] step={steps} action={json.dumps(action)} reward=0.00 done=false error={str(e)}")
            continue

        steps += 1
        reward = result.get("reward", 0.0)
        rewards.append(reward)
        obs = result.get("observation", obs)
        done = result.get("done", False)
        error = result.get("info", {}).get("error") or result.get("info", {}).get("penalty_reason")

        action_str = json.dumps(action)
        print(
            f"[STEP] step={steps} action={action_str} "
            f"reward={reward:.2f} done={'true' if done else 'false'} "
            f"error={error if error else 'null'}"
        )

        if done:
            break

        # Rate limit protection
        time.sleep(1)

    grade = get_grade()
    score = grade.get("score", 0.0)
    success = score >= 0.5
    rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.00"
    print(
        f"[END] success={'true' if success else 'false'} "
        f"steps={steps} score={score:.2f} rewards={rewards_str}"
    )

    return grade, calls_used


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    # Verify server is up
    try:
        r = requests.get(f"{ENV_BASE_URL}/", timeout=5)
        if r.status_code != 200:
            print(f"ERROR: Server returned {r.status_code}", file=sys.stderr)
            sys.exit(1)
    except Exception:
        print(f"ERROR: Server at {ENV_BASE_URL} not responding.", file=sys.stderr)
        sys.exit(1)

    tasks = ["task_1","task_2","task_3"]
    scores: dict[str, float] = {}
    total_calls = 0

    for task_id in tasks:
        remaining = MAX_TOTAL_CALLS - total_calls
        if remaining <= 0:
            print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}")
            print(f"[END] success=false steps=0 score=0.00 rewards=0.00")
            scores[task_id] = 0.0
            continue

        grade, used = run_episode(task_id, remaining)
        total_calls += used
        scores[task_id] = grade.get("score", 0.0)

    mean = sum(scores.values()) / len(scores) if scores else 0.0

    # Summary to stderr (not part of mandated format)
    print(f"\n{'='*50}", file=sys.stderr)
    print(f"SUMMARY: {json.dumps(scores)} mean={mean:.4f} calls={total_calls}", file=sys.stderr)


if __name__ == "__main__":
    main()
