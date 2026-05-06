import logging
from datetime import datetime
from typing import List
from .models import PullRequestNode, PRAnalysisResult, ReviewNode
from .config import settings

logger = logging.getLogger(__name__)

class PRAnalyzer:
    def __init__(self, template_patterns: List[str], strict_mode: bool = False):
        self.template_patterns = template_patterns
        self.strict_mode = strict_mode

    def check_template(self, body: str) -> bool:
        if not body:
            return False
        
        matches = [pattern.lower() in body.lower() for pattern in self.template_patterns]
        
        if self.strict_mode:
            return all(matches)
        return any(matches)

    def check_approval(self, pr: PullRequestNode) -> bool:
        reviews_data = pr.reviews.get("nodes", [])
        reviews = [ReviewNode(**r) for r in reviews_data]
        
        # Filter for approvals that happened BEFORE the merge time
        # GitHub API 'reviews' nodes are usually chronological, but we'll be explicit.
        valid_approvals = [
            r for r in reviews 
            if r.state == "APPROVED" and r.createdAt < pr.mergedAt
        ]
        
        return len(valid_approvals) > 0

    def check_tests(self, pr: PullRequestNode) -> bool:
        if not pr.files or "nodes" not in pr.files:
            return False
            
        for file_node in pr.files["nodes"]:
            if not file_node or "path" not in file_node:
                continue
            path = file_node["path"].lower()
            # Only consider files/directories that have 'test' in the name
            if "test" in path:
                return True
        return False

    def analyze(self, pr: PullRequestNode) -> PRAnalysisResult:
        template_used = self.check_template(pr.body)
        approved_before_merge = self.check_approval(pr)
        has_tests = self.check_tests(pr)
        
        # Calculate Turnaround Time (TAT) in hours
        tat_delta = pr.mergedAt - pr.createdAt
        tat_hours = tat_delta.total_seconds() / 3600.0
        
        # Calculate Time to 1st Review (TTR)
        reviews_data = pr.reviews.get("nodes", [])
        ttr_hours = None
        approved_by = None
        
        if reviews_data:
            # First review of any kind
            first_review_at = datetime.fromisoformat(reviews_data[0]["createdAt"].replace("Z", "+00:00"))
            ttr_delta = first_review_at - pr.createdAt
            ttr_hours = ttr_delta.total_seconds() / 3600.0
            
            # Find the first valid approver (before merge)
            for r_node in reviews_data:
                r_created = datetime.fromisoformat(r_node["createdAt"].replace("Z", "+00:00"))
                if r_node["state"] == "APPROVED" and r_created < pr.mergedAt:
                    approved_by = r_node.get("author", {}).get("login", "unknown")
                    break

        merger = pr.mergedBy.get("login", "unknown") if pr.mergedBy else "unknown"
        
        return PRAnalysisResult(
            repo=pr.repo_name,
            pr_number=pr.number,
            title=pr.title,
            author=pr.author_login,
            merged_at=pr.mergedAt,
            merged_by=merger,
            approved_by=approved_by,
            template_used=template_used,
            approved_before_merge=approved_before_merge,
            has_tests=has_tests,
            tat_hours=round(tat_hours, 2),
            ttr_hours=round(ttr_hours, 2) if ttr_hours is not None else None
        )
