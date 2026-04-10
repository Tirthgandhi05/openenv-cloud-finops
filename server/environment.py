# environment.py  — Cloud FinOps Sandbox — Game Engine
from __future__ import annotations
import copy
from typing import Dict, List, Optional, Tuple
from openenv.core.env_server import Environment
from models import (
    FinOpsAction, FinOpsObservation, FinOpsState,
    Action, ActionType, AgentResource, GraderBreakdown, GraderResult,
    INSTANCE_SIZE_COST_MULTIPLIER, INSTANCE_SIZE_ORDER,
    Observation, Resource, ResourceStatus, ResourceType, StepResult, StorageTier,
)
from resources import TASKS, TASK_META

# Reward weights
W_SAVINGS        = 1.0
W_DOWNTIME       = 8_000
W_HONEYPOT       = 8_000
W_SEQUENCE       = 3_000
W_FALSE_KILL     = 5_000
W_WASTED_ACTION  = 10
W_WAIT_STEP      = 5

# Grader weights 
GRADER_DOWNTIME_PENALTY    = 0.20
GRADER_FALSE_KILL_PENALTY  = 0.20
GRADER_HONEYPOT_PENALTY    = 0.20
GRADER_SEQUENCE_PENALTY    = 0.15


class FinOpsEnvironment(Environment):
    def __init__(self) -> None:
        self._task_id: Optional[str] = None
        self._resources: Dict[str, Resource] = {}
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

    def reset(self, task_id: str = "task_1") -> FinOpsObservation:
        if task_id not in TASKS:
            raise KeyError(f"Unknown task_id '{task_id}'. Valid: {list(TASKS)}")
        meta = TASK_META[task_id]
        raw = TASKS[task_id]
        self._resources = {r.id: r.model_copy(deep=True) for r in raw}
        self._task_id = task_id
        self._initial_bill = sum(r.monthly_cost for r in self._resources.values())
        self._step = 0
        self._max_steps = meta["max_steps"]
        self._savings_target = meta["savings_target"]
        self._regions = meta.get("regions", ["us-east-1"])
        self._downtime_events = 0
        self._honeypot_hits = 0
        self._sequence_violations = 0
        self._false_kills = 0
        self._traffic_migrated_from = None
        return self._make_observation(feedback="Episode started. Good luck.")

    def step(self, action: FinOpsAction) -> StepResult:
        if self._task_id is None:
            raise RuntimeError("Call reset() before step().")
        self._step += 1
        done = False
        reward, feedback, info = self._apply_action(action)
        if self._step >= self._max_steps:
            done = True
            feedback += f" [Episode ended: max steps ({self._max_steps}) reached.]"
        obs = self._make_observation(feedback=feedback)
        return StepResult(reward=reward, done=done, info=info, observation=obs)

    @property
    def state(self) -> FinOpsState:
        return FinOpsState(
            episode_id=self._task_id or "",
            step_count=self._step,
            task_id=self._task_id,
            monthly_bill_start=round(self._initial_bill, 2),
            monthly_bill_current=round(self._current_bill(), 2),
            savings_target=self._savings_target,
            downtime_events=self._downtime_events,
            honeypot_hits=self._honeypot_hits,
            sequence_violations=self._sequence_violations,
            false_kills=self._false_kills,
            done=(self._step >= self._max_steps),
        )

    def grade(self) -> GraderResult:
        if self._task_id is None:
            raise RuntimeError("Call reset() before grade().")
        current_bill = self._current_bill()
        money_saved = self._initial_bill - current_bill
        target = self._savings_target
        savings_ratio = min(1.0, money_saved / target) if target > 0 else 0.0
        downtime_penalty = self._downtime_events * GRADER_DOWNTIME_PENALTY
        false_kill_penalty = self._false_kills * GRADER_FALSE_KILL_PENALTY
        honeypot_penalty = self._honeypot_hits * GRADER_HONEYPOT_PENALTY
        sequence_penalty = self._sequence_violations * GRADER_SEQUENCE_PENALTY
        raw_score = savings_ratio - downtime_penalty - false_kill_penalty
        raw_score -= honeypot_penalty + sequence_penalty
        final = max(0.0, min(1.0, raw_score))
        breakdown = GraderBreakdown(
            savings_ratio=round(savings_ratio, 4),
            downtime_penalty=round(downtime_penalty, 4),
            false_kill_penalty=round(false_kill_penalty, 4),
            honeypot_penalty=round(honeypot_penalty, 4),
            sequence_penalty=round(sequence_penalty, 4),
            final_score=round(final, 4),
        )
        if final >= 0.85: verdict = "Excellent — top-tier optimization."
        elif final >= 0.60: verdict = "Good — solid savings with acceptable risk."
        elif final >= 0.35: verdict = "Partial — room for improvement."
        else: verdict = "Poor — too many penalties or insufficient savings."
        return GraderResult(
            task_id=self._task_id, score=round(final, 4),
            money_saved=round(money_saved, 2), savings_target=target,
            downtime_events=self._downtime_events, false_kills=self._false_kills,
            honeypot_hits=self._honeypot_hits, sequence_violations=self._sequence_violations,
            breakdown=breakdown,
            message=f"{verdict} Saved ${money_saved:,.0f} of ${target:,.0f} target.",
        )

    def _apply_action(self, action: FinOpsAction) -> Tuple[float, str, dict]:
        t = action.action_type
        if t == ActionType.TERMINATE: return self._handle_terminate(action)
        elif t == ActionType.RESIZE: return self._handle_resize(action)
        elif t == ActionType.MIGRATE_STORAGE: return self._handle_migrate_storage(action)
        elif t == ActionType.MIGRATE_TRAFFIC: return self._handle_migrate_traffic(action)
        elif t == ActionType.WAIT: return self._handle_wait(action)
        else: return 0.0, f"Unknown action type '{t}'.", {"error": "unknown_action"}

    def _handle_terminate(self, action: FinOpsAction) -> Tuple[float, str, dict]:
        resource = self._get_resource(action.resource_id)
        if resource is None:
            return 0.0, f"Resource '{action.resource_id}' not found.", {"error": "not_found"}
        if not resource.is_active:
            return -W_WASTED_ACTION, f"{resource.name} is already {resource.status}.", {"warning": "already_inactive"}

        if (self._task_id == "task_3" and resource.region == "us-east-1"
                and resource.is_production and not resource.traffic_migrated):
            self._sequence_violations += 1
            self._downtime_events += 1
            penalty = W_SEQUENCE + W_DOWNTIME
            return -penalty, (
                f"SEQUENCE VIOLATION: Terminated {resource.name} in us-east-1 "
                f"before migrate_traffic. Production outage! Penalty: -${penalty:,.0f}"
            ), {"penalty_reason": "sequence_violation", "penalty": penalty}

        east1_unlocked = (
            self._task_id == "task_3" and resource.region == "us-east-1"
            and resource.is_production and resource.connections_drained
        )

        if not resource.safe_to_terminate and not east1_unlocked:
            if resource.peak_cpu_2am or resource.peak_queries_2am:
                self._honeypot_hits += 1
                self._downtime_events += 1
                penalty = W_HONEYPOT + W_DOWNTIME
                return -penalty, (
                    f"HONEYPOT HIT: {resource.name} looks idle on 24h average, "
                    f"but runs critical batch jobs at 02:00. "
                    f"Production outage. Penalty: -${penalty:,.0f}"
                ), {"penalty_reason": "honeypot_hit", "penalty": penalty}

        # Active production resource
        if not resource.safe_to_terminate and not east1_unlocked:
            self._downtime_events += 1
            if resource.is_production:
                self._false_kills += 1
                penalty = W_DOWNTIME + W_FALSE_KILL
            else:
                penalty = W_DOWNTIME
            resource.status = ResourceStatus.DELETED
            return -penalty, (
                f"DISASTER: {resource.name} is active production "
                f"(traffic={resource.traffic_per_hour}/hr). "
                f"Terminating caused downtime. Penalty: -${penalty:,.0f}"
            ), {"penalty_reason": "active_resource_killed", "penalty": penalty}

        # Safe termination
        savings = resource.monthly_cost
        resource.status = ResourceStatus.DELETED
        reward = W_SAVINGS * savings
        return reward, (
            f"Terminated {resource.name}. Saved ${savings:,.2f}/month. +{reward:,.0f} reward."
        ), {"savings_delta": savings}

    def _handle_resize(self, action: FinOpsAction) -> Tuple[float, str, dict]:
        resource = self._get_resource(action.resource_id)
        if resource is None:
            return 0.0, f"Resource '{action.resource_id}' not found.", {"error": "not_found"}
        if resource.resource_type not in (ResourceType.VM, ResourceType.DATABASE):
            return 0.0, f"{resource.name} is {resource.resource_type} — cannot resize.", {"error": "wrong_resource_type"}
        if not resource.is_active:
            return -W_WASTED_ACTION, f"{resource.name} is {resource.status}.", {"warning": "inactive_resource"}

        current_size = resource.instance_size
        new_size = action.new_size
        if current_size is None:
            return 0.0, f"{resource.name} has no instance_size.", {"error": "no_size"}

        current_idx = INSTANCE_SIZE_ORDER.index(current_size.value if hasattr(current_size, 'value') else current_size)
        new_idx = INSTANCE_SIZE_ORDER.index(new_size.value if hasattr(new_size, 'value') else new_size)
        if new_idx >= current_idx:
            return -W_WASTED_ACTION, f"Cannot resize {resource.name} from {current_size} to {new_size} — must downsize.", {"warning": "not_a_downsize"}

        # Penalty: resizing busy machine
        if not resource.safe_to_terminate and resource.cpu_avg_24h and resource.cpu_avg_24h > 60:
            self._downtime_events += 1
            penalty = W_DOWNTIME * 0.5
            old_cost = resource.monthly_cost
            new_cost = self._compute_resized_cost(resource, new_size)
            resource.monthly_cost = new_cost
            resource.instance_size = new_size
            savings = old_cost - new_cost
            net = W_SAVINGS * savings - penalty
            return net, (
                f"WARNING: {resource.name} at {resource.cpu_avg_24h:.1f}% CPU — "
                f"resize caused performance incident. Saved ${savings:,.2f}/month but penalty applied."
            ), {"savings_delta": savings, "penalty": penalty}

        # Penalty: resizing a compliance/audit-required resource
        if not resource.safe_to_terminate and resource.is_production:
            self._downtime_events += 1
            self._false_kills += 1
            penalty = W_DOWNTIME + W_FALSE_KILL
            old_cost = resource.monthly_cost
            new_cost = self._compute_resized_cost(resource, new_size)
            resource.monthly_cost = new_cost
            resource.instance_size = new_size
            savings = old_cost - new_cost
            net = W_SAVINGS * savings - penalty
            return net, (
                f"DISASTER: {resource.name} is production-critical. "
                f"Resizing caused compliance violation and downtime. Penalty: -${penalty:,.0f}"
            ), {"savings_delta": savings, "penalty": penalty}

        old_cost = resource.monthly_cost
        new_cost = self._compute_resized_cost(resource, new_size)
        resource.monthly_cost = new_cost
        resource.instance_size = new_size
        savings = old_cost - new_cost
        reward = W_SAVINGS * savings
        return reward, (
            f"Resized {resource.name} from {current_size} → {new_size}. "
            f"Saved ${savings:,.2f}/month. +{reward:,.0f} reward."
        ), {"savings_delta": savings}

    def _handle_migrate_storage(self, action: FinOpsAction) -> Tuple[float, str, dict]:
        resource = self._get_resource(action.resource_id)
        if resource is None:
            return 0.0, f"Resource '{action.resource_id}' not found.", {"error": "not_found"}
        if resource.resource_type != ResourceType.STORAGE:
            return 0.0, f"{resource.name} is not storage.", {"error": "wrong_resource_type"}
        if resource.storage_tier == StorageTier.COLD:
            return -W_WASTED_ACTION, f"{resource.name} already cold.", {"warning": "already_cold"}

        # Penalty: migrating active storage
        if resource.last_accessed_days_ago is not None and resource.last_accessed_days_ago < 30:
            self._downtime_events += 1
            penalty = W_DOWNTIME * 0.3
            old_cost = resource.monthly_cost
            new_cost = round(old_cost * 0.20, 2)
            resource.monthly_cost = new_cost
            resource.storage_tier = StorageTier.COLD
            resource.status = ResourceStatus.MIGRATED
            savings = old_cost - new_cost
            net = W_SAVINGS * savings - penalty
            return net, (
                f"WARNING: {resource.name} accessed {resource.last_accessed_days_ago} days ago — "
                f"cold migration may affect workflows."
            ), {"savings_delta": savings, "penalty": penalty}

        # Penalty: migrating a dependency volume
        if resource.dependency_of and not resource.safe_to_terminate:
            self._downtime_events += 1
            self._false_kills += 1
            penalty = W_DOWNTIME + W_FALSE_KILL
            old_cost = resource.monthly_cost
            new_cost = round(old_cost * 0.20, 2)
            resource.monthly_cost = new_cost
            resource.storage_tier = StorageTier.COLD
            resource.status = ResourceStatus.MIGRATED
            savings = old_cost - new_cost
            net = W_SAVINGS * savings - penalty
            return net, (
                f"DISASTER: {resource.name} has dependencies: {resource.dependency_of}. "
                f"Cold migration broke dependent services!"
            ), {"savings_delta": savings, "penalty": penalty}

        old_cost = resource.monthly_cost
        new_cost = round(old_cost * 0.20, 2)
        resource.monthly_cost = new_cost
        resource.storage_tier = StorageTier.COLD
        resource.status = ResourceStatus.MIGRATED
        savings = old_cost - new_cost
        reward = W_SAVINGS * savings
        return reward, (
            f"Migrated {resource.name} to cold storage. "
            f"${old_cost:,.2f} → ${new_cost:,.2f}/month. Saved ${savings:,.2f}/month."
        ), {"savings_delta": savings}

    def _handle_migrate_traffic(self, action: FinOpsAction) -> Tuple[float, str, dict]:
        if self._task_id != "task_3":
            return -W_WASTED_ACTION, "migrate_traffic only valid in task_3.", {"warning": "wrong_task"}
        source = action.source_region
        if source not in self._regions:
            return 0.0, f"Region '{source}' not found.", {"error": "unknown_region"}
        if self._traffic_migrated_from == source:
            return -W_WASTED_ACTION, f"Traffic from {source} already migrated.", {"warning": "already_migrated"}

        count = 0
        unlocked_savings = 0.0
        for r in self._resources.values():
            if r.region == source and r.is_active and r.is_production:
                r.traffic_migrated = True
                unlocked_savings += r.monthly_cost
                count += 1
        self._traffic_migrated_from = source
        preview_reward = round(unlocked_savings * 0.05, 2)
        return preview_reward, (
            f"Traffic migrated from {source}. {count} production resources marked for drain. "
            f"Call WAIT next, then TERMINATE."
        ), {"migrated_region": source, "resources_affected": count}

    def _handle_wait(self, action: FinOpsAction) -> Tuple[float, str, dict]:
        if self._task_id != "task_3":
            return -W_WAIT_STEP, "WAIT has no effect outside task_3.", {"warning": "wrong_task"}
        if self._traffic_migrated_from is None:
            self._sequence_violations += 1
            return -W_SEQUENCE, (
                "SEQUENCE VIOLATION: WAIT before MIGRATE_TRAFFIC. "
                "Call migrate_traffic first."
            ), {"penalty_reason": "wait_before_migrate"}
        if self._all_connections_drained():
            return -W_WAIT_STEP, "Already drained. Terminate now.", {"warning": "already_drained"}

        source = self._traffic_migrated_from
        drained = 0
        for r in self._resources.values():
            if r.region == source and r.traffic_migrated and not r.connections_drained:
                r.connections_drained = True
                drained += 1
        return 0.0, (
            f"Draining connections on {source}... {drained} resources drained. "
            f"Safe to terminate {source} infrastructure."
        ), {"drained_count": drained}

    def _get_resource(self, resource_id: Optional[str]) -> Optional[Resource]:
        if resource_id is None: return None
        return self._resources.get(resource_id)

    def _current_bill(self) -> float:
        return sum(r.monthly_cost for r in self._resources.values() if r.is_active)

    def _all_connections_drained(self) -> bool:
        if self._traffic_migrated_from is None: return False
        source = self._traffic_migrated_from
        return all(
            r.connections_drained for r in self._resources.values()
            if r.region == source and r.is_production
        )

    def _compute_resized_cost(self, resource: Resource, new_size) -> float:
        new_size_str = new_size.value if hasattr(new_size, 'value') else str(new_size)
        current_size_str = (
            resource.instance_size.value if hasattr(resource.instance_size, 'value')
            else str(resource.instance_size)
        )
        if resource.base_cost_at_large:
            return round(resource.base_cost_at_large * INSTANCE_SIZE_COST_MULTIPLIER[new_size_str], 2)
        else:
            current_factor = INSTANCE_SIZE_COST_MULTIPLIER.get(current_size_str, 1.0)
            new_factor = INSTANCE_SIZE_COST_MULTIPLIER[new_size_str]
            ratio = new_factor / current_factor if current_factor else 1.0
            return round(resource.monthly_cost * ratio, 2)

    def _make_observation(self, feedback: str = "") -> FinOpsObservation:
        current_bill = self._current_bill()
        savings = self._initial_bill - current_bill
        uptime = max(0.0, 100.0 - self._downtime_events * 5.0)
        visible = [r.to_agent_view() for r in self._resources.values() if r.is_active]
        return FinOpsObservation(
            task_id=self._task_id, step=self._step, max_steps=self._max_steps,
            monthly_bill_start=round(self._initial_bill, 2),
            monthly_bill_current=round(current_bill, 2),
            savings_target=self._savings_target, savings_achieved=round(savings, 2),
            uptime_percent=round(uptime, 2), downtime_events=self._downtime_events,
            regions=self._regions, traffic_migrated_from=self._traffic_migrated_from,
            connections_drained=self._all_connections_drained(),
            resources=visible, honeypot_hits=self._honeypot_hits,
            sequence_violations=self._sequence_violations, feedback=feedback,
        )


# Keep old name as alias for backwards compatibility
FinOpsEnv = FinOpsEnvironment
