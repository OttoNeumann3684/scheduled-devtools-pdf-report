from pathlib import Path

from src.report_service import BuildEvent, Diagnostic, ReleaseOperation, render_markdown, should_publish


def test_release_with_passed_build_is_publishable(tmp_path: Path) -> None:
    events = [BuildEvent("next-build", "passed", 1200)]
    releases = [ReleaseOperation("1.4.0", "succeeded")]
    diagnostics = [Diagnostic("lint", "info")]
    assert should_publish(events, releases, diagnostics)
    assert "next-build" in render_markdown(events, releases, diagnostics)


def test_failed_build_blocks_report_even_with_release() -> None:
    assert not should_publish(
        [BuildEvent("next-build", "failed", 1200)],
        [ReleaseOperation("1.4.0", "succeeded")],
        [],
    )
