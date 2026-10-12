"""Manifest checks with a separate failure gate and an unvalidated heuristic score."""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class Finding:
    check_id: str
    severity: str
    title: str
    detail: str
    deduction: int


@dataclass
class AuditConfig:
    split_mode: str = "holdout"
    folds: tuple = ()
    label_mode: str = "row"
    allow_single_class: bool = False
    show_ids: bool = False


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
SEVERITY_ICON = {"CRITICAL": "[!!]", "HIGH": "[!]", "MEDIUM": "[*]", "LOW": "[.]"}
_NAME_LIKE = re.compile(r"[A-Za-z]+[ _\-][A-Za-z]+")


def _safe_value(value):
    """Prevent terminal escape/control sequences when IDs are explicitly shown."""
    return "".join(char if char.isprintable() else "?" for char in value)


def check_leakage(rows, config=None):
    config = config or AuditConfig()
    by_patient = defaultdict(set)
    for row in rows:
        by_patient[row["patient_id"]].add(row["split"])
    leaked = {patient: splits for patient, splits in by_patient.items() if len(splits) > 1}
    if not leaked:
        return []
    detail = "One patient must remain in one partition (or one held-out fold assignment). Rebuild the split at patient level."
    if config.show_ids:
        shown = ["%s (%s)" % (_safe_value(patient), ", ".join(_safe_value(s) for s in sorted(splits)))
                 for patient, splits in sorted(leaked.items())[:10]]
        detail += " Identifiers: " + "; ".join(shown)
        if len(leaked) > 10:
            detail += "; %d additional identifiers omitted." % (len(leaked) - 10)
    return [Finding("leakage", "CRITICAL", "%d patient(s) occur in multiple partitions" % len(leaked), detail, 10)]


def check_partition_presence(rows, config=None):
    config = config or AuditConfig()
    expected = set(config.folds) if config.split_mode == "cv" else {"train", "test"}
    present = {row["split"] for row in rows}
    missing = sorted(expected - present)
    if not missing:
        return []
    return [Finding("partition_presence", "CRITICAL", "Required partitions are missing: %s" % ", ".join(missing),
                    "Holdout requires train and test; validation is optional. CV requires every explicitly configured fold to contain valid rows.", 15)]


def check_single_class_split(rows, config=None):
    config = config or AuditConfig()
    if config.allow_single_class:
        return []
    labels = defaultdict(set)
    for row in rows:
        labels[row["split"]].add(row["label"])
    return [Finding("single_class_split", "CRITICAL", "Partition '%s' contains only one class" % split,
                    "Under the default classification checks, each partition must contain at least two classes. For an intentional single-class task, use --allow-single-class and assess task-specific evaluation separately.", 15)
            for split in sorted(labels) if len(labels[split]) == 1]


def check_patient_labels(rows, config=None):
    config = config or AuditConfig()
    if config.label_mode != "patient":
        return []
    by_patient = defaultdict(set)
    for row in rows:
        by_patient[row["patient_id"]].add(row["label"])
    conflicting = sum(len(labels) > 1 for labels in by_patient.values())
    if not conflicting:
        return []
    return [Finding("patient_labels", "CRITICAL", "%d patient(s) have conflicting labels" % conflicting,
                    "--label-mode patient requires a single label per patient. Use the default row mode for legitimate lesion-level, longitudinal, or multiple-label observations; it does not validate a multi-label encoding scheme.", 10)]


def check_stratification(rows, threshold=0.20):
    by_split = defaultdict(Counter)
    patient_labels = defaultdict(lambda: defaultdict(set))
    for row in rows:
        by_split[row["split"]][row["label"]] += 1
        patient_labels[row["split"]][row["patient_id"]].add(row["label"])
    if len(by_split) < 2:
        return []
    labels = {label for counts in by_split.values() for label in counts}
    findings = []
    for label in sorted(labels):
        row_shares = {split: counts[label] / sum(counts.values()) for split, counts in by_split.items()}
        patient_shares = {split: sum(label in labs for labs in people.values()) / len(people)
                          for split, people in patient_labels.items()}
        row_spread = max(row_shares.values()) - min(row_shares.values())
        patient_spread = max(patient_shares.values()) - min(patient_shares.values())
        if max(row_spread, patient_spread) > threshold:
            detail = "; ".join("%s: rows %.1f%%, patients %.1f%%" % (split, row_shares[split] * 100, patient_shares[split] * 100)
                               for split in sorted(by_split))
            findings.append(Finding("stratification", "HIGH", "Class '%s' differs between partitions" % _safe_value(label),
                                    detail + ". Patient proportions count patients with this label at least once; multi-label proportions can sum above 100%. A >20 percentage-point spread is a review heuristic, not proof of bias.", 8))
    return findings


