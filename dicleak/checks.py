"""The seven integrity checks. Each returns a list of Finding."""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class Finding:
    check_id: str
    severity: str  # CRITICAL / HIGH / MEDIUM / LOW
    title: str
    detail: str
    deduction: int


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
SEVERITY_ICON = {"CRITICAL": "[!!]", "HIGH": "[!]", "MEDIUM": "[*]", "LOW": "[.]"}

_NAME_LIKE = re.compile(r"[A-Za-z]+[ _\-][A-Za-z]+")


def _splits_of(rows):
    return sorted({r["split"] for r in rows})


def check_leakage(rows):
    """CRITICAL: the same patient appears in more than one split."""
    by_patient = defaultdict(set)
    for r in rows:
        by_patient[r["patient_id"]].add(r["split"])
    leaked = {p: sorted(s) for p, s in by_patient.items() if len(s) > 1}
    findings = []
    for i, (patient, splits) in enumerate(sorted(leaked.items())):
        if i >= 10:
            findings.append(Finding(
                "leakage", "CRITICAL",
                "Patient-level data leakage (+%d more patients)" % (len(leaked) - 10),
                "Additional leaked patients not listed individually.",
                0,
            ))
            break
        findings.append(Finding(
            "leakage", "CRITICAL",
            "Patient '%s' appears in multiple splits: %s" % (patient, ", ".join(splits)),
            "The same patient in train and test lets the model memorize "
            "patient-specific features instead of learning the disease. "
            "This inflates reported accuracy and is a known cause of "
            "non-reproducible results and retractions in medical AI.",
            10 if i == 0 else 5,
        ))
    return findings


def check_single_class_split(rows):
    """CRITICAL: a split that contains only one label value."""
    findings = []
    by_split = defaultdict(set)
    for r in rows:
        by_split[r["split"]].add(r["label"])
    for split in sorted(by_split):
        labels = by_split[split]
        if len(labels) == 1:
            findings.append(Finding(
                "single_class_split", "CRITICAL",
                "Split '%s' contains only one class: '%s'" % (split, next(iter(labels))),
                "A split with a single class cannot train or fairly evaluate "
                "a classifier. Check your stratification or labeling pipeline.",
                15,
            ))
    return findings


def check_stratification(rows, threshold=0.20):
    """HIGH: label distribution differs strongly between splits."""
    findings = []
    by_split = defaultdict(Counter)
    for r in rows:
        by_split[r["split"]][r["label"]] += 1
    labels = {lbl for c in by_split.values() for lbl in c}
    for lbl in sorted(labels):
        shares = {}
        for split, counter in by_split.items():
            total = sum(counter.values())
            shares[split] = counter[lbl] / total if total else 0.0
        spread = max(shares.values()) - min(shares.values())
        if spread > threshold:
            detail = ", ".join(
                "%s=%.0f%%" % (s, shares[s] * 100) for s in sorted(shares))
            findings.append(Finding(
                "stratification", "HIGH",
                "Class '%s' is unevenly distributed across splits (%s)" % (lbl, detail),
                "A spread of %.0fpp between splits means the model sees a "
                "different class balance at train vs. test time, which skews "
                "metrics. Stratify by label when splitting." % (spread * 100),
                8,
            ))
    return findings


def check_split_ratios(rows):
    """MEDIUM: test split too small, or a split nearly empty."""
    findings = []
    counter = Counter(r["split"] for r in rows)
    total = sum(counter.values())
    for split in sorted(counter):
        share = counter[split] / total
        if split == "test" and share < 0.10:
            findings.append(Finding(
                "split_ratios", "MEDIUM",
                "Test split is only %.1f%% of the data (%d rows)" % (share * 100, counter[split]),
                "A tiny test set gives noisy performance estimates with wide "
                "confidence intervals. Aim for at least 10-20%.",
                6,
            ))
        elif share < 0.05:
            findings.append(Finding(
                "split_ratios", "MEDIUM",
                "Split '%s' is only %.1f%% of the data (%d rows)" % (split, share * 100, counter[split]),
                "A near-empty split contributes little and may indicate a "
                "splitting bug.",
                6,
            ))
    return findings


def check_patient_count(rows):
    """LOW/MEDIUM: too few unique patients to generalize."""
    n = len({r["patient_id"] for r in rows})
    if n < 20:
        return [Finding(
            "patient_count", "MEDIUM",
            "Only %d unique patients in the whole dataset" % n,
            "With so few patients, results are unlikely to generalize and "
            "reviewers will question external validity.",
            8,
        )]
    if n < 50:
        return [Finding(
            "patient_count", "LOW",
            "Only %d unique patients in the whole dataset" % n,
            "Small patient counts limit generalizability; consider "
            "multi-center data or external validation.",
            4,
        )]
    return []


def check_duplicates(rows):
    """MEDIUM: the same file listed twice (only when filepaths are given).

    Without filepaths, repeated (patient, split, label) rows are expected --
    one patient normally contributes multiple images -- so the check is skipped.
    """
    keyed = [r for r in rows if r.get("filepath")]
    if not keyed:
        return []
    seen = Counter(r["filepath"] for r in keyed)
    dup_files = sum(1 for c in seen.values() if c > 1)
    if dup_files:
        return [Finding(
            "duplicates", "MEDIUM",
            "%d file(s) listed more than once in the manifest" % dup_files,
            "Duplicate files overweight those samples and can hint at a "
            "broken export or merge step upstream.",
            5,
        )]
    return []


def check_phi_risk(rows):
    """HIGH: patient ids that look like real names (de-identification failure)."""
    flagged = sorted({r["patient_id"] for r in rows if _NAME_LIKE.search(r["patient_id"])})
    if not flagged:
        return []
    shown = ", ".join("'%s'" % p for p in flagged[:5])
    more = " (+%d more)" % (len(flagged) - 5) if len(flagged) > 5 else ""
    return [Finding(
        "phi_risk", "HIGH",
        "%d patient id(s) look like personal names: %s%s" % (len(flagged), shown, more),
        "IDs resembling names suggest the data was not de-identified. "
        "Sharing or publishing this dataset may violate privacy rules "
        "(HIPAA/GDPR) and journal data policies.",
        8,
    )]


ALL_CHECKS = (
    check_leakage,
    check_single_class_split,
    check_stratification,
    check_split_ratios,
    check_patient_count,
    check_duplicates,
    check_phi_risk,
)


def run_all(rows):
    findings = []
    for check in ALL_CHECKS:
        findings.extend(check(rows))
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.check_id))
    return findings


def score(findings):
    return max(0, 100 - sum(f.deduction for f in findings))
