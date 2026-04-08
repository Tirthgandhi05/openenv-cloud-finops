# environment.py
# Cloud FinOps Sandbox — OpenEnv submission
# NovaCart infrastructure simulation — Game Engine
from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple

from models import (
    Action,
    ActionType,
    AgentResource,
    GraderBreakdown,
    GraderResult,
    INSTANCE_SIZE_COST_MULTIPLIER,
    INSTANCE_SIZE_ORDER,
    Observation,
    Resource,
    ResourceStatus,
    ResourceType,
    StepResult,
    StorageTier,
)
from resources import TASKS, TASK_META


# ══════════════════════════════════════════════════════════════════════════════
# Reward weights  (tune these to make scoring feel right)
# ══════════════════════════════════════════════════════════════════════════════

W_SAVINGS        = 1.0    # reward per $ saved per month
W_DOWNTIME       = 8_000  # penalty per downtime event (killing active resource)
W_HONEYPOT       = 8_000  # penalty per honeypot hit (Task 3)
W_SEQUENCE       = 3_000  # penalty per sequence violation (Task 3)
W_FALSE_KILL     = 5_000  # extra penalty for terminating is_production resource
W_WASTED_ACTION  = 10     # small penalty for acting on already-optimized resource
W_WAIT_STEP      = 5      # tiny penalty for WAIT steps (opportunity cost)


# ══════════════════════════════════════════════════════════════════════════════
# Grader weights  — MUST match graders.py exactly
# ══════════════════════════════════════════════════════════════════════════════

GRADER_DOWNTIME_PENALTY    = 0.20   # per event, subtracted from score
GRADER_FALSE_KILL_PENALTY  = 0.20   # per false kill
GRADER_HONEYPOT_PENALTY    = 0.20   # per honeypot hit (Task 3)  ← aligned to graders.py
GRADER_SEQUENCE_PENALTY    = 0.15   # per sequence violation (Task 3)


# ══════════════════════════════════════════════════════════════════════════════
# Environment
# ══════════════════════════════════════════════════════════════════════════════

