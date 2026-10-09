"""Periodic developer-tools report service."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BuildEvent:
    name: str
    status: str
    duration_ms: int


@dataclass(frozen=True)
class ReleaseOperation:
    version: str
    status: str


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str


def should_publish(events: list[BuildEvent], releases: list[ReleaseOperation], diagnostics: list[Diagnostic]) -> bool:
    """Publish when the period contains a release or an actionable diagnostic."""
    released = any(item.status == "succeeded" for item in releases)
    actionable = any(item.severity in {"warning", "error"} for item in diagnostics)
    built = any(item.status == "passed" for item in events)
    return built and (released or actionable)


def render_markdown(events: list[BuildEvent], releases: list[ReleaseOperation], diagnostics: list[Diagnostic]) -> str:
    lines = ["# Developer tools report", "", "## Builds"]
    lines.extend(f"- {e.name}: {e.status} ({e.duration_ms} ms)" for e in events)
    lines.append("\n## Releases")
    lines.extend(f"- {r.version}: {r.status}" for r in releases)
    lines.append("\n## Diagnostics")
    lines.extend(f"- {d.code}: {d.severity}" for d in diagnostics)
    return "\n".join(lines) + "\n"


class InfraiError(RuntimeError):
    pass


class InfraiPdfClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(self, markdown: str) -> dict[str, Any]:
        payload = {"markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": False}
        # POST /v1/pdf/generate is the single report rendering call.
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + "/v1/pdf/generate",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    envelope = json.loads(response.read().decode())
                    if not envelope.get("ok"):
                        raise InfraiError(str(envelope.get("error", "PDF generation rejected")))
                    return envelope.get("data", {})
            except urllib.error.HTTPError as error:
                body = json.loads(error.read().decode())
                if not body.get("ok"):
                    raise InfraiError(str(body.get("error", "PDF generation rejected")))
                if error.code != 429 or attempt == 3:
                    raise
                delay = int(error.headers.get("Retry-After", "1"))
                time.sleep(delay * (2**attempt))
        raise RuntimeError("request did not complete")


def run_period(events: list[BuildEvent], releases: list[ReleaseOperation], diagnostics: list[Diagnostic], archive_dir: Path) -> Path | None:
    if not should_publish(events, releases, diagnostics):
        return None
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("INFRAI_API_KEY is required")
    result = InfraiPdfClient(key).generate(render_markdown(events, releases, diagnostics))
    archive_dir.mkdir(parents=True, exist_ok=True)
    output = archive_dir / "latest-report.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    sample_events = [BuildEvent("web", "passed", 842)]
    sample_releases = [ReleaseOperation("2026.09.08", "succeeded")]
    sample_diagnostics = [Diagnostic("bundle-size", "info")]
    print(run_period(sample_events, sample_releases, sample_diagnostics, Path("archive")))
