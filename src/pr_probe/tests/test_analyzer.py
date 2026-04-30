import unittest
import os

# Set dummy token for tests before importing analyzer
os.environ["GITHUB_TOKEN"] = "dummy_token"

from datetime import datetime, timedelta
from pr_probe.analyzer import PRAnalyzer
from pr_probe.models import PullRequestNode

class TestPRAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = PRAnalyzer(template_patterns=["## Description", "## Checklist"], strict_mode=False)
        self.merge_time = datetime(2024, 4, 30, 12, 0, 0)

    def create_mock_pr(self, body, reviews):
        return PullRequestNode(
            number=123,
            title="Test PR",
            author={"login": "testuser"},
            mergedAt=self.merge_time,
            body=body,
            repository={"name": "test-repo"},
            reviews={"nodes": reviews}
        )

    def test_template_detection_lenient(self):
        # One pattern matches
        pr = self.create_mock_pr("## Description\nSome content", [])
        self.assertTrue(self.analyzer.check_template(pr.body))
        
        # No pattern matches
        pr = self.create_mock_pr("Just some text", [])
        self.assertFalse(self.analyzer.check_template(pr.body))

    def test_template_detection_strict(self):
        analyzer_strict = PRAnalyzer(template_patterns=["## Description", "## Checklist"], strict_mode=True)
        
        # Only one matches (should fail)
        pr = self.create_mock_pr("## Description\nSome content", [])
        self.assertFalse(analyzer_strict.check_template(pr.body))
        
        # Both match (should pass)
        pr = self.create_mock_pr("## Description\n## Checklist", [])
        self.assertTrue(analyzer_strict.check_template(pr.body))

    def test_approval_before_merge(self):
        # Approved 1 hour before merge
        reviews = [
            {"state": "APPROVED", "createdAt": (self.merge_time - timedelta(hours=1)).isoformat()}
        ]
        pr = self.create_mock_pr("## Description", reviews)
        self.assertTrue(self.analyzer.check_approval(pr))

    def test_approval_after_merge(self):
        # Approved 1 hour AFTER merge
        reviews = [
            {"state": "APPROVED", "createdAt": (self.merge_time + timedelta(hours=1)).isoformat()}
        ]
        pr = self.create_mock_pr("## Description", reviews)
        self.assertFalse(self.analyzer.check_approval(pr))

    def test_dismissed_approval(self):
        # State is not APPROVED
        reviews = [
            {"state": "DISMISSED", "createdAt": (self.merge_time - timedelta(hours=1)).isoformat()}
        ]
        pr = self.create_mock_pr("## Description", reviews)
        self.assertFalse(self.analyzer.check_approval(pr))

if __name__ == "__main__":
    unittest.main()
