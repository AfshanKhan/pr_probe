import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    github_token: Optional[str] = None
    default_days: int = 7
    template_patterns: List[str] = [
        "## What changed & why",
        "## Risk & impact",
        "## Testing evidence",
        "## Task completion checklist",
        "## Reviewer notes"
    ]
    strict_template_mode: bool = False
    cache_dir: str = ".cache"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
