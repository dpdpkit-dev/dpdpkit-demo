"""The live demo for the CI tools page: `dpdpkit-lint-action` and `dpdpkit-conformance`, run for real.

- lint: the action runs `dpdpkit lint` from dpdpkit-core, so this page calls the same `run_lint()` on a config the
  visitor picks or edits, and shows the plain output, the GitHub annotation output and the exit code.
- conformance: `python -m dpdpkit_conformance` runs as a subprocess against two small apps (`conformance_demo/`), one
  wired the documented way and one whose admin guard lets everyone in. A run takes a few seconds and the answer never
  changes, so each target is run once per process.
"""

import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import Request

from dpdpkit.lint import run_lint

BASE = Path(__file__).parent
GOOD = (BASE / "lint_samples" / "good.yaml").read_text(encoding="utf-8")
LIMIT = 20000

# The marketing purpose's retention rule is the last line before the notice block in the sample.
_MARKETING_RETENTION = re.compile(r"^    retention: \{trigger: withdrawal, period_days: 0\}\n", re.M)
SAMPLES = {
    "good": ("A complete config", GOOD),
    "missing-retention": ("A purpose with no retention rule", _MARKETING_RETENTION.sub("", GOOD)),
    "no-notice": ("No notice at all", GOOD[: GOOD.index("\nnotice:")] + "\n"),
}
TARGETS = {
    "passing": ("An app wired the documented way", "conformance_demo.passing:app"),
    "failing": ("The same app, but its admin guard lets every caller in as an admin", "conformance_demo.failing:app"),
}
LINT_WORKFLOW = """\
jobs:
  dpdp-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: dpdpkit-dev/dpdpkit-lint-action@v1
        with:
          config: dpdpkit.yaml
          strict: "false"
"""


def _lint(text: str, strict: bool, fmt: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "dpdpkit.yaml"
        path.write_text(text, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_lint([str(path)], strict=strict, fmt=fmt)
    shown = (out.getvalue() + err.getvalue()).replace(str(path), "dpdpkit.yaml").replace(path.as_posix(), "dpdpkit.yaml")
    return code, shown.strip()


def lint_section(sample: str, text: str | None, strict: bool) -> dict:
    if text is None:
        text = SAMPLES[sample][1]
    code, plain = _lint(text, strict, "text")
    _, annotations = _lint(text, strict, "github")
    return {
        "samples": {k: label for k, (label, _) in SAMPLES.items()},
        "sample": sample,
        "text": text,
        "strict": strict,
        "exit_code": code,
        "plain": plain,
        "annotations": annotations,
        "workflow": LINT_WORKFLOW.replace('strict: "false"', f'strict: "{str(strict).lower()}"'),
    }


@lru_cache(maxsize=None)
def run_conformance(target: str) -> dict:
    env = {**os.environ, "DPDPKIT_ASGI_APP": TARGETS[target][1], "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-m", "dpdpkit_conformance", "-v", "-rf", "--tb=no", "-p", "no:warnings"],
        cwd=BASE, env=env, capture_output=True, text=True, encoding="utf-8", timeout=240,
    )
    tests, reasons = [], {}
    for line in proc.stdout.splitlines():
        if m := re.match(r"(?:\S+::)?(test_\w+) (PASSED|FAILED|SKIPPED|ERROR)", line):
            tests.append({"name": m[1], "outcome": m[2].lower()})
        elif m := re.match(r"FAILED \S+::(test_\w+)(?: - (.*))?$", line):
            reasons[m[1]] = m[2] or ""
    for t in tests:
        t["reason"] = reasons.get(t["name"], "")[:160]
    summary = proc.stdout.strip().splitlines()[-1].strip("= ") if proc.stdout.strip() else proc.stderr.strip()[-300:]
    return {"target": target, "exit_code": proc.returncode, "tests": tests, "summary": summary}


def view(request: Request) -> dict:
    q = request.query_params
    sample = q.get("sample") if q.get("sample") in SAMPLES else "good"
    text = q.get("config")
    text = text[:LIMIT] if text else None
    target = q.get("target")
    return {
        "ci_lint": lint_section(sample, text, q.get("strict") == "1"),
        "ci_targets": {k: label for k, (label, _) in TARGETS.items()},
        "ci_target": target if target in TARGETS else None,
        "ci_run": run_conformance(target) if target in TARGETS else None,
    }
