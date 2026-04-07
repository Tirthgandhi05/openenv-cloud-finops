"""
inference.py — Cloud FinOps Cost Optimization Sandbox
OpenEnv-compliant inference script.

LLM: Groq (llama-3.3-70b-versatile via OpenAI client)
Fallback: deterministic heuristic that still scores meaningfully.

Log format strictly follows the [START] / [STEP] / [END] spec:
    [START] task=<id> env=<benchmark> model=<model>
    [STEP]  step=<n> action=<json> reward=<float> done=<bool> error=<str|null>
    [END]   success=<bool> steps=<n> score=<float> rewards=<csv>

Score is fetched from POST /grader (the only true hackathon score).
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] openai package not installed. Run: pip install openai", file=sys.stderr)
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# Configuration  (all overridable via environment variables)
# ══════════════════════════════════════════════════════════════════════════════

# Required by hackathon spec — must use these exact variable names
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "llama-3.3-70b-versatile")
HF_TOKEN     = (
    os.environ.get("HF_TOKEN")
    or os.environ.get("GROQ_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or ""
)

# Environment server (local or HF Space URL)
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

# Episode config
TASKS: List[str]     = ["task_1", "task_2", "task_3"]
BENCHMARK: str       = "cloud-finops-env"
MAX_STEPS_PER_TASK   = {"task_1": 3, "task_2": 4, "task_3": 4}  # stay under env limits
SUCCESS_SCORE_THRESHOLD = 0.40

# Groq rate-limit safety: pause between LLM calls (seconds)
LLM_CALL_DELAY = 0.5

if not HF_TOKEN:
    print("[WARN] HF_TOKEN / GROQ_API_KEY not set — LLM calls will fail.", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════════════════
# Logging  (strict [START] / [STEP] / [END] format required by validator)
# ══════════════════════════════════════════════════════════════════════════════

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    err_str = error if error else "null"
    print(
        f"[STEP] step={step} action={action} "
        f"reward={reward:.4f} done={str(done).lower()} error={err_str}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.4f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.4f} rewards=[{rewards_str}]",
        flush=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Environment HTTP client
# ══════════════════════════════════════════════════════════════════════════════

class EnvClient:
    """Thin wrapper around the FastAPI environment server."""

    def __init__(self, base_url: str = ENV_BASE_URL) -> None:
        self._base = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def reset(self, task_id: str) -> Dict[str, Any]:
        r = self._session.post(
            f"{self._base}/reset",
            params={"task_id": task_id},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r = self._session.post(
            f"{self._base}/step",
            json=action,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def grader(self) -> Dict[str, Any]:
        r = self._session.post(f"{self._base}/grader", timeout=30)
        r.raise_for_status()
        return r.json()

    def tasks(self) -> List[Dict[str, Any]]:
        r = self._session.get(f"{self._base}/tasks", timeout=30)
        r.raise_for_status()
        return r.json()

    def health(self) -> bool:
        try:
            r = self._session.get(f"{self._base}/", timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def close(self) -> None:
        self._session.close()


# ══════════════════════════════════════════════════════════════════════════════
# JSON parser (handles markdown fences, leading text, etc.)
# ══════════════════════════════════════════════════════════════════════════════

def extract_json(text: str) -> Dict[str, Any]:
    """Extract the first valid JSON object from an LLM response string."""
    text = text.strip()
    # Strip markdown code fences
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
    text = "\n".join(lines).strip()
    # Find first { ... }
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(text[start:end])
    raise ValueError(f"No JSON object found in: {text[:200]!r}")


# ══════════════════════════════════════════════════════════════════════════════
# System prompt  (the single most important thing for score quality)
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
You are an expert Cloud FinOps engineer. Your job: cut cloud waste without causing downtime.
Return EXACTLY ONE JSON action object. No markdown. No explanation. Just the JSON.

═══ VALID ACTIONS ════════════════════════════════════════════════════════════════
{"action_type":"terminate","resource_id":"<id>"}
{"action_type":"resize","resource_id":"<id>","new_size":"nano|micro|small|medium|large"}
{"action_type":"migrate_storage","resource_id":"<id>","target_tier":"cold"}
{"action_type":"migrate_traffic","source_region":"us-east-1"}
{"action_type":"wait"}

═══ TASK STRATEGIES ══════════════════════════════════════════════════════════════

TASK 1 — Orphan Cleanup (EASY):
  Target: delete ONLY safe orphans. Safe = (attached_to IS NULL) AND (traffic_per_hour == 0).
  DO NOT touch resources with traffic > 0, cpu_avg_24h > 30, or queries_per_hour > 0.
  IDs to look for: ip_address with no traffic, storage volumes with attached_to=null,
  VMs with status "stopped".

TASK 2 — Rightsizing (MEDIUM):
  Target: save $6,000/month.
  RESIZE: VMs/DBs with cpu_avg_24h < 10 AND traffic_per_hour < 500. Resize to "small".
  MIGRATE_STORAGE: volumes with last_accessed_days_ago > 180. Migrate to "cold".
  DO NOT resize if cpu_avg_24h > 40 — that causes downtime penalty.
  DO NOT terminate anything — use resize and migrate_storage only.

TASK 3 — Multi-Region Shutdown (HARD):
  Target: save $15,000/month by shutting down us-east-1.
  MANDATORY SEQUENCE (violating it gives huge penalty):
    Step 1: {"action_type":"migrate_traffic","source_region":"us-east-1"}
    Step 2: {"action_type":"wait"}
    Step 3: Terminate us-east-1 resources ONE BY ONE.
  
  HONEYPOT WARNING — DO NOT terminate these, they look idle but run batch jobs at 02:00:
    - Any database in us-west-2 with cpu_avg_24h < 5 (batch analytics)
    - Any VM tagged env="dev" with traffic_per_hour > 1000 (dev tag lies)
    - Any volume with dependency_of set (even if attached_to=null)
  
  Also safe to terminate/resize in us-west-2:
    - Stopped VMs (status="stopped")
    - Unassigned IPs (attached_to=null, traffic=0)
    - Volumes with last_accessed_days_ago > 300 → migrate_storage cold
    - VMs with cpu_avg_24h < 8 AND no production traffic → resize to "small"

═══ SCORING RULES ════════════════════════════════════════════════════════════════
  GOOD: +reward for every dollar saved per month
  BAD:  -8000 for killing any production resource (downtime event)
  WORSE:-8000 for hitting a honeypot (batch job database killed)
  BAD:  -3000 for sequence violation (terminate before migrate_traffic+wait)

═══ CRITICAL RULES ═══════════════════════════════════════════════════════════════
  - Never terminate a resource with traffic_per_hour > 1000
  - Never terminate a resource with cpu_avg_24h > 50
  - Never terminate a resource with queries_per_hour > 5000
  - Never terminate a volume with dependency_of set (even if attached_to=null)
  - For Task 3: ALWAYS call migrate_traffic then wait BEFORE terminating east-1 prod
  - Return ONLY the JSON — no commentary, no markdown, no explanation
"""


