# Cloud FinOps Sandbox — OpenEnv
from __future__ import annotations
 
from typing import Any, Dict, List, Optional
from enum import Enum
 
from pydantic import BaseModel, Field, model_validator
  
INSTANCE_SIZE_ORDER = ["nano", "micro", "small", "medium", "large", "xlarge"]

INSTANCE_SIZE_COST_MULTIPLIER: dict[str, float] = {
    "nano":   0.09,   # nano   ≈  9% of large cost
    "micro":  0.15,   # micro  ≈ 15%
    "small":  0.34,   # small  ≈ 34%
    "medium": 0.61,   # medium ≈ 61%
    "large":  1.00,   # large  = reference
    "xlarge": 2.00,   # xlarge = 2× large
}
  
class ResourceType(str, Enum):
    VM            = "vm"
    DATABASE      = "database"
    STORAGE       = "storage"
    IP_ADDRESS    = "ip_address"
    SNAPSHOT      = "snapshot"
    LOAD_BALANCER = "load_balancer"
    CDN           = "cdn"
    CACHE         = "cache" 
 
 
class ResourceStatus(str, Enum):
    RUNNING  = "running"
    STOPPED  = "stopped"
    ORPHANED = "orphaned"
    DELETED  = "deleted"
    MIGRATED = "migrated"
 
class StorageTier(str, Enum):
    HOT  = "hot"
    COLD = "cold"
 
class ActionType(str, Enum):
    TERMINATE       = "terminate"
    RESIZE          = "resize"
    MIGRATE_STORAGE = "migrate_storage"
    MIGRATE_TRAFFIC = "migrate_traffic"
    WAIT            = "wait"
 
 
class InstanceSize(str, Enum):
    NANO   = "nano"
    MICRO  = "micro"
    SMALL  = "small"
    MEDIUM = "medium"
    LARGE  = "large"
    XLARGE = "xlarge"
 
 
class TaskDifficulty(str, Enum):
    EASY   = "easy"
    MEDIUM = "medium"
    HARD   = "hard"
 
 
# Internal Resource
 
class Resource(BaseModel):
    """
    Contains hidden fields never sent to agent.
    """
    id:            str
    name:          str
    resource_type: ResourceType
    status:        ResourceStatus = ResourceStatus.RUNNING
    region:        str = "us-east-1"
    monthly_cost:  float
 
    # visible to agent
    cpu_avg_24h:      Optional[float] = None
    ram_avg_24h:      Optional[float] = None
    traffic_per_hour: Optional[int]   = None
    queries_per_hour: Optional[int]   = None   # ← ADDED: visible database/cache metric
 
    # HIDDEN
    peak_cpu_2am:     Optional[float] = None
    peak_queries_2am: Optional[int]   = None

    attached_to:   Optional[str]       = None
    dependency_of: Optional[List[str]] = None
 
    # Storage
    storage_tier:           Optional[StorageTier] = None
    last_accessed_days_ago: Optional[int]         = None
    size_gb:                Optional[int]         = None
 
    # Instance sizing
    instance_size:    Optional[InstanceSize] = None
    base_cost_at_large: Optional[float] = None
 
    tags: Dict[str, str] = Field(default_factory=dict)
 
    # HIDDEN: 
    safe_to_terminate: bool = True
    is_production:     bool = False
 
    traffic_migrated:    bool = False
    connections_drained: bool = False
 
    @property
    def is_active(self) -> bool:
        return self.status not in (ResourceStatus.DELETED, ResourceStatus.MIGRATED)
 
    def to_agent_view(self) -> AgentResource:
        """strips all hidden fields."""
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
            queries_per_hour=self.queries_per_hour,   # ← ADDED: passed through to agent
            attached_to=self.attached_to,
            dependency_of=self.dependency_of,
            storage_tier=self.storage_tier,
            last_accessed_days_ago=self.last_accessed_days_ago,
            size_gb=self.size_gb,
            instance_size=self.instance_size,
            tags=self.tags,
        )
 
 
# Agent Resource
 
class AgentResource(BaseModel):
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
 
 
# Action
 
class Action(BaseModel):
 
    action_type:   ActionType
    resource_id:   Optional[str]          = None
    new_size:      Optional[InstanceSize] = None
    target_tier:   Optional[StorageTier]  = None
    target_region: Optional[str]          = None
    source_region: Optional[str]          = None
 
    @model_validator(mode="after")
    def validate_fields(self) -> "Action":
        if self.source_region and not self.target_region:
            object.__setattr__(self, "target_region", self.source_region)
 
        t = self.action_type
        if t == ActionType.RESIZE and self.new_size is None:
            raise ValueError("RESIZE requires new_size.")
        if t == ActionType.MIGRATE_STORAGE and self.target_tier is None:
            raise ValueError("MIGRATE_STORAGE requires target_tier.")
        if t == ActionType.MIGRATE_TRAFFIC and not (self.target_region or self.source_region):
            raise ValueError("MIGRATE_TRAFFIC requires source_region or target_region.")
        if t not in (ActionType.WAIT, ActionType.MIGRATE_TRAFFIC) and self.resource_id is None:
            raise ValueError(f"{t} requires resource_id.")
        return self
 
 
# Step Result
 
class StepResult(BaseModel):
    reward:      float
    done:        bool = False
    info:        Dict[str, Any] = Field(default_factory=dict)
    observation: Observation
 
 
# Observation
 
class Observation(BaseModel):
    task_id:   str
    step:      int = 0
    max_steps: int
 
    monthly_bill_start:   float
    monthly_bill_current: float
    savings_target:       float
    savings_achieved:     float
 
    uptime_percent:  float = 100.0
    downtime_events: int   = 0
 
    regions:               List[str]      = Field(default_factory=list)
    traffic_migrated_from: Optional[str]  = None
    connections_drained:   bool           = False
 
    resources: List[AgentResource]
 
    honeypot_hits:       int = 0
    sequence_violations: int = 0
    feedback:            str = ""
 
 
# Grader
 
class GraderBreakdown(BaseModel):
    savings_ratio:      float = 0.0
    downtime_penalty:   float = 0.0
    false_kill_penalty: float = 0.0
    honeypot_penalty:   float = 0.0
    sequence_penalty:   float = 0.0
    final_score:        float = 0.0
 
 
class GraderResult(BaseModel):
    task_id:             str
    score:               float = Field(..., gt=0.0, lt=1.0)
    money_saved:         float
    savings_target:      float
    downtime_events:     int
    false_kills:         int
    honeypot_hits:       int
    sequence_violations: int
    breakdown:           GraderBreakdown
    message:             str
 
 
# Task Info
 
class ActionSchema(BaseModel):
    action_type:     ActionType
    required_fields: List[str]
    description:     str
 
 
class TaskInfo(BaseModel):
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
 
 
# Baseline result models
 
class TaskBaselineResult(BaseModel):
    task_id:         str
    score:           float
    money_saved:     float
    steps_taken:     int
    downtime_events: int
    notes:           str
 
 
class BaselineResult(BaseModel):
    model_used:  str
    results:     List[TaskBaselineResult]
    mean_score:  float
 
StepResult.model_rebuild()