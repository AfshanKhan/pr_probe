from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ReviewNode(BaseModel):
    state: str
    createdAt: datetime

class PullRequestNode(BaseModel):
    number: int
    title: str
    author: Optional[dict] = None
    createdAt: datetime
    mergedAt: datetime
    mergedBy: Optional[dict] = None
    body: str
    repository: dict
    files: Optional[dict] = None
    reviews: dict

    @property
    def author_login(self) -> str:
        return self.author["login"] if self.author else "ghost"

    @property
    def repo_name(self) -> str:
        owner = self.repository.get("owner", {}).get("login", "unknown")
        name = self.repository.get("name", "unknown")
        return f"{owner}/{name}"

class PRAnalysisResult(BaseModel):
    repo: str
    pr_number: int
    title: str
    author: str
    merged_at: datetime
    merged_by: str
    approved_by: Optional[str] = None
    template_used: bool
    approved_before_merge: bool
    has_tests: bool
    tat_hours: float
    ttr_hours: Optional[float] = None

class RepoMetrics(BaseModel):
    total_prs: int
    template_usage_count: int
    approved_before_merge_count: int
    has_tests_count: int
    avg_tat_hours: float
    avg_ttr_hours: Optional[float]

    @property
    def template_usage_percent(self) -> float:
        return (self.template_usage_count / self.total_prs * 100) if self.total_prs > 0 else 0.0
    
    @property
    def approval_percent(self) -> float:
        return (self.approved_before_merge_count / self.total_prs * 100) if self.total_prs > 0 else 0.0

    @property
    def has_tests_percent(self) -> float:
        return (self.has_tests_count / self.total_prs * 100) if self.total_prs > 0 else 0.0

class SummaryMetrics(BaseModel):
    total_prs: int
    template_usage_count: int
    approved_before_merge_count: int
    has_tests_count: int
    avg_tat_hours: float
    avg_ttr_hours: Optional[float]
    repo_metrics: Optional[dict] = None # Dict[str, RepoMetrics]
    
    @property
    def template_usage_percent(self) -> float:
        return (self.template_usage_count / self.total_prs * 100) if self.total_prs > 0 else 0.0
    
    @property
    def approval_percent(self) -> float:
        return (self.approved_before_merge_count / self.total_prs * 100) if self.total_prs > 0 else 0.0

    @property
    def has_tests_percent(self) -> float:
        return (self.has_tests_count / self.total_prs * 100) if self.total_prs > 0 else 0.0