# ══════════════════════════════════════════════════════════════════════════════
# Prompt builders
# ══════════════════════════════════════════════════════════════════════════════

def _summarize_resources(resources: List[Dict]) -> str:
    """
    Compact resource summary — keeps prompt within Groq token limits.
    Shows the most decision-relevant fields only.
    """
    lines = []
    for r in resources:
        rid     = r.get("id", "?")
        rtype   = r.get("resource_type", "?")
        status  = r.get("status", "?")
        region  = r.get("region", "?")
        cost    = r.get("monthly_cost", 0)
        cpu     = r.get("cpu_avg_24h")
        traffic = r.get("traffic_per_hour")
        queries = r.get("queries_per_hour")
        size    = r.get("instance_size")
        att     = r.get("attached_to")
        dep     = r.get("dependency_of")
        tags    = r.get("tags", {})
        last_acc = r.get("last_accessed_days_ago")
        stor_tier = r.get("storage_tier")

        parts = [f"[{rid}] {rtype}/{status} region={region} cost=${cost:.0f}/mo"]
        if cpu   is not None: parts.append(f"cpu={cpu:.1f}%")
        if traffic is not None: parts.append(f"traffic={traffic}/hr")
        if queries is not None: parts.append(f"queries={queries}/hr")
        if size:                parts.append(f"size={size}")
        if stor_tier:           parts.append(f"storage={stor_tier}")
        if last_acc is not None: parts.append(f"last_accessed={last_acc}d_ago")
        if att is not None:     parts.append(f"attached_to={att}")
        if dep:                 parts.append(f"dependency_of={dep}  *** DO NOT DELETE ***")
        if tags.get("env") == "dev" and (traffic or 0) > 500:
            parts.append("*** TAG LIES: dev-tagged but has live traffic ***")
        lines.append("  " + " | ".join(parts))
    return "\n".join(lines)


