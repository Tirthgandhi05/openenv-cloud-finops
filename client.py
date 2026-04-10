# client.py — Cloud FinOps Sandbox — Typed OpenEnv client
from __future__ import annotations

from openenv.core import EnvClient, StepResult

from models import FinOpsAction, FinOpsObservation, FinOpsState


class CloudFinOpsEnv(EnvClient[FinOpsAction, FinOpsObservation, FinOpsState]):

    def _step_payload(self, action: FinOpsAction) -> dict:
        return action.model_dump()

    def _parse_result(self, payload: dict) -> StepResult[FinOpsObservation]:
        obs = FinOpsObservation(**payload["observation"])
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> FinOpsState:
        return FinOpsState(**payload)
