"""
resources.py — Simulated cloud infrastructure

Design principles:
  Budget: each task ≤ 20 steps. Total across 3 tasks ≤ 50 LLM calls.
"""
from __future__ import annotations
from models import Resource, ResourceType, ResourceStatus, StorageTier, InstanceSize

# TASK 1 — EASY

TASK_1_RESOURCES: list[Resource] = [
    Resource(
        id="ip-unused-001", name="Unassigned Elastic IP #1",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={"env": "unknown"}, safe_to_terminate=True, base_cost_at_large=None,
    ),
    Resource(
        id="ip-unused-002", name="Unassigned Elastic IP #2",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={}, safe_to_terminate=True, base_cost_at_large=None,
    ),
    Resource(
        id="vol-orphan-001", name="Orphan EBS Volume 500 GB",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=55.00,
        attached_to=None, size_gb=500, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=180, safe_to_terminate=True, base_cost_at_large=None,
    ),
    Resource(
        id="vol-orphan-002", name="Orphan EBS Volume 200 GB",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=22.00,
        attached_to=None, size_gb=200, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=210, safe_to_terminate=True, base_cost_at_large=None,
    ),
    Resource(
        id="vol-orphan-003", name="Orphan EBS Volume 1 TB",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=110.00,
        attached_to=None, size_gb=1000, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=145, safe_to_terminate=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-stopped-001", name="Stopped VM — legacy-worker-east",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-east-1", monthly_cost=180.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.MEDIUM,
        tags={"env": "legacy"}, safe_to_terminate=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-stopped-002", name="Stopped VM — old-batch-runner",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-east-1", monthly_cost=210.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE,
        tags={"env": "dev", "team": "data"}, safe_to_terminate=True, base_cost_at_large=210.00,
    ),
    Resource(
        id="snapshot-old-001", name="DB Snapshot — prod-postgres-2022-06",
        resource_type=ResourceType.SNAPSHOT, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=38.00,
        attached_to=None, size_gb=380,
        last_accessed_days_ago=730, safe_to_terminate=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-api-gateway", name="API Gateway — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=71.4, ram_avg_24h=68.2, traffic_per_hour=45000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod", "tier": "api"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-payment-proc", name="Payment Processor — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=890.00,
        cpu_avg_24h=68.1, ram_avg_24h=72.0, traffic_per_hour=12000,
        instance_size=InstanceSize.XLARGE,
        tags={"env": "prod", "compliance": "PCI-DSS"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=620.00,
    ),
    Resource(
        id="db-postgres-main", name="PostgreSQL Primary — prod",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=1840.00,
        cpu_avg_24h=74.3, ram_avg_24h=81.0, queries_per_hour=28000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="db-redis-cache", name="Redis Cache Cluster — prod",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=420.00,
        cpu_avg_24h=45.2, ram_avg_24h=88.0, queries_per_hour=95000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-web-frontend-1", name="Web Frontend Node 1 — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=52.1, ram_avg_24h=55.3, traffic_per_hour=38000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-web-frontend-2", name="Web Frontend Node 2 — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=49.7, ram_avg_24h=51.8, traffic_per_hour=35000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="lb-main", name="Application Load Balancer — prod",
        resource_type=ResourceType.LOAD_BALANCER, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=290.00,
        cpu_avg_24h=38.0, traffic_per_hour=80000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vol-db-primary", name="PostgreSQL Primary Data Volume",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=180.00,
        attached_to="db-postgres-main", size_gb=2000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=0,
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-checkout-svc", name="Checkout Service — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=540.00,
        cpu_avg_24h=61.4, ram_avg_24h=63.0, traffic_per_hour=9500,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="cdn-assets", name="CDN — static assets and media",
        resource_type=ResourceType.CDN, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=680.00,
        cpu_avg_24h=29.0, traffic_per_hour=120000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-auth-service", name="Auth Service — prod",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=430.00,
        cpu_avg_24h=44.1, ram_avg_24h=48.9, traffic_per_hour=18000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="vol-backups-active", name="Live Backup Volume — postgres",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=95.00,
        attached_to="db-postgres-main", size_gb=1000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=1,
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
]

TASK_1_BILL = sum(r.monthly_cost for r in TASK_1_RESOURCES)
TASK_1_TARGET = 705.00
TASK_1_ORPHAN_IDS = {
    "ip-unused-001", "ip-unused-002",
    "vol-orphan-001", "vol-orphan-002", "vol-orphan-003",
    "vm-stopped-001", "vm-stopped-002", "snapshot-old-001",
}


# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 — MEDIUM
# 20 resources | 5 resize + 3 cold candidates + 2 traps
# Traps: one "idle" VM that runs cron jobs, one "old" volume that's a dep
# ══════════════════════════════════════════════════════════════════════════════

TASK_2_RESOURCES: list[Resource] = [
    Resource(
        id="vm-ml-training", name="ML Training Server — idle",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=1240.00,
        cpu_avg_24h=6.1, ram_avg_24h=11.2, traffic_per_hour=0,
        instance_size=InstanceSize.XLARGE,
        tags={"env": "ml", "team": "data-science"},
        safe_to_terminate=True, is_production=False, base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-analytics-worker-1", name="Analytics Worker 1 — oversized",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=4.2, ram_avg_24h=8.1, traffic_per_hour=120,
        instance_size=InstanceSize.LARGE,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False, base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-analytics-worker-2", name="Analytics Worker 2 — oversized",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=3.8, ram_avg_24h=7.4, traffic_per_hour=95,
        instance_size=InstanceSize.LARGE,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False, base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-reporting-svc", name="Reporting Service — oversized",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=5.3, ram_avg_24h=9.0, traffic_per_hour=45,
        instance_size=InstanceSize.LARGE,
        tags={"env": "internal", "team": "ops"},
        safe_to_terminate=True, is_production=False, base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-internal-tools", name="Internal Tools Server — oversized",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=7.2, ram_avg_24h=13.1, traffic_per_hour=180,
        instance_size=InstanceSize.LARGE,
        tags={"env": "internal", "team": "eng"},
        safe_to_terminate=True, is_production=False, base_cost_at_large=620.00,
    ),

    Resource(
        id="vm-etl-scheduler", name="ETL Scheduler — looks idle",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=3.1, ram_avg_24h=5.8, traffic_per_hour=12,
        instance_size=InstanceSize.LARGE,
        tags={"env": "data", "schedule": "nightly"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=620.00,
        peak_cpu_2am=94.0, peak_queries_2am=800_000,
    ),

    Resource(
        id="vol-logs-2023", name="App Logs Archive 2023",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=340.00,
        attached_to=None, size_gb=3200,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=425,
        safe_to_terminate=False, is_production=False, base_cost_at_large=None,
    ),
    Resource(
        id="vol-logs-2022", name="App Logs Archive 2022",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=290.00,
        attached_to=None, size_gb=2800,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=790,
        safe_to_terminate=False, is_production=False, base_cost_at_large=None,
    ),
    Resource(
        id="vol-archive-q1-2023", name="Q1 2023 Data Archive",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=180.00,
        attached_to=None, size_gb=1700,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=548,
        safe_to_terminate=False, is_production=False, base_cost_at_large=None,
    ),

    Resource(
        id="vol-compliance-archive", name="Compliance Data Archive 2021",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=420.00,
        attached_to=None, size_gb=4000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=610,
        dependency_of=["vm-payment-proc", "db-postgres-main"],
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),

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
        safe_to_terminate=False, is_production=True, base_cost_at_large=620.00,
    ),
    Resource(
        id="db-postgres-main", name="PostgreSQL Primary — prod",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=1840.00,
        cpu_avg_24h=76.2, ram_avg_24h=83.1, queries_per_hour=31000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="db-redis-cache", name="Redis Cache Cluster — prod",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=420.00,
        cpu_avg_24h=48.0, ram_avg_24h=89.0, queries_per_hour=98000,
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
        id="cdn-assets", name="CDN — static assets",
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
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
]

TASK_2_BILL = sum(r.monthly_cost for r in TASK_2_RESOURCES)
TASK_2_TARGET = 3500.00


# TASK 3 — HARD

TASK_3_RESOURCES: list[Resource] = [

    Resource(
        id="ip-east-unused-1", name="Unassigned Elastic IP (east-1)",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        safe_to_terminate=True, is_production=False, base_cost_at_large=None,
    ),
    Resource(
        id="ip-east-unused-2", name="Unassigned Elastic IP #2 (east-1)",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        safe_to_terminate=True, is_production=False, base_cost_at_large=None,
    ),
    Resource(
        id="vol-east-orphan-1", name="Orphan Volume 2TB (east-1)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=180.00,
        attached_to=None, size_gb=2000, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=290,
        safe_to_terminate=True, is_production=False, base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-stopped-1", name="Stopped VM — legacy-api-east",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE, tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False, base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-east-old-worker", name="Old Analytics Worker (east-1)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=3.1, ram_avg_24h=6.8, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE, tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False, base_cost_at_large=620.00,
    ),
    Resource(
        id="snapshot-east-old", name="Old DB Snapshot (east-1 2022)",
        resource_type=ResourceType.SNAPSHOT, status=ResourceStatus.ORPHANED,
        region="us-east-1", monthly_cost=38.00,
        attached_to=None, size_gb=400, last_accessed_days_ago=800,
        safe_to_terminate=True, is_production=False, base_cost_at_large=None,
    ),

    Resource(
        id="lb-east-main", name="Load Balancer — us-east-1",
        resource_type=ResourceType.LOAD_BALANCER, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=290.00,
        traffic_per_hour=70000, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-api", name="API Gateway (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=620.00,
        cpu_avg_24h=69.0, ram_avg_24h=66.0, traffic_per_hour=38000,
        instance_size=InstanceSize.LARGE, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-east-payment", name="Payment Processor (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=890.00,
        cpu_avg_24h=72.0, ram_avg_24h=74.0, traffic_per_hour=11000,
        instance_size=InstanceSize.XLARGE,
        tags={"env": "prod", "compliance": "PCI-DSS"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=620.00,
    ),
    Resource(
        id="vm-east-checkout", name="Checkout Service (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=540.00,
        cpu_avg_24h=58.0, ram_avg_24h=61.0, traffic_per_hour=8000,
        instance_size=InstanceSize.LARGE, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="db-east-postgres", name="PostgreSQL Primary (east-1 prod)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=1840.00,
        cpu_avg_24h=71.0, ram_avg_24h=79.0, queries_per_hour=25000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-auth", name="Auth Service (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=430.00,
        cpu_avg_24h=42.0, ram_avg_24h=47.0, traffic_per_hour=16000,
        instance_size=InstanceSize.LARGE, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="vol-east-db-primary", name="PostgreSQL Data Volume (east-1)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=180.00,
        attached_to="db-east-postgres", size_gb=2000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=0,
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-frontend-1", name="Web Frontend 1 (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=48.0, ram_avg_24h=51.0, traffic_per_hour=32000,
        instance_size=InstanceSize.LARGE, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-east-frontend-2", name="Web Frontend 2 (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=380.00,
        cpu_avg_24h=51.0, ram_avg_24h=54.0, traffic_per_hour=35000,
        instance_size=InstanceSize.LARGE, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),
    Resource(
        id="cdn-east-assets", name="CDN East (static and media)",
        resource_type=ResourceType.CDN, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=680.00,
        traffic_per_hour=95000, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="cache-east-redis", name="Redis Cache (east-1 prod)",
        resource_type=ResourceType.CACHE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=420.00,
        cpu_avg_24h=41.0, queries_per_hour=88000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-east-search", name="Search Service (east-1 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=540.00,
        cpu_avg_24h=55.0, ram_avg_24h=60.0, traffic_per_hour=14000,
        instance_size=InstanceSize.LARGE, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=540.00,
    ),
    Resource(
        id="db-east-replica", name="PostgreSQL Read Replica (east-1)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-east-1", monthly_cost=920.00,
        cpu_avg_24h=38.0, ram_avg_24h=45.0, queries_per_hour=18000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),

    Resource(
        id="ip-west-unused-1", name="Unassigned Elastic IP (west-2)",
        resource_type=ResourceType.IP_ADDRESS, status=ResourceStatus.ORPHANED,
        region="us-west-2", monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        safe_to_terminate=True, is_production=False, base_cost_at_large=None,
    ),
    Resource(
        id="vol-west-orphan-1", name="Orphan Volume 1TB (west-2)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.ORPHANED,
        region="us-west-2", monthly_cost=110.00,
        attached_to=None, size_gb=1000, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=380,
        safe_to_terminate=True, is_production=False, base_cost_at_large=None,
    ),
    Resource(
        id="vm-west-stopped-1", name="Stopped VM — old-worker-west",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-west-2", monthly_cost=210.00,
        cpu_avg_24h=0.0, traffic_per_hour=0, instance_size=InstanceSize.MEDIUM,
        safe_to_terminate=True, is_production=False, base_cost_at_large=380.00,
    ),
    Resource(
        id="snapshot-west-old", name="Old DB Snapshot (west-2 2022)",
        resource_type=ResourceType.SNAPSHOT, status=ResourceStatus.ORPHANED,
        region="us-west-2", monthly_cost=42.00,
        attached_to=None, size_gb=400, last_accessed_days_ago=600,
        safe_to_terminate=True, is_production=False, base_cost_at_large=None,
    ),

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
        safe_to_terminate=False, is_production=True, base_cost_at_large=590.00,
    ),
    Resource(
        id="lb-west-main", name="Load Balancer — us-west-2",
        resource_type=ResourceType.LOAD_BALANCER, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=270.00,
        traffic_per_hour=78000, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="db-west-postgres-main", name="PostgreSQL Primary (west-2 prod)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=1840.00,
        cpu_avg_24h=78.0, ram_avg_24h=82.0, queries_per_hour=33000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="db-west-redis-cache", name="Redis Cache Cluster (west-2 prod)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=420.00,
        cpu_avg_24h=51.0, ram_avg_24h=89.0, queries_per_hour=102000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-west-checkout", name="Checkout Service (west-2 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=540.00,
        cpu_avg_24h=62.0, ram_avg_24h=65.0, traffic_per_hour=9800,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-west-frontend-1", name="Web Frontend 1 (west-2 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=380.00,
        cpu_avg_24h=56.0, ram_avg_24h=58.0, traffic_per_hour=40000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="vm-west-frontend-2", name="Web Frontend 2 (west-2 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=380.00,
        cpu_avg_24h=53.0, ram_avg_24h=55.0, traffic_per_hour=37000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),

    Resource(
        id="db-west-batch-etl", name="Batch ETL Database (west-2)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=4200.00,
        cpu_avg_24h=2.3, queries_per_hour=180,
        peak_cpu_2am=91.4, peak_queries_2am=1_500_000,
        tags={"env": "analytics", "schedule": "nightly", "team": "data-science"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="db-west-ml-pipeline", name="ML Pipeline Database (west-2)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=3800.00,
        cpu_avg_24h=1.8, queries_per_hour=95,
        peak_cpu_2am=87.2, peak_queries_2am=980_000,
        tags={"env": "ml", "schedule": "nightly", "team": "ml"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),

    Resource(
        id="vm-west-shadow-api", name="Shadow API — tagged dev (west-2)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=430.00,
        cpu_avg_24h=31.0, ram_avg_24h=38.0, traffic_per_hour=8400,
        instance_size=InstanceSize.MEDIUM,
        tags={"env": "dev", "team": "backend"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=380.00,
    ),

    Resource(
        id="vol-west-shared-assets", name="Shared Media Assets Volume (west-2)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=680.00,
        attached_to=None,
        dependency_of=["vm-west-payment", "vm-west-checkout", "vm-west-frontend-1"],
        size_gb=6200, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=None,
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),

    Resource(
        id="vm-west-dr-standby", name="DR Standby Node (west-2) — stopped",
        resource_type=ResourceType.VM, status=ResourceStatus.STOPPED,
        region="us-west-2", monthly_cost=620.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE,
        tags={"env": "dr", "role": "standby", "priority": "critical"},
        dependency_of=["lb-west-main"],
        safe_to_terminate=False, is_production=True, base_cost_at_large=620.00,
        peak_cpu_2am=None, peak_queries_2am=None,
    ),

    Resource(
        id="vm-west-audit-logger", name="PCI Audit Logger (west-2) — oversized?",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=620.00,
        cpu_avg_24h=8.5, ram_avg_24h=12.0, traffic_per_hour=350,
        instance_size=InstanceSize.LARGE,
        tags={"env": "compliance", "compliance": "PCI-DSS", "audit": "required"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=620.00,
    ),

    Resource(
        id="vm-west-auth", name="Auth Service (west-2 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=430.00,
        cpu_avg_24h=44.0, ram_avg_24h=48.0, traffic_per_hour=17000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
    Resource(
        id="cdn-west-assets", name="CDN West (static and media)",
        resource_type=ResourceType.CDN, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=680.00,
        traffic_per_hour=110000, tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="vm-west-search", name="Search Service (west-2 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=540.00,
        cpu_avg_24h=59.0, ram_avg_24h=62.0, traffic_per_hour=15000,
        instance_size=InstanceSize.LARGE,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=540.00,
    ),
    Resource(
        id="vol-west-db-primary", name="PostgreSQL Data Volume (west-2)",
        resource_type=ResourceType.STORAGE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=180.00,
        attached_to="db-west-postgres-main", size_gb=2000,
        storage_tier=StorageTier.HOT, last_accessed_days_ago=0,
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="cache-west-redis", name="Redis Cache (west-2 prod)",
        resource_type=ResourceType.CACHE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=420.00,
        cpu_avg_24h=49.0, queries_per_hour=96000,
        tags={"env": "prod"},
        safe_to_terminate=False, is_production=True, base_cost_at_large=None,
    ),
    Resource(
        id="db-west-replica", name="PostgreSQL Read Replica (west-2)",
        resource_type=ResourceType.DATABASE, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=920.00,
        cpu_avg_24h=35.0, ram_avg_24h=42.0, queries_per_hour=16000,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=None,
    ),
    Resource(
        id="vm-west-notification", name="Notification Service (west-2 prod)",
        resource_type=ResourceType.VM, status=ResourceStatus.RUNNING,
        region="us-west-2", monthly_cost=380.00,
        cpu_avg_24h=28.0, ram_avg_24h=32.0, traffic_per_hour=6200,
        instance_size=InstanceSize.MEDIUM,
        tags={"env": "prod"}, safe_to_terminate=False, is_production=True,
        base_cost_at_large=380.00,
    ),
]

TASK_3_BILL = sum(r.monthly_cost for r in TASK_3_RESOURCES)
TASK_3_TARGET = 10000.00  # Harder target — need east-1 shutdown + west-2 orphans

EAST_1_PRODUCTION_IDS: set[str] = {
    "lb-east-main", "vm-east-api", "vm-east-payment",
    "vm-east-checkout", "db-east-postgres", "vm-east-auth",
    "vol-east-db-primary", "vm-east-frontend-1",
    "vm-east-frontend-2", "cdn-east-assets", "cache-east-redis",
    "vm-east-search", "db-east-replica",
}



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
        "max_steps": 15,
        "regions": ["us-east-1"],
        "grading_notes": (
            "Score = (orphans_deleted/8) - (false_kills * 0.20) - (downtime * 0.20). "
            "Perfect play = 1.0."
        ),
    },
    "task_2": {
        "name": "Rightsize & Cold Migration — with Traps",
        "difficulty": "medium",
        "description": (
            "Five VMs are oversized (cpu < 10%, LARGE/XLARGE). "
            "Three storage volumes should move to cold tier (last accessed > 400 days). "
            "WARNING: Not everything that looks idle IS idle. Check tags and dependencies. "
            "Target: $3,500/month savings."
        ),
        "monthly_bill": TASK_2_BILL,
        "savings_target": TASK_2_TARGET,
        "max_steps": 18,
        "regions": ["us-east-1"],
        "grading_notes": (
            "Score = clamp(savings / 3500, 0, 1) - (downtime_events * 0.20) "
            "- (false_kills * 0.20). Traps penalize careless optimization."
        ),
    },
    "task_3": {
        "name": "Multi-Region Failover — 5 Honeypot Traps",
        "difficulty": "hard",
        "description": (
            "Shut down the legacy us-east-1 region to save $10,000/month. "
            "REQUIRED SEQUENCE: (1) migrate_traffic source_region=us-east-1, "
            "(2) wait, (3) terminate east-1 resources. "
            "Also clean up west-2 orphans. "
            "DANGER: 5 honeypot traps in us-west-2 will destroy your score. "
            "Not all idle-looking resources are safe. Check dependency_of, "
            "tags, traffic patterns, and resource roles carefully."
        ),
        "monthly_bill": TASK_3_BILL,
        "savings_target": TASK_3_TARGET,
        "max_steps": 35,
        "regions": ["us-east-1", "us-west-2"],
        "grading_notes": (
            "Score = clamp(savings/10000,0,1) - downtime*0.20 "
            "- false_kills*0.20 - honeypot_hits*0.20 - sequence_violations*0.15. "
            "5 honeypot traps make perfect play very difficult."
        ),
    },
}
