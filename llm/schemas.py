from pydantic import BaseModel, Field
from typing import List, Literal

RiskLevel = Literal["Low", "Medium", "High"]

class TopicIdea(BaseModel):
    title: str = Field(..., min_length=5, max_length=120)
    problem_statement: str = Field(..., min_length=40, max_length=400)
    why_it_matters: str = Field(..., min_length=20, max_length=220)

    datasets: List[str] = Field(..., min_length=1, max_length=4)
    baseline: str = Field(..., min_length=10, max_length=120)
    improvement: str = Field(..., min_length=10, max_length=160)

    scope_fit: str = Field(..., min_length=20, max_length=220)  # why it fits time+degree
    risk: RiskLevel
    deliverables: List[str] = Field(..., min_length=2, max_length=5)

class TopicPickerOutput(BaseModel):
    ideas: List[TopicIdea] = Field(..., min_length=3, max_length=5)
    recommended_index: int = Field(..., ge=0, le=4)
    note: str = Field(..., min_length=10, max_length=220)