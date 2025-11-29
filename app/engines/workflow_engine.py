from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class WorkflowEngine(ABC):
    """
    Abstract interface for workflow-level reasoning and planning.

    Responsibilities:
    - Describe workflow / intent families supported by this engine.
    - Decide whether a given workflow intent can be handled.
    - Produce structured workflow blueprints (no execution).
    - Explain those blueprints in a human-readable way.

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
        Initialize the workflow engine with optional configuration and logger.

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
        Return a structured description of supported workflow capabilities.

        The dictionary should be machine-readable and include:
        - Supported workflow / intent families (e.g. 'email_assistant').
        - Expected input structures.
        - Expected output structures.

        This method MUST NOT perform any side effects.
        """
        raise NotImplementedError("WorkflowEngine.describe_capabilities() not implemented")

    @abstractmethod
    def can_handle_intent(
        self,
        intent_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Indicate whether this engine can handle the given workflow intent type.

        :param intent_type: Logical workflow intent identifier
                            (e.g. 'personal_email_v1', 'ncri_marketing_v1').
        :param metadata:    Optional additional context about the intent.
        :return:            True if this engine should be considered for the intent.
        """
        raise NotImplementedError("WorkflowEngine.can_handle_intent() not implemented")

    @abstractmethod
    def design_workflow(
        self,
        intent_type: str,
        intent_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Produce a structured workflow blueprint for the given intent.

        The blueprint dictionary may include:
        - A list of step definitions.
        - Dependencies between steps.
        - Expected inputs and outputs for each step.
        - Optional flags for human review or checkpoints.

        IMPORTANT:
        - The blueprint is descriptive only; no execution or I/O must occur here.
        """
        raise NotImplementedError("WorkflowEngine.design_workflow() not implemented")

    @abstractmethod
    def explain_workflow(self, workflow_blueprint: Dict[str, Any]) -> str:
        """
        Convert a workflow blueprint into a human-readable explanation.

        :param workflow_blueprint: The blueprint produced by `design_workflow`.
        :return:                   A string suitable for logging or Operator-facing UI.
        """
        raise NotImplementedError("WorkflowEngine.explain_workflow() not implemented")