def build_first_prompt(obs: Dict, task_id: str) -> str:
    bill_start   = obs.get("monthly_bill_start", 0)
    bill_current = obs.get("monthly_bill_current", 0)
    saved        = obs.get("savings_achieved", 0)
    target       = obs.get("savings_target", 0)
    max_steps    = obs.get("max_steps", 30)
    regions      = obs.get("regions", [])
    resources    = obs.get("resources", [])

    return (
        f"=== TASK: {task_id.upper()} | Step 0/{max_steps} ===\n"
        f"Monthly bill: ${bill_current:,.0f} (started at ${bill_start:,.0f})\n"
        f"Savings achieved: ${saved:,.0f} / target ${target:,.0f}\n"
        f"Regions: {regions}\n"
        f"Resources ({len(resources)} visible):\n"
        f"{_summarize_resources(resources)}\n\n"
        f"Return your FIRST action as JSON only."
    )


def build_step_prompt(
    obs: Dict,
    task_id: str,
    step: int,
    last_feedback: str,
    last_reward: float,
) -> str:
    bill_current = obs.get("monthly_bill_current", 0)
    saved        = obs.get("savings_achieved", 0)
    target       = obs.get("savings_target", 0)
    max_steps    = obs.get("max_steps", 30)
    left         = max_steps - step
    downtime     = obs.get("downtime_events", 0)
    honeypots    = obs.get("honeypot_hits", 0)
    seq_viols    = obs.get("sequence_violations", 0)
    resources    = obs.get("resources", [])
    migrated_from = obs.get("traffic_migrated_from")
    drained       = obs.get("connections_drained", False)

    lines = [
        f"=== Step {step}/{max_steps} | {left} steps left ===",
        f"Bill: ${bill_current:,.0f} | Saved: ${saved:,.0f} / ${target:,.0f}",
        f"Penalties: downtime={downtime} honeypots={honeypots} seq_violations={seq_viols}",
        f"Last reward: {last_reward:+.1f} | Feedback: {last_feedback}",
    ]

    # Task 3 drain state — critical info
    if task_id == "task_3":
        if migrated_from:
            drain_status = "DRAINED — safe to terminate" if drained else "draining — call WAIT"
            lines.append(f"Traffic migrated from: {migrated_from} ({drain_status})")
        else:
            lines.append("*** TASK 3: Call migrate_traffic first before terminating east-1 ***")

    # Urgency
    if left <= 5:
        lines.append(f"!!! URGENT: only {left} steps left — act efficiently !!!")

    lines.append(f"Resources ({len(resources)} remaining):")
    lines.append(_summarize_resources(resources))
    lines.append("Return next action as JSON only.")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Deterministic fallback  (runs when LLM fails — scores meaningfully)
# ══════════════════════════════════════════════════════════════════════════════

def _task1_fallback(resources: List[Dict]) -> Optional[Dict]:
    """Delete orphans: null attachment + zero traffic."""
    for r in resources:
        rtype   = r.get("resource_type", "")
        status  = r.get("status", "")
        att     = r.get("attached_to")
        traffic = r.get("traffic_per_hour") or 0
        cpu     = r.get("cpu_avg_24h") or 0

        if rtype == "ip_address" and traffic == 0 and att is None:
            return {"action_type": "terminate", "resource_id": r["id"]}
        if rtype == "snapshot":
            return {"action_type": "terminate", "resource_id": r["id"]}
        if status == "stopped" and traffic == 0 and cpu == 0:
            return {"action_type": "terminate", "resource_id": r["id"]}
        if rtype == "storage" and att is None and traffic == 0 and not r.get("dependency_of"):
            last = r.get("last_accessed_days_ago") or 0
            if last > 60:
                return {"action_type": "terminate", "resource_id": r["id"]}
    return None


def _task2_fallback(resources: List[Dict]) -> Optional[Dict]:
    """Resize idle VMs; cold-migrate old storage."""
    # Cold migration first (no downtime risk)
    for r in resources:
        if r.get("resource_type") == "storage":
            last = r.get("last_accessed_days_ago") or 0
            tier = r.get("storage_tier", "")
            if tier == "hot" and last > 180:
                return {
                    "action_type": "migrate_storage",
                    "resource_id": r["id"],
                    "target_tier": "cold",
                }
    # Resize clearly idle VMs
    for r in resources:
        rtype   = r.get("resource_type", "")
        cpu     = r.get("cpu_avg_24h") or 0
        traffic = r.get("traffic_per_hour") or 0
        size    = r.get("instance_size", "")
        if rtype in ("vm", "database") and cpu < 10 and traffic < 500 and size in ("large", "xlarge"):
            return {
                "action_type": "resize",
                "resource_id": r["id"],
                "new_size": "small",
            }
    return None


