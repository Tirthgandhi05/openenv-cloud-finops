# graders.py
# Cloud FinOps Sandbox — deterministic episode scoring.
from __future__ import annotations

from models import GraderBreakdown, GraderResult

# ── Penalty weights ────────────────────────────────────────────────────────────
# These MUST match the constants in environment.py exactly.
GRADER_DOWNTIME_PENALTY   = 0.20
GRADER_FALSE_KILL_PENALTY = 0.20
GRADER_HONEYPOT_PENALTY   = 0.20   # per honeypot hit (Task 3)
GRADER_SEQUENCE_PENALTY   = 0.15   # per sequence violation (Task 3)


def run_grader(env) -> GraderResult:
    """
    Score a completed (or in-progress) episode.
    Accepts a FinOpsEnv instance directly.
    Returns GraderResult with score in [0.0, 1.0].
    """
    current_bill = env._current_bill()
    money_saved  = env._initial_bill - current_bill
    target       = env._savings_target

    savings_ratio      = min(1.0, money_saved / target) if target > 0 else 0.0
    downtime_penalty   = env._downtime_events     * GRADER_DOWNTIME_PENALTY
    false_kill_penalty = env._false_kills         * GRADER_FALSE_KILL_PENALTY
    honeypot_penalty   = env._honeypot_hits       * GRADER_HONEYPOT_PENALTY
    sequence_penalty   = env._sequence_violations * GRADER_SEQUENCE_PENALTY

    raw   = savings_ratio - downtime_penalty - false_kill_penalty
    raw  -= honeypot_penalty + sequence_penalty
    final = max(0.0, min(1.0, raw))

    breakdown = GraderBreakdown(
        savings_ratio=round(savings_ratio, 4),
        downtime_penalty=round(downtime_penalty, 4),
        false_kill_penalty=round(false_kill_penalty, 4),
        honeypot_penalty=round(honeypot_penalty, 4),
        sequence_penalty=round(sequence_penalty, 4),
        final_score=round(final, 4),
    )

    if final >= 0.85:
        verdict = "Excellent — top-tier optimization."
    elif final >= 0.60:
        verdict = "Good — solid savings with acceptable risk."
    elif final >= 0.35:
        verdict = "Partial — room for improvement."
    else:
        verdict = "Poor — honeypots triggered or sequence badly violated."

    task_id = env._task_id

    if task_id == "task_1":
        from resources import TASK_1_ORPHAN_IDS
        remaining_orphans = sum(
            1 for rid in TASK_1_ORPHAN_IDS
            if rid in env._resources and env._resources[rid].is_active
        )
        deleted_orphans = len(TASK_1_ORPHAN_IDS) - remaining_orphans
        detail = (
            f"Deleted {deleted_orphans}/{len(TASK_1_ORPHAN_IDS)} orphans. "
            f"False kills: {env._false_kills}. "
            f"Saved ${money_saved:,.0f} of ${target:,.0f} target."
        )
    elif task_id == "task_2":
        detail = (
            f"Saved ${money_saved:,.0f} of ${target:,.0f} target. "
            f"Downtime events: {env._downtime_events}. "
            f"False kills: {env._false_kills}."
        )
    else:
        # Task 3 — include sequence completion and breakdown details
        detail = (
            f"Saved ${money_saved:,.0f} of ${target:,.0f} target. "
            f"Sequence completed: {env._all_connections_drained()}. "
            f"Honeypot hits: {env._honeypot_hits}. "
            f"Sequence violations: {env._sequence_violations}. "
            f"Downtime events: {env._downtime_events}. "
            f"Breakdown: savings={savings_ratio:.3f} "
            f"-downtime={downtime_penalty:.2f} "
            f"-honeypot={honeypot_penalty:.2f} "
            f"-sequence={sequence_penalty:.2f} "
            f"= {final:.4f}"
        )

    return GraderResult(
        task_id=task_id,
        score=round(final, 4),
        money_saved=round(money_saved, 2),
        savings_target=target,
        downtime_events=env._downtime_events,
        false_kills=env._false_kills,
        honeypot_hits=env._honeypot_hits,
        sequence_violations=env._sequence_violations,
        breakdown=breakdown,
        message=f"{verdict} {detail}",
    )
