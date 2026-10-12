# Changelog

## 0.1.1 — 2026-10-12

- Any CRITICAL finding fails the audit gate, independently of the retained heuristic score.
- Remove publication-readiness grades and explain the score's unvalidated scope.
- Validate required values, unknown partitions, duplicate or alias-conflicting headers, and record shape; preserve input accounting and line diagnostics.
- Require train + test in default holdout mode; add explicit CV held-out fold assignment mode.
- Report rows and patient label incidences; add optional patient-level label consistency and intentional single-class opt-out.
- Hide patient identifiers by default; add explicit `--show-ids`, escaped Markdown, and terminal control-character handling.
- Clarify filepath-only comparisons and flag cross-partition path assignments.
- Add structured JSON reports, input/output path protection, and atomic report replacement.
- Add English/Chinese documentation, reproducible synthetic examples, generated reports, tests, CI, package URLs, and contribution templates.

## 0.1.0

- Initial CSV manifest auditor and CLI with seven checks and Markdown output.