def check_split_ratios(rows, config=None):
    config = config or AuditConfig()
    if not rows:
        return []
    row_counts = Counter(row["split"] for row in rows)
    patient_counts = {split: len({row["patient_id"] for row in rows if row["split"] == split}) for split in row_counts}
    total_patients = len({row["patient_id"] for row in rows})
    findings = []
    for split in sorted(row_counts):
        row_share = row_counts[split] / len(rows)
        patient_share = patient_counts[split] / total_patients
        threshold = 0.10 if config.split_mode == "holdout" and split == "test" else 0.05
        if min(row_share, patient_share) < threshold:
            findings.append(Finding("split_ratios", "MEDIUM", "Partition '%s' has a small sample share" % _safe_value(split),
                                    "%d rows (%.1f%%); %d patients (%.1f%% of all unique patients). The %.0f%% threshold is a review heuristic; choose evaluation size using the study design and precision requirements. Leaked patients can make patient shares sum above 100%%." %
                                    (row_counts[split], row_share * 100, patient_counts[split], patient_share * 100, threshold * 100), 6))
    return findings


def check_patient_count(rows):
    n = len({row["patient_id"] for row in rows})
    if n < 20:
        severity, deduction = "MEDIUM", 8
    elif n < 50:
        severity, deduction = "LOW", 4
    else:
        return []
    return [Finding("patient_count", severity, "Only %d unique patients in valid rows" % n,
                    "This is a small-sample review flag. Generalizability and statistical power depend on the task and design, not this count threshold alone.", deduction)]


def check_duplicates(rows):
    keyed = [row for row in rows if row.get("filepath")]
    counts = Counter(row["filepath"] for row in keyed)
    duplicate_paths = sum(n > 1 for n in counts.values())
    findings = []
    if duplicate_paths:
        findings.append(Finding("duplicates", "MEDIUM", "%d filepath value(s) repeat in the manifest" % duplicate_paths,
                                "This compares exact path strings only. Repeated paths may overweight observations, but no files, hashes, DICOM headers, or image pixels are inspected; equal or different paths do not establish content identity.", 5))
    by_path = defaultdict(set)
    for row in keyed:
        by_path[row["filepath"]].add(row["split"])
    cross_split = sum(len(splits) > 1 for splits in by_path.values())
    if cross_split:
        findings.append(Finding("cross_partition_filepath", "CRITICAL", "%d filepath value(s) occur in multiple partitions" % cross_split,
                                "A manifest claims the same path across partitions. Resolve the assignment or path ambiguity before use. This is a manifest inconsistency, not a pixel-level duplicate-image finding.", 10))
    return findings


def check_phi_risk(rows, config=None):
    config = config or AuditConfig()
    flagged = sorted({row["patient_id"] for row in rows if _NAME_LIKE.search(row["patient_id"])})
    if not flagged:
        return []
    detail = "A limited Latin-character name-pattern heuristic matched these identifiers. False positives and false negatives are expected. This check does not establish de-identification or regulatory compliance. Review source data privately."
    if config.show_ids:
        detail += " Identifiers (up to five): " + ", ".join(_safe_value(value) for value in flagged[:5])
    return [Finding("phi_risk", "HIGH", "%d patient identifier(s) match a name-like pattern" % len(flagged), detail, 8)]


ALL_CHECKS = (check_leakage, check_single_class_split, check_stratification,
              check_split_ratios, check_patient_count, check_duplicates, check_phi_risk)


def run_all(rows, config=None, diagnostics=()):
    config = config or AuditConfig()
    findings = []
    for diagnostic in diagnostics:
        findings.append(Finding("input_validation", "CRITICAL", "Input line %d: %s" % (diagnostic.line, diagnostic.message),
                                "Invalid input rows are excluded from distribution checks but always fail the audit gate. Correct the manifest and rerun.", 5))
    if not rows:
        findings.append(Finding("input_validation", "CRITICAL", "No valid observations remain", "Correct all invalid input rows before interpreting dataset statistics.", 15))
    findings.extend(check_partition_presence(rows, config))
    findings.extend(check_leakage(rows, config))
    findings.extend(check_single_class_split(rows, config))
    findings.extend(check_patient_labels(rows, config))
    findings.extend(check_stratification(rows))
    findings.extend(check_split_ratios(rows, config))
    findings.extend(check_patient_count(rows))
    findings.extend(check_duplicates(rows))
    findings.extend(check_phi_risk(rows, config))
    return sorted(findings, key=lambda finding: (SEVERITY_ORDER[finding.severity], finding.check_id))


def score(findings):
    """Legacy deduction heuristic; not a validated quality or readiness metric."""
    return max(0, 100 - sum(finding.deduction for finding in findings))


def gate_passes(findings):
    return not any(finding.severity == "CRITICAL" for finding in findings) and score(findings) >= 60
