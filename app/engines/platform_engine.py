from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PlatformEngine(ABC):
    """
    Abstract interface for platform-level reasoning and planning.

    Responsibilities:
    - Describe platform and integration capabilities.
    - Decide whether a given platform task type can be handled.
    - Produce structured platform task plans (no execution).
    - Explain those plans in a human-readable way.

    Phase E NOTE:
    This is a skeleton only. It MUST NOT perform any I/O, DB operations,
    orchestration, or LLM calls.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the platform engine with optional configuration and logger.

        :param config: Arbitrary configuration values for this engine.
        :param logger: Optional logger; if not provided, a class-level logger
                       will be created.
        """
        self.config: Dict[str, Any] = config or {}
        self.logger: logging.Logger = logger or logging.getLogger(
            self.__class__.__name__
        )

    @abstractmethod
    def describe_capabilities(self) -> Dict[str, Any]:
        """
        Return a structured description of what this engine can handle.

        The dictionary should be machine-readable and include:
        - Supported platform task types.
        - Integration families and feature flags.
        - Relevant configuration knobs at the engine boundary.

        This method MUST NOT perform any side effects.
        """
        raise NotImplementedError("PlatformEngine.describe_capabilities() not implemented")

    @abstractmethod
    def can_handle_task(
        self,
        task_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Indicate whether this engine can handle the given platform task type.

        :param task_type: Logical task type identifier
                          (e.g. 'design_llm_gateway', 'setup_observability').
        :param metadata:  Optional additional context about the task.
        :return:          True if this engine should be considered for the task.
        """
        raise NotImplementedError("PlatformEngine.can_handle_task() not implemented")

    @abstractmethod
    def plan_task(
        self,
        task_type: str,
        input_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Produce a structured plan for the given platform task.

        Converts an abstract task description into a plan object that may include:
        - Proposed sub-steps.
        - Required integrations or components.
        - Expected outputs and intermediate artifacts.

        IMPORTANT:
        - The plan is descriptive only; no execution or I/O must occur here.
        """
        raise NotImplementedError("PlatformEngine.plan_task() not implemented")

    @abstractmethod
    def explain_plan(self, plan: Dict[str, Any]) -> str:
        """
        Convert a structured plan into a human-readable explanation.

        :param plan: The plan dictionary produced by `plan_task`.
        :return:     A string suitable for logging or Operator-facing UI.
        """
        raise NotImplementedError("PlatformEngine.explain_plan() not implemented")
