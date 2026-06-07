"""
PanSou plugin - High-performance cloud drive search engine.
Supports 13+ cloud drives including Quark, Baidu, AliYun.

Requires a self-hosted PanSou instance (Docker):
  docker run -d --name pansou -p 8888:8888 ghcr.io/fish2018/pansou:latest

Then set endpoint to http://localhost:8888 in config.json.

GitHub: https://github.com/fish2018/pansou
"""

import json
import urllib.request
from typing import Optional

from . import ResourcePlugin, ResourceResult


class Plugin(ResourcePlugin):
    name = "pansou"
    display_name = "PanSou 网盘搜索"
    requires_auth = False
    url = "https://github.com/fish2018/pansou"

    def __init__(self, config: dict = None):
        super().__init__(config)
        # Configurable endpoint - user sets their own PanSou instance URL
        self.endpoint = (config or {}).get("endpoint", "").rstrip("/")
        # Timeout for API calls
        self.timeout = (config or {}).get("timeout", 15)

    def search(self, query: str, page: int = 1) -> list[ResourceResult]:
        if not self.endpoint:
            print("[pansou] No endpoint configured. Set 'endpoint' in config.json plugins.pansou")
            print("[pansou]   Docker: docker run -d --name pansou -p 8888:8888 ghcr.io/fish2018/pansou:latest")
            print("[pansou]   Then set endpoint to http://localhost:8888")
            return []

        url = f"{self.endpoint}/api/search"
        payload = json.dumps({
            "kw": query,
            "cloud_types": ["quark"],
            "res": "merge",
            "page": page,
        }).encode()

        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; MediaVault/1.0)",
        })

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            print(f"[pansou] Search error: {e}")
            return []

        # Parse PanSou response format
        api_data = data.get("data", {})
        merged = api_data.get("merged_by_type", {})
        quark_results = merged.get("quark", [])

        # Also check top-level merged_by_type (backward compat)
        if not quark_results:
            merged = data.get("merged_by_type", {})
            quark_results = merged.get("quark", [])

        results = []
        seen = set()
        for item in quark_results:
            # PanSou uses 'note' field for title, not 'title'
            title = (item.get("note") or item.get("title", "")).strip()
            share_url = item.get("url", "").strip()
            if not title or not share_url:
                continue
            # Deduplicate by URL
            if share_url in seen:
                continue
            seen.add(share_url)

            password = item.get("password", "")
            date = item.get("datetime") or item.get("date", "")

            # Truncate overly long titles
            if len(title) > 120:
                title = title[:120] + "..."

            results.append(ResourceResult(
                title=title,
                source="quark",
                url=share_url,
                quality=self._guess_quality(title),
                site=self.name,
                extra={
                    "password": password,
                    "date": date,
                },
            ))

        return results

    def extract_link(self, resource: ResourceResult) -> Optional[str]:
        """PanSou already returns direct Quark share URLs."""
        if resource.url.startswith("https://pan.quark.cn/"):
            return resource.url
        return None

    @staticmethod
    def _guess_quality(title: str) -> str:
        """Extract quality info from title."""
        t = title.lower()
        if "2160p" in t or "4k" in t or "uhd" in t:
            return "4K"
        if "1080p" in t:
            return "1080p"
        if "720p" in t:
            return "720p"
        if "480p" in t:
            return "480p"
        return ""
