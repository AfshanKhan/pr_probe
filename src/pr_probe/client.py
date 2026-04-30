import asyncio
import httpx
import logging
import json
import os
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from .models import PullRequestNode
from .config import settings

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"

class GitHubClient:
    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)
        self.cache_dir = settings.cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_cache_path(self, query_str: str) -> str:
        query_hash = hashlib.md5(query_str.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"cache_{query_hash}.json")

    async def close(self):
        await self.client.aclose()

    async def query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.client.post(GRAPHQL_URL, json={"query": query, "variables": variables})
        
        if response.status_code == 403 and "rate limit" in response.text.lower():
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
            wait_time = max(reset_time - datetime.now().timestamp(), 60)
            logger.warning(f"Rate limit reached. Waiting for {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            return await self.query(query, variables)
            
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            raise Exception(f"GraphQL error: {data['errors'][0]['message']}")
            
        return data["data"]

    async def fetch_merged_prs(self, org: Optional[str], days: int, repos: Optional[List[str]] = None, use_cache: bool = True) -> List[PullRequestNode]:
        since_date_dt = datetime.now() - timedelta(days=days)
        since_date_str = since_date_dt.strftime("%Y-%m-%d")
        
        if not repos and org:
            # Org-wide search is still needed for entire organizations
            query_str = f"org:{org} is:pr is:merged merged:>={since_date_str}"
            return await self._fetch_via_search(query_str, use_cache)
        
        # For specific repos, direct querying is much more reliable than search
        all_prs = []
        for repo_full_name in (repos or []):
            if "/" not in repo_full_name:
                continue
            
            owner, name = repo_full_name.split("/", 1)
            logger.info(f"Directly probing repository: {owner}/{name}")
            
            repo_prs = await self._fetch_repo_directly(owner, name, since_date_dt)
            all_prs.extend(repo_prs)
            
        return all_prs

    async def _fetch_repo_directly(self, owner: str, name: str, since_date: datetime) -> List[PullRequestNode]:
        graphql_query = """
        query($owner: String!, $name: String!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            pullRequests(states: [MERGED], orderBy: {field: UPDATED_AT, direction: DESC}, first: 50, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                number
                title
                author { login }
                createdAt
                mergedAt
                mergedBy { login }
                body
                repository { 
                  name 
                  owner { login }
                }
                reviews(first: 100) {
                  nodes {
                    state
                    createdAt
                    author { login }
                  }
                }
              }
            }
          }
        }
        """
        
        repo_prs = []
        cursor = None
        has_next_page = True
        
        while has_next_page:
            variables = {"owner": owner, "name": name, "cursor": cursor}
            try:
                data = await self.query(graphql_query, variables)
            except Exception as e:
                logger.error(f"Error fetching repo {owner}/{name}: {e}")
                break
                
            repo_data = data.get("repository")
            if not repo_data:
                logger.warning(f"Repository {owner}/{name} not found or inaccessible.")
                break
                
            pr_data = repo_data["pullRequests"]
            for node in pr_data["nodes"]:
                if not node: continue
                merged_at = datetime.fromisoformat(node["mergedAt"].replace("Z", "+00:00"))
                
                # Since we fetch DESC, if we hit a PR older than our window, we can stop
                if merged_at < since_date.replace(tzinfo=merged_at.tzinfo):
                    has_next_page = False
                    break
                
                repo_prs.append(PullRequestNode(**node))
            
            if not has_next_page:
                break
                
            page_info = pr_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            cursor = page_info["endCursor"]
            
        return repo_prs

    async def _fetch_via_search(self, query_str: str, use_cache: bool) -> List[PullRequestNode]:
        cache_path = self._get_cache_path(query_str)
        if use_cache and os.path.exists(cache_path):
            logger.info("Loading PRs from cache...")
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)
                return [PullRequestNode(**node) for node in cached_data]

        graphql_query = """
        query($query: String!, $cursor: String) {
          search(query: $query, type: ISSUE, first: 100, after: $cursor) {
            issueCount
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              ... on PullRequest {
                number
                title
                author { login }
                createdAt
                mergedAt
                mergedBy { login }
                body
                repository { 
                  name 
                  owner { login }
                }
                reviews(first: 100) {
                  nodes {
                    state
                    createdAt
                    author { login }
                  }
                }
              }
            }
          }
        }
        """
        all_prs = []
        cursor = None
        has_next_page = True
        logger.info(f"Fetching PRs with query: {query_str}")
        
        while has_next_page:
            variables = {"query": query_str, "cursor": cursor}
            data = await self.query(graphql_query, variables)
            search_data = data["search"]
            
            if cursor is None:
                count = search_data.get('issueCount', 0)
                logger.info(f"GitHub Search found {count} potential results.")
            
            for node in search_data.get("nodes", []):
                if node and "number" in node:
                    all_prs.append(PullRequestNode(**node))
            
            page_info = search_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            cursor = page_info["endCursor"]
            
        # Save to cache
        with open(cache_path, 'w') as f:
            json.dump([pr.model_dump(mode='json') for pr in all_prs], f)
            
        return all_prs

    async def fetch_org_repos(self, org: str) -> List[str]:
        graphql_query = """
        query($org: String!, $cursor: String) {
          organization(login: $org) {
            repositories(first: 100, after: $cursor, isFork: false) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                name
              }
            }
          }
        }
        """
        
        repos = []
        cursor = None
        has_next_page = True
        
        while has_next_page:
            variables = {"org": org, "cursor": cursor}
            data = await self.query(graphql_query, variables)
            repo_data = data["organization"]["repositories"]
            
            for node in repo_data["nodes"]:
                repos.append(node["name"])
                
            page_info = repo_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            cursor = page_info["endCursor"]
            
        return repos
