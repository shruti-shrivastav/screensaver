from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class QuestionStatus(str, Enum):
    ANALYZING = "analyzing"
    ANALYZED  = "analyzed"
    SOLVING   = "solving"
    SOLVED    = "solved"
    FAILED    = "failed"
    STOPPED   = "stopped"
    ERROR     = "error"


class SolutionStatus(str, Enum):
    PENDING  = "pending"
    SOLVING  = "solving"
    SOLVED   = "solved"
    FAILED   = "failed"
    STOPPED  = "stopped"
    NO_TESTS = "no_tests"
    ERROR    = "error"


class Example(BaseModel):
    input: str
    output: str
    explanation: str = ""


class TestCase(BaseModel):
    input: str
    output: str


class QuestionData(BaseModel):
    title: str
    description: str
    constraints: str = ""
    examples: list[Example] = Field(default_factory=list)
    test_cases: list[TestCase] = Field(default_factory=list)


class TestResult(BaseModel):
    input: str
    expected: str
    actual: str
    passed: bool


class Solution(BaseModel):
    status: SolutionStatus = SolutionStatus.PENDING
    code: str = ""
    explanation: str = ""
    iterations: int = 0
    test_results: list[TestResult] = Field(default_factory=list)
    model_used: str = ""


class Question(BaseModel):
    id: str
    session_id: str
    status: QuestionStatus = QuestionStatus.ANALYZING
    data: Optional[QuestionData] = None
    model_used: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
