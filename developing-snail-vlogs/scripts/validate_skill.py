#!/usr/bin/env python3
"""Validate repository-level invariants for developing-snail-vlogs."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
MANIFEST = ROOT / "references" / "b-vlog-source-manifest.md"
ANALYSIS = ROOT / "references" / "b-vlog-final-analysis.md"
OPENAI_YAML = ROOT / "agents" / "openai.yaml"


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    required_files = [SKILL, MANIFEST, ANALYSIS, OPENAI_YAML]
    for path in required_files:
        if not path.is_file():
            fail(f"missing required file: {path.relative_to(ROOT)}", errors)

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    skill_text = SKILL.read_text(encoding="utf-8")
    skill_lines = skill_text.splitlines()
    if len(skill_lines) > 500:
        fail(f"SKILL.md has {len(skill_lines)} lines; keep it at or below 500", errors)

    frontmatter = re.match(r"\A---\n(.*?)\n---\n", skill_text, re.DOTALL)
    if not frontmatter:
        fail("SKILL.md has invalid YAML frontmatter delimiters", errors)
    else:
        keys = []
        for line in frontmatter.group(1).splitlines():
            if line and not line.startswith((" ", "\t")) and ":" in line:
                keys.append(line.split(":", 1)[0].strip())
        if keys != ["name", "description"]:
            fail(f"frontmatter keys must be name, description; got {keys}", errors)

    required_phrases = [
        "宏观环境块 → 核心事件章节 → 连续故事段 → 实际切镜",
        "4—7",
        "5—8",
        "0—10s",
        "Motion Carrier",
        "writing-snail-vlog-subtitles",
    ]
    for phrase in required_phrases:
        if phrase not in skill_text:
            fail(f"SKILL.md is missing required rule: {phrase}", errors)

    if "C:\\Users" in skill_text:
        fail("SKILL.md must not contain a user-local Windows path", errors)

    reference_paths = sorted(set(re.findall(r"references/[A-Za-z0-9_.\-/]+", skill_text)))
    for reference in reference_paths:
        if not (ROOT / reference).is_file():
            fail(f"SKILL.md references missing file: {reference}", errors)

    yaml_text = OPENAI_YAML.read_text(encoding="utf-8")
    if "$developing-snail-vlogs" not in yaml_text:
        fail("agents/openai.yaml default_prompt must mention $developing-snail-vlogs", errors)
    if "宏观环境块" not in yaml_text or "核心事件章节" not in yaml_text:
        fail("agents/openai.yaml must expose the four-layer workflow", errors)

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    declared_hash = re.search(
        r"内部文件 SHA-256 \| `([0-9a-f]{64})`", manifest_text
    )
    declared_bytes = re.search(r"内部文件字节数 \| (\d+) \|", manifest_text)
    declared_lines = re.search(r"内部文件行数 \| (\d+) \|", manifest_text)

    analysis_bytes = ANALYSIS.read_bytes()
    actual_hash = hashlib.sha256(analysis_bytes).hexdigest()
    actual_size = len(analysis_bytes)
    actual_lines = len(ANALYSIS.read_text(encoding="utf-8").splitlines())

    if not declared_hash or declared_hash.group(1) != actual_hash:
        fail(f"analysis SHA mismatch: actual {actual_hash}", errors)
    if not declared_bytes or int(declared_bytes.group(1)) != actual_size:
        fail(f"analysis byte-count mismatch: actual {actual_size}", errors)
    if not declared_lines or int(declared_lines.group(1)) != actual_lines:
        fail(f"analysis line-count mismatch: actual {actual_lines}", errors)

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print(
        f"[OK] developing-snail-vlogs: {len(skill_lines)} SKILL lines, "
        f"{len(reference_paths)} references, analysis {actual_lines} lines / "
        f"{actual_size} bytes / {actual_hash}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
