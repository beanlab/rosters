#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path


PHASE_FILE_PREFIX = {
    "builder": "01-builder.md",
    "drafter": "02-drafter.md",
    "critic": "03-critic.md",
    "editor": "04-editor.md",
}


def slugify_title(title: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]+", "_", title.strip())
    cleaned = re.sub(r"[ _]+", "_", cleaned).strip("_")
    return cleaned or "untitled_story"


def detect_project_root(start: Path) -> tuple[Path, Path]:
    cur = start.resolve()
    for d in [cur, *cur.parents]:
        if d.name == ".myteam":
            return d, d.parent
    raise RuntimeError("Could not find .myteam root from current path.")


def new_run_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{now}-{secrets.token_hex(2)}"


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def load_inline_or_file(inline_text: str | None, file_path: str | None) -> str | None:
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    return inline_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Append hybrid story logs (markdown + jsonl).")
    parser.add_argument("--title", required=True, help="Story title")
    parser.add_argument("--phase", required=True, help="Phase name: builder|drafter|critic|editor")
    parser.add_argument("--action", required=True, help="Short action label")
    parser.add_argument("--input-summary", required=True, help="Concise input summary")
    parser.add_argument("--output-summary", required=True, help="Concise output summary")
    parser.add_argument("--run-id", help="Run id; generated if omitted")
    parser.add_argument("--agent", help="Agent name; defaults to phase")
    parser.add_argument("--skill", help="Skill name (optional)")
    parser.add_argument("--next-payload", help="Next-step payload text (optional)")
    parser.add_argument("--files-touched", help="Comma-separated file paths (optional)")
    parser.add_argument(
        "--task-input-text",
        help="Exact task input text. Prefer this over summarized input when available.",
    )
    parser.add_argument(
        "--task-output-text",
        help="Exact task output text written by the agent for this task.",
    )
    parser.add_argument(
        "--task-input-file",
        help="Path to a UTF-8 text file containing exact task input text.",
    )
    parser.add_argument(
        "--task-output-file",
        help="Path to a UTF-8 text file containing exact task output text.",
    )
    parser.add_argument(
        "--inference-reasoning",
        help=(
            "Detailed reasoning for all inferences made in this task. "
            "If no inference occurred, state that explicitly."
        ),
    )
    parser.add_argument(
        "--inference-reasoning-file",
        help="Path to a UTF-8 text file containing inference reasoning details.",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc).isoformat()
    run_id = args.run_id or new_run_id()
    agent = args.agent or args.phase
    story_slug = slugify_title(args.title)

    myteam_root, project_root = detect_project_root(Path(__file__).resolve())
    logs_root = project_root / "st-logs" / story_slug / run_id
    phase_file_name = PHASE_FILE_PREFIX.get(args.phase.lower(), f"99-{args.phase.lower()}.md")
    phase_file = logs_root / phase_file_name
    jsonl_file = logs_root / "events.jsonl"

    files_touched = []
    if args.files_touched:
        files_touched = [p.strip() for p in args.files_touched.split(",") if p.strip()]

    task_input_text = load_inline_or_file(args.task_input_text, args.task_input_file)
    task_output_text = load_inline_or_file(args.task_output_text, args.task_output_file)
    inference_reasoning = load_inline_or_file(
        args.inference_reasoning, args.inference_reasoning_file
    )

    task_input_block = (
        f"### Task Input (Verbatim)\n```text\n{task_input_text}\n```\n"
        if task_input_text
        else "### Task Input (Verbatim)\n- Not provided.\n"
    )
    task_output_block = (
        f"### Task Output (Verbatim)\n```text\n{task_output_text}\n```\n"
        if task_output_text
        else "### Task Output (Verbatim)\n- Not provided.\n"
    )
    inference_block = (
        f"### Inference Reasoning\n{inference_reasoning}\n"
        if inference_reasoning
        else "### Inference Reasoning\n- No inference reasoning provided.\n"
    )

    skill_line = f"\n## Skill: {args.skill}\n" if args.skill else ""
    payload_block = f"\n## Next Step Payload\n{args.next_payload}\n" if args.next_payload else ""

    md_entry = (
        f"\n## Event: {args.action}\n"
        f"- Timestamp (UTC): {now}\n"
        f"- Run ID: {run_id}\n"
        f"- Agent: {agent}\n"
        f"- Phase: {args.phase}\n"
        f"- Story: {args.title}\n"
        f"{skill_line}"
        f"### Inputs\n- {args.input_summary}\n"
        f"### Outputs\n- {args.output_summary}\n"
        f"{task_input_block}"
        f"{task_output_block}"
        f"{inference_block}"
        f"{payload_block}"
    )
    append_text(phase_file, md_entry)

    event = {
        "timestamp_utc": now,
        "run_id": run_id,
        "title": args.title,
        "story_slug": story_slug,
        "agent": agent,
        "phase": args.phase,
        "skill": args.skill,
        "action": args.action,
        "input_summary": args.input_summary,
        "output_summary": args.output_summary,
        "task_input_text": task_input_text,
        "task_output_text": task_output_text,
        "inference_reasoning": inference_reasoning,
        "next_payload": args.next_payload,
        "files_touched": files_touched,
        "phase_log": str(phase_file.relative_to(project_root)),
    }
    append_text(jsonl_file, json.dumps(event, ensure_ascii=True) + "\n")

    print(f"run_id={run_id}")
    print(f"phase_log={phase_file}")
    print(f"events_jsonl={jsonl_file}")
    print(f"myteam_root={myteam_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