def _task3_fallback(resources: List[Dict], obs: Dict) -> Optional[Dict]:
    """
    Task 3 sequence: migrate_traffic → wait → terminate east-1 waste + west-2 waste.
    Never touches honeypots (batch DBs, dev-tagged with traffic, dependency_of volumes).
    """
    migrated_from = obs.get("traffic_migrated_from")
    drained       = obs.get("connections_drained", False)

    # Step 1: migrate traffic if not done
    if not migrated_from:
        return {"action_type": "migrate_traffic", "source_region": "us-east-1"}

    # Step 2: wait for drain if not complete
    if migrated_from and not drained:
        return {"action_type": "wait"}

    # Step 3: terminate safe east-1 waste (orphans, stopped VMs)
    for r in resources:
        if r.get("region") != "us-east-1":
            continue
        rtype   = r.get("resource_type", "")
        status  = r.get("status", "")
        traffic = r.get("traffic_per_hour") or 0
        cpu     = r.get("cpu_avg_24h") or 0
        att     = r.get("attached_to")
        dep     = r.get("dependency_of")

        if dep:  # hidden dependency — never touch
            continue
        if status == "stopped" and traffic == 0 and cpu == 0:
            return {"action_type": "terminate", "resource_id": r["id"]}
        if rtype == "ip_address" and traffic == 0 and att is None:
            return {"action_type": "terminate", "resource_id": r["id"]}
        if rtype == "snapshot":
            return {"action_type": "terminate", "resource_id": r["id"]}
        # After drain, east-1 production is safe to terminate
        if r.get("region") == "us-east-1" and traffic < 2000 and cpu < 80:
            return {"action_type": "terminate", "resource_id": r["id"]}

    # Step 4: west-2 orphans and cold storage (safe regardless of sequence)
    for r in resources:
        if r.get("region") != "us-west-2":
            continue
        rtype   = r.get("resource_type", "")
        status  = r.get("status", "")
        traffic = r.get("traffic_per_hour") or 0
        cpu     = r.get("cpu_avg_24h") or 0
        att     = r.get("attached_to")
        dep     = r.get("dependency_of")
        last    = r.get("last_accessed_days_ago") or 0
        tags    = r.get("tags", {})

        if dep:
            continue
        # HONEYPOT CHECK: skip dev-tagged resources with real traffic
        if tags.get("env") == "dev" and traffic > 500:
            continue
        # HONEYPOT CHECK: skip west-2 DBs with suspiciously low cpu (batch jobs)
        if rtype == "database" and (cpu or 0) < 5:
            continue

        if status == "stopped" and traffic == 0:
            return {"action_type": "terminate", "resource_id": r["id"]}
        if rtype == "ip_address" and traffic == 0 and att is None:
            return {"action_type": "terminate", "resource_id": r["id"]}
        if rtype == "storage" and att is None and last > 300 and not dep:
            return {
                "action_type": "migrate_storage",
                "resource_id": r["id"],
                "target_tier": "cold",
            }
        if rtype == "storage" and last > 180 and not dep:
            return {
                "action_type": "migrate_storage",
                "resource_id": r["id"],
                "target_tier": "cold",
            }
        if rtype == "vm" and cpu < 8 and traffic < 300:
            return {
                "action_type": "resize",
                "resource_id": r["id"],
                "new_size": "small",
            }

    return None


def smart_fallback(obs: Dict, task_id: str) -> Dict:
    """Deterministic heuristic.  Never panics.  Always returns a valid action."""
    resources = obs.get("resources", [])

    action = None
    if task_id == "task_1":
        action = _task1_fallback(resources)
    elif task_id == "task_2":
        action = _task2_fallback(resources)
    elif task_id == "task_3":
        action = _task3_fallback(resources, obs)

    return action or {"action_type": "wait"}


# ══════════════════════════════════════════════════════════════════════════════
# Action validation / repair  (prevent 422 errors from the server)
# ══════════════════════════════════════════════════════════════════════════════

_VALID_SIZES  = {"nano", "micro", "small", "medium", "large", "xlarge"}
_VALID_TYPES  = {"terminate", "resize", "migrate_storage", "migrate_traffic", "wait"}
_SIZE_ORDER   = ["nano", "micro", "small", "medium", "large", "xlarge"]

