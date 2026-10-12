# Contributing

Thank you for helping make manifest audits easier to reproduce.

1. Open an issue describing the split design and expected behavior. Include only a small **synthetic** CSV; do not submit patient identifiers, source reports, image files, or credentials.
2. Install with `python -m pip install -e ".[dev]"` and run `python -m pytest -q`.
3. Keep runtime dependencies optional or absent, support Python 3.9+, and add regression tests for substantive changes.
4. Explain new flags and assumptions in both READMEs. Avoid claims of clinical validation or regulatory compliance without supporting validation.
5. If sample behavior changes, rerun `python samples/generate_samples.py` and regenerate the reports in `docs/` using the documented commands.

A test for leakage should check the **exit code and failure gate**, including high-score leakage examples, rather than merely checking a score deduction. Include legitimate repeated observations and multi-label or longitudinal cases when changing label checks.

For a security-sensitive report, avoid including confidential data in a public issue. This project has no private disclosure channel advertised; provide a non-sensitive description or contact the maintainer through their public GitHub profile to arrange an appropriate channel.
