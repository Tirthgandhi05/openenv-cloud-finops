# baseline.py
# Cloud FinOps Sandbox — OpenEnv submission
# Baseline agent: GPT-4o with heuristic fallback.
#
# Usage:
#   python baseline.py               → pretty-print scores for all 3 tasks
#   python baseline.py --json        → emit JSON to stdout (consumed by POST /baseline)
#   python baseline.py --task task_2 → run one task only (pretty-print)
#
# GPT-4o is used when OPENAI_API_KEY is set.
# Heuristic fallback runs with no API key (or on any GPT failure).
#
# Expected scores:
#   Task 1 (heuristic): ~0.85   Task 1 (GPT-4o): ~0.90
#   Task 2 (heuristic): ~0.55   Task 2 (GPT-4o): ~0.65
#   Task 3 (heuristic): ~0.30   Task 3 (GPT-4o): ~0.40
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# ── Local imports (must be in same directory) ─────────────────────────────────
from environment import FinOpsEnv
from graders import run_grader
from models import (
    Action,
    ActionType,
    AgentResource,
    GraderResult,
    INSTANCE_SIZE_ORDER,
    InstanceSize,
    Observation,
    ResourceType,
    StorageTier,
    TaskBaselineResult,
    BaselineResult,
)

# ══════════════════════════════════════════════════════════════════════════════
# GPT-4o agent
# ══════════════════════════════════════════════════════════════════════════════

OPENAI_MODEL = "gpt-4o"

SYSTEM_PROMPT = """You are an expert cloud FinOps engineer.
You are given the current state of a cloud infrastructure and must decide which
single action to take to reduce costs without causing downtime.

Rules:
- You MUST return ONLY a valid JSON object — no prose, no markdown, no backticks.
- The JSON must match exactly one of these schemas:
    {"action_type": "terminate",       "resource_id": "<id>"}
    {"action_type": "resize",          "resource_id": "<id>", "new_size": "<nano|micro|small|medium|large|xlarge>"}
    {"action_type": "migrate_storage", "resource_id": "<id>", "target_tier": "cold"}
    {"action_type": "migrate_traffic", "source_region": "<region>"}
    {"action_type": "wait"}
- Never terminate a resource with high traffic_per_hour (> 1000) or high cpu_avg_24h (> 40%)
  unless you are in task_3 and the drain sequence is complete.
- In task_3, always call migrate_traffic THEN wait BEFORE terminating us-east-1 production resources.
- Watch for dependency_of fields — do not terminate a volume that another resource depends on.
- Prefer safe actions: terminate orphans first, then resize oversized VMs, then cold-migrate stale storage.
"""

def _build_gpt_prompt(obs: Observation, task_description: str) -> str:
    resources_json = json.dumps(
        [r.model_dump() for r in obs.resources],
        indent=2,
        default=str,
    )
    return f"""TASK: {obs.task_id}
DESCRIPTION: {task_description}
STEP: {obs.step}/{obs.max_steps}
MONTHLY BILL: ${obs.monthly_bill_current:,.2f} (started at ${obs.monthly_bill_start:,.2f})
SAVINGS ACHIEVED: ${obs.savings_achieved:,.2f} / TARGET: ${obs.savings_target:,.2f}
DOWNTIME EVENTS: {obs.downtime_events}
HONEYPOT HITS: {obs.honeypot_hits}
SEQUENCE VIOLATIONS: {obs.sequence_violations}
TRAFFIC MIGRATED FROM: {obs.traffic_migrated_from or "none"}
CONNECTIONS DRAINED: {obs.connections_drained}
FEEDBACK (last action): {obs.feedback}

RESOURCES (current active):
{resources_json}

Choose ONE action to take. Return only JSON."""


