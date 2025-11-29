"""
Engine interfaces for the Jensen agent core.

This package currently exposes abstract skeletons only:
- PlatformEngine
- WorkflowEngine

Concrete implementations and orchestrator wiring will be added
in later Phase E tasks.
"""

from .platform_engine import PlatformEngine
from .workflow_engine import WorkflowEngine

__all__ = ["PlatformEngine", "WorkflowEngine"]
