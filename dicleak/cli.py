"""Command-line interface."""

import argparse
import sys

from . import __version__
from .checks import run_all, score
from .readers import load_manifest
from .report import render_markdown, render_terminal


def build_parser():
    p = argparse.ArgumentParser(
        prog="dicleak",
        description="Audit a medical-imaging AI dataset manifest for "
                    "patient-level leakage and split flaws.",
    )
    p.add_argument("manifest", help="CSV with patient_id, split and label columns")
    p.add_argument("--report", metavar="OUT.md",
                   help="also write a Markdown report to OUT.md")
    p.add_argument("--cta", metavar="URL",
                   help="append a service link footer to the Markdown report")
    p.add_argument("--version", action="version", version="dicleak " + __version__)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    rows, warnings = load_manifest(args.manifest)
    for w in warnings:
        print("warning: %s" % w, file=sys.stderr)
    findings = run_all(rows)
    value = score(findings)
    print(render_terminal(findings, value, rows))
    if args.report:
        md = render_markdown(findings, value, rows, cta_url=args.cta)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(md)
        print("Markdown report written to %s" % args.report)
    return 0 if value >= 60 else 1


if __name__ == "__main__":
    sys.exit(main())
