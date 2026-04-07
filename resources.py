# resources.py
# Cloud FinOps Sandbox — OpenEnv submission
# NovaCart e-commerce platform — fake AWS infrastructure for all 3 tasks.
#
# Design principles:
#   1. Every number is intentional — costs, CPU%, traffic, last_accessed are
#      internally consistent with a real mid-size e-commerce company.
#   2. "Orphans" have clearly visible signals (attached_to=None, traffic=0).
#   3. "Honeypots" in Task 3 look idle on 24h averages but have hidden
#      peak_cpu_2am / peak_queries_2am fields the grader uses.
#   4. safe_to_terminate=False is NEVER exposed to the agent.
from __future__ import annotations

from models import (
    InstanceSize,
    Resource,
    ResourceStatus,
    ResourceType,
    StorageTier,
)


# ══════════════════════════════════════════════════════════════════════════════
# TASK 1 — Easy  (20 resources, 8 obvious orphans, no traps)
# Savings available: $705/mo.  Expected agent score: ~0.85
# ══════════════════════════════════════════════════════════════════════════════

TASK_1_RESOURCES: list[Resource] = [

    # ── Orphans (safe to delete — the answer key) ─────────────────────────────

    Resource(
        id="ip-unused-001", name="ip-unused-001",
        resource_type=ResourceType.IP_ADDRESS, region="us-east-1",
        monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={"env": "legacy", "team": "infra"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="ip-unused-002", name="ip-unused-002",
        resource_type=ResourceType.IP_ADDRESS, region="us-east-1",
        monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={"env": "legacy", "team": "infra"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-orphan-001", name="vol-orphan-001",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=55.00,
        size_gb=500, storage_tier=StorageTier.HOT,
        attached_to=None, last_accessed_days_ago=120,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-orphan-002", name="vol-orphan-002",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=22.00,
        size_gb=200, storage_tier=StorageTier.HOT,
        attached_to=None, last_accessed_days_ago=200,
        tags={"env": "dev"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-orphan-003", name="vol-orphan-003",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=110.00,
        size_gb=1000, storage_tier=StorageTier.HOT,
        attached_to=None, last_accessed_days_ago=90,
        tags={"env": "legacy", "team": "data"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-stopped-001", name="vm-stopped-001",
        resource_type=ResourceType.VM, region="us-east-1",
        status=ResourceStatus.STOPPED,
        monthly_cost=180.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.MEDIUM, base_cost_at_large=360.00,
        tags={"env": "staging", "team": "backend"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-stopped-002", name="vm-stopped-002",
        resource_type=ResourceType.VM, region="us-east-1",
        status=ResourceStatus.STOPPED,
        monthly_cost=210.00,
        cpu_avg_24h=0.0, ram_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.MEDIUM, base_cost_at_large=420.00,
        tags={"env": "staging", "team": "frontend"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="snapshot-old-001", name="snapshot-old-001",
        resource_type=ResourceType.SNAPSHOT, region="us-east-1",
        monthly_cost=38.00,
        last_accessed_days_ago=730,
        tags={"env": "legacy", "created": "2022-01"},
        safe_to_terminate=True, is_production=False,
    ),

    # ── Active production (DO NOT TOUCH) ─────────────────────────────────────

    Resource(
        id="vm-api-gateway", name="prod-api-gateway-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=620.00,
        cpu_avg_24h=71.3, ram_avg_24h=58.2, traffic_per_hour=45_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=620.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-payment-proc", name="prod-payment-processor-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=890.00,
        cpu_avg_24h=68.7, ram_avg_24h=62.1, traffic_per_hour=12_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=890.00,
        tags={"env": "production", "team": "payments", "pci": "true"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="db-postgres-main", name="prod-postgres-primary-east-1",
        resource_type=ResourceType.DATABASE, region="us-east-1",
        monthly_cost=1_840.00,
        cpu_avg_24h=74.2, ram_avg_24h=70.8,
        queries_per_hour=28_000, traffic_per_hour=28_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=1_840.00,
        tags={"env": "production", "team": "data", "backup": "true"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="db-redis-cache", name="prod-redis-cache-east-1",
        resource_type=ResourceType.DATABASE, region="us-east-1",
        monthly_cost=420.00,
        cpu_avg_24h=44.9, ram_avg_24h=81.3, traffic_per_hour=95_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=420.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-web-frontend-1", name="prod-web-frontend-east-1a",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=380.00,
        cpu_avg_24h=52.1, ram_avg_24h=41.7, traffic_per_hour=38_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=380.00,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-web-frontend-2", name="prod-web-frontend-east-1b",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=380.00,
        cpu_avg_24h=48.6, ram_avg_24h=39.4, traffic_per_hour=35_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=380.00,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="lb-main", name="prod-lb-main-east-1",
        resource_type=ResourceType.LOAD_BALANCER, region="us-east-1",
        monthly_cost=290.00,
        cpu_avg_24h=37.8, traffic_per_hour=80_000,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vol-db-primary", name="vol-db-primary-east-1",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=180.00,
        size_gb=2000, storage_tier=StorageTier.HOT,
        attached_to="db-postgres-main",
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-checkout-svc", name="prod-checkout-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=540.00,
        cpu_avg_24h=60.8, ram_avg_24h=55.3, traffic_per_hour=9_500,
        instance_size=InstanceSize.LARGE, base_cost_at_large=540.00,
        tags={"env": "production", "team": "commerce"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="cdn-assets", name="prod-cdn-assets-global",
        resource_type=ResourceType.CDN, region="us-east-1",
        monthly_cost=680.00,
        cpu_avg_24h=28.9, traffic_per_hour=120_000,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-auth-service", name="prod-auth-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=430.00,
        cpu_avg_24h=43.6, ram_avg_24h=37.9, traffic_per_hour=18_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=430.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vol-backups-active", name="vol-db-backups-east-1",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=95.00,
        size_gb=800, storage_tier=StorageTier.HOT,
        attached_to="db-postgres-main",
        last_accessed_days_ago=1,
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 — Medium  (30 resources, rightsize + cold-migrate)
# Savings target: $6,000/mo.  Max achievable: ~$4,600.  Expected score: ~0.60
# ══════════════════════════════════════════════════════════════════════════════

TASK_2_RESOURCES: list[Resource] = [

    # ── Clearly oversized VMs — resize from large/xlarge to small/micro ───────

    Resource(
        id="vm-analytics-worker-1", name="vm-analytics-worker-east-1a",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=847.00,
        cpu_avg_24h=4.2, ram_avg_24h=8.1, traffic_per_hour=120,
        instance_size=InstanceSize.LARGE, base_cost_at_large=847.00,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-analytics-worker-2", name="vm-analytics-worker-east-1b",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=847.00,
        cpu_avg_24h=3.8, ram_avg_24h=7.4, traffic_per_hour=95,
        instance_size=InstanceSize.LARGE, base_cost_at_large=847.00,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-ml-training", name="vm-ml-training-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=1_240.00,
        cpu_avg_24h=6.1, ram_avg_24h=11.2, traffic_per_hour=0,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=1_240.00,
        tags={"env": "ml", "team": "data-science"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-reporting-svc", name="vm-reporting-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=620.00,
        cpu_avg_24h=5.3, ram_avg_24h=9.0, traffic_per_hour=45,
        instance_size=InstanceSize.LARGE, base_cost_at_large=620.00,
        tags={"env": "internal", "team": "data"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-internal-tools", name="vm-internal-tools-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=620.00,
        cpu_avg_24h=7.2, ram_avg_24h=13.1, traffic_per_hour=180,
        instance_size=InstanceSize.LARGE, base_cost_at_large=620.00,
        tags={"env": "internal", "team": "ops"},
        safe_to_terminate=True, is_production=False,
    ),

    # ── Cold storage candidates ────────────────────────────────────────────────

    Resource(
        id="vol-logs-2023", name="vol-access-logs-2023",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=340.00,
        size_gb=3400, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=430,
        tags={"env": "archive", "team": "infra"},
        safe_to_terminate=False, is_production=False,
        # don't delete — cold-migrate only
    ),
    Resource(
        id="vol-logs-2022", name="vol-access-logs-2022",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=290.00,
        size_gb=2900, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=790,
        tags={"env": "archive", "team": "infra"},
        safe_to_terminate=False, is_production=False,
    ),
    Resource(
        id="vol-archive-q1-2023", name="vol-quarterly-archive-q1-2023",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=180.00,
        size_gb=1800, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=548,
        tags={"env": "archive", "team": "finance"},
        safe_to_terminate=False, is_production=False,
    ),
    Resource(
        id="vol-old-backups", name="vol-old-db-backups-2023",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=220.00,
        size_gb=2200, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=240,
        tags={"env": "backup", "team": "data"},
        safe_to_terminate=False, is_production=False,
    ),
    Resource(
        id="vol-media-archive", name="vol-product-image-archive-2022",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=410.00,
        size_gb=4100, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=335,
        tags={"env": "archive", "team": "content"},
        safe_to_terminate=False, is_production=False,
    ),

    # ── Borderline — low CPU but some real traffic (resize, don't delete) ─────

    Resource(
        id="vm-staging-env", name="vm-staging-environment-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=430.00,
        cpu_avg_24h=12.4, ram_avg_24h=21.7, traffic_per_hour=850,
        instance_size=InstanceSize.MEDIUM, base_cost_at_large=860.00,
        tags={"env": "staging", "team": "qa"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-dev-tools", name="vm-dev-tools-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=380.00,
        cpu_avg_24h=9.8, ram_avg_24h=18.2, traffic_per_hour=420,
        instance_size=InstanceSize.MEDIUM, base_cost_at_large=760.00,
        tags={"env": "dev", "team": "engineering"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-image-processor", name="vm-image-processor-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=540.00,
        cpu_avg_24h=18.2, ram_avg_24h=29.6, traffic_per_hour=2_200,
        instance_size=InstanceSize.LARGE, base_cost_at_large=540.00,
        tags={"env": "production", "team": "content"},
        safe_to_terminate=True, is_production=False,
    ),

    # ── Active production (DO NOT TOUCH) ─────────────────────────────────────

    Resource(
        id="t2-vm-api-gateway", name="prod-api-gateway-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=620.00,
        cpu_avg_24h=73.1, ram_avg_24h=61.4, traffic_per_hour=48_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=620.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vm-payment", name="prod-payment-processor-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=890.00,
        cpu_avg_24h=70.8, ram_avg_24h=64.3, traffic_per_hour=13_500,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=890.00,
        tags={"env": "production", "team": "payments"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-db-postgres-main", name="prod-postgres-primary-east-1",
        resource_type=ResourceType.DATABASE, region="us-east-1",
        monthly_cost=1_840.00,
        cpu_avg_24h=76.1, ram_avg_24h=72.4,
        queries_per_hour=31_000, traffic_per_hour=31_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=1_840.00,
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-db-redis", name="prod-redis-cache-east-1",
        resource_type=ResourceType.DATABASE, region="us-east-1",
        monthly_cost=420.00,
        cpu_avg_24h=47.9, ram_avg_24h=83.1, traffic_per_hour=98_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=420.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vm-frontend-1", name="prod-web-frontend-east-1a",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=380.00,
        cpu_avg_24h=54.9, ram_avg_24h=43.2, traffic_per_hour=41_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=380.00,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vm-frontend-2", name="prod-web-frontend-east-1b",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=380.00,
        cpu_avg_24h=50.7, ram_avg_24h=40.8, traffic_per_hour=38_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=380.00,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-lb-main", name="prod-lb-main-east-1",
        resource_type=ResourceType.LOAD_BALANCER, region="us-east-1",
        monthly_cost=290.00,
        cpu_avg_24h=40.6, traffic_per_hour=85_000,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vm-checkout", name="prod-checkout-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=540.00,
        cpu_avg_24h=63.8, ram_avg_24h=56.2, traffic_per_hour=10_200,
        instance_size=InstanceSize.LARGE, base_cost_at_large=540.00,
        tags={"env": "production", "team": "commerce"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-cdn-assets", name="prod-cdn-assets-global",
        resource_type=ResourceType.CDN, region="us-east-1",
        monthly_cost=680.00,
        cpu_avg_24h=31.2, traffic_per_hour=125_000,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vm-auth", name="prod-auth-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=430.00,
        cpu_avg_24h=45.9, ram_avg_24h=39.4, traffic_per_hour=19_500,
        instance_size=InstanceSize.LARGE, base_cost_at_large=430.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-db-postgres-replica", name="prod-postgres-replica-east-1",
        resource_type=ResourceType.DATABASE, region="us-east-1",
        monthly_cost=1_240.00,
        cpu_avg_24h=57.8, ram_avg_24h=61.1,
        queries_per_hour=15_000, traffic_per_hour=15_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=1_240.00,
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vm-recommendation", name="prod-recommendation-engine-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=780.00,
        cpu_avg_24h=62.4, ram_avg_24h=67.3, traffic_per_hour=22_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=780.00,
        tags={"env": "production", "team": "ml"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vol-db-primary", name="vol-db-primary-east-1",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=180.00,
        size_gb=2000, storage_tier=StorageTier.HOT,
        attached_to="t2-db-postgres-main",
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vol-db-replica", name="vol-db-replica-east-1",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=140.00,
        size_gb=2000, storage_tier=StorageTier.HOT,
        attached_to="t2-db-postgres-replica",
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vm-notification", name="prod-notification-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=380.00,
        cpu_avg_24h=38.6, ram_avg_24h=32.1, traffic_per_hour=5_500,
        instance_size=InstanceSize.LARGE, base_cost_at_large=380.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-lb-internal", name="prod-lb-internal-east-1",
        resource_type=ResourceType.LOAD_BALANCER, region="us-east-1",
        monthly_cost=190.00,
        cpu_avg_24h=27.9, traffic_per_hour=24_000,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="t2-vm-search", name="prod-search-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=620.00,
        cpu_avg_24h=66.8, ram_avg_24h=71.2, traffic_per_hour=17_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=620.00,
        tags={"env": "production", "team": "commerce"},
        safe_to_terminate=False, is_production=True,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 — Hard  (50 resources, 2 regions, honeypots, drain sequence)
# Savings target: $15,000/mo.  Safe savings: ~$8,400.
# Agent CANNOT hit target without touching borderline resources.
# Expected agent score: ~0.35
# ══════════════════════════════════════════════════════════════════════════════

TASK_3_RESOURCES: list[Resource] = [

    # ═══════════════════════════════════
    # us-east-1  (legacy, expensive)
    # ═══════════════════════════════════

    # ── Clear waste in us-east-1 (safe to terminate or cold-migrate) ─────────

    Resource(
        id="ip-east-unused-1", name="ip-east-unused-001",
        resource_type=ResourceType.IP_ADDRESS, region="us-east-1",
        monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="ip-east-unused-2", name="ip-east-unused-002",
        resource_type=ResourceType.IP_ADDRESS, region="us-east-1",
        monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-east-orphan-1", name="vol-east-orphan-001",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=180.00,
        size_gb=1800, storage_tier=StorageTier.HOT,
        attached_to=None, last_accessed_days_ago=210,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-east-orphan-2", name="vol-east-orphan-002",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=95.00,
        size_gb=950, storage_tier=StorageTier.HOT,
        attached_to=None, last_accessed_days_ago=300,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-east-stopped-1", name="vm-east-stopped-001",
        resource_type=ResourceType.VM, region="us-east-1",
        status=ResourceStatus.STOPPED,
        monthly_cost=380.00,
        cpu_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE, base_cost_at_large=380.00,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-east-stopped-2", name="vm-east-stopped-002",
        resource_type=ResourceType.VM, region="us-east-1",
        status=ResourceStatus.STOPPED,
        monthly_cost=430.00,
        cpu_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE, base_cost_at_large=430.00,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-east-old-worker", name="vm-east-old-analytics-worker",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=847.00,
        cpu_avg_24h=3.1, ram_avg_24h=5.8, traffic_per_hour=0,
        instance_size=InstanceSize.LARGE, base_cost_at_large=847.00,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-east-logs-2022", name="vol-east-access-logs-2022",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=340.00,
        size_gb=3400, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=850,
        tags={"env": "archive", "team": "infra"},
        safe_to_terminate=False, is_production=False,
    ),
    Resource(
        id="vol-east-logs-2023", name="vol-east-access-logs-2023",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=290.00,
        size_gb=2900, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=450,
        tags={"env": "archive", "team": "infra"},
        safe_to_terminate=False, is_production=False,
    ),
    Resource(
        id="vm-east-dev-1", name="vm-east-dev-tools-001",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=620.00,
        cpu_avg_24h=5.2, ram_avg_24h=9.7, traffic_per_hour=80,
        instance_size=InstanceSize.LARGE, base_cost_at_large=620.00,
        tags={"env": "dev", "team": "engineering"},
        safe_to_terminate=True, is_production=False,
    ),

    # ── Active production in us-east-1  (need migrate_traffic FIRST) ─────────

    Resource(
        id="vm-east-api", name="prod-api-gateway-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=620.00,
        cpu_avg_24h=69.4, ram_avg_24h=57.3, traffic_per_hour=38_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=620.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-east-payment", name="prod-payment-processor-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=890.00,
        cpu_avg_24h=71.8, ram_avg_24h=63.2, traffic_per_hour=11_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=890.00,
        tags={"env": "production", "team": "payments", "pci": "true"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="lb-east-main", name="prod-lb-main-east-1",
        resource_type=ResourceType.LOAD_BALANCER, region="us-east-1",
        monthly_cost=290.00,
        cpu_avg_24h=35.6, traffic_per_hour=70_000,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-east-checkout", name="prod-checkout-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=540.00,
        cpu_avg_24h=57.9, ram_avg_24h=51.8, traffic_per_hour=8_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=540.00,
        tags={"env": "production", "team": "commerce"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="db-east-postgres", name="prod-postgres-primary-east-1",
        resource_type=ResourceType.DATABASE, region="us-east-1",
        monthly_cost=1_840.00,
        cpu_avg_24h=70.7, ram_avg_24h=68.4,
        queries_per_hour=25_000, traffic_per_hour=25_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=1_840.00,
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-east-auth", name="prod-auth-service-east-1",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=430.00,
        cpu_avg_24h=41.8, ram_avg_24h=36.2, traffic_per_hour=16_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=430.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vol-east-db-primary", name="vol-db-primary-east-1",
        resource_type=ResourceType.STORAGE, region="us-east-1",
        monthly_cost=180.00,
        size_gb=2000, storage_tier=StorageTier.HOT,
        attached_to="db-east-postgres",
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-east-frontend-1", name="prod-web-frontend-east-1a",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=380.00,
        cpu_avg_24h=47.9, ram_avg_24h=38.6, traffic_per_hour=32_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=380.00,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-east-frontend-2", name="prod-web-frontend-east-1b",
        resource_type=ResourceType.VM, region="us-east-1",
        monthly_cost=380.00,
        cpu_avg_24h=50.7, ram_avg_24h=41.3, traffic_per_hour=35_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=380.00,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="cdn-east-assets", name="prod-cdn-assets-east-1",
        resource_type=ResourceType.CDN, region="us-east-1",
        monthly_cost=680.00,
        cpu_avg_24h=26.4, traffic_per_hour=95_000,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),

    # ═══════════════════════════════════
    # us-west-2  (newer, cheaper)
    # ═══════════════════════════════════

    # ── Clear waste in us-west-2 ──────────────────────────────────────────────

    Resource(
        id="ip-west-unused-1", name="ip-west-unused-001",
        resource_type=ResourceType.IP_ADDRESS, region="us-west-2",
        monthly_cost=45.00,
        traffic_per_hour=0, attached_to=None,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-west-orphan-1", name="vol-west-orphan-001",
        resource_type=ResourceType.STORAGE, region="us-west-2",
        monthly_cost=110.00,
        size_gb=1100, storage_tier=StorageTier.HOT,
        attached_to=None, last_accessed_days_ago=390,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-west-stopped-1", name="vm-west-stopped-001",
        resource_type=ResourceType.VM, region="us-west-2",
        status=ResourceStatus.STOPPED,
        monthly_cost=210.00,
        cpu_avg_24h=0.0, traffic_per_hour=0,
        instance_size=InstanceSize.MEDIUM, base_cost_at_large=420.00,
        tags={"env": "legacy"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-west-logs-2023", name="vol-west-access-logs-2023",
        resource_type=ResourceType.STORAGE, region="us-west-2",
        monthly_cost=220.00,
        size_gb=2200, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=390,
        tags={"env": "archive", "team": "infra"},
        safe_to_terminate=False, is_production=False,
    ),

    # ── Active production in us-west-2 (primary serving region — do not touch) ─

    Resource(
        id="vm-west-api", name="prod-api-gateway-west-2",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=590.00,
        cpu_avg_24h=73.9, ram_avg_24h=60.2, traffic_per_hour=42_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=590.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-payment", name="prod-payment-processor-west-2",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=840.00,
        cpu_avg_24h=67.8, ram_avg_24h=61.4, traffic_per_hour=12_500,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=840.00,
        tags={"env": "production", "team": "payments", "pci": "true"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="lb-west-main", name="prod-lb-main-west-2",
        resource_type=ResourceType.LOAD_BALANCER, region="us-west-2",
        monthly_cost=270.00,
        cpu_avg_24h=33.2, traffic_per_hour=78_000,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-checkout", name="prod-checkout-service-west-2",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=510.00,
        cpu_avg_24h=61.4, ram_avg_24h=53.7, traffic_per_hour=9_200,
        instance_size=InstanceSize.LARGE, base_cost_at_large=510.00,
        tags={"env": "production", "team": "commerce"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-frontend-1", name="prod-web-frontend-west-2a",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=360.00,
        cpu_avg_24h=53.7, ram_avg_24h=44.1, traffic_per_hour=37_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=360.00,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-frontend-2", name="prod-web-frontend-west-2b",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=360.00,
        cpu_avg_24h=48.9, ram_avg_24h=40.6, traffic_per_hour=33_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=360.00,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-auth", name="prod-auth-service-west-2",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=410.00,
        cpu_avg_24h=43.8, ram_avg_24h=37.4, traffic_per_hour=17_500,
        instance_size=InstanceSize.LARGE, base_cost_at_large=410.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="cdn-west-assets", name="prod-cdn-assets-west-2",
        resource_type=ResourceType.CDN, region="us-west-2",
        monthly_cost=640.00,
        cpu_avg_24h=29.1, traffic_per_hour=110_000,
        tags={"env": "production", "team": "frontend"},
        safe_to_terminate=False, is_production=True,
    ),

    # ── HONEYPOT TRAPS (the soul of Task 3) ───────────────────────────────────
    #
    # Trap 1 — Midnight batch jobs.
    #   24h average looks completely idle.
    #   peak_queries_2am / peak_cpu_2am are HIDDEN from agent.
    #   Destroying these kills the nightly ML pipeline.
    #
    Resource(
        id="db-west-analytics-1", name="db-west-analytics-warehouse-001",
        resource_type=ResourceType.DATABASE, region="us-west-2",
        monthly_cost=4_200.00,
        cpu_avg_24h=2.3, ram_avg_24h=6.1,
        queries_per_hour=180, traffic_per_hour=180,
        # HIDDEN:
        peak_queries_2am=1_500_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=4_200.00,
        tags={"env": "analytics", "team": "data-science"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="db-west-analytics-2", name="db-west-analytics-warehouse-002",
        resource_type=ResourceType.DATABASE, region="us-west-2",
        monthly_cost=3_800.00,
        cpu_avg_24h=1.8, ram_avg_24h=4.9,
        queries_per_hour=95, traffic_per_hour=95,
        # HIDDEN:
        peak_queries_2am=980_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=3_800.00,
        tags={"env": "analytics", "team": "data-science"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-batch-processor", name="vm-west-nightly-batch-processor",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=1_240.00,
        cpu_avg_24h=3.1, ram_avg_24h=7.2, traffic_per_hour=45,
        # HIDDEN:
        peak_cpu_2am=94.2,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=1_240.00,
        tags={"env": "batch", "team": "data-engineering"},
        safe_to_terminate=False, is_production=True,
    ),

    # Trap 2 — Tags that lie ("dev" but serving real mobile traffic).
    Resource(
        id="vm-west-dev-api", name="vm-west-dev-mobile-api",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=430.00,
        cpu_avg_24h=31.4, ram_avg_24h=27.8, traffic_per_hour=8_400,
        instance_size=InstanceSize.MEDIUM, base_cost_at_large=860.00,
        tags={"env": "dev", "team": "backend"},   # tag lies — this is production mobile API
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="db-west-dev-replica", name="db-west-dev-analytics-replica",
        resource_type=ResourceType.DATABASE, region="us-west-2",
        monthly_cost=840.00,
        cpu_avg_24h=22.1, ram_avg_24h=31.6,
        queries_per_hour=847, traffic_per_hour=847,  # 847 active connections
        instance_size=InstanceSize.LARGE, base_cost_at_large=840.00,
        tags={"env": "dev", "team": "data"},   # tag lies — analytics dashboard uses this
        safe_to_terminate=False, is_production=True,
    ),

    # Trap 3 — Hidden dependency.  attached_to=None looks orphaned.
    #          dependency_of is VISIBLE — a careful agent will notice it.
    Resource(
        id="vol-west-media-archive", name="vol-west-product-media-archive",
        resource_type=ResourceType.STORAGE, region="us-west-2",
        monthly_cost=680.00,
        size_gb=6800, storage_tier=StorageTier.HOT,
        attached_to=None,                          # looks orphaned!
        last_accessed_days_ago=3,                  # but accessed 3 days ago
        dependency_of=["vm-west-payment", "vm-west-checkout"],  # VISIBLE clue
        tags={"env": "production", "team": "content"},
        safe_to_terminate=False, is_production=True,
    ),

    # ── More active production in us-west-2 ──────────────────────────────────

    Resource(
        id="db-west-postgres-main", name="prod-postgres-primary-west-2",
        resource_type=ResourceType.DATABASE, region="us-west-2",
        monthly_cost=1_840.00,
        cpu_avg_24h=78.2, ram_avg_24h=74.1,
        queries_per_hour=33_000, traffic_per_hour=33_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=1_840.00,
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="db-west-redis-cache", name="prod-redis-cache-west-2",
        resource_type=ResourceType.DATABASE, region="us-west-2",
        monthly_cost=420.00,
        cpu_avg_24h=50.9, ram_avg_24h=84.2, traffic_per_hour=102_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=420.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-search", name="prod-search-service-west-2",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=590.00,
        cpu_avg_24h=63.7, ram_avg_24h=68.9, traffic_per_hour=18_000,
        instance_size=InstanceSize.LARGE, base_cost_at_large=590.00,
        tags={"env": "production", "team": "commerce"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-notification", name="prod-notification-service-west-2",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=360.00,
        cpu_avg_24h=35.9, ram_avg_24h=29.4, traffic_per_hour=6_200,
        instance_size=InstanceSize.LARGE, base_cost_at_large=360.00,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vol-west-db-primary", name="vol-db-primary-west-2",
        resource_type=ResourceType.STORAGE, region="us-west-2",
        monthly_cost=180.00,
        size_gb=2000, storage_tier=StorageTier.HOT,
        attached_to="db-west-postgres-main",
        tags={"env": "production", "team": "data"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="lb-west-internal", name="prod-lb-internal-west-2",
        resource_type=ResourceType.LOAD_BALANCER, region="us-west-2",
        monthly_cost=180.00,
        cpu_avg_24h=24.7, traffic_per_hour=28_000,
        tags={"env": "production", "team": "platform"},
        safe_to_terminate=False, is_production=True,
    ),
    Resource(
        id="vm-west-recommendation", name="prod-recommendation-engine-west-2",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=740.00,
        cpu_avg_24h=66.8, ram_avg_24h=70.4, traffic_per_hour=24_000,
        instance_size=InstanceSize.XLARGE, base_cost_at_large=740.00,
        tags={"env": "production", "team": "ml"},
        safe_to_terminate=False, is_production=True,
    ),

    # ── More clear waste in us-west-2 (oversized + cold candidates) ──────────

    Resource(
        id="vm-west-analytics-idle", name="vm-west-analytics-idle-worker",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=847.00,
        cpu_avg_24h=4.8, ram_avg_24h=8.9, traffic_per_hour=65,
        instance_size=InstanceSize.LARGE, base_cost_at_large=847.00,
        tags={"env": "analytics", "team": "data"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vm-west-reporting", name="vm-west-reporting-service",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=620.00,
        cpu_avg_24h=6.2, ram_avg_24h=10.4, traffic_per_hour=40,
        instance_size=InstanceSize.LARGE, base_cost_at_large=620.00,
        tags={"env": "internal", "team": "data"},
        safe_to_terminate=True, is_production=False,
    ),
    Resource(
        id="vol-west-old-backups", name="vol-west-old-db-backups",
        resource_type=ResourceType.STORAGE, region="us-west-2",
        monthly_cost=310.00,
        size_gb=3100, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=270,
        tags={"env": "backup", "team": "data"},
        safe_to_terminate=False, is_production=False,
    ),
    Resource(
        id="vol-west-archive-2022", name="vol-west-archive-2022",
        resource_type=ResourceType.STORAGE, region="us-west-2",
        monthly_cost=260.00,
        size_gb=2600, storage_tier=StorageTier.HOT,
        last_accessed_days_ago=670,
        tags={"env": "archive", "team": "infra"},
        safe_to_terminate=False, is_production=False,
    ),
    Resource(
        id="vm-west-internal-tools", name="vm-west-internal-tools",
        resource_type=ResourceType.VM, region="us-west-2",
        monthly_cost=430.00,
        cpu_avg_24h=8.1, ram_avg_24h=14.3, traffic_per_hour=220,
        instance_size=InstanceSize.MEDIUM, base_cost_at_large=860.00,
        tags={"env": "internal", "team": "ops"},
        safe_to_terminate=True, is_production=False,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# Registry — consumed by environment.py and server.py
# ══════════════════════════════════════════════════════════════════════════════

TASKS: dict[str, list[Resource]] = {
    "task_1": TASK_1_RESOURCES,
    "task_2": TASK_2_RESOURCES,
    "task_3": TASK_3_RESOURCES,
}

TASK_META: dict[str, dict] = {
    "task_1": {
        "name": "Orphan Cleanup",
        "difficulty": "easy",
        "description": (
            "NovaCart is paying for 8 completely orphaned resources — unattached "
            "IPs, detached volumes, and stopped VMs. Identify and terminate all "
            "orphans without touching any production infrastructure."
        ),
        "savings_target": 705.00,
        "max_steps": 30,
        "regions": ["us-east-1"],
        "grading_notes": (
            "Score = (orphans_found / 8) - (false_kills × 0.20) - (downtime_events × 0.20). "
            "A perfect run deletes all 8 orphans, touches nothing else, scores 1.0."
        ),
    },
    "task_2": {
        "name": "Rightsizing & Cold Migration",
        "difficulty": "medium",
        "description": (
            "NovaCart is running massively oversized VMs and keeping 18+ months of logs "
            "in hot storage. Downsize underutilized instances and migrate stale volumes "
            "to cold storage. Target: $6,000/month savings."
        ),
        "savings_target": 6_000.00,
        "max_steps": 40,
        "regions": ["us-east-1"],
        "grading_notes": (
            "Score = (savings / $6,000) - penalties. "
            "Max achievable savings ≈ $4,600 — agent cannot reach 1.0 without "
            "touching borderline resources. Penalized for downsizing high-CPU machines."
        ),
    },
    "task_3": {
        "name": "Multi-Region Failover & Shutdown",
        "difficulty": "hard",
        "description": (
            "NovaCart runs duplicate infrastructure in us-east-1 (legacy, expensive) and "
            "us-west-2 (primary). The CFO mandates $15,000/month in cuts. "
            "To safely shut down us-east-1: (1) call migrate_traffic(source='us-east-1'), "
            "(2) call wait() to drain connections, (3) then terminate. "
            "Beware: three 'honeypot' resources look idle on 24h averages but run "
            "critical batch jobs at 02:00. Read all fields carefully."
        ),
        "savings_target": 15_000.00,
        "max_steps": 60,
        "regions": ["us-east-1", "us-west-2"],
        "grading_notes": (
            "Score = (savings / $15,000) - (downtime × 0.20) - (honeypot_hits × 0.25) "
            "- (sequence_violations × 0.15). "
            "Safe savings ≈ $8,400 → max score without traps ≈ 0.56. "
            "Hitting all 3 honeypots reduces score to near 0."
        ),
    },
}
