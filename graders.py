# graders.py
# Cloud FinOps Sandbox — OpenEnv submission
# Task-specific scoring functions.  Called at episode end via env.grade().
#
# Design notes:
#   - Each grader function operates on a *live* FinOpsEnv instance so it can
#     inspect env._resources (the mutated post-episode state), env._false_kills,
#     env._honeypot_hits, env._sequence_violations, env._downtime_events, and
#     env._initial_bill.
#   - env.grade() already computes the canonical GraderResult; these helpers
#     add task-specific breakdown commentary and assertion checks on top.
#   - All scores are clamped to [0.0, 1.0].
#   - Import-safe: no circular imports.  graders.py imports from environment.py.
from __future__ import annotations

from typing import TYPE_CHECKING

from models import GraderBreakdown, GraderResult

if TYPE_CHECKING:
    from environment import FinOpsEnv


# ══════════════════════════════════════════════════════════════════════════════
# Constants — must match TASK_META in resources.py
# ══════════════════════════════════════════════════════════════════════════════

TASK_1_SAVINGS_TARGET = 705.00
TASK_2_SAVINGS_TARGET = 6_000.00
TASK_3_SAVINGS_TARGET = 15_000.00

# Grader penalty weights (per event)
T1_FALSE_KILL_PENALTY  = 0.20   # per active resource incorrectly terminated
T1_DOWNTIME_PENALTY    = 0.20   # per downtime event

T2_DOWNTIME_PENALTY    = 0.20   # per downtime event
T2_FALSE_KILL_PENALTY  = 0.20   # per false kill

T3_DOWNTIME_PENALTY    = 0.20   # per downtime event
T3_HONEYPOT_PENALTY    = 0.25   # per honeypot hit
T3_SEQUENCE_PENALTY    = 0.15   # per sequence violation

# IDs the Task 1 grader checks — exactly the 8 safe orphans in resources.py
TASK_1_ORPHAN_IDS: frozenset[str] = frozenset({
    "ip-unused-001",
    "ip-unused-002",
    "vol-orphan-001",
    "vol-orphan-002",
    "vol-orphan-003",
    "vm-stopped-001",
    "vm-stopped-002",
    "snapshot-old-001",
})

# IDs that require the migrate_traffic + wait sequence before termination
EAST_1_PRODUCTION_IDS: frozenset[str] = frozenset({
    "vm-east-api",
    "vm-east-payment",
    "lb-east-main",
    "vm-east-checkout",
    "db-east-postgres",
    "vm-east-auth",
    "vol-east-db-primary",
    "vm-east-frontend-1",
    "vm-east-frontend-2",
    "cdn-east-assets",
})


# ══════════════════════════════════════════════════════════════════════════════
# Internal utility
# ══════════════════════════════════════════════════════════════════════════════

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ══════════════════════════════════════════════════════════════════════════════
# Task 1 grader — Orphan Cleanup
# ══════════════════════════════════════════════════════════════════════════════

