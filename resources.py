"""
resources.py — Simulated cloud infrastructure for NovaCart (fictional e-commerce).

Design principles for 50-call budget:
  Task 1 — 8 orphans to delete.   Achievable in  8 steps. Max 12.
  Task 2 — 5 resize + 3 cold.     Achievable in  8 steps. Max 15.
  Task 3 — migrate+wait+15 terms. Achievable in 17 steps. Max 25.
  Total worst-case: 52 steps → well within 50 per run with early stopping.

Savings targets are sized so the heuristic agent can hit ~0.7+ on each task.
"""

from __future__ import annotations
from models import Resource, ResourceType, ResourceStatus, StorageTier, InstanceSize

# ══════════════════════════════════════════════════════════════════════════════
# TASK 1 — EASY
# 20 resources | Bill: $7,450 | Savings target: $705 | Max steps: 12
# 8 obvious orphans (no traffic, no attachment). 12 active production.
# Agent just needs to find status=orphaned/stopped + traffic=0.
# ══════════════════════════════════════════════════════════════════════════════

TASK_1_RESOURCES: list[Resource] = [

    # ── 8 ORPHANS ─────────────────────────────────────────────────────────────
    Resource(
        id="ip-unused-001", name="Unassigned Elastic IP #1",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={"env": "unknown"}, safe_to_terminate=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="ip-unused-002", name="Unassigned Elastic IP #2",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={}, safe_to_terminate=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-orphan-001", name="Orphan EBS Volume 500 GB",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=55.00,
        attached_to=None, size_gb=500, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=180, safe_to_terminate=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-orphan-002", name="Orphan EBS Volume 200 GB",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=22.00,
        attached_to=None, size_gb=200, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=210, safe_to_terminate=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-orphan-003", name="Orphan EBS Volume 1 TB",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=110.00,
        attached_to=None, size_gb=1000, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=145, safe_to_terminate=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-stopped-001", name="Stopped VM — legacy-worker-east",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-east-1", monthly_cost=180.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.MEDIUM,
        tags={"env": "legacy"}, safe_to_terminate=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-stopped-002", name="Stopped VM — old-batch-runner",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-east-1", monthly_cost=210.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE,
        tags={"env": "dev", "team": "data"}, safe_to_terminate=True,
        base_cost_at_large=210.00,
    ),
    Resource(
        id="snapshot-old-001", name="DB Snapshot — prod-postgres-2022-06",
        resource_type=ResourceType.SNAPSHOT, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=38.00,
        attached_to=None, size_gb=380,
        last_accessed_days_ago=730, safe_to_terminate=True,
        base_cost_at_large=None,
    ),

    # ── 12 ACTIVE PRODUCTION ──────────────────────────────────────────────────
    Resource(
        id="vm-api-gateway", name="API Gateway — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=71.4, ram_avg_24h=68.2, traffic_per_hour=45000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod", "tier": "api"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-payment-proc", name="Payment Processor — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=890.00,
        cpu_avg_24h=68.1, ram_avg_24h=72.0, traffic_per_hour=12000,
        instance_size=InstanceSize.XLARGE,
        tags={"env": "prod", "compliance": "PCI-DSS"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="db-postgres-main", name="PostgreSQL Primary — prod",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=1840.00,
        cpu_avg_24h=74.3, ram_avg_24h=81.0, traffic_per_hour=28000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="db-redis-cache", name="Redis Cache Cluster — prod",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=420.00,
        cpu_avg_24h=45.2, ram_avg_24h=88.0, traffic_per_hour=95000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-web-frontend-1", name="Web Frontend Node 1 — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=52.1, ram_avg_24h=55.3, traffic_per_hour=38000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-web-frontend-2", name="Web Frontend Node 2 — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=49.7, ram_avg_24h=51.8, traffic_per_hour=35000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="lb-main", name="Application Load Balancer — prod",
        resource_type=ResourceType.LOAD_BALANCER, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=290.00,
        cpu_avg_24h=38.0, traffic_per_hour=80000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-db-primary", name="PostgreSQL Primary Data Volume",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=180.00,
        attached_to="db-postgres-main", size_gb=2000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=0,
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-checkout-svc", name="Checkout Service — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=540.00,
        cpu_avg_24h=61.4, ram_avg_24h=63.0, traffic_per_hour=9500,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="cdn-assets", name="CDN — static assets and media",
        resource_type=ResourceType.CDN, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=680.00,
        cpu_avg_24h=29.0, traffic_per_hour=120000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-auth-service", name="Auth Service — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=430.00,
        cpu_avg_24h=44.1, ram_avg_24h=48.9, traffic_per_hour=18000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vol-backups-active", name="Live Backup Volume — postgres",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=95.00,
        attached_to="db-postgres-main", size_gb=1000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=1,
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
]

TASK_1_BILL   = sum(r.monthly_cost for r in TASK_1_RESOURCES)   # 7,450
TASK_1_TARGET = 705.00   # delete all 8 orphans = exact score 1.0
TASK_1_ORPHAN_IDS = {
    "ip-unused-001", "ip-unused-002",
    "vol-orphan-001", "vol-orphan-002", "vol-orphan-003",
    "vm-stopped-001", "vm-stopped-002",
    "snapshot-old-001",
}


# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 — MEDIUM
# 18 resources | Bill: ~$11,700 | Savings target: $3,500 | Max steps: 15
#
# Safe savings available:
#   Resize 5 VMs (xlarge→small saves ~$1,030 each, large→small saves ~$410):
#     vm-ml-training:       xlarge → small  saves $1,030
#     vm-analytics-worker-1: large → small  saves  $410
#     vm-analytics-worker-2: large → small  saves  $410
#     vm-reporting-svc:     large → small   saves  $410
#     vm-internal-tools:    large → small   saves  $410
#   Total resize savings: ~$2,670
#
#   Cold migrate 3 volumes (saves 80%):
#     vol-logs-2023:   $340 → $68  saves $272
#     vol-logs-2022:   $290 → $58  saves $232
#     vol-archive:     $180 → $36  saves $144
#   Total cold savings: ~$648
#
# Total safe savings: ~$3,318 (score ~0.95 — grader caps at 1.0)
# ══════════════════════════════════════════════════════════════════════════════

TASK_2_RESOURCES: list[Resource] = [

    # ── 5 OVERSIZED VMs (resize these) ───────────────────────────────────────
    Resource(
        id="vm-ml-training", name="ML Training Server — idle",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=1240.00,
        cpu_avg_24h=6.1, ram_avg_24h=11.2, traffic_per_hour=0,
        instance_size=InstanceSize.XLARGE,
        tags={"env": "ml", "team": "data-science"},
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-analytics-worker-1", name="Analytics Worker 1 — oversized",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=4.2, ram_avg_24h=8.1, traffic_per_hour=120,
        instance_size=InstanceSize.LARGE,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-analytics-worker-2", name="Analytics Worker 2 — oversized",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=3.8, ram_avg_24h=7.4, traffic_per_hour=95,
        instance_size=InstanceSize.LARGE,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-reporting-svc", name="Reporting Service — oversized",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=5.3, ram_avg_24h=9.0, traffic_per_hour=45,
        instance_size=InstanceSize.LARGE,
        tags={"env": "internal", "team": "ops"},
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-internal-tools", name="Internal Tools Server — oversized",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=7.2, ram_avg_24h=13.1, traffic_per_hour=180,
        instance_size=InstanceSize.LARGE,
        tags={"env": "internal", "team": "eng"},
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=620.00,
    ),

    # ── 3 COLD STORAGE CANDIDATES ─────────────────────────────────────────────
    Resource(
        id="vol-logs-2023", name="App Logs Archive 2023",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=340.00,
        attached_to=None, size_gb=3200,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=425,
        safe_to_terminate=False, is_production=False,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-logs-2022", name="App Logs Archive 2022",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=290.00,
        attached_to=None, size_gb=2800,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=790,
        safe_to_terminate=False, is_production=False,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-archive-q1-2023", name="Q1 2023 Data Archive",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=180.00,
        attached_to=None, size_gb=1700,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=548,
        safe_to_terminate=False, is_production=False,
        base_cost_at_large=None,
    ),

    # ── 10 ACTIVE PRODUCTION (do not touch) ───────────────────────────────────
    Resource(
        id="vm-api-gateway", name="API Gateway — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=73.1, ram_avg_24h=70.4, traffic_per_hour=48000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-payment-proc", name="Payment Processor — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=890.00,
        cpu_avg_24h=71.0, ram_avg_24h=74.2, traffic_per_hour=13500,
        instance_size=InstanceSize.XLARGE,
        tags={"env": "prod", "compliance": "PCI-DSS"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="db-postgres-main", name="PostgreSQL Primary — prod",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=1840.00,
        cpu_avg_24h=76.2, ram_avg_24h=83.1, traffic_per_hour=31000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="db-redis-cache", name="Redis Cache Cluster — prod",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=420.00,
        cpu_avg_24h=48.0, ram_avg_24h=89.0, traffic_per_hour=98000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-web-frontend-1", name="Web Frontend Node 1 — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=55.3, ram_avg_24h=57.0, traffic_per_hour=41000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-checkout-svc", name="Checkout Service — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=540.00,
        cpu_avg_24h=64.2, ram_avg_24h=66.0, traffic_per_hour=10200,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="cdn-assets", name="CDN — static assets and media",
        resource_type=ResourceType.CDN, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=680.00,
        cpu_avg_24h=31.0, traffic_per_hour=125000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-auth-service", name="Auth Service — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=430.00,
        cpu_avg_24h=46.0, ram_avg_24h=50.2, traffic_per_hour=19500,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="lb-main", name="Application Load Balancer — prod",
        resource_type=ResourceType.LOAD_BALANCER, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=290.00,
        cpu_avg_24h=41.0, traffic_per_hour=85000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-db-primary", name="PostgreSQL Primary Data Volume",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=180.00,
        attached_to="db-postgres-main", size_gb=2000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=0,
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-search-service", name="Search Service — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=67.0, ram_avg_24h=71.0, traffic_per_hour=17000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=620.00,
    ),
]

TASK_2_BILL   = sum(r.monthly_cost for r in TASK_2_RESOURCES)   # ~$11,700
TASK_2_TARGET = 3500.00   # achievable with 5 resizes + 3 cold migrations


# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 — HARD: MULTI-REGION HONEYPOT FAILOVER
# 35 resources | Bill: ~$22,800 | Savings target: $8,000 | Max steps: 25
#
# Designed for 50-call budget. Achievable in ~17 steps with correct play:
#   Step 1:   migrate_traffic(source_region="us-east-1")
#   Step 2:   wait()
#   Steps 3-7:  Delete 5 east-1 obvious orphans/stopped VMs       (~$1,185)
#   Steps 8-17: Terminate 10 east-1 production resources (unlocked) (~$6,410)
#   Steps 18-21: Delete 4 west-2 orphans                           (~$410)
#   Total safe savings: ~$8,005 → hits target
#
# Honeypot traps prevent shortcuts:
#   Trap 1: db-west-analytics-1/2 — cpu_avg=2% but peak_queries_2am=1.5M
#   Trap 2: vm-west-dev-api — tagged "dev" but traffic=8,400/hr
#   Trap 3: vol-west-media-archive — attached_to=None but dependency_of set
# ══════════════════════════════════════════════════════════════════════════════

TASK_3_RESOURCES: list[Resource] = [

    # ══ us-east-1 — LEGACY REGION (shut down after traffic migration) ══════════

    # Obvious waste — safe to delete immediately (no migration needed)
    Resource(
        id="ip-east-unused-1", name="Unassigned Elastic IP (east-1)",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=None,
    ),
    Resource(
        id="ip-east-unused-2", name="Unassigned Elastic IP #2 (east-1)",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-east-orphan-1", name="Orphan Volume 2TB (east-1)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=180.00,
        attached_to=None, size_gb=2000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=290,
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-stopped-1", name="Stopped VM — legacy-api-east",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-east-old-worker", name="Old Analytics Worker (east-1)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=3.1, ram_avg_24h=6.8, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=620.00,
    ),

    # East-1 active production — safe_to_terminate=False UNTIL migrate+wait done
    # Environment unlocks these dynamically after drain sequence.
    Resource(
        id="lb-east-main", name="Load Balancer — us-east-1 (migrate target)",
        resource_type=ResourceType.LOAD_BALANCER, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=290.00,
        traffic_per_hour=70000,
        tags={"env": "prod", "note": "call migrate_traffic then wait before terminating"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-api", name="API Gateway (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=69.0, ram_avg_24h=66.0, traffic_per_hour=38000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-east-payment", name="Payment Processor (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=890.00,
        cpu_avg_24h=72.0, ram_avg_24h=74.0, traffic_per_hour=11000,
        instance_size=InstanceSize.XLARGE,
        tags={"env": "prod", "compliance": "PCI-DSS"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-east-checkout", name="Checkout Service (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=540.00,
        cpu_avg_24h=58.0, ram_avg_24h=61.0, traffic_per_hour=8000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="db-east-postgres", name="PostgreSQL Primary (east-1 prod)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=1840.00,
        cpu_avg_24h=71.0, ram_avg_24h=79.0, traffic_per_hour=25000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-auth", name="Auth Service (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=430.00,
        cpu_avg_24h=42.0, ram_avg_24h=47.0, traffic_per_hour=16000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vol-east-db-primary", name="PostgreSQL Data Volume (east-1)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=180.00,
        attached_to="db-east-postgres", size_gb=2000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=0,
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-frontend-1", name="Web Frontend 1 (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=48.0, ram_avg_24h=51.0, traffic_per_hour=32000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-east-frontend-2", name="Web Frontend 2 (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=51.0, ram_avg_24h=54.0, traffic_per_hour=35000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="cdn-east-assets", name="CDN East (static and media)",
        resource_type=ResourceType.CDN, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=680.00,
        traffic_per_hour=95000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),

    # ══ us-west-2 — PRIMARY REGION (stays running) ════════════════════════════

    # Clear waste in west-2
    Resource(
        id="ip-west-unused-1", name="Unassigned Elastic IP (west-2)",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-west-2", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=None,
    ),
    Resource(
        id="vol-west-orphan-1", name="Orphan Volume 1TB (west-2)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-west-2", monthly_cost=110.00,
        attached_to=None, size_gb=1000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=380,
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-west-stopped-1", name="Stopped VM — old-worker-west",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-west-2", monthly_cost=210.00,
        cpu_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.MEDIUM,
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="snapshot-west-old", name="Old DB Snapshot (west-2 2022)",
        resource_type=ResourceType.SNAPSHOT, status=ResourceStatus.ORPHANED,
        region="us-west-2", monthly_cost=42.00,
        attached_to=None, size_gb=400,
        last_accessed_days_ago=600,
        safe_to_terminate=True, is_production=False,
        base_cost_at_large=None,
    ),

    # Active production in west-2
    Resource(
        id="vm-west-api", name="API Gateway (west-2 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=590.00,
        cpu_avg_24h=74.0, ram_avg_24h=71.0, traffic_per_hour=42000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=590.00,
    ),
    Resource(
        id="vm-west-payment", name="Payment Processor (west-2 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=840.00,
        cpu_avg_24h=68.0, ram_avg_24h=73.0, traffic_per_hour=12500,
        instance_size=InstanceSize.XLARGE,
        tags={"env": "prod", "compliance": "PCI-DSS"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=590.00,
    ),
    Resource(
        id="lb-west-main", name="Load Balancer — us-west-2",
        resource_type=ResourceType.LOAD_BALANCER, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=270.00,
        traffic_per_hour=78000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="db-west-postgres-main", name="PostgreSQL Primary (west-2 prod)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=1840.00,
        cpu_avg_24h=78.0, ram_avg_24h=82.0, traffic_per_hour=33000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="db-west-redis-cache", name="Redis Cache Cluster (west-2 prod)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=420.00,
        cpu_avg_24h=51.0, ram_avg_24h=89.0, traffic_per_hour=102000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),

    # ── 🍯 HONEYPOT TRAP 1: Midnight Batch Jobs ───────────────────────────────
    # cpu_avg_24h=2% looks completely idle.
    # peak_queries_2am is HIDDEN from agent (not in AgentResource).
    # Signal the agent CAN see: high monthly_cost + database type.
    # Deleting = honeypot hit + downtime event.
    Resource(
        id="db-west-analytics-1",
        name="Analytics DB — ML Pipeline (west-2)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=4200.00,
        cpu_avg_24h=2.3, traffic_per_hour=180,
        peak_cpu_2am=91.4,
        peak_queries_2am=1_500_000,
        tags={"env": "analytics", "team": "data-science"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="db-west-analytics-2",
        name="Analytics DB — Recommendation Model (west-2)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=3800.00,
        cpu_avg_24h=1.8, traffic_per_hour=95,
        peak_cpu_2am=87.2,
        peak_queries_2am=980_000,
        tags={"env": "analytics", "team": "ml"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),

    # ── 🍯 HONEYPOT TRAP 2: Tags That Lie ────────────────────────────────────
    # tagged "dev" but traffic_per_hour=8,400 → real production traffic.
    Resource(
        id="vm-west-dev-api",
        name="Backend API — tagged dev, serves mobile app (west-2)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=430.00,
        cpu_avg_24h=31.0, ram_avg_24h=38.0, traffic_per_hour=8400,
        instance_size=InstanceSize.MEDIUM,
        tags={"env": "dev", "team": "backend"},
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),

    # ── 🍯 HONEYPOT TRAP 3: Hidden Dependency ─────────────────────────────────
    # attached_to=None looks orphaned. dependency_of IS visible to agent.
    # Agent must read dependency_of before terminating.
    Resource(
        id="vol-west-media-archive",
        name="Media Processing Volume (west-2)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=680.00,
        attached_to=None,
        dependency_of=["vm-west-payment", "vm-west-checkout"],
        size_gb=6200, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=None,
        safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
]

TASK_3_BILL   = sum(r.monthly_cost for r in TASK_3_RESOURCES)   # ~$22,800
TASK_3_TARGET = 8000.00   # achievable in ~17 steps with correct play

# East-1 production IDs that unlock after migrate_traffic + wait
EAST_1_PRODUCTION_IDS: set[str] = {
    "lb-east-main", "vm-east-api", "vm-east-payment",
    "vm-east-checkout", "db-east-postgres", "vm-east-auth",
    "vol-east-db-primary", "vm-east-frontend-1",
    "vm-east-frontend-2", "cdn-east-assets",
}


# ══════════════════════════════════════════════════════════════════════════════
# TASK REGISTRY — consumed by environment.py and server.py
# ══════════════════════════════════════════════════════════════════════════════

TASKS: dict[str, list[Resource]] = {
    "task_1": TASK_1_RESOURCES,
    "task_2": TASK_2_RESOURCES,
    "task_3": TASK_3_RESOURCES,
}

TASK_META: dict[str, dict] = {
    "task_1": {
        "name": "Orphan Cleanup — Find and Delete Cloud Waste",
        "difficulty": "easy",
        "description": (
            "NovaCart is paying for 8 orphaned resources: unattached IPs, "
            "detached volumes, and stopped VMs. Identify and terminate them "
            "without touching any active production resource."
        ),
        "monthly_bill": TASK_1_BILL,
        "savings_target": TASK_1_TARGET,
        "max_steps": 12,
        "regions": ["us-east-1"],
        "grading_notes": (
            "Score = (orphans_deleted/8) - (false_kills * 0.25). "
            "Perfect play = 1.0. Any false kill loses 0.25."
        ),
    },
    "task_2": {
        "name": "Rightsize — Downgrade Oversized Instances",
        "difficulty": "medium",
        "description": (
            "Five VMs are massively oversized (cpu < 8%, LARGE/XLARGE). "
            "Three storage volumes should move to cold tier (last accessed > 400 days). "
            "Target: $3,500/month savings. Do not touch active production."
        ),
        "monthly_bill": TASK_2_BILL,
        "savings_target": TASK_2_TARGET,
        "max_steps": 15,
        "regions": ["us-east-1"],
        "grading_notes": (
            "Score = clamp(savings_achieved / 3500, 0, 1) - (downtime_events * 0.20). "
            "Resize + cold-migrate to maximize savings."
        ),
    },
    "task_3": {
        "name": "Multi-Region Failover — Honeypot Shutdown",
        "difficulty": "hard",
        "description": (
            "Shut down the legacy us-east-1 region to save $8,000/month. "
            "REQUIRED SEQUENCE: (1) migrate_traffic source_region=us-east-1, "
            "(2) wait, (3) terminate east-1 resources. "
            "Beware: 3 honeypot traps in us-west-2 will destroy your score. "
            "Trap 1: Analytics DBs look idle (cpu=2%) but run batch at 2am. "
            "Trap 2: Dev-tagged VM has real traffic (8,400/hr). "
            "Trap 3: Volume looks orphaned but has dependency_of set."
        ),
        "monthly_bill": TASK_3_BILL,
        "savings_target": TASK_3_TARGET,
        "max_steps": 25,
        "regions": ["us-east-1", "us-west-2"],
        "grading_notes": (
            "Score = clamp(savings/8000,0,1) - downtime*0.15 "
            "- honeypot_hits*0.20 - sequence_violations*0.15."
        ),
    },
}