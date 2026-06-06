#!/usr/bin/env python3
"""One-command learning loop for the spm-study skill."""

from __future__ import annotations

from study_modules.cli import build_parser
from study_modules.materials import case_range_chapters_text
from study_modules.router import set_case_range_chapters_resolver

set_case_range_chapters_resolver(case_range_chapters_text)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
