"""
Schemas for workflow definitions in Jensen Core.

This is a minimal, future-proof format:
- WorkflowDefinition: id, name, description, steps, metadata
- WorkflowStep: id, type, inputs, outputs, metadata, tags
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class WorkflowStep(BaseModel):
    id: str
    type: str
    inputs: Dict[str, Any] = {}
    outputs: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep]
    metadata: Optional[Dict[str, Any]] = None
