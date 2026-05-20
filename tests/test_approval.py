"""Tests for the ApprovalService run-state guard and approval endpoint."""

import pytest
from unittest.mock import MagicMock, patch

from src.agent import AgentRegistry
from src.agent.registry import AgentStatus
from src.approval.service import ApprovalService, ApprovalError


# ---------------------------------------------------------------------------
# Unit tests for ApprovalService.check_run_state
# ---------------------------------------------------------------------------

class TestCheckRunState:
    """Verify that the run-state guard fails closed for every invalid state."""

    def _make_agent(self, status: str) -> dict:
        return {
            "id": "test-agent-1",
            "name": "test-agent",
            "type": "worker",
            "status": status,
            "config": {},
            "created_at": 1000.0,
            "updated_at": 1000.0,
            "version": "1.0.0",
            "metrics": {"tasks_completed": 0, "errors": 0, "uptime": 0},
        }

    def test_agent_not_found_returns_404(self):
        """A non-existent agent must produce a 404 ApprovalError."""
        registry = AgentRegistry()
        service = ApprovalService(registry=registry)
        with pytest.raises(ApprovalError) as exc:
            service.check_run_state("nonexistent")
        assert exc.value.status_code == 404
        assert "not found" in exc.value.message.lower()

    def test_agent_with_no_status_returns_400(self):
        """An agent record missing the status field returns 400."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get.return_value = {"id": "a1", "name": "no-status"}
        service = ApprovalService(registry=registry)
        with pytest.raises(ApprovalError) as exc:
            service.check_run_state("a1")
        assert exc.value.status_code == 400
        assert "no status" in exc.value.message.lower()

    @pytest.mark.parametrize(
        "invalid_status",
        [
            AgentStatus.PENDING.value,    # "pending"
            AgentStatus.STOPPED.value,    # "stopped"
            AgentStatus.FAILED.value,     # "failed"
            AgentStatus.TERMINATED.value,  # "terminated"
        ],
    )
    def test_invalid_states_return_409(self, invalid_status):
        """Agents in stopped/failed/terminated/pending state must be rejected with 409."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get.return_value = self._make_agent(invalid_status)
        service = ApprovalService(registry=registry)
        with pytest.raises(ApprovalError) as exc:
            service.check_run_state("a1")
        assert exc.value.status_code == 409
        assert "cannot proceed" in exc.value.message.lower()

    @pytest.mark.parametrize(
        "valid_status",
        [
            AgentStatus.RUNNING.value,  # "running"
            AgentStatus.PAUSED.value,   # "paused"
        ],
    )
    def test_valid_states_pass(self, valid_status):
        """Agents in running or paused state must pass the guard."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get.return_value = self._make_agent(valid_status)
        service = ApprovalService(registry=registry)
        # Should not raise
        service.check_run_state("a1")


# ---------------------------------------------------------------------------
# Unit tests for ApprovalService.approve_step
# ---------------------------------------------------------------------------

class TestApproveStep:
    """Verify that approve_step calls check_run_state first and returns
    a proper result on success."""

    def test_approve_step_rejects_invalid_state(self):
        """If check_run_state raises, approve_step must propagate the error."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get.return_value = {
            "id": "a1", "name": "bad-agent", "status": "stopped",
        }
        service = ApprovalService(registry=registry)
        with pytest.raises(ApprovalError) as exc:
            service.approve_step("a1", "step-42")
        assert exc.value.status_code == 409

    def test_approve_step_succeeds_for_valid_state(self):
        """For an agent in RUNNING state, approve_step must return a result dict."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get.return_value = {
            "id": "a1",
            "name": "good-agent",
            "type": "worker",
            "status": AgentStatus.RUNNING.value,
            "config": {},
            "created_at": 1000.0,
            "updated_at": 1000.0,
            "version": "1.0.0",
            "metrics": {"tasks_completed": 0, "errors": 0, "uptime": 100},
        }
        service = ApprovalService(registry=registry)
        result = service.approve_step("a1", "step-42")
        assert result["agent_id"] == "a1"
        assert result["step_id"] == "step-42"
        assert result["status"] == "approved"

    def test_approve_step_not_found(self):
        """A missing agent must produce a 404 ApprovalError via check_run_state."""
        registry = AgentRegistry()
        service = ApprovalService(registry=registry)
        with pytest.raises(ApprovalError) as exc:
            service.approve_step("nonexistent", "step-1")
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Integration-style test with a real AgentRegistry
# ---------------------------------------------------------------------------

class TestApprovalServiceIntegration:
    """End-to-end tests using a real in-memory AgentRegistry."""

    def test_real_registry_running_agent_passes(self):
        """A registered agent moved to RUNNING must pass the guard."""
        registry = AgentRegistry()
        agent_id = registry.register("worker-1", "worker")
        registry.update_status(agent_id, AgentStatus.RUNNING)

        service = ApprovalService(registry=registry)
        service.check_run_state(agent_id)  # should not raise

    def test_real_registry_paused_agent_passes(self):
        """A registered agent moved to PAUSED must pass the guard."""
        registry = AgentRegistry()
        agent_id = registry.register("worker-1", "worker")
        registry.update_status(agent_id, AgentStatus.PAUSED)

        service = ApprovalService(registry=registry)
        service.check_run_state(agent_id)

    @pytest.mark.parametrize(
        "final_status",
        [AgentStatus.PENDING, AgentStatus.STOPPED, AgentStatus.FAILED, AgentStatus.TERMINATED],
    )
    def test_real_registry_invalid_state_rejected(self, final_status):
        """Agents in non-approvable states must be rejected."""
        registry = AgentRegistry()
        agent_id = registry.register("worker-1", "worker")
        registry.update_status(agent_id, final_status)

        service = ApprovalService(registry=registry)
        with pytest.raises(ApprovalError) as exc:
            service.check_run_state(agent_id)
        assert exc.value.status_code == 409

    def test_approve_step_with_real_registry(self):
        """Full approve_step flow with a real registry must succeed."""
        registry = AgentRegistry()
        agent_id = registry.register("worker-1", "worker")
        registry.update_status(agent_id, AgentStatus.RUNNING)

        service = ApprovalService(registry=registry)
        result = service.approve_step(agent_id, "step-42")
        assert result["agent_id"] == agent_id
        assert result["step_id"] == "step-42"
        assert result["status"] == "approved"
