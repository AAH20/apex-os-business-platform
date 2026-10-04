"""Saga state machine for APEX-OS Business Platform."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class SagaState(Enum):
    """Saga execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPENSATING = "compensating"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"
    PARTIALLY_COMPENSATED = "partially_compensated"
    TIMED_OUT = "timed_out"


class SagaStepState(Enum):
    """Individual step states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


# Valid state transitions for the saga itself
VALID_SAGA_TRANSITIONS: Dict[SagaState, Set[SagaState]] = {
    SagaState.PENDING: {SagaState.RUNNING, SagaState.FAILED},
    SagaState.RUNNING: {
        SagaState.COMPLETED,
        SagaState.FAILED,
        SagaState.COMPENSATING,
        SagaState.TIMED_OUT,
    },
    SagaState.COMPENSATING: {
        SagaState.COMPENSATED,
        SagaState.PARTIALLY_COMPENSATED,
        SagaState.FAILED,
    },
    SagaState.COMPLETED: set(),  # terminal
    SagaState.FAILED: set(),  # terminal
    SagaState.COMPENSATED: set(),  # terminal
    SagaState.PARTIALLY_COMPENSATED: set(),  # terminal
    SagaState.TIMED_OUT: {SagaState.COMPENSATING, SagaState.FAILED},
}

# Valid state transitions for individual steps
VALID_STEP_TRANSITIONS: Dict[SagaStepState, Set[SagaStepState]] = {
    SagaStepState.PENDING: {SagaStepState.RUNNING, SagaStepState.SKIPPED},
    SagaStepState.RUNNING: {
        SagaStepState.SUCCEEDED,
        SagaStepState.FAILED,
        SagaStepState.TIMED_OUT,
    },
    SagaStepState.SUCCEEDED: {SagaStepState.COMPENSATING},
    SagaStepState.FAILED: {SagaStepState.COMPENSATING, SagaStepState.SKIPPED},
    SagaStepState.COMPENSATING: {
        SagaStepState.COMPENSATED,
        SagaStepState.COMPENSATION_FAILED,
    },
    SagaStepState.COMPENSATED: set(),  # terminal
    SagaStepState.COMPENSATION_FAILED: set(),  # terminal
    SagaStepState.SKIPPED: set(),  # terminal
    SagaStepState.TIMED_OUT: {SagaStepState.COMPENSATING},
}


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: Enum
    to_state: Enum
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    reason: Optional[str] = None


class SagaStateMachine:
    """Manages state transitions for a saga and its steps."""

    def __init__(self) -> None:
        self._saga_state: SagaState = SagaState.PENDING
        self._step_states: Dict[str, SagaStepState] = {}
        self._transitions: List[StateTransition] = []
        self._lock = threading.RLock()

    @property
    def saga_state(self) -> SagaState:
        return self._saga_state

    @property
    def step_states(self) -> Dict[str, SagaStepState]:
        return dict(self._step_states)

    @property
    def transitions(self) -> List[StateTransition]:
        return list(self._transitions)

    def can_transition_saga(self, new_state: SagaState) -> bool:
        """Check if a saga state transition is valid."""
        return new_state in VALID_SAGA_TRANSITIONS.get(self._saga_state, set())

    def can_transition_step(self, step_name: str, new_state: SagaStepState) -> bool:
        """Check if a step state transition is valid."""
        current = self._step_states.get(step_name, SagaStepState.PENDING)
        return new_state in VALID_STEP_TRANSITIONS.get(current, set())

    def transition_saga(self, new_state: SagaState, reason: Optional[str] = None) -> bool:
        """Transition the saga to a new state. Returns True if successful."""
        with self._lock:
            if not self.can_transition_saga(new_state):
                return False
            old_state = self._saga_state
            self._saga_state = new_state
            self._transitions.append(
                StateTransition(old_state, new_state, reason=reason)
            )
            return True

    def transition_step(
        self, step_name: str, new_state: SagaStepState, reason: Optional[str] = None
    ) -> bool:
        """Transition a step to a new state. Returns True if successful."""
        with self._lock:
            if not self.can_transition_step(step_name, new_state):
                return False
            old_state = self._step_states.get(step_name, SagaStepState.PENDING)
            self._step_states[step_name] = new_state
            self._transitions.append(
                StateTransition(old_state, new_state, reason=reason)
            )
            return True

    def get_step_state(self, step_name: str) -> SagaStepState:
        """Get the current state of a step."""
        return self._step_states.get(step_name, SagaStepState.PENDING)

    def is_saga_terminal(self) -> bool:
        """Check if the saga is in a terminal state."""
        return self._saga_state in {
            SagaState.COMPLETED,
            SagaState.FAILED,
            SagaState.COMPENSATED,
            SagaState.PARTIALLY_COMPENSATED,
        }

    def is_step_terminal(self, step_name: str) -> bool:
        """Check if a step is in a terminal state."""
        state = self.get_step_state(step_name)
        return state in {
            SagaStepState.COMPENSATED,
            SagaStepState.COMPENSATION_FAILED,
            SagaStepState.SKIPPED,
        }

    def get_saga_history(self) -> List[Dict[str, Any]]:
        """Get the full transition history as serializable dicts."""
        return [
            {
                "from": t.from_state.value if isinstance(t.from_state, Enum) else t.from_state,
                "to": t.to_state.value if isinstance(t.to_state, Enum) else t.to_state,
                "timestamp": t.timestamp,
                "reason": t.reason,
            }
            for t in self._transitions
        ]
