"""Configuration management for parser module."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class Config:
    """Configuration for the parser module."""

    email: str = ""
    api_keys: dict[str, str | None] = field(default_factory=dict)
    institutional: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    unofficial: dict[str, Any] = field(default_factory=dict)
    download: dict[str, Any] = field(default_factory=dict)
    rate_limits: dict[str, Any] = field(default_factory=dict)
    batch: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "Config":
        """Load configuration from file and environment variables.

        Args:
            config_path: Path to config.yaml file (optional)

        Returns:
            Config object with merged settings
        """
        data: dict[str, Any] = {}

        # Try to load from file
        if config_path:
            config_file = Path(config_path)
            if config_file.exists() and HAS_YAML:
                with open(config_file) as f:
                    data = yaml.safe_load(f) or {}

        # Extract user info
        user_data = data.get("user", {})
        email = os.getenv("PARSER_EMAIL",
                os.getenv("PAPER_EMAIL",
                user_data.get("email", "")))

        # API keys with environment variable overrides
        api_keys = data.get("api_keys", {})
        api_keys["ncbi"] = os.getenv("NCBI_API_KEY", api_keys.get("ncbi"))
        api_keys["semantic_scholar"] = os.getenv(
            "S2_API_KEY",
            os.getenv("SEMANTIC_SCHOLAR_API_KEY", api_keys.get("semantic_scholar"))
        )
        api_keys["crossref_plus"] = os.getenv(
            "CROSSREF_PLUS_API_KEY", api_keys.get("crossref_plus")
        )
        api_keys["openalex"] = os.getenv(
            "OPENALEX_API_KEY", api_keys.get("openalex")
        )

        # Default source configuration with priorities
        default_sources = {
            "unpaywall": {"enabled": True, "priority": 1},
            "arxiv": {"enabled": True, "priority": 2},
            "pmc": {"enabled": True, "priority": 3},
            "biorxiv": {"enabled": True, "priority": 4},
            "semantic_scholar": {"enabled": True, "priority": 5},
            "openalex": {"enabled": True, "priority": 6},
            "institutional": {"enabled": False, "priority": 7},
            "web_search": {"enabled": True, "priority": 8},
            "scihub": {"enabled": False, "priority": 9},
            "libgen": {"enabled": False, "priority": 10},
        }
        sources = data.get("sources", {})
        for source, defaults in default_sources.items():
            if source not in sources:
                sources[source] = defaults
            else:
                for key, value in defaults.items():
                    if key not in sources[source]:
                        sources[source][key] = value

        # Default download configuration
        default_download: dict[str, Any] = {
            "output_dir": "./downloads",
            "filename_format": "{first_author}_{year}_{title_short}.pdf",
            "max_title_length": 50,
            "create_subfolders": False,
            "skip_existing": True,
        }
        download: dict[str, Any] = data.get("download", {})
        for key, value in default_download.items():
            if key not in download:
                download[key] = value

        # Default rate limits per source
        default_rate_limits: dict[str, Any] = {
            "global_delay": 1.0,
            "per_source_delays": {
                "crossref": 0.5,
                "unpaywall": 0.1,
                "arxiv": 3.0,
                "pmc": 0.34,
                "semantic_scholar": 3.0,
                "openalex": 0.1,
                "biorxiv": 1.0,
                "scihub": 5.0,
                "libgen": 3.0,
            },
        }
        rate_limits: dict[str, Any] = data.get("rate_limits", {})
        for key, value in default_rate_limits.items():
            if key not in rate_limits:
                rate_limits[key] = value

        # Default batch configuration
        default_batch: dict[str, Any] = {
            "max_concurrent": 3,
            "retry_failed": True,
            "max_retries": 2,
            "save_progress": True,
            "progress_file": ".retrieval_progress.json",
        }
        batch: dict[str, Any] = data.get("batch", {})
        for key, value in default_batch.items():
            if key not in batch:
                batch[key] = value

        # Default institutional configuration
        default_institutional: dict[str, Any] = {
            "enabled": False,
            "vpn_enabled": False,
            "vpn_script": None,
            "vpn_disconnect_script": None,
            "proxy_url": None,
            "cookies_file": ".institutional_cookies.pkl",
            "university": None,
        }
        institutional: dict[str, Any] = data.get("institutional", {})
        for key, value in default_institutional.items():
            if key not in institutional:
                institutional[key] = value

        return cls(
            email=email,
            api_keys=api_keys,
            institutional=institutional,
            sources=sources,
            unofficial=data.get("unofficial", {}),
            download=download,
            rate_limits=rate_limits,
            batch=batch,
        )

    def is_source_enabled(self, source: str) -> bool:
        """Check if a source is enabled."""
        return self.sources.get(source, {}).get("enabled", False)

    def is_unofficial_enabled(self) -> bool:
        """Check if unofficial sources are enabled with disclaimer."""
        return self.unofficial.get("disclaimer_accepted", False)

    def get_source_priority(self, source: str) -> int:
        """Get the priority for a source (lower = higher priority)."""
        return self.sources.get(source, {}).get("priority", 999)

    def get_sorted_sources(self) -> list[str]:
        """Get sources sorted by priority."""
        return sorted(
            self.sources.keys(),
            key=lambda s: self.get_source_priority(s)
        )

    def get_source_delay(self, source: str) -> float:
        """Get the rate limit delay for a specific source."""
        per_source = self.rate_limits.get("per_source_delays", {})
        return per_source.get(source, self.rate_limits.get("global_delay", 1.0))

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "email": self.email,
            "api_keys": {k: "***" if v else None for k, v in self.api_keys.items()},
            "sources": self.sources,
            "download": self.download,
            "rate_limits": self.rate_limits,
            "batch": self.batch,
        }
