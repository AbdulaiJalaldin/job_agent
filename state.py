from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class UserIdentityState(BaseModel):
    profile: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    proof_stack: List[Any] = Field(default_factory=list)
    goals: str = ""
    learning_history: Optional[str] = None
    current_task: Optional[str] = None
    task_queue: List[str] = Field(default_factory=list)

