 ☁️ Cloud FinOps Cost Optimization

![Python](https://img.shields.io/badge/python-%233776AB.svg?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/fastapi-%23009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/pydantic-%23E92063.svg?style=for-the-badge&logo=pydantic&logoColor=white)
![Uvicorn](https://img.shields.io/badge/uvicorn-%23000000.svg?style=for-the-badge&logo=uvicorn&logoColor=white)

![Reinforcement Learning](https://img.shields.io/badge/Reinforcement%20Learning-Agent-blue?style=for-the-badge)
![OpenAI](https://img.shields.io/badge/LLM-Agents-black?style=for-the-badge&logo=openai&logoColor=white)

![REST API](https://img.shields.io/badge/API-REST-orange?style=for-the-badge)
![Simulation](https://img.shields.io/badge/Cloud-Simulation-green?style=for-the-badge)

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![OpenEnv](https://img.shields.io/badge/OpenEnv-Evaluation-purple?style=for-the-badge)

---

An **OpenEnv environment for training and evaluating AI agents on cloud infrastructure cost optimization**.

In this environment the agent acts as a **FinOps / SRE engineer** responsible for reducing a company's cloud bill without disrupting production systems.

The environment simulates realistic infrastructure issues such as:

- orphan resources  
- oversized machines  
- inefficient storage tiers  
- misleading metadata  
- hidden dependencies  

Instead of debugging incidents, the challenge here is **making safe optimization decisions under uncertainty**.

---

##  Why This Environment

Every cloud-based company struggles with **cloud cost management**.

Infrastructure grows quickly, resources are forgotten, and systems become overprovisioned. FinOps engineers typically review dashboards and manually decide what to remove, resize, or migrate.

This environment recreates that real-world decision loop:

- **Inspect Infrastructure** — Review resource metrics, cost data, and relationships between services  
- **Identify Waste** — Detect unused resources such as orphan volumes, idle IP addresses, and stopped machines  
- **Optimize Resources** — Resize oversized instances or move rarely accessed storage to cheaper tiers  
- **Avoid Risk** — Ensure that critical services and hidden dependencies are not accidentally removed  
- **Manage Infrastructure Changes** — Safely migrate traffic or consolidate regions during large-scale optimizations  

---

##  What Makes This Environment Interesting

Unlike simple cleanup scripts, this environment includes several **real-world complications**:

- Low CPU does **not always mean a resource is safe to remove**
- Some workloads run only during specific hours (for example nightly batch jobs)
- Resource tags can be **incorrect or misleading**
- Some services depend on resources that **appear unused**
- Infrastructure may span **multiple regions with live traffic**

Agents must reason carefully about the available signals before taking action.

---

##  Infrastructure Scenarios

| ID | Scenario Type | Cause | Optimization Pattern |
|----|---------------|------|----------------------|
| CF-001 | Orphan storage volume | VM deleted but volume left attached | Detect `attached_to: null` → terminate volume |
| CF-002 | Unused Elastic IP | IP reserved but not assigned | Identify `assigned_to: null` → release IP |
| CF-003 | Oversized compute instance | Low utilization workload | CPU < 10% → resize instance |
| CF-004 | Cold storage candidate | Old logs rarely accessed | `last_accessed > 365 days` → migrate to cold tier |
| CF-005 | Multi-region redundancy | Infrastructure duplicated across regions | migrate traffic → shutdown redundant region |
| CF-006 | Hidden dependency trap | Resource appears unused but supports other services | check `dependency_of` before deletion |

---

##  Tasks

| Task ID | Difficulty | Max Steps | What the Agent Does |
|--------|-----------|----------|--------------------|
| `orphan_cleanup` | Easy | 20 | Identify and remove unused infrastructure such as orphan volumes and idle IPs |
| `resource_rightsizing` | Medium | 30 | Optimize inefficient infrastructure by resizing oversized machines and migrating cold storage |
| `region_consolidation` | Hard | 60 | Safely migrate traffic between regions and shut down redundant infrastructure without causing downtime |

---
## ⚙️ Action Space

The agent interacts with the environment by performing **cloud infrastructure optimization actions**.  
Each action changes the infrastructure state and may affect **cost, reliability, and system stability**.

---

### Optimization actions (reduce infrastructure cost):

```json
{"action_type": "terminate", "parameters": {"resource_id": "vol-orphan-001"}}
{"action_type": "terminate", "parameters": {"resource_id": "ip-unused-002"}}
{"action_type": "resize", "parameters": {"resource_id": "vm-analytics-worker", "new_size": "small"}}
{"action_type": "resize", "parameters": {"resource_id": "vm-dev-tools", "new_size": "medium"}}
{"action_type": "migrate_storage", "parameters": {"resource_id": "vol-logs-2022", "target_tier": "cold"}}
```
### Infrastructure migration actions (large-scale optimization):
```json
{"action_type": "migrate_traffic", "parameters": {"resource_id": "lb-east-main", "target_region": "us-west-2"}}
{"action_type": "wait", "parameters": {}}
```
### Shutdown actions (complete region consolidation):
```json
{"action_type": "terminate", "parameters": {"resource_id": "vm-east-api-01"}}
{"action_type": "terminate", "parameters": {"resource_id": "db-east-main"}}
{"action_type": "terminate", "parameters": {"resource_id": "cache-east-redis"}}
```
## Observation Space

| Field | Type | Description |
|------|------|-------------|
| `task_id` | string | Active optimization task (e.g. `orphan_cleanup`, `resource_rightsizing`) |
| `step` | int | Current step number in the episode |
| `max_steps` | int | Maximum number of steps allowed |
| `monthly_bill_start` | float | Total cloud bill at the start of the episode |
| `monthly_bill_current` | float | Current infrastructure cost after actions |
| `savings_target` | float | Target cost reduction required for the task |
| `savings_achieved` | float | Total savings achieved so far |
| `uptime_percent` | float | Current system reliability percentage |
| `downtime_events` | int | Number of production outages caused by the agent |
| `honeypot_hits` | int | Times the agent triggered a trap resource |
| `sequence_violations` | int | Times the agent skipped required action order |
| `regions` | list[string] | Cloud regions currently active in the infrastructure |
| `traffic_migration_done` | bool | Indicates whether traffic migration has occurred |
| `connections_drained` | bool | Indicates whether connection draining has completed |
| `resources` | list[Resource] | List of all infrastructure resources visible to the agent |

## Reward Function

The environment provides rewards based on **cost optimization and infrastructure reliability**.

### Dense reward shaping during the episode

| Event | Reward |
|------|--------|
| Terminate orphan resource | +resource monthly cost |
| Resize oversized instance | +(old_cost − new_cost) |
| Migrate storage to cold tier | +0.8 × storage cost |
| Successful traffic migration | +50 |
| Safe region shutdown | +100 |
| Terminate active production resource | −10000 |
| Trigger downtime event | −5000 |
| Hit honeypot resource | −3000 |
| Invalid or redundant action | −10 |
| Exceed step limit | −50 |

---

### Final scoring (episode end)

| Task | Scoring Logic |
|------|---------------|
| `orphan_cleanup` | score = (orphans_removed / total_orphans) − (false_deletions × 0.3) |
| `resource_rightsizing` | score = (money_saved / savings_target) − (downtime_events × 0.2) |
| `region_consolidation` | score = (money_saved / savings_target) − (downtime_events × 0.25) − (honeypot_hits × 0.25) − (sequence_violations × 0.20) |

## Grader Scoring

Final scoring is computed deterministically using the `/grader` endpoint.

The grader evaluates the agent based on **cost savings, reliability, and safe infrastructure changes**.

| Task | Scoring Logic |
|-----|---------------|
| `orphan_cleanup` | 1.0 × (orphans_removed / total_orphans) − 0.3 × false_deletions |
| `resource_rightsizing` | (money_saved / savings_target) − 0.2 × downtime_events |
| `region_consolidation` | (money_saved / savings_target) − 0.25 × downtime_events − 0.25 × honeypot_hits − 0.20 × sequence_violations |

Scores are clamped to the range **[0.0 – 1.0]**.

## API Endpoints

| Method | Path | Description |
|------|------|-------------|
| GET | `/` | Environment status |
| GET | `/health` | Health check and version info |
| POST | `/reset?task_id=...` | Start a new episode for a given task |
| POST | `/step` | Submit an action (JSON body) |
| GET | `/state` | Retrieve the full current environment state |
| GET | `/tasks` | List all available tasks and action schemas |
| POST | `/grader` | Compute the final score for the current episode |
| POST | `/baseline` | Run the baseline agent across all tasks |
### Example Step Request

```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "terminate",
    "resource_id": "vol-orphan-001"
  }'
```
