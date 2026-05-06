import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime, timedelta
from tabulate import tabulate
from dotenv import load_dotenv

# Add current directory to path to allow relative imports if run as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pr_probe.config import settings
from pr_probe.client import GitHubClient
from pr_probe.analyzer import PRAnalyzer
from pr_probe.exporter import export_json, calculate_metrics, export_xlsx, format_duration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pr_probe")

def parse_repo(repo_str: str) -> Optional[str]:
    """Extract owner/repo from a URL or full name."""
    repo_str = repo_str.strip().strip("[]'\"").rstrip("/")
    if not repo_str:
        return None
        
    if "github.com/" in repo_str:
        # Handle cases like https://github.com/org/repo
        return repo_str.split("github.com/")[-1]
    return repo_str

async def run(args):
    # Load token from env if not provided in settings
    token = os.getenv("GITHUB_TOKEN") or settings.github_token
    if not token:
        logger.error("GitHub token not found. Set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    client = GitHubClient(token)
    analyzer = PRAnalyzer(
        template_patterns=settings.template_patterns, 
        strict_mode=settings.strict_template_mode
    )

    try:
        org = args.org
        raw_repos = args.repos
        repos = []
        if raw_repos:
            # Split by comma first, then by space to handle all formats
            parts = []
            for p in raw_repos.split(","):
                parts.extend(p.split())
            
            parsed = [parse_repo(p) for p in parts]
            repos = [r for r in parsed if r] # Remove None values

        days = args.days or settings.default_days
        
        # Determine date range
        until_date_dt = datetime.now()
        if args.to_date:
            until_date_dt = datetime.strptime(args.to_date, "%d-%m-%Y")
            
        if args.from_date:
            since_date_dt = datetime.strptime(args.from_date, "%d-%m-%Y")
        else:
            since_date_dt = until_date_dt - timedelta(days=days)

        since_date_str = since_date_dt.strftime("%d-%m-%Y")
        until_date_str = until_date_dt.strftime("%d-%m-%Y")

        if not org and not repos:
            logger.error("Either --org or --repos must be provided.")
            sys.exit(1)

        date_msg = f"since {since_date_str} to {until_date_str}"
        if not args.from_date and not args.to_date:
             date_msg += f" (last {days} days)"
             
        logger.info(f"Analyzing PRs merged {date_msg}")
        
        # 1. Fetch PRs
        prs = await client.fetch_merged_prs(org, since_date_dt, until_date_dt, repos, use_cache=not args.no_cache)
        
        if not prs:
            print("\n" + "!"*40)
            print("NO PRs FOUND: No merged PRs found for the given criteria.")
            print("1. Check your organization name and repo list.")
            print("2. Try increasing --days (e.g., --days 14).")
            print("3. IMPORTANT: Ensure your GitHub Token is SAML SSO AUTHORIZED for the org.")
            print("!"*40 + "\n")
            return

        # 2. Analyze PRs
        results = [analyzer.analyze(pr) for pr in prs]
        
        # 3. Calculate metrics
        metrics = calculate_metrics(results)
        
        # 4. Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = "reports"
        session_dir = os.path.join(reports_dir, timestamp)
        
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
            
        if args.output == "json" or args.output == "both":
            json_file = os.path.join(session_dir, "pr_report.json")
            export_json(results, metrics, json_file)
            logger.info(f"Exported JSON to {json_file}")
            
        if args.output == "xlsx" or args.output == "both":
            xlsx_file = os.path.join(session_dir, "pr_report.xlsx")
            export_xlsx(results, metrics, xlsx_file)
            logger.info(f"Exported Excel report to {xlsx_file}")

        # 5. Print Summary
        header_text = f"REPORT SUMMARY: {org if org else 'Custom Repos'}"
        summary_data = [
            ["Total PRs Merged", metrics.total_prs],
            ["PRs Using Template", f"{metrics.template_usage_count} ({metrics.template_usage_percent:.1f}%)"],
            ["Approved Before Merge", f"{metrics.approved_before_merge_count} ({metrics.approval_percent:.1f}%)"],
            ["Avg Turnaround (TAT)", format_duration(metrics.avg_tat_hours)],
            ["Avg Time to 1st Review", format_duration(metrics.avg_ttr_hours)]
        ]
        print("\n" + "="*40)
        print(f"{header_text} (Last {days} days)")
        print("="*40)
        print(tabulate(summary_data, tablefmt="grid"))
        print("="*40 + "\n")

    finally:
        await client.close()

def main():
    parser = argparse.ArgumentParser(description="Analyze GitHub PRs for template usage and approvals.")
    parser.add_argument("--org", help="GitHub organization name")
    parser.add_argument("--repos", help="Comma-separated list of repos (short names, owner/repo, or URLs)")
    parser.add_argument("--days", type=int, help="Number of days to look back (default 7). Ignored if --from-date is used.")
    parser.add_argument("--from-date", help="Start date in DD-MM-YYYY format (e.g. 01-04-2026)")
    parser.add_argument("--to-date", help="End date in DD-MM-YYYY format (e.g. 15-04-2026). Defaults to current date if omitted.")
    parser.add_argument("--output", choices=["json", "xlsx", "both"], default="json", help="Output format")
    parser.add_argument("--no-cache", action="store_true", help="Disable local caching")
    
    args = parser.parse_args()
    
    # Load .env file
    load_dotenv()
    
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
