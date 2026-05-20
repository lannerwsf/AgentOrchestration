"""Approval Service — Shared run-state guard for human-in-the-loop approval."""

import logging
from typing import Optional

from src.agent import AgentRegistry
from src.agent.registry import AgentStatus
from src.agent.runtime import RuntimeState

logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    """Raised when an approval operation cannot proceed."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ApprovalService:
    """Shared service layer for approval endpoint logic.

    The run-state guard is applied *before* any lookup or mutation so that
    invalid requests fail closed with a deterministic 4xx response.
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()

    def check_run_state(self, agent_id: str) -> None:
        """Validate that the agent is in a state eligible for approval.

        Fails closed — raises ApprovalError with a 4xx status for any
        disallowed state instead of allowing the request to proceed to
        data access or mutation.

        Args:
            agent_id: The agent to validate.

        Raises:
            ApprovalError: If the agent does not exist or is in a state
                that cannot be approved.
        """
        agent = self.registry.get(agent_id)
        if not agent:
            raise ApprovalError(
                f"Agent '{agent_id}' not found",
                status_code=404,
            )

        status = agent.get("status")
        if status is None:
            raise ApprovalError(
                f"Agent '{agent_id}' has no status set",
                status_code=400,
            )

        # Agents must be in a running or paused state to receive approval.
        # A stopped, crashed, or starting agent cannot meaningfully
        # accept a human approval step.
        valid_states = {AgentStatus.RUNNING.value, AgentStatus.PAUSED.value}
        if status not in valid_states:
            raise ApprovalError(
                f"Agent '{agent_id}' is in state '{status}'. "
                f"Expected one of: {', '.join(sorted(valid_states))}. "
                f"Approval cannot proceed.",
                status_code=409,
            )

    def approve_step(self, agent_id: str, step_id: str) -> dict:
        """Record a human approval for a given agent workflow step.

        The run-state check is applied first; if it fails the method
        raises before touching any data.

        Args:
            agent_id: The agent whose step is being approved.
            step_id: The workflow step to approve.

        Returns:
            A result dict with the approval outcome.

        Raises:
            ApprovalError: If the agent state is invalid for approval.
        """
        self.check_run_state(agent_id)
        # After the guard passes, perform the actual approval mutation.
        logger.info("Approval recorded for agent %s step %s", agent_id, step_id)
        return {
            "agent_id": agent_id,
            "step_id": step_id,
            "status": "approved",
        }