def grade_task_1(env: "FinOpsEnv") -> GraderResult:
    """
    Score = (orphans_deleted / 8) - (false_kills × 0.20) - (downtime_events × 0.20)
    Clamped to [0.0, 1.0].

    A perfect run deletes all 8 orphans without touching anything else → 1.0.
    Each incorrectly terminated production resource subtracts 0.20.
    """
    if env._task_id != "task_1":
        raise ValueError(f"grade_task_1 called on task '{env._task_id}'.")

    # Count how many of the 8 orphan IDs are no longer active
    surviving_ids = {rid for rid, r in env._resources.items() if r.is_active}
    orphans_deleted = sum(
        1 for oid in TASK_1_ORPHAN_IDS if oid not in surviving_ids
    )
    total_orphans = len(TASK_1_ORPHAN_IDS)  # 8

    # Count false kills: active production resources that were deleted
    # env._false_kills tracks this during episode
    false_kills    = env._false_kills
    downtime_events = env._downtime_events

    placement_score   = orphans_deleted / total_orphans
    false_kill_penalty = false_kills    * T1_FALSE_KILL_PENALTY
    downtime_penalty   = downtime_events * T1_DOWNTIME_PENALTY

    # Note: downtime overlaps false_kills — we cap combined penalty to avoid
    # double-counting the same incident.  Use the larger of the two.
    combined_penalty = max(false_kill_penalty, downtime_penalty)
    raw = placement_score - combined_penalty
    final = _clamp(raw)

    # Savings for display (may differ from target if agent under/over-performed)
    current_bill = sum(
        r.monthly_cost for r in env._resources.values() if r.is_active
    )
    money_saved = round(env._initial_bill - current_bill, 2)

    # Verdict string
    if final >= 0.90:
        verdict = "Excellent — all orphans cleaned up, no false kills."
    elif final >= 0.70:
        verdict = "Good — most orphans removed with minimal damage."
    elif final >= 0.40:
        verdict = "Partial — some orphans missed or production resources harmed."
    else:
        verdict = "Poor — too many false kills or orphans left behind."

    breakdown = GraderBreakdown(
        savings_ratio=round(placement_score, 4),       # reuses field: orphan ratio
        downtime_penalty=round(combined_penalty, 4),
        false_kill_penalty=round(false_kill_penalty, 4),
        honeypot_penalty=0.0,
        sequence_penalty=0.0,
        final_score=round(final, 4),
    )

    return GraderResult(
        task_id="task_1",
        score=round(final, 4),
        money_saved=money_saved,
        savings_target=TASK_1_SAVINGS_TARGET,
        downtime_events=downtime_events,
        false_kills=false_kills,
        honeypot_hits=0,
        sequence_violations=0,
        breakdown=breakdown,
        message=(
            f"{verdict} "
            f"Deleted {orphans_deleted}/{total_orphans} orphans. "
            f"False kills: {false_kills}. "
            f"Saved ${money_saved:,.0f} of ${TASK_1_SAVINGS_TARGET:,.0f} target."
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Task 2 grader — Rightsizing & Cold Migration
# ══════════════════════════════════════════════════════════════════════════════

def grade_task_2(env: "FinOpsEnv") -> GraderResult:
    """
    Score = (savings_achieved / $6,000) - (downtime_events × 0.20) - (false_kills × 0.20)
    Clamped to [0.0, 1.0].

    Max achievable savings ≈ $4,600 → max honest score ≈ 0.77.
    Agent cannot hit 1.0 without causing downtime on high-CPU machines.
    """
    if env._task_id != "task_2":
        raise ValueError(f"grade_task_2 called on task '{env._task_id}'.")

    current_bill = sum(
        r.monthly_cost for r in env._resources.values() if r.is_active
    )
    money_saved = round(env._initial_bill - current_bill, 2)

    savings_ratio      = _clamp(money_saved / TASK_2_SAVINGS_TARGET)
    downtime_penalty   = env._downtime_events * T2_DOWNTIME_PENALTY
    false_kill_penalty = env._false_kills     * T2_FALSE_KILL_PENALTY

    raw   = savings_ratio - downtime_penalty - false_kill_penalty
    final = _clamp(raw)

    if final >= 0.70:
        verdict = "Good — solid rightsizing and cold migration."
    elif final >= 0.45:
        verdict = "Partial — some savings achieved but room to improve."
    else:
        verdict = "Poor — insufficient savings or too many penalties."

    breakdown = GraderBreakdown(
        savings_ratio=round(savings_ratio, 4),
        downtime_penalty=round(downtime_penalty, 4),
        false_kill_penalty=round(false_kill_penalty, 4),
        honeypot_penalty=0.0,
        sequence_penalty=0.0,
        final_score=round(final, 4),
    )

    return GraderResult(
        task_id="task_2",
        score=round(final, 4),
        money_saved=money_saved,
        savings_target=TASK_2_SAVINGS_TARGET,
        downtime_events=env._downtime_events,
        false_kills=env._false_kills,
        honeypot_hits=0,
        sequence_violations=0,
        breakdown=breakdown,
        message=(
            f"{verdict} "
            f"Saved ${money_saved:,.0f} of ${TASK_2_SAVINGS_TARGET:,.0f} target. "
            f"Downtime events: {env._downtime_events}. "
            f"False kills: {env._false_kills}."
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Task 3 grader — Multi-Region Failover & Shutdown
# ══════════════════════════════════════════════════════════════════════════════

def grade_task_3(env: "FinOpsEnv") -> GraderResult:
    """
    Score = (savings / $15,000)
            - (downtime_events  × 0.20)
            - (honeypot_hits    × 0.25)
            - (sequence_violations × 0.15)
    Clamped to [0.0, 1.0].

    Safe savings (no honeypots, correct sequence) ≈ $8,400 → raw ≈ 0.56.
    Hitting all 3 honeypots wipes ~0.75 from the score.
    Perfect play: correctly sequence-drain + terminate east-1 PLUS find west-2
    waste → approach 1.0.
    """
    if env._task_id != "task_3":
        raise ValueError(f"grade_task_3 called on task '{env._task_id}'.")

    current_bill = sum(
        r.monthly_cost for r in env._resources.values() if r.is_active
    )
    money_saved = round(env._initial_bill - current_bill, 2)

    savings_ratio    = _clamp(money_saved / TASK_3_SAVINGS_TARGET)
    downtime_penalty = env._downtime_events     * T3_DOWNTIME_PENALTY
    honeypot_penalty = env._honeypot_hits       * T3_HONEYPOT_PENALTY
    sequence_penalty = env._sequence_violations * T3_SEQUENCE_PENALTY

    raw   = savings_ratio - downtime_penalty - honeypot_penalty - sequence_penalty
    final = _clamp(raw)

    # Extra diagnostic: did the agent complete the sequence correctly?
    sequence_done = env._traffic_migrated_from is not None and env._all_connections_drained()

    if final >= 0.80:
        verdict = "Excellent — near-perfect multi-region shutdown."
    elif final >= 0.50:
        verdict = "Good — solid savings, sequence mostly respected."
    elif final >= 0.25:
        verdict = "Partial — some savings but penalties dragged score down."
    else:
        verdict = "Poor — honeypots triggered or sequence badly violated."

    breakdown = GraderBreakdown(
        savings_ratio=round(savings_ratio, 4),
        downtime_penalty=round(downtime_penalty, 4),
        false_kill_penalty=0.0,
        honeypot_penalty=round(honeypot_penalty, 4),
        sequence_penalty=round(sequence_penalty, 4),
        final_score=round(final, 4),
    )

    return GraderResult(
        task_id="task_3",
        score=round(final, 4),
        money_saved=money_saved,
        savings_target=TASK_3_SAVINGS_TARGET,
        downtime_events=env._downtime_events,
        false_kills=env._false_kills,
        honeypot_hits=env._honeypot_hits,
        sequence_violations=env._sequence_violations,
        breakdown=breakdown,
        message=(
            f"{verdict} "
            f"Saved ${money_saved:,.0f} of ${TASK_3_SAVINGS_TARGET:,.0f} target. "
            f"Sequence completed: {sequence_done}. "
            f"Honeypot hits: {env._honeypot_hits}. "
            f"Sequence violations: {env._sequence_violations}. "
            f"Downtime events: {env._downtime_events}."
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Dispatcher — called by server.py and baseline.py
# ══════════════════════════════════════════════════════════════════════════════

def run_grader(env: "FinOpsEnv") -> GraderResult:
    """
    Route to the correct task grader.  Falls back to env.grade() for
    unknown task IDs so the server never throws a 500.
    """
    task_id = env._task_id
    if task_id == "task_1":
        return grade_task_1(env)
    elif task_id == "task_2":
        return grade_task_2(env)
    elif task_id == "task_3":
        return grade_task_3(env)
    else:
        # Generic fallback — uses env's built-in grade()
        return env.grade()
