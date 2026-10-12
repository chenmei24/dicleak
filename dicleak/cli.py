"""Command-line interface and independent critical-finding failure gate."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from . import __version__
from .checks import AuditConfig, gate_passes, run_all, score
from .readers import ManifestError, read_manifest
from .report import _cta_link, render_json, render_markdown, render_terminal


def build_parser():
    parser = argparse.ArgumentParser(prog="dicleak", description="Audit a medical-imaging AI CSV manifest for patient-level leakage and partition flaws.")
    parser.add_argument("manifest", help="CSV with patient_id, split and label columns")
    parser.add_argument("--report", metavar="OUT.md", help="also write a Markdown report")
    parser.add_argument("--json", metavar="OUT.json", dest="json_report", help="also write a structured JSON report")
    parser.add_argument("--cta", metavar="URL", help="append an HTTP(S) service link to the Markdown report")
    parser.add_argument("--split-mode", choices=("holdout", "cv"), default="holdout", help="holdout (train + test, optional val) or held-out fold assignments")
    parser.add_argument("--folds", metavar="NAME", nargs="+", help="CV only: explicitly list at least two held-out fold names")
    parser.add_argument("--label-mode", choices=("row", "patient"), default="row", help="row allows patient label variation; patient requires one label per patient")
    parser.add_argument("--allow-single-class", action="store_true", help="skip single-class partition failures for intentional single-class tasks")
    parser.add_argument("--show-ids", action="store_true", help="include a limited number of patient identifiers in findings; review before sharing")
    parser.add_argument("--version", action="version", version="dicleak " + __version__)
    return parser


def _write_report(path, content):
    """Replace the output atomically after generating the complete report."""
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=destination.parent, delete=False) as fh:
            temporary = fh.name
            fh.write(content)
        os.replace(temporary, destination)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _validate_output_paths(manifest, outputs):
    paths = [Path(manifest)] + [Path(path) for path in outputs if path]
    for index, path in enumerate(paths):
        for previous in paths[:index]:
            if path.resolve() == previous.resolve() or (path.exists() and previous.exists() and os.path.samefile(path, previous)):
                raise ValueError("input and output paths must be distinct")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    folds = tuple(args.folds or ())
    if args.split_mode == "holdout" and folds:
        parser.error("--folds is only valid with --split-mode cv")
    if args.split_mode == "cv" and (len(folds) < 2 or len(set(folds)) != len(folds) or any(not fold.strip() or fold != fold.strip() for fold in folds)):
        parser.error("--split-mode cv requires --folds with at least two distinct nonempty names")
    config = AuditConfig(args.split_mode, folds, args.label_mode, args.allow_single_class, args.show_ids)
    try:
        _validate_output_paths(args.manifest, (args.report, args.json_report))
        if args.cta:
            _cta_link(args.cta)
        manifest = read_manifest(args.manifest, args.split_mode, folds)
        findings = run_all(manifest.rows, config, manifest.diagnostics)
        value = score(findings)
        print(render_terminal(findings, value, manifest.rows, manifest, config))
        if args.report:
            _write_report(args.report, render_markdown(findings, value, manifest.rows, args.cta, manifest, config))
            print("Markdown report written.")
        if args.json_report:
            _write_report(args.json_report, render_json(findings, value, manifest.rows, manifest, config))
            print("JSON report written.")
    except (ManifestError, OSError, ValueError) as exc:
        print("dicleak: %s" % exc, file=sys.stderr)
        return 2
    return 0 if gate_passes(findings) else 1


if __name__ == "__main__":
    sys.exit(main())
