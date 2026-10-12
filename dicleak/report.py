"""Escaped terminal, Markdown and JSON reports without patient IDs by default."""

import html
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from urllib.parse import urlsplit

from . import __version__
from .checks import AuditConfig, SEVERITY_ICON, gate_passes

SCOPE = ("Manifest checks only. No images, DICOM metadata, content hashes, model predictions, "
         "or external validation were inspected. A passing gate is not evidence of clinical validity, "
         "de-identification, regulatory compliance, or publication readiness.")
SCORE_NOTE = "Unvalidated deduction heuristic; not a clinical or statistical quality score."


def _stats(rows, manifest=None):
    by_split = defaultdict(list)
    for row in rows:
        by_split[row["split"]].append(row)
    labels = Counter(row["label"] for row in rows)
    patient_labels = defaultdict(set)
    for row in rows:
        patient_labels[row["label"]].add(row["patient_id"])
    return {
        "input_rows": manifest.input_rows if manifest else len(rows),
        "valid_rows": len(rows),
        "invalid_rows": manifest.invalid_rows if manifest else 0,
        "unique_patients": len({row["patient_id"] for row in rows}),
        "partitions": {
            split: {"rows": len(partition_rows),
                    "patients": len({row["patient_id"] for row in partition_rows}),
                    "labels": {label: {
                        "rows": sum(row["label"] == label for row in partition_rows),
                        "patients": len({row["patient_id"] for row in partition_rows if row["label"] == label})}
                        for label in sorted({row["label"] for row in partition_rows})}}
            for split, partition_rows in sorted(by_split.items())},
        "labels": {label: {"rows": labels[label], "patients": len(patient_labels[label])} for label in sorted(labels)},
    }


def _plain(value):
    return "".join(char if char.isprintable() else "?" for char in str(value))


def _markdown(value):
    # Escape HTML and Markdown metacharacters, including table separators/newlines.
    value = html.escape(str(value), quote=True).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~\-])", r"\\\1", value)


def report_data(findings, score_value, rows, manifest=None, config=None):
    config = config or AuditConfig()
    return {
        "tool": "dicleak", "version": __version__,
        "gate": "pass" if gate_passes(findings) else "fail",
        "heuristic_score": score_value,
        "score_note": SCORE_NOTE,
        "scope": SCOPE,
        "configuration": asdict(config),
        "dataset": _stats(rows, manifest),
        "input_diagnostics": [asdict(d) for d in manifest.diagnostics] if manifest else [],
        "findings": [asdict(finding) for finding in findings],
    }


def render_json(findings, score_value, rows, manifest=None, config=None):
    return json.dumps(report_data(findings, score_value, rows, manifest, config), ensure_ascii=False, indent=2) + "\n"


def render_terminal(findings, score_value, rows, manifest=None, config=None):
    config = config or AuditConfig()
    st = _stats(rows, manifest)
    lines = ["dicleak %s manifest audit" % __version__,
             "Gate: %s" % ("PASS (configured checks only)" if gate_passes(findings) else "FAIL"),
             "Heuristic score: %d/100. %s" % (score_value, SCORE_NOTE),
             "Mode: %s; label mode: %s; patient identifiers: %s" %
             (config.split_mode, config.label_mode, "shown" if config.show_ids else "hidden"),
             "Input rows: %d; valid rows: %d; invalid rows: %d; unique patients: %d" %
             (st["input_rows"], st["valid_rows"], st["invalid_rows"], st["unique_patients"]), ""]
    for split, counts in st["partitions"].items():
        lines.append("Partition %s: %d rows; %d patients" % (_plain(split), counts["rows"], counts["patients"]))
        for label, label_counts in counts["labels"].items():
            lines.append("  Label %s: %d rows; %d patients" % (_plain(label), label_counts["rows"], label_counts["patients"]))
    lines.append("Patient label counts are incidences: one patient may contribute to multiple labels.")
    lines.append("")
    if not findings:
        lines.append("No findings from the configured manifest checks.")
    for finding in findings:
        lines.extend(["%s %s %s (-%d)" % (SEVERITY_ICON[finding.severity], finding.severity, _plain(finding.title), finding.deduction),
                      "  " + _plain(finding.detail)])
    lines.extend(["", SCOPE])
    return "\n".join(lines)


def _cta_link(cta_url):
    parts = urlsplit(cta_url)
    if parts.scheme not in ("http", "https") or not parts.netloc or any(char.isspace() or char in "<>" for char in cta_url):
        raise ValueError("--cta requires an absolute HTTP(S) URL without spaces or angle brackets")
    return cta_url.replace("(", "%28").replace(")", "%29").replace("\\", "%5C")


def render_markdown(findings, score_value, rows, cta_url=None, manifest=None, config=None):
    config = config or AuditConfig()
    st = _stats(rows, manifest)
    lines = ["# dicleak manifest audit report", "",
             "**Gate: %s**" % ("PASS (configured checks only)" if gate_passes(findings) else "FAIL"), "",
             "**Heuristic score: %d/100.** %s" % (score_value, SCORE_NOTE), "",
             "Version: %s. Mode: %s. Label mode: %s. Patient identifiers: %s." %
             (__version__, config.split_mode, config.label_mode, "shown" if config.show_ids else "hidden"), "",
             "## Input accounting", "", "| Metric | Count |", "|---|---:|",
             "| Input rows | %d |" % st["input_rows"],
             "| Valid rows | %d |" % st["valid_rows"],
             "| Invalid rows | %d |" % st["invalid_rows"],
             "| Unique patients in valid rows | %d |" % st["unique_patients"], "",
             "## Partition and label counts", "", "| Partition | Label | Rows | Patients |", "|---|---|---:|---:|"]
    for split, counts in st["partitions"].items():
        lines.append("| %s | All labels | %d | %d |" % (_markdown(split), counts["rows"], counts["patients"]))
        for label, label_counts in counts["labels"].items():
            lines.append("| %s | %s | %d | %d |" % (_markdown(split), _markdown(label), label_counts["rows"], label_counts["patients"]))
    lines.extend(["", "Patient label counts are incidences: one patient may contribute to multiple labels. Patients in multiple partitions are counted in each partition.", "",
                  "## Findings (%d)" % len(findings), ""])
    if not findings:
        lines.append("No findings from the configured manifest checks.")
    for finding in findings:
        lines.extend(["### %s: %s" % (finding.severity, _markdown(finding.title)), "",
                      "Check: %s. Heuristic deduction: %d." % (finding.check_id, finding.deduction), "", _markdown(finding.detail), ""])
    lines.extend(["## Scope", "", SCOPE, "",
                  "Patient identifiers are hidden by default, but labels, fold names, and any custom link remain visible. Review reports before sharing.", ""])
    if cta_url:
        lines.extend(["---", "", "[Clinical data audit service](%s)" % _cta_link(cta_url), ""])
    return "\n".join(lines)