def _resource_ids(obs: Dict) -> set:
    return {r["id"] for r in obs.get("resources", [])}

def _get_resource(obs: Dict, rid: str) -> Optional[Dict]:
    for r in obs.get("resources", []):
        if r["id"] == rid:
            return r
    return None


def validate_and_repair(action: Dict, obs: Dict, task_id: str) -> Optional[Dict]:
    """
    Return the action if it's valid, a repaired version if fixable,
    or None if it must be overridden by smart_fallback.
    """
    at = action.get("action_type", "")

    # Unknown action type
    if at not in _VALID_TYPES:
        return None

    # WAIT — always valid
    if at == "wait":
        return action

    # MIGRATE_TRAFFIC — needs source_region, no resource_id
    if at == "migrate_traffic":
        if not action.get("source_region"):
            action["source_region"] = "us-east-1"
        action.pop("resource_id", None)
        return action

    # All other actions need resource_id
    rid = action.get("resource_id")
    valid_ids = _resource_ids(obs)

    if not rid or rid not in valid_ids:
        return None   # can't repair — fallback

    resource = _get_resource(obs, rid)

    if at == "terminate":
        # Never terminate a resource with dependency_of set
        if resource and resource.get("dependency_of"):
            return None
        return action

    if at == "resize":
        new_size = action.get("new_size", "")
        if new_size not in _VALID_SIZES:
            action["new_size"] = "small"
        # Repair: if resize would be an upsize, switch to wait
        if resource:
            cur = resource.get("instance_size", "large")
            cur_idx = _SIZE_ORDER.index(cur) if cur in _SIZE_ORDER else 4
            new_idx = _SIZE_ORDER.index(action["new_size"])
            if new_idx >= cur_idx:
                return None   # can't upsize — fallback
        return action

    if at == "migrate_storage":
        action["target_tier"] = "cold"   # always cold
        return action

    return action


# ══════════════════════════════════════════════════════════════════════════════
# LLM call
# ══════════════════════════════════════════════════════════════════════════════

def call_llm(
    client: OpenAI,
    messages: List[Dict],
) -> Optional[str]:
    """Call Groq via OpenAI client.  Returns raw text or None on error."""
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.0,
            max_tokens=200,
            stream=False,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"  [LLM ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Episode runner
# ══════════════════════════════════════════════════════════════════════════════

def run_task(task_id: str, client: OpenAI, env: EnvClient) -> float:
    """
    Run one full episode for task_id.
    Returns the true grader score (0.0–1.0) from POST /grader.
    """
    max_steps = MAX_STEPS_PER_TASK.get(task_id, 30)
    rewards:  List[float] = []
    steps_taken = 0
    score = 0.0

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    # ── Reset ────────────────────────────────────────────────────────────────
    try:
        obs = env.reset(task_id)
    except Exception as e:
        print(f"  [ERROR] reset failed: {e}", file=sys.stderr)
        log_end(success=False, steps=0, score=0.0, rewards=[])
        return 0.0

    # ── Conversation history (multi-turn, capped to keep tokens low) ─────────
    messages: List[Dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": build_first_prompt(obs, task_id)},
    ]

    last_feedback = obs.get("feedback", "")
    last_reward   = 0.0
    done          = False

    for step in range(1, max_steps + 1):
        steps_taken = step

        # ── LLM call ─────────────────────────────────────────────────────────
        raw_text = call_llm(client, messages)
        time.sleep(LLM_CALL_DELAY)   # Groq rate limit safety

        # ── Parse LLM output ─────────────────────────────────────────────────
        llm_action: Optional[Dict] = None
        if raw_text:
            try:
                llm_action = extract_json(raw_text)
            except Exception:
                pass

        # ── Validate / repair / override ─────────────────────────────────────
        error_note: Optional[str] = None

        if llm_action is not None:
            repaired = validate_and_repair(llm_action, obs, task_id)
            if repaired is None:
                error_note = f"override:invalid_action={llm_action.get('action_type')}"
                action = smart_fallback(obs, task_id)
                print(f"  [OVERRIDE] step {step}: {llm_action} → fallback", file=sys.stderr)
            else:
                action = repaired
        else:
            error_note = "fallback:llm_parse_failed"
            action = smart_fallback(obs, task_id)
            print(f"  [FALLBACK] step {step}: LLM gave nothing useful", file=sys.stderr)

        # ── Step ─────────────────────────────────────────────────────────────
        try:
            result  = env.step(action)
            reward  = float(result.get("reward", 0.0))
            done    = bool(result.get("done", False))
            new_obs = result.get("observation", obs)
        except Exception as e:
            # Server rejected the action — fallback and retry next step
            error_note = f"server_error:{type(e).__name__}"
            reward  = 0.0
            done    = False
            new_obs = obs
            print(f"  [SERVER ERROR] step {step}: {e}", file=sys.stderr)

        rewards.append(reward)
        log_step(step=step, action=json.dumps(action), reward=reward, done=done, error=error_note)

        if done:
            break

        # ── Update conversation ───────────────────────────────────────────────
        # Add assistant turn (what it said) + new user turn (new state)
        if raw_text:
            messages.append({"role": "assistant", "content": raw_text})
        else:
            messages.append({"role": "assistant", "content": json.dumps(action)})

        last_feedback = new_obs.get("feedback", "")
        last_reward   = reward
        obs           = new_obs

        step_msg = build_step_prompt(obs, task_id, step, last_feedback, last_reward)
        messages.append({"role": "user", "content": step_msg})

        # Keep conversation window tight (Groq free tier is token-limited)
        # Keep system + first user + last 6 turns (12 messages max)
        if len(messages) > 14:
            messages = messages[:2] + messages[-12:]

    # ── Fetch true grader score ───────────────────────────────────────────────
    try:
        grade = env.grader()
        score = float(grade.get("score", 0.0))
        money_saved = grade.get("money_saved", 0.0)
        print(
            f"  [GRADE] task={task_id} score={score:.4f} "
            f"money_saved=${money_saved:,.0f} "
            f"message={grade.get('message', '')}",
            file=sys.stderr,
        )
    except Exception as e:
        # Fallback: estimate from cumulative reward (not ideal but safe)
        print(f"  [WARN] grader call failed: {e} — estimating score", file=sys.stderr)
        score = min(max(sum(rewards) / 50_000.0, 0.0), 1.0)

    score = min(max(score, 0.0), 1.0)
    success = score >= SUCCESS_SCORE_THRESHOLD
    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


