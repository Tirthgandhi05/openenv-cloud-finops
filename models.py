# models.py
# Cloud FinOps Sandbox — OpenEnv submission
# NovaCart infrastructure simulation
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


# ══════════════════════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════════════════════

class ResourceType(str, Enum):
    VM            = "vm"
    DATABASE      = "database"
    STORAGE       = "storage"
    IP_ADDRESS    = "ip_address"
    SNAPSHOT      = "snapshot"
    LOAD_BALANCER = "load_balancer"
    CDN           = "cdn"


class ResourceStatus(str, Enum):
    """
    Lifecycle states.  Only RUNNING / STOPPED are valid starting states.
    DELETED and MIGRATED are set by the environment after actions;
    they make resources invisible in future observations.
    ORPHANED is a logical tag the agent infers from visible fields
    (attached_to=None, traffic=0) — it is NOT set by the environment.
    """
    RUNNING  = "running"
    STOPPED  = "stopped"
    DELETED  = "deleted"   # set after terminate_resource succeeds
    MIGRATED = "migrated"  # set after storage migrated to cold tier


class StorageTier(str, Enum):
    HOT  = "hot"
    COLD = "cold"


class ActionType(str, Enum):
    TERMINATE       = "terminate"        # permanently delete a resource
    RESIZE          = "resize"           # downgrade instance tier
    MIGRATE_STORAGE = "migrate_storage"  # move volume to cold storage
    MIGRATE_TRAFFIC = "migrate_traffic"  # shift live traffic away from a region (Task 3)
    WAIT            = "wait"             # wait for connections to drain (Task 3)


class InstanceSize(str, Enum):
    """Ordered from cheapest to most expensive."""
    NANO   = "nano"
    MICRO  = "micro"
    SMALL  = "small"
    MEDIUM = "medium"
    LARGE  = "large"
    XLARGE = "xlarge"


# Monthly cost multiplier relative to SMALL = 1.0
INSTANCE_SIZE_COST_MULTIPLIER: Dict[str, float] = {
    "nano":   0.25,
    "micro":  0.50,
    "small":  1.00,
    "medium": 2.00,
    "large":  4.00,
    "xlarge": 8.00,
}

# Ordered list for resize validation (agent may only downsize)
INSTANCE_SIZE_ORDER = ["nano", "micro", "small", "medium", "large", "xlarge"]


class TaskDifficulty(str, Enum):
    EASY   = "easy"
    MEDIUM = "medium"
    HARD   = "hard"


# ══════════════════════════════════════════════════════════════════════════════
# Internal Resource — NEVER serialized to agent
# ══════════════════════════════════════════════════════════════════════════════

