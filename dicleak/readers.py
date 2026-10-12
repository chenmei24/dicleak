"""CSV manifest validation; invalid rows are counted, never silently accepted."""

import csv
from dataclasses import dataclass, field

COLUMN_ALIASES = {
    "patient_id": "patient_id", "patientid": "patient_id", "patient": "patient_id",
    "subject_id": "patient_id", "subjectid": "patient_id", "subject": "patient_id", "pid": "patient_id",
    "split": "split", "subset": "split", "fold": "split", "partition": "split", "set": "split", "phase": "split",
    "label": "label", "class": "label", "target": "label", "diagnosis": "label", "annotation": "label",
    "filepath": "filepath", "file_path": "filepath", "path": "filepath", "filename": "filepath", "file": "filepath",
}
SPLIT_ALIASES = {
    "train": "train", "training": "train", "trn": "train",
    "val": "val", "valid": "val", "validation": "val", "dev": "val",
    "test": "test", "testing": "test", "tst": "test",
}
REQUIRED = ("patient_id", "split", "label")


class ManifestError(ValueError):
    """The file cannot be interpreted as a manifest."""


@dataclass
class InputDiagnostic:
    line: int
    code: str
    message: str


@dataclass
class Manifest:
    rows: list
    input_rows: int
    invalid_rows: int
    diagnostics: list = field(default_factory=list)


def _normalize_header(name):
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def read_manifest(path, split_mode="holdout", folds=()):
    """Read validated rows and value-free diagnostics with original CSV line numbers.

    CV manifests contain one held-out fold assignment per observation. Fold names
    are case-sensitive and must be supplied explicitly; holdout aliases are not
    applied to CV fold names.
    """
    if split_mode not in ("holdout", "cv"):
        raise ManifestError("split mode must be holdout or cv")
    if split_mode == "cv" and (len(folds) < 2 or len(set(folds)) != len(folds) or any(not f for f in folds)):
        raise ManifestError("CV requires at least two distinct nonempty fold names")
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh, strict=True)
            try:
                headers = next(reader)
            except StopIteration:
                raise ManifestError("empty file: no header row") from None
            if not headers:
                raise ManifestError("empty header row")
            normalized = [_normalize_header(name) for name in headers]
            if any(not name for name in normalized):
                raise ManifestError("empty column name")
            if len(set(normalized)) != len(normalized):
                raise ManifestError("duplicate normalized column names")
            mapping = {}
            for index, name in enumerate(normalized):
                canonical = COLUMN_ALIASES.get(name)
                if canonical:
                    if canonical in mapping.values():
                        raise ManifestError("multiple columns map to '%s'; keep one alias" % canonical)
                    mapping[index] = canonical
            missing = [name for name in REQUIRED if name not in mapping.values()]
            if missing:
                raise ManifestError("missing required columns: %s" % ", ".join(missing))
            rows, diagnostics = [], []
            input_rows = invalid_rows = 0
            for cells in reader:
                input_rows += 1
                line = reader.line_num
                problems = []
                if len(cells) != len(headers):
                    problems.append(InputDiagnostic(line, "column_count", "column count differs from header"))
                else:
                    row = {canonical: cells[index].strip() for index, canonical in mapping.items()}
                    for name in REQUIRED:
                        if not row[name]:
                            problems.append(InputDiagnostic(line, "missing_value", "empty required field: %s" % name))
                    if row["split"]:
                        if split_mode == "holdout":
                            row["split"] = SPLIT_ALIASES.get(row["split"].lower(), row["split"].lower())
                            allowed = ("train", "val", "test")
                        else:
                            allowed = folds
                        if row["split"] not in allowed:
                            problems.append(InputDiagnostic(line, "unknown_split", "unrecognized split; use the configured split names"))
                if problems:
                    invalid_rows += 1
                    diagnostics.extend(problems)
                else:
                    rows.append(row)
            if not input_rows:
                raise ManifestError("manifest contains no data rows")
            return Manifest(rows, input_rows, invalid_rows, diagnostics)
    except (OSError, UnicodeError, csv.Error) as exc:
        # Do not echo file contents or identifiers in input errors.
        raise ManifestError("cannot read manifest (%s)" % type(exc).__name__) from exc


def load_manifest(path):
    """Compatibility wrapper returning validated rows and diagnostics as strings."""
    try:
        manifest = read_manifest(path)
    except ManifestError as exc:
        raise SystemExit("dicleak: %s" % exc) from exc
    if manifest.diagnostics:
        raise SystemExit("dicleak: invalid input: " + "; ".join(
            "line %d: %s" % (d.line, d.message) for d in manifest.diagnostics))
    return manifest.rows, []
