from pydantic import BaseModel
from typing import Optional, Dict
from app.models.task_result import TaskStatusEnum


class UploadResponse(BaseModel):
    task_id: str


class TestResults(BaseModel):
    overall_coverage: float
    bugs: Dict[str, int]
    code_smells: Dict[str, int]
    vulnerabilities: Dict[str, int]


class ResultsResponse(BaseModel):
    status: TaskStatusEnum
    results: Optional[TestResults] = None
