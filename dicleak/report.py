"""Terminal and Markdown report rendering."""

from collections import Counter

from .checks import SEVERITY_ICON


def _stats(rows):
    patients = {r["patient_id"] for r in rows}
    splits = Counter(r["split"] for r in rows)
    labels = Counter(r["label"] for r in rows)
    return {
        "rows": len(rows),
        "patients": len(patients),
        "splits": dict(sorted(splits.items())),
        "labels": dict(sorted(labels.items())),
    }


def _grade(score):
    if score >= 90:
        return "A - publishable shape"
    if score >= 75:
        return "B - minor issues"
    if score >= 60:
        return "C - fix before training"
    return "D - do not train on this"


def render_terminal(findings, score_value, rows):
    st = _stats(rows)
    lines = []
    lines.append("=" * 60)
    lines.append("dicleak dataset audit")
    lines.append("=" * 60)
    lines.append("rows: %d   patients: %d" % (st["rows"], st["patients"]))
    lines.append("splits: %s" % ", ".join(
        "%s=%d" % kv for kv in st["splits"].items()))
    lines.append("labels: %s" % ", ".join(
        "%s=%d" % kv for kv in st["labels"].items()))
    lines.append("-" * 60)
    lines.append("score: %d/100  [%s]" % (score_value, _grade(score_value)))
    lines.append("-" * 60)
    if not findings:
        lines.append("No issues found. Clean split.")
    for f in findings:
        icon = SEVERITY_ICON.get(f.severity, "[?]")
        lines.append("%s %s (-%d)" % (icon, f.title, f.deduction))
        lines.append("    %s" % f.detail)
    lines.append("=" * 60)
    return "\n".join(lines)


def render_markdown(findings, score_value, rows, cta_url=None):
    st = _stats(rows)
    lines = []
    lines.append("# dicleak dataset audit report")
    lines.append("")
    lines.append("**Score: %d/100** - %s" % (score_value, _grade(score_value)))
    lines.append("")
    lines.append("## Dataset overview")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    lines.append("| rows | %d |" % st["rows"])
    lines.append("| unique patients | %d |" % st["patients"])
    for split, n in st["splits"].items():
        lines.append("| split `%s` | %d |" % (split, n))
    for label, n in st["labels"].items():
        lines.append("| label `%s` | %d |" % (label, n))
    lines.append("")
    lines.append("## Findings (%d)" % len(findings))
    lines.append("")
    if not findings:
        lines.append("No issues found. Clean split.")
    for f in findings:
        lines.append("### %s %s (-%d)" % (
            SEVERITY_ICON.get(f.severity, "[?]"), f.title, f.deduction))
        lines.append("")
        lines.append("Severity: **%s** | Check: `%s`" % (f.severity, f.check_id))
        lines.append("")
        lines.append(f.detail)
        lines.append("")
    if cta_url:
        lines.append("---")
        lines.append(
            "Need expert eyes on your medical-imaging dataset? "
            "[Clinical data audit service](%s)" % cta_url)
    return "\n".join(lines)
