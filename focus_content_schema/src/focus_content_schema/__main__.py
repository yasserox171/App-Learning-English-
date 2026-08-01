"""CLI:

    python -m focus_content_schema validate <payload.json>
    python -m focus_content_schema validate-ir <ir.json>
    python -m focus_content_schema schema [-o out.json]
    python -m focus_content_schema prompt [-o out.md]

``validate`` exits non-zero and prints the error list when the file is invalid,
so it drops straight into a pipeline or a pre-commit hook.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ir import export_ir_json_schema
from .payload import validate_ir_dict, validate_payload
from .prompt import render_prompt_fragment

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2


def _load(path: str) -> tuple[object | None, str | None]:
    file = Path(path)
    if not file.exists():
        return None, f"file not found: {path}"
    try:
        return json.loads(file.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"{path}: invalid JSON — {exc}"


def _report(path: str, errors: list[str], kind: str) -> int:
    if errors:
        print(f"✗ {path}: {len(errors)} error(s)", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return EXIT_INVALID
    print(f"✓ {path}: valid {kind}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="focus_content_schema",
        description="Validate Focus Languages lesson content before import.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="validate a built import payload")
    p_val.add_argument("file", help="path to the payload JSON")

    p_ir = sub.add_parser("validate-ir", help="validate raw LLM IR output")
    p_ir.add_argument("file", help="path to the IR JSON")

    p_schema = sub.add_parser("schema", help="print the IR JSON Schema")
    p_schema.add_argument("-o", "--output", help="write to a file instead")

    p_prompt = sub.add_parser("prompt", help="print the LLM prompt fragment")
    p_prompt.add_argument("-o", "--output", help="write to a file instead")

    args = parser.parse_args(argv)

    if args.command in ("validate", "validate-ir"):
        data, error = _load(args.file)
        if error:
            print(f"✗ {error}", file=sys.stderr)
            return EXIT_USAGE
        if args.command == "validate":
            return _report(args.file, validate_payload(data), "import payload")
        return _report(args.file, validate_ir_dict(data), "IR document")

    if args.command == "schema":
        text = json.dumps(export_ir_json_schema(), indent=2, ensure_ascii=False)
    else:
        text = render_prompt_fragment()

    if getattr(args, "output", None):
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"✓ written to {args.output}")
    else:
        print(text)
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