class Resource(BaseModel):
    """
    Full internal resource record.

    Fields prefixed with a comment "# HIDDEN" are intentionally absent from
    AgentResource.  The environment uses them for reward/penalty logic;
    the agent must infer danger from the visible fields alone.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    id:            str
    name:          str
    resource_type: ResourceType
    status:        ResourceStatus = ResourceStatus.RUNNING
    region:        str = "us-east-1"
    monthly_cost:  float   # USD/month at current size/tier

    # ── Utilization (visible to agent) ────────────────────────────────────────
    cpu_avg_24h:       Optional[float] = None   # 0–100 %
    ram_avg_24h:       Optional[float] = None   # 0–100 %
    traffic_per_hour:  Optional[int]   = None   # HTTP requests/hr
    queries_per_hour:  Optional[int]   = None   # DB queries/hr (databases only)

    # ── HIDDEN: honeypot trap fields ──────────────────────────────────────────
    # Absent from to_agent_view().  Agent must read the visible averages only.
    peak_cpu_2am:     Optional[float] = None   # actual CPU % at 02:00
    peak_queries_2am: Optional[int]   = None   # actual queries/hr at 02:00

    # ── Attachment / dependency ───────────────────────────────────────────────
    attached_to:   Optional[str]       = None  # resource id this volume is attached to
    dependency_of: Optional[List[str]] = None  # VISIBLE in Task 3 (agent must notice)

    # ── Storage ───────────────────────────────────────────────────────────────
    storage_tier:           Optional[StorageTier] = None
    last_accessed_days_ago: Optional[int]         = None  # None → actively used
    size_gb:                Optional[int]         = None

    # ── Instance sizing ───────────────────────────────────────────────────────
    instance_size:       Optional[InstanceSize] = None
    base_cost_at_large:  Optional[float]        = None  # reference cost at LARGE tier
    #  environment uses this to compute new monthly_cost after resize

    # ── Metadata ──────────────────────────────────────────────────────────────
    tags: Dict[str, str] = Field(default_factory=dict)

    # ── HIDDEN: internal safety flags ────────────────────────────────────────
    safe_to_terminate: bool = True   # ground truth — never shown to agent
    is_production:     bool = False  # ground truth — never shown to agent

    # ── Task 3 traffic-drain state (mutated by environment) ───────────────────
    traffic_migrated:    bool = False
    connections_drained: bool = False

    # ── Computed helpers ──────────────────────────────────────────────────────
    @property
    def cost_per_hour(self) -> float:
        return round(self.monthly_cost / 730, 4)   # 730 h/month average

    @property
    def is_active(self) -> bool:
        return self.status in (ResourceStatus.RUNNING, ResourceStatus.STOPPED)

    def to_agent_view(self) -> AgentResource:
        """
        Sanitized view safe to send to the agent.

        Strips:
          - safe_to_terminate, is_production
          - peak_cpu_2am, peak_queries_2am
          - traffic_migrated, connections_drained
          - base_cost_at_large

        Keeps dependency_of intentionally — it is a visible clue in Task 3
        that a careful agent should notice.
        """
        return AgentResource(
            id=self.id,
            name=self.name,
            resource_type=self.resource_type,
            status=self.status,
            region=self.region,
            monthly_cost=self.monthly_cost,
            cpu_avg_24h=self.cpu_avg_24h,
            ram_avg_24h=self.ram_avg_24h,
            traffic_per_hour=self.traffic_per_hour,
            queries_per_hour=self.queries_per_hour,
            attached_to=self.attached_to,
            dependency_of=self.dependency_of,
            storage_tier=self.storage_tier,
            last_accessed_days_ago=self.last_accessed_days_ago,
            size_gb=self.size_gb,
            instance_size=self.instance_size,
            tags=self.tags,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Agent Resource — sanitized view sent in every Observation
# ══════════════════════════════════════════════════════════════════════════════

class AgentResource(BaseModel):
    """
    What the agent sees.  Constructed exclusively via Resource.to_agent_view().
    No ground-truth safety flags, no hidden peak data.
    """
    id:            str
    name:          str
    resource_type: ResourceType
    status:        ResourceStatus
    region:        str
    monthly_cost:  float

    cpu_avg_24h:      Optional[float] = None
    ram_avg_24h:      Optional[float] = None
    traffic_per_hour: Optional[int]   = None
    queries_per_hour: Optional[int]   = None

    attached_to:   Optional[str]       = None
    dependency_of: Optional[List[str]] = None

    storage_tier:           Optional[StorageTier]  = None
    last_accessed_days_ago: Optional[int]          = None
    size_gb:                Optional[int]          = None
    instance_size:          Optional[InstanceSize] = None

    tags: Dict[str, str] = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# Action
# ══════════════════════════════════════════════════════════════════════════════

class Action(BaseModel):
    """
    One action submitted by the agent per POST /step call.

    Field requirements by action_type:
      TERMINATE       → resource_id
      RESIZE          → resource_id, new_size  (must be strictly smaller tier)
      MIGRATE_STORAGE → resource_id, target_tier  (always "cold")
      MIGRATE_TRAFFIC → source_region  (no resource_id — whole-region operation)
      WAIT            → (no fields required)
    """
    action_type:   ActionType
    resource_id:   Optional[str]          = Field(None, description="Target resource ID.")
    new_size:      Optional[InstanceSize] = Field(None, description="Required for RESIZE.")
    target_tier:   Optional[StorageTier]  = Field(None, description="Required for MIGRATE_STORAGE.")
    source_region: Optional[str]          = Field(None, description="Required for MIGRATE_TRAFFIC.")

    @model_validator(mode="after")
    def _validate_fields(self) -> Action:
        t = self.action_type
        if t == ActionType.RESIZE:
            if not self.resource_id:
                raise ValueError("RESIZE requires resource_id.")
            if not self.new_size:
                raise ValueError("RESIZE requires new_size.")
        elif t == ActionType.MIGRATE_STORAGE:
            if not self.resource_id:
                raise ValueError("MIGRATE_STORAGE requires resource_id.")
            if not self.target_tier:
                raise ValueError("MIGRATE_STORAGE requires target_tier.")
        elif t == ActionType.MIGRATE_TRAFFIC:
            if not self.source_region:
                raise ValueError("MIGRATE_TRAFFIC requires source_region.")
            # resource_id is NOT required — this is a region-level operation
        elif t == ActionType.TERMINATE:
            if not self.resource_id:
                raise ValueError("TERMINATE requires resource_id.")
        # WAIT requires nothing
        return self


# ══════════════════════════════════════════════════════════════════════════════
# Observation
# ══════════════════════════════════════════════════════════════════════════════

class Observation(BaseModel):
    """
    Full environment state.  Returned by /reset and embedded in every
    StepResult.  Resources are always AgentResource — never raw Resource.
    """
    task_id:   str
    step:      int = 0
    max_steps: int

    # Financial snapshot
    monthly_bill_start:   float
    monthly_bill_current: float
    savings_target:       float
    savings_achieved:     float

    # Reliability
    uptime_percent:  float = 100.0
    downtime_events: int   = 0

    # Task 3 multi-region drain state
    regions:               List[str]     = Field(default_factory=list)
    traffic_migrated_from: Optional[str] = None   # region drained
    connections_drained:   bool          = False

    # Sanitized resource list
    resources: List[AgentResource]

    # Running penalty counters (visible so agent can self-correct)
    honeypot_hits:       int = 0
    sequence_violations: int = 0

    # Human-readable step feedback
    feedback: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Step Result
# ══════════════════════════════════════════════════════════════════════════════

class StepResult(BaseModel):
    """Returned by POST /step."""
    reward:      float
    done:        bool = False
    info:        Dict[str, Any] = Field(default_factory=dict)
    observation: Observation


# ══════════════════════════════════════════════════════════════════════════════
# Task Info  (GET /tasks)
# ══════════════════════════════════════════════════════════════════════════════

class ActionSchema(BaseModel):
    """Human-readable description of one action type for the /tasks endpoint."""
    action_type:     ActionType
    required_fields: List[str]
    description:     str


class TaskInfo(BaseModel):
    """Metadata about one task, returned by GET /tasks."""
    task_id:           str
    name:              str
    difficulty:        TaskDifficulty
    description:       str
    monthly_bill:      float
    savings_target:    float
    max_steps:         int
    regions:           List[str]
    available_actions: List[ActionSchema]
    grading_notes:     str


# ══════════════════════════════════════════════════════════════════════════════
# Grader Result  (POST /grader)
# ══════════════════════════════════════════════════════════════════════════════

class GraderBreakdown(BaseModel):
    savings_ratio:      float = 0.0   # savings_achieved / savings_target, capped 1.0
    downtime_penalty:   float = 0.0   # subtracted for each downtime event
    honeypot_penalty:   float = 0.0   # subtracted for each honeypot hit (Task 3)
    sequence_penalty:   float = 0.0   # subtracted for wrong-order ops (Task 3)
    false_kill_penalty: float = 0.0   # subtracted for terminating active resources
    final_score:        float = 0.0   # max(0.0, sum of above), capped 1.0


class GraderResult(BaseModel):
    """Full grader output."""
    task_id:             str
    score:               float = Field(..., ge=0.0, le=1.0)
    money_saved:         float
    savings_target:      float
    downtime_events:     int
    false_kills:         int
    honeypot_hits:       int
    sequence_violations: int
    breakdown:           GraderBreakdown
    message:             str


# ══════════════════════════════════════════════════════════════════════════════
# Baseline Result  (POST /baseline)
# ══════════════════════════════════════════════════════════════════════════════

class TaskBaselineResult(BaseModel):
    task_id:     str
    score:       float
    money_saved: float
    steps_taken: int
    downtime_events: int
    notes:       str


class BaselineResult(BaseModel):
    """Returned by POST /baseline — runs all 3 tasks and reports scores."""
    model_used:  str   # e.g. "gpt-4o" or "heuristic-fallback"
    results:     List[TaskBaselineResult]
    mean_score:  float


# ══════════════════════════════════════════════════════════════════════════════
# Resolve forward references (Pydantic v2 with from __future__ import annotations)
# ══════════════════════════════════════════════════════════════════════════════
StepResult.model_rebuild()
Observation.model_rebuild()
