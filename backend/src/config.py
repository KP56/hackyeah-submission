import os
from dataclasses import dataclass
from typing import List, Any
import yaml


DEFAULT_CONFIG_YAML = {
    "nylas": {
        "api_key": "",           # Fill from Nylas Dashboard → API Keys
        "client_id": "",         # Fill from Nylas Dashboard → Overview
        "api_uri": "https://api.us.nylas.com",
        "redirect_uri": "https://google.com",  # Valid redirect URI
    },
    "gemini": {
        "api_key": "",           # Fill your Google Generative AI key
        "model": "gemini-2.5-flash-lite"  # Gemini model to use
    },
    "watch": {
        "dirs": [
            "~/Desktop",          # Desktop folder
            "~/Downloads",        # Downloads folder
            "~/Documents",        # Documents folder
        ],
        "recent_ops_capacity": 100,
        "pattern_interval_seconds": 60,
    },
    "logging": {
        "enabled": False
    },
    "backend": {
        "port": 8002             # Backend server port
    }
}


@dataclass
class AppConfig:
    nylas_api_key: str | None
    nylas_client_id: str | None
    nylas_redirect_uri: str | None
    nylas_api_uri: str | None

    gemini_api_key: str | None
    gemini_model: str

    watch_dirs: List[str]
    pattern_agent_interval_seconds: int
    recent_ops_capacity: int

    logging_enabled: bool
    
    backend_port: int


def _load_yaml(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(DEFAULT_CONFIG_YAML, f, sort_keys=False, allow_unicode=True)
        return DEFAULT_CONFIG_YAML
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def load_config(path: str = "config.yaml") -> AppConfig:
    data = _load_yaml(path)
    nylas = data.get("nylas", {})
    gemini = data.get("gemini", {})
    watch = data.get("watch", {})
    logging_cfg = data.get("logging", {})
    backend_cfg = data.get("backend", {})

    return AppConfig(
        nylas_api_key=nylas.get("api_key") if nylas.get("api_key") else None,
        nylas_client_id=nylas.get("client_id") if nylas.get("client_id") else None,
        nylas_redirect_uri=nylas.get("redirect_uri") or "https://google.com",
        nylas_api_uri=nylas.get("api_uri") or "https://api.us.nylas.com",
        gemini_api_key=gemini.get("api_key") if gemini.get("api_key") else None,
        gemini_model=gemini.get("model", "gemini-2.5-flash-lite"),
        watch_dirs=[d for d in [os.path.expanduser(d) for d in (watch.get("dirs") or ["~/Desktop", "~/Downloads", "~/Documents"])] if os.path.exists(d)],
        pattern_agent_interval_seconds=int(watch.get("pattern_interval_seconds", 60)),
        recent_ops_capacity=int(watch.get("recent_ops_capacity", 100)),
        logging_enabled=bool(logging_cfg.get("enabled", False)),
        backend_port=int(backend_cfg.get("port", 8002)),
    )