# ══════════════════════════════════════════════════════════════════════════════
# Main entrypoint
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print(f"Cloud FinOps Sandbox — inference.py", flush=True)
    print(f"  ENV_BASE_URL : {ENV_BASE_URL}",     flush=True)
    print(f"  API_BASE_URL : {API_BASE_URL}",     flush=True)
    print(f"  MODEL_NAME   : {MODEL_NAME}",       flush=True)
    print(f"  HF_TOKEN     : {'set' if HF_TOKEN else 'MISSING'}", flush=True)
    print(flush=True)

    # ── Init clients ─────────────────────────────────────────────────────────
    llm_client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)
    env_client = EnvClient(ENV_BASE_URL)

    # ── Health check ─────────────────────────────────────────────────────────
    if not env_client.health():
        print(
            f"[ERROR] Environment server not reachable at {ENV_BASE_URL}. "
            f"Start it with: uvicorn server:app --host 0.0.0.0 --port 7860",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"Environment server: OK ({ENV_BASE_URL})", flush=True)

    # ── Run all tasks ─────────────────────────────────────────────────────────
    scores: Dict[str, float] = {}

    for task_id in TASKS:
        print(f"\n{'═'*60}", flush=True)
        print(f"  Running {task_id.upper()}", flush=True)
        print(f"{'═'*60}", flush=True)
        try:
            score = run_task(task_id, llm_client, env_client)
        except KeyboardInterrupt:
            print("\n[INTERRUPTED]", flush=True)
            break
        except Exception as e:
            print(f"[ERROR] {task_id} crashed: {e}", file=sys.stderr)
            score = 0.0
        scores[task_id] = score

    # ── Summary ──────────────────────────────────────────────────────────────
    env_client.close()

    print(f"\n{'═'*60}", flush=True)
    print("SCORE SUMMARY", flush=True)
    print(f"{'═'*60}", flush=True)

    total = 0.0
    for task_id, score in scores.items():
        status = "PASS" if score >= SUCCESS_SCORE_THRESHOLD else "FAIL"
        print(f"  {task_id:<12} {score:.4f}  [{status}]", flush=True)
        total += score

    if scores:
        mean = total / len(scores)
        print(f"  {'mean':<12} {mean:.4f}", flush=True)
        print(flush=True)

        # JSON blob for machine parsing (hackathon validator reads this)
        summary = {
            "model": MODEL_NAME,
            "scores": scores,
            "mean_score": round(mean, 4),
        }
        print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
