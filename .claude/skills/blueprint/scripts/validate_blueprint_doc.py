#!/usr/bin/env python3
"""
Minimal structural validator for Codex blueprint documents.

Usage:
  python .codex/skills/blueprint/scripts/validate_blueprint_doc.py ./blueprint-my-task.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_TOP_HEADERS = [
    "## 0. Goals and Deliverables",
    "## 1. Working Context",
    "## 2. Workflow Definition",
    "## 3. Implementation Spec",
    "## 4. Validation Checklist",
]

REQUIRED_CONTEXT_SUBHEADERS = [
    "### Background",
    "### Objective",
    "### Scope",
    "### Inputs",
    "### Outputs",
    "### Constraints",
    "### Terms",
]

REQUIRED_STEP_FIELDS = [
    "1) Step Goal:",
    "2) Input / Output:",
    "3) LLM Decision Area:",
    "4) Code Processing Area:",
    "5) Success Criteria:",
    "6) Validation Method:",
    "7) Failure Handling:",
    "8) Skills / Scripts:",
    "9) Intermediate Artifact Rule:",
]

REQUIRED_STATES = [
    "`COLLECTING_REQUIREMENTS`",
    "`PLANNING`",
    "`RUNNING_SCRIPT`",
    "`VALIDATING`",
    "`NEEDS_USER_INPUT`",
    "`DONE`",
    "`FAILED`",
]


STEP_HEADING_RE = re.compile(r"^#### Step \d{2}:", flags=re.MULTILINE)
FENCED_BLOCK_RE = re.compile(r"```.*?```", flags=re.DOTALL)


def strip_fenced_code_blocks(text: str) -> str:
    return re.sub(FENCED_BLOCK_RE, "", text)


def assert_in_order(text: str, items: list[str], issues: list[str], label: str) -> None:
    cursor = -1
    for item in items:
        idx = text.find(item)
        if idx == -1:
            issues.append(f"Missing {label}: {item}")
            continue
        if idx < cursor:
            issues.append(f"Out-of-order {label}: {item}")
        cursor = idx


def split_step_blocks(text: str) -> list[str]:
    matches = list(STEP_HEADING_RE.finditer(text))
    blocks: list[str] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append(text[start:end])
    return blocks


def validate(path: Path) -> tuple[bool, list[str]]:
    if not path.exists():
        return False, [f"File not found: {path}"]

    text = path.read_text(encoding="utf-8")
    text_no_code = strip_fenced_code_blocks(text)
    issues: list[str] = []

    if not re.fullmatch(r"blueprint-.+\.md", path.name):
        issues.append("Filename should follow blueprint-<task-name>.md")

    assert_in_order(text_no_code, REQUIRED_TOP_HEADERS, issues, "top header")
    assert_in_order(text_no_code, REQUIRED_CONTEXT_SUBHEADERS, issues, "context section")

    for item in REQUIRED_STATES:
        if item not in text_no_code:
            issues.append(f"Missing state token: {item}")

    step_blocks = split_step_blocks(text_no_code)
    if len(step_blocks) < 2:
        issues.append("Require at least two workflow steps using '#### Step NN:' headings")
    else:
        for idx, block in enumerate(step_blocks, start=1):
            for field in REQUIRED_STEP_FIELDS:
                if field not in block:
                    issues.append(f"Missing step field in Step {idx:02d}: {field}")

    if "output/step01_" not in text_no_code:
        issues.append("Expected at least one intermediate artifact path using output/stepNN_<name>.<ext>")

    return len(issues) == 0, issues


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python validate_blueprint_doc.py <blueprint-md-path>")
        return 1

    ok, issues = validate(Path(sys.argv[1]))
    if ok:
        print("Blueprint document is structurally valid.")
        return 0

    print("Blueprint document validation failed:")
    for issue in issues:
        print(f"- {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