def _call_gpt(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Call GPT-4o and parse the JSON action. Returns None on any failure."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as exc:
        print(f"  [GPT error] {exc}", file=sys.stderr)
        return None


def _parse_action(raw: Dict[str, Any]) -> Optional[Action]:
    """Convert raw dict to validated Action model. Returns None on bad input."""
    try:
        return Action(**raw)
    except Exception as exc:
        print(f"  [Action parse error] {raw} → {exc}", file=sys.stderr)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Heuristic fallback agent
# ══════════════════════════════════════════════════════════════════════════════

# Thresholds for the heuristic
HEURISTIC_CPU_IDLE_THRESHOLD  = 10.0   # % — below this → safe to resize
HEURISTIC_TRAFFIC_IDLE        = 200    # req/hr — below this → treat as unused
HEURISTIC_COLD_DAYS_THRESHOLD = 240    # days since last access → cold-migrate
HEURISTIC_RESIZE_TARGET       = InstanceSize.SMALL  # default resize target


def _is_orphan(r: AgentResource) -> bool:
    """Heuristic: resource looks like safe waste."""
    has_no_traffic = (r.traffic_per_hour is None or r.traffic_per_hour < HEURISTIC_TRAFFIC_IDLE)
    has_no_attachment = r.attached_to is None
    has_no_dependency = not r.dependency_of
    is_stopped = (r.status is not None and str(r.status) in ("stopped", "ResourceStatus.STOPPED"))
    cpu_idle = r.cpu_avg_24h is None or r.cpu_avg_24h < 1.0

    if r.resource_type in (ResourceType.IP_ADDRESS,):
        return has_no_traffic and has_no_attachment

    if r.resource_type == ResourceType.SNAPSHOT:
        return True  # old snapshots are always waste

    if str(r.resource_type) in ("ip_address",):
        return has_no_traffic and has_no_attachment

    if is_stopped:
        return cpu_idle and has_no_traffic

    return False


def _is_cold_candidate(r: AgentResource) -> bool:
    """Heuristic: storage volume that should be cold-migrated."""
    return (
        str(r.resource_type) in ("storage", "ResourceType.STORAGE")
        and str(r.storage_tier) in ("hot", "StorageTier.HOT")
        and r.last_accessed_days_ago is not None
        and r.last_accessed_days_ago >= HEURISTIC_COLD_DAYS_THRESHOLD
        and not r.dependency_of  # don't migrate volumes that things depend on
    )


def _is_oversized(r: AgentResource) -> bool:
    """Heuristic: VM or DB with low CPU and large/xlarge size."""
    return (
        str(r.resource_type) in ("vm", "database", "ResourceType.VM", "ResourceType.DATABASE")
        and r.instance_size is not None
        and str(r.instance_size) in ("large", "xlarge", "InstanceSize.LARGE", "InstanceSize.XLARGE")
        and r.cpu_avg_24h is not None
        and r.cpu_avg_24h < HEURISTIC_CPU_IDLE_THRESHOLD
        and (r.traffic_per_hour is None or r.traffic_per_hour < 5_000)
        and not r.dependency_of
    )


def _choose_resize_target(current_size_str: str) -> InstanceSize:
    """Drop two tiers for large/xlarge, one tier for others."""
    cs = current_size_str.lower().replace("instancesize.", "")
    idx = INSTANCE_SIZE_ORDER.index(cs) if cs in INSTANCE_SIZE_ORDER else -1
    # Drop two tiers (but not below nano)
    target_idx = max(0, idx - 2)
    return InstanceSize(INSTANCE_SIZE_ORDER[target_idx])


def _is_dangerous_tag_lie(r: AgentResource) -> bool:
    """
    Task 3 trap 2 defence: resource tagged 'dev' but has real traffic.
    Do not let heuristic terminate it.
    """
    dev_tag = r.tags.get("env", "") == "dev"
    has_real_traffic = r.traffic_per_hour is not None and r.traffic_per_hour > 1_000
    return dev_tag and has_real_traffic


def _heuristic_action(obs: Observation) -> Optional[Action]:
    """
    Deterministic rule-based agent.

    Priority order:
      1. Task 3 — do migrate_traffic if not done, then wait.
      2. Terminate obvious orphans (IPs, snapshots, stopped VMs).
      3. Cold-migrate stale hot storage.
      4. Resize oversized low-CPU VMs/DBs.
      5. None → episode ends naturally.
    """
    task = obs.task_id
    resources = obs.resources

    # ── Task 3: sequence step ─────────────────────────────────────────────────
    if task == "task_3":
        if obs.traffic_migrated_from is None:
            # Step 1: migrate traffic away from east-1
            return Action(
                action_type=ActionType.MIGRATE_TRAFFIC,
                source_region="us-east-1",
            )
        if not obs.connections_drained:
            # Step 2: drain
            return Action(action_type=ActionType.WAIT)

    # ── Terminate orphans ─────────────────────────────────────────────────────
    for r in resources:
        # Skip tag-lie traps in Task 3
        if task == "task_3" and _is_dangerous_tag_lie(r):
            continue
        # Skip if it has dependency_of set (Trap 3 defence)
        if r.dependency_of:
            continue
        if _is_orphan(r):
            return Action(action_type=ActionType.TERMINATE, resource_id=r.id)

    # ── Cold-migrate stale storage ────────────────────────────────────────────
    for r in resources:
        if _is_cold_candidate(r):
            return Action(
                action_type=ActionType.MIGRATE_STORAGE,
                resource_id=r.id,
                target_tier=StorageTier.COLD,
            )

    # ── Resize oversized VMs ──────────────────────────────────────────────────
    for r in resources:
        if task == "task_3" and _is_dangerous_tag_lie(r):
            continue
        if _is_oversized(r):
            current_str = (
                r.instance_size.value
                if hasattr(r.instance_size, "value")
                else str(r.instance_size)
            )
            target = _choose_resize_target(current_str)
            # Sanity: target must be strictly smaller
            try:
                cur_idx = INSTANCE_SIZE_ORDER.index(
                    current_str.lower().replace("instancesize.", "")
                )
                tgt_idx = INSTANCE_SIZE_ORDER.index(target.value)
                if tgt_idx < cur_idx:
                    return Action(
                        action_type=ActionType.RESIZE,
                        resource_id=r.id,
                        new_size=target,
                    )
            except ValueError:
                continue

    # ── Task 3: after drain, terminate east-1 production ─────────────────────
    if task == "task_3" and obs.connections_drained:
        east1_production_ids = {
            "vm-east-api", "vm-east-payment", "lb-east-main",
            "vm-east-checkout", "db-east-postgres", "vm-east-auth",
            "vol-east-db-primary", "vm-east-frontend-1",
            "vm-east-frontend-2", "cdn-east-assets",
        }
        for r in resources:
            if r.id in east1_production_ids:
                return Action(action_type=ActionType.TERMINATE, resource_id=r.id)

    return None  # nothing left to do


# ══════════════════════════════════════════════════════════════════════════════
# Episode runner
# ══════════════════════════════════════════════════════════════════════════════

TASK_DESCRIPTIONS = {
    "task_1": (
        "Identify and terminate all 8 orphaned resources (unattached IPs, "
        "detached volumes, stopped VMs). Do not touch production resources."
    ),
    "task_2": (
        "Resize oversized VMs (cpu < 10%, instance_size LARGE/XLARGE) and "
        "cold-migrate stale storage (last_accessed > 240 days). "
        "Target: $6,000/month savings."
    ),
    "task_3": (
        "Shut down the us-east-1 legacy region to save ~$8,400/month. "
        "SEQUENCE: call migrate_traffic(source_region='us-east-1') FIRST, "
        "then wait(), then terminate east-1 resources. "
        "Also clean west-2 waste. Beware honeypots: low cpu_avg but high peak load. "
        "Watch dependency_of fields. Resources tagged 'dev' may have real traffic."
    ),
}


def run_task(
    task_id: str,
    api_key: Optional[str],
    verbose: bool = True,
) -> Tuple[GraderResult, int]:
    """
    Run one full episode.  Returns (GraderResult, steps_taken).
    Uses GPT-4o if api_key is provided; falls back to heuristic on any failure.
    """
    env = FinOpsEnv()
    obs = env.reset(task_id)
    task_desc = TASK_DESCRIPTIONS.get(task_id, "Optimize cloud costs.")
    use_gpt = bool(api_key)
    steps = 0
    consecutive_noop = 0  # heuristic returns None → stop early

    if verbose:
        print(f"\n{'─'*60}")
        print(f"  {task_id.upper()}  |  bill=${obs.monthly_bill_start:,.0f}  "
              f"target_savings=${obs.savings_target:,.0f}  max_steps={obs.max_steps}")
        print(f"  Agent: {'GPT-4o' if use_gpt else 'heuristic-fallback'}")
        print(f"{'─'*60}")

    while steps < obs.max_steps:
        action = None

        # Try GPT-4o
        if use_gpt:
            prompt = _build_gpt_prompt(obs, task_desc)
            raw = _call_gpt(prompt, api_key)
            if raw:
                action = _parse_action(raw)

        # Fallback to heuristic
        if action is None:
            action = _heuristic_action(obs)

        if action is None:
            consecutive_noop += 1
            if verbose:
                print(f"  step {steps+1:2d}: no action available — stopping early.")
            if consecutive_noop >= 2:
                break
            continue
        else:
            consecutive_noop = 0

        result = env.step(action)
        steps += 1
        obs = result.observation

        if verbose:
            reward_str = f"{result.reward:+,.0f}"
            savings_str = f"${obs.savings_achieved:,.0f}"
            print(
                f"  step {steps:2d}: {action.action_type.value:<16} "
                f"resource={getattr(action, 'resource_id', None) or getattr(action, 'source_region', None) or '—':<28} "
                f"reward={reward_str:>8}  saved={savings_str}"
            )

        if result.done:
            if verbose:
                print(f"  Episode done at step {steps}.")
            break

        # Small delay to avoid hammering the OpenAI API
        if use_gpt:
            time.sleep(0.5)

    grade = run_grader(env)

    if verbose:
        print(f"\n  SCORE:       {grade.score:.4f}")
        print(f"  Saved:       ${grade.money_saved:,.2f}")
        print(f"  Downtime:    {grade.downtime_events}")
        print(f"  False kills: {grade.false_kills}")
        print(f"  Honeypots:   {grade.honeypot_hits}")
        print(f"  Seq viol:    {grade.sequence_violations}")
        print(f"  Message:     {grade.message}")

    return grade, steps


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Cloud FinOps baseline agent.")
    parser.add_argument("--json",  action="store_true", help="Emit JSON to stdout.")
    parser.add_argument("--task",  type=str, default=None,
                        help="Run one task only (task_1 / task_2 / task_3).")
    args = parser.parse_args()

    api_key  = os.environ.get("OPENAI_API_KEY")
    verbose  = not args.json
    tasks    = [args.task] if args.task else ["task_1", "task_2", "task_3"]

    results: List[TaskBaselineResult] = []

    for task_id in tasks:
        grade, steps = run_task(task_id, api_key, verbose=verbose)
        results.append(
            TaskBaselineResult(
                task_id=task_id,
                score=grade.score,
                money_saved=grade.money_saved,
                steps_taken=steps,
                downtime_events=grade.downtime_events,
                notes=grade.message,
            )
        )

    mean_score = sum(r.score for r in results) / len(results) if results else 0.0
    model_used = f"gpt-4o" if api_key else "heuristic-fallback"

    baseline_result = BaselineResult(
        model_used=model_used,
        results=results,
        mean_score=round(mean_score, 4),
    )

    if args.json:
        # Consumed by POST /baseline — must be clean JSON on stdout
        print(json.dumps(baseline_result.model_dump(), default=str))
    else:
        print(f"\n{'═'*60}")
        print(f"  BASELINE SUMMARY  ({model_used})")
        print(f"{'═'*60}")
        for r in results:
            print(f"  {r.task_id}: score={r.score:.4f}  saved=${r.money_saved:,.0f}"
                  f"  steps={r.steps_taken}  downtime={r.downtime_events}")
        print(f"  MEAN SCORE: {mean_score:.4f}")
        print(f"{'═'*60}")


if __name__ == "__main__":
    main()