class FinOpsEnv:
    """
    Stateful FinOps simulation environment.

    Usage:
        env = FinOpsEnv()
        obs = env.reset("task_1")

        while not done:
            action = agent.act(obs)
            result = env.step(action)
            obs, reward, done = result.observation, result.reward, result.done

        grade = env.grade()
    """

    def __init__(self) -> None:
        self._task_id: Optional[str] = None
        self._resources: Dict[str, Resource] = {}     # id → Resource (mutable)
        self._initial_bill: float = 0.0
        self._step: int = 0
        self._max_steps: int = 0
        self._downtime_events: int = 0
        self._honeypot_hits: int = 0
        self._sequence_violations: int = 0
        self._false_kills: int = 0
        self._regions: List[str] = []
        self._traffic_migrated_from: Optional[str] = None
        self._savings_target: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def reset(self, task_id: str) -> Observation:
        """
        Load a fresh task.  Returns the initial observation.
        Raises KeyError if task_id is not in {"task_1", "task_2", "task_3"}.
        """
        if task_id not in TASKS:
            raise KeyError(f"Unknown task_id '{task_id}'. Valid: {list(TASKS)}")

        meta = TASK_META[task_id]

        # Deep-copy so repeated resets don't share state
        raw = TASKS[task_id]
        self._resources = {r.id: r.model_copy(deep=True) for r in raw}

        self._task_id             = task_id
        self._initial_bill        = sum(r.monthly_cost for r in self._resources.values())
        self._step                = 0
        self._max_steps           = meta["max_steps"]
        self._savings_target      = meta["savings_target"]
        self._regions             = meta.get("regions", ["us-east-1"])
        self._downtime_events     = 0
        self._honeypot_hits       = 0
        self._sequence_violations = 0
        self._false_kills         = 0
        self._traffic_migrated_from = None

        return self._make_observation(feedback="Episode started. Good luck.")

    def step(self, action: Action) -> StepResult:
        """
        Apply one agent action.  Returns reward, done flag, and new observation.
        Raises RuntimeError if called before reset().
        """
        if self._task_id is None:
            raise RuntimeError("Call reset() before step().")

        self._step += 1
        done = False
        reward, feedback, info = self._apply_action(action)

        # Episode ends if max steps reached
        if self._step >= self._max_steps:
            done = True
            feedback += f" [Episode ended: max steps ({self._max_steps}) reached.]"

        obs = self._make_observation(feedback=feedback)
        return StepResult(reward=reward, done=done, info=info, observation=obs)

    def state(self) -> Observation:
        """Return current observation without advancing the step counter."""
        if self._task_id is None:
            raise RuntimeError("Call reset() before state().")
        return self._make_observation(feedback="State snapshot.")

    def grade(self) -> GraderResult:
        """
        Compute final episode score.  Can be called at any time after reset().
        """
        if self._task_id is None:
            raise RuntimeError("Call reset() before grade().")

        current_bill = self._current_bill()
        money_saved  = self._initial_bill - current_bill
        target       = self._savings_target

        savings_ratio      = min(1.0, money_saved / target) if target > 0 else 0.0
        downtime_penalty   = self._downtime_events   * GRADER_DOWNTIME_PENALTY
        false_kill_penalty = self._false_kills        * GRADER_FALSE_KILL_PENALTY
        honeypot_penalty   = self._honeypot_hits      * GRADER_HONEYPOT_PENALTY
        sequence_penalty   = self._sequence_violations * GRADER_SEQUENCE_PENALTY

        raw_score  = savings_ratio - downtime_penalty - false_kill_penalty
        raw_score -= honeypot_penalty + sequence_penalty
        final      = max(0.0, min(1.0, raw_score))

        breakdown = GraderBreakdown(
            savings_ratio=round(savings_ratio, 4),
            downtime_penalty=round(downtime_penalty, 4),
            false_kill_penalty=round(false_kill_penalty, 4),
            honeypot_penalty=round(honeypot_penalty, 4),
            sequence_penalty=round(sequence_penalty, 4),
            final_score=round(final, 4),
        )

        # Human-readable summary message
        if final >= 0.85:
            verdict = "Excellent — top-tier optimization."
        elif final >= 0.60:
            verdict = "Good — solid savings with acceptable risk."
        elif final >= 0.35:
            verdict = "Partial — room for improvement."
        else:
            verdict = "Poor — too many penalties or insufficient savings."

        return GraderResult(
            task_id=self._task_id,
            score=round(final, 4),
            money_saved=round(money_saved, 2),
            savings_target=target,
            downtime_events=self._downtime_events,
            false_kills=self._false_kills,
            honeypot_hits=self._honeypot_hits,
            sequence_violations=self._sequence_violations,
            breakdown=breakdown,
            message=f"{verdict} Saved ${money_saved:,.0f} of ${target:,.0f} target.",
        )

    # ── Action dispatch ───────────────────────────────────────────────────────

    def _apply_action(
        self, action: Action
    ) -> Tuple[float, str, dict]:
        """
        Route action to the correct handler.
        Returns (reward, feedback_message, info_dict).
        """
        t = action.action_type

        if t == ActionType.TERMINATE:
            return self._handle_terminate(action)
        elif t == ActionType.RESIZE:
            return self._handle_resize(action)
        elif t == ActionType.MIGRATE_STORAGE:
            return self._handle_migrate_storage(action)
        elif t == ActionType.MIGRATE_TRAFFIC:
            return self._handle_migrate_traffic(action)
        elif t == ActionType.WAIT:
            return self._handle_wait(action)
        else:
            return 0.0, f"Unknown action type '{t}'.", {"error": "unknown_action"}

    # ── Terminate ─────────────────────────────────────────────────────────────

    def _handle_terminate(self, action: Action) -> Tuple[float, str, dict]:
        resource = self._get_resource(action.resource_id)
        if resource is None:
            return 0.0, f"Resource '{action.resource_id}' not found.", {"error": "not_found"}

        if not resource.is_active:
            return (
                -W_WASTED_ACTION,
                f"{resource.name} is already {resource.status} — no action taken.",
                {"warning": "already_inactive"},
            )

        # ── Task 3: sequence enforcement ─────────────────────────────────────
        # Terminating a us-east-1 production resource without draining first
        # is a sequence violation.
        if (
            self._task_id == "task_3"
            and resource.region == "us-east-1"
            and resource.is_production
            and not resource.traffic_migrated
        ):
            self._sequence_violations += 1
            self._downtime_events += 1
            penalty = W_SEQUENCE + W_DOWNTIME
            return (
                -penalty,
                (
                    f"SEQUENCE VIOLATION: You terminated {resource.name} in us-east-1 "
                    f"before calling migrate_traffic. Traffic was not drained. "
                    f"Production outage! Penalty: -${penalty:,.0f}"
                ),
                {"penalty_reason": "sequence_violation", "penalty": penalty},
            )

        # ── Task 3: east-1 production UNLOCKED after full drain sequence ──────
        # After migrate_traffic(us-east-1) + wait, connections_drained=True.
        # These resources are now safe to terminate — do NOT fall through to
        # the generic safe_to_terminate=False penalty below.
        east1_unlocked = (
            self._task_id == "task_3"
            and resource.region == "us-east-1"
            and resource.is_production
            and resource.connections_drained
        )

        # ── Honeypot check (Task 3) ───────────────────────────────────────────
        # Only applies to resources that are NOT unlocked east-1 resources.
        if self._task_id == "task_3" and not resource.safe_to_terminate and not east1_unlocked:
            if resource.peak_cpu_2am or resource.peak_queries_2am:
                self._honeypot_hits += 1
                self._downtime_events += 1
                penalty = W_HONEYPOT + W_DOWNTIME
                return (
                    -penalty,
                    (
                        f"HONEYPOT HIT: {resource.name} looks idle on 24h average, "
                        f"but runs critical batch jobs at 02:00. "
                        f"Destroying it caused a production outage. Penalty: -${penalty:,.0f}"
                    ),
                    {"penalty_reason": "honeypot_hit", "penalty": penalty},
                )

        # ── Active production resource (Tasks 1–3) ───────────────────────────
        # east1_unlocked resources bypass this check — they are safe to delete.
        if not resource.safe_to_terminate and not east1_unlocked:
            self._downtime_events += 1
            if resource.is_production:
                self._false_kills += 1
                penalty = W_DOWNTIME + W_FALSE_KILL
            else:
                penalty = W_DOWNTIME
            resource.status = ResourceStatus.DELETED
            return (
                -penalty,
                (
                    f"DISASTER: {resource.name} is an active production resource "
                    f"(traffic={resource.traffic_per_hour}/hr, "
                    f"cpu={resource.cpu_avg_24h}%). Terminating it caused downtime. "
                    f"Penalty: -${penalty:,.0f}"
                ),
                {"penalty_reason": "active_resource_killed", "penalty": penalty},
            )

        # ── Safe termination (includes unlocked east-1 resources) ────────────
        savings = resource.monthly_cost
        resource.status = ResourceStatus.DELETED
        reward = W_SAVINGS * savings
        return (
            reward,
            f"Terminated {resource.name}. Saved ${savings:,.2f}/month. +{reward:,.0f} reward.",
            {"savings_delta": savings},
        )

    # ── Resize ────────────────────────────────────────────────────────────────

    def _handle_resize(self, action: Action) -> Tuple[float, str, dict]:
        resource = self._get_resource(action.resource_id)
        if resource is None:
            return 0.0, f"Resource '{action.resource_id}' not found.", {"error": "not_found"}

        if resource.resource_type not in (ResourceType.VM, ResourceType.DATABASE):
            return (
                0.0,
                f"{resource.name} is a {resource.resource_type} — cannot resize.",
                {"error": "wrong_resource_type"},
            )

        if not resource.is_active:
            return (
                -W_WASTED_ACTION,
                f"{resource.name} is {resource.status} — cannot resize.",
                {"warning": "inactive_resource"},
            )

        current_size = resource.instance_size
        new_size     = action.new_size

        if current_size is None:
            return 0.0, f"{resource.name} has no instance_size set.", {"error": "no_size"}

        current_idx = INSTANCE_SIZE_ORDER.index(current_size.value if hasattr(current_size, 'value') else current_size)
        new_idx     = INSTANCE_SIZE_ORDER.index(new_size.value if hasattr(new_size, 'value') else new_size)

        if new_idx >= current_idx:
            return (
                -W_WASTED_ACTION,
                (
                    f"Cannot resize {resource.name} from {current_size} to {new_size} "
                    f"— must downsize to a smaller tier."
                ),
                {"warning": "not_a_downsize"},
            )

        # Penalty: resizing an actually-busy machine
        if not resource.safe_to_terminate and resource.cpu_avg_24h and resource.cpu_avg_24h > 60:
            self._downtime_events += 1
            penalty = W_DOWNTIME * 0.5   # half penalty for resize vs delete
            # Still apply the resize so agent sees the cost change
            old_cost = resource.monthly_cost
            new_cost = self._compute_resized_cost(resource, new_size)
            resource.monthly_cost  = new_cost
            resource.instance_size = new_size
            savings = old_cost - new_cost
            net = W_SAVINGS * savings - penalty
            return (
                net,
                (
                    f"WARNING: {resource.name} was at {resource.cpu_avg_24h:.1f}% CPU — "
                    f"resizing it caused a performance incident. "
                    f"Saved ${savings:,.2f}/month but incurred penalty. Net reward: {net:,.0f}"
                ),
                {"savings_delta": savings, "penalty": penalty},
            )

        old_cost = resource.monthly_cost
        new_cost = self._compute_resized_cost(resource, new_size)
        resource.monthly_cost  = new_cost
        resource.instance_size = new_size
        savings = old_cost - new_cost
        reward  = W_SAVINGS * savings

        return (
            reward,
            (
                f"Resized {resource.name} from {current_size} → {new_size}. "
                f"Saved ${savings:,.2f}/month. +{reward:,.0f} reward."
            ),
            {"savings_delta": savings},
        )

    # ── Migrate storage ───────────────────────────────────────────────────────

    def _handle_migrate_storage(self, action: Action) -> Tuple[float, str, dict]:
        resource = self._get_resource(action.resource_id)
        if resource is None:
            return 0.0, f"Resource '{action.resource_id}' not found.", {"error": "not_found"}

        if resource.resource_type != ResourceType.STORAGE:
            return (
                0.0,
                f"{resource.name} is not a storage volume — cannot migrate.",
                {"error": "wrong_resource_type"},
            )

        if resource.storage_tier == StorageTier.COLD:
            return (
                -W_WASTED_ACTION,
                f"{resource.name} is already in cold storage.",
                {"warning": "already_cold"},
            )

        # Penalty: migrating actively-accessed storage
        if resource.last_accessed_days_ago is not None and resource.last_accessed_days_ago < 30:
            self._downtime_events += 1
            penalty = W_DOWNTIME * 0.3
            old_cost = resource.monthly_cost
            new_cost = round(old_cost * 0.20, 2)   # cold = 20% of hot cost
            resource.monthly_cost = new_cost
            resource.storage_tier = StorageTier.COLD
            resource.status       = ResourceStatus.MIGRATED
            savings = old_cost - new_cost
            net = W_SAVINGS * savings - penalty
            return (
                net,
                (
                    f"WARNING: {resource.name} was accessed {resource.last_accessed_days_ago} days ago "
                    f"— migrating it to cold storage may affect active workflows. "
                    f"Saved ${savings:,.2f}/month but incurred penalty. Net: {net:,.0f}"
                ),
                {"savings_delta": savings, "penalty": penalty},
            )

        old_cost = resource.monthly_cost
        new_cost = round(old_cost * 0.20, 2)
        resource.monthly_cost = new_cost
        resource.storage_tier = StorageTier.COLD
        resource.status       = ResourceStatus.MIGRATED
        savings = old_cost - new_cost
        reward  = W_SAVINGS * savings

        return (
            reward,
            (
                f"Migrated {resource.name} to cold storage. "
                f"Cost: ${old_cost:,.2f} → ${new_cost:,.2f}/month. "
                f"Saved ${savings:,.2f}/month. +{reward:,.0f} reward."
            ),
            {"savings_delta": savings},
        )

    # ── Migrate traffic (Task 3) ──────────────────────────────────────────────

    def _handle_migrate_traffic(self, action: Action) -> Tuple[float, str, dict]:
        if self._task_id != "task_3":
            return (
                -W_WASTED_ACTION,
                "migrate_traffic is only valid in task_3.",
                {"warning": "wrong_task"},
            )

        source = action.source_region
        if source not in self._regions:
            return (
                0.0,
                f"Region '{source}' not found. Available: {self._regions}",
                {"error": "unknown_region"},
            )

        if self._traffic_migrated_from == source:
            return (
                -W_WASTED_ACTION,
                f"Traffic from {source} already migrated.",
                {"warning": "already_migrated"},
            )

        # Mark all resources in source region as traffic-migrated
        count = 0
        unlocked_savings = 0.0
        for r in self._resources.values():
            if r.region == source and r.is_active and r.is_production:
                r.traffic_migrated = True
                unlocked_savings += r.monthly_cost
                count += 1

        self._traffic_migrated_from = source

        # Small positive reward — previews the value this action unlocks.
        # Without this, the LLM has no incentive to call migrate_traffic first.
        preview_reward = round(unlocked_savings * 0.05, 2)

        return (
            preview_reward,
            (
                f"Traffic successfully migrated away from {source}. "
                f"{count} production resources marked for drain. "
                f"Now call WAIT to drain connections, then TERMINATE the infrastructure."
            ),
            {"migrated_region": source, "resources_affected": count},
        )

    # ── Wait / drain (Task 3) ─────────────────────────────────────────────────

    def _handle_wait(self, action: Action) -> Tuple[float, str, dict]:
        if self._task_id != "task_3":
            return (
                -W_WAIT_STEP,
                "WAIT has no effect outside task_3.",
                {"warning": "wrong_task"},
            )

        if self._traffic_migrated_from is None:
            self._sequence_violations += 1
            return (
                -W_SEQUENCE,
                (
                    "SEQUENCE VIOLATION: You called WAIT before MIGRATE_TRAFFIC. "
                    "There is no traffic to drain. Call migrate_traffic first."
                ),
                {"penalty_reason": "wait_before_migrate"},
            )

        if self._all_connections_drained():
            return (
                -W_WAIT_STEP,
                "Connections already drained. You can now safely terminate the region.",
                {"warning": "already_drained"},
            )

        # Drain connections on all resources in the migrated region
        source = self._traffic_migrated_from
        drained = 0
        for r in self._resources.values():
            if r.region == source and r.traffic_migrated and not r.connections_drained:
                r.connections_drained = True
                drained += 1

        # Return 0.0 (no penalty) on a correct, productive drain.
        # The opportunity cost of waiting is already priced in by the agent's
        # step budget; an extra -5 discourages the correct sequence.
        return (
            0.0,
            (
                f"Waiting for connection drain on {source}... "
                f"{drained} resources fully drained. "
                f"Safe to terminate {source} infrastructure now."
            ),
            {"drained_count": drained},
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_resource(self, resource_id: Optional[str]) -> Optional[Resource]:
        if resource_id is None:
            return None
        return self._resources.get(resource_id)

    def _current_bill(self) -> float:
        return sum(
            r.monthly_cost
            for r in self._resources.values()
            if r.is_active
        )

    def _active_resources(self) -> List[Resource]:
        return [r for r in self._resources.values() if r.is_active]

    def _all_connections_drained(self) -> bool:
        if self._traffic_migrated_from is None:
            return False
        source = self._traffic_migrated_from
        return all(
            r.connections_drained
            for r in self._resources.values()
            if r.region == source and r.is_production
        )

    def _compute_resized_cost(self, resource: Resource, new_size) -> float:
        """
        Compute new monthly cost after resizing.
        Uses base_cost_at_large if set, otherwise scales from current cost.
        """
        new_size_str = new_size.value if hasattr(new_size, 'value') else str(new_size)
        current_size_str = (
            resource.instance_size.value
            if hasattr(resource.instance_size, 'value')
            else str(resource.instance_size)
        )

        if resource.base_cost_at_large:
            # Preferred: use the anchored reference cost
            base   = resource.base_cost_at_large
            factor = INSTANCE_SIZE_COST_MULTIPLIER[new_size_str]
            return round(base * factor, 2)
        else:
            # Fallback: scale proportionally from current
            current_factor = INSTANCE_SIZE_COST_MULTIPLIER.get(current_size_str, 1.0)
            new_factor     = INSTANCE_SIZE_COST_MULTIPLIER[new_size_str]
            ratio = new_factor / current_factor if current_factor else 1.0
            return round(resource.monthly_cost * ratio, 2)

    def _make_observation(self, feedback: str = "") -> Observation:
        current_bill = self._current_bill()
        savings      = self._initial_bill - current_bill

        # Uptime calculation: each downtime event drops uptime by a fixed amount
        uptime = max(0.0, 100.0 - self._downtime_events * 5.0)

        # Only show active resources to agent (deleted/migrated disappear)
        visible = [
            r.to_agent_view()
            for r in self._resources.values()
            if r.is_active
        ]

        return Observation(
            task_id=self._task_id,
            step=self._step,
            max_steps=self._max_steps,
            monthly_bill_start=round(self._initial_bill, 2),
            monthly_bill_current=round(current_bill, 2),
            savings_target=self._savings_target,
            savings_achieved=round(savings, 2),
            uptime_percent=round(uptime, 2),
            downtime_events=self._downtime_events,
            regions=self._regions,
            traffic_migrated_from=self._traffic_migrated_from,
            connections_drained=self._all_connections_drained(),
            resources=visible,
            honeypot_hits=self._honeypot_hits,
            sequence_violations=self._sequence_violations,
            feedback=feedback,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Quick smoke-test — run directly: python environment.py
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from models import Action, ActionType, InstanceSize, StorageTier

    env = FinOpsEnv()

    for task_id in ("task_1", "task_2", "task_3"):
        print(f"\n{'='*60}")
        print(f"  {task_id.upper()}")
        print(f"{'='*60}")

        obs = env.reset(task_id)
        print(f"  Resources  : {len(obs.resources)}")
        print(f"  Start bill : ${obs.monthly_bill_start:,.2f}/mo")
        print(f"  Target     : ${obs.savings_target:,.2f}/mo savings")

        # ── Task-specific smoke actions ──────────────────────────────────────
        if task_id == "task_1":
            # Delete first IP address found
            ip = next((r for r in obs.resources if r.resource_type == "ip_address"), None)
            if ip:
                result = env.step(Action(action_type=ActionType.TERMINATE, resource_id=ip.id))
                print(f"  Terminate {ip.name}: reward={result.reward:,.0f}")
                print(f"  Feedback: {result.observation.feedback}")

        elif task_id == "task_2":
            # Resize first xlarge VM found
            vm = next(
                (r for r in obs.resources
                 if r.resource_type == "vm" and r.instance_size == "xlarge"),
                None,
            )
            if vm:
                result = env.step(Action(
                    action_type=ActionType.RESIZE,
                    resource_id=vm.id,
                    new_size=InstanceSize.SMALL,
                ))
                print(f"  Resize {vm.name}: reward={result.reward:,.0f}")
                print(f"  Feedback: {result.observation.feedback}")

        elif task_id == "task_3":
            # Test the full drain sequence and then a production termination
            result = env.step(Action(
                action_type=ActionType.MIGRATE_TRAFFIC,
                source_region="us-east-1",
            ))
            print(f"  migrate_traffic: reward={result.reward:,.0f}")
            print(f"  Feedback: {result.observation.feedback}")

            result = env.step(Action(action_type=ActionType.WAIT))
            print(f"  wait: reward={result.reward:,.0f}")
            print(f"  Feedback: {result.observation.feedback}")

            # This should now succeed (no penalty) after the drain sequence
            result = env.step(Action(
                action_type=ActionType.TERMINATE,
                resource_id="lb-east-main",
            ))
            print(f"  terminate lb-east-main: reward={result.reward:,.0f}")
            print(f"  Feedback: {result.observation.feedback}")

        grade = env.grade()
        print(f"  Score      : {grade.score:.4f}")
        print(f"  Money saved: ${grade.money_saved:,.2f}")

    print("\nSmoke-test complete.")
