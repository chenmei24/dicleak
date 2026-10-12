"""CSV manifest loading and column normalization."""

import csv
import sys

# accepted header spellings -> canonical field name
COLUMN_ALIASES = {
    "patient_id": "patient_id",
    "patientid": "patient_id",
    "patient": "patient_id",
    "subject_id": "patient_id",
    "subjectid": "patient_id",
    "subject": "patient_id",
    "pid": "patient_id",
    "split": "split",
    "subset": "split",
    "fold": "split",
    "partition": "split",
    "set": "split",
    "phase": "split",
    "label": "label",
    "class": "label",
    "target": "label",
    "diagnosis": "label",
    "annotation": "label",
    "filepath": "filepath",
    "file_path": "filepath",
    "path": "filepath",
    "filename": "filepath",
    "file": "filepath",
}

SPLIT_ALIASES = {
    "train": "train",
    "training": "train",
    "trn": "train",
    "val": "val",
    "valid": "val",
    "validation": "val",
    "dev": "val",
    "test": "test",
    "testing": "test",
    "tst": "test",
}

REQUIRED = ("patient_id", "split", "label")


def _normalize_header(name):
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def load_manifest(path):
    """Load a CSV manifest, return (rows, warnings).

    rows: list of dicts with keys patient_id / split / label / filepath.
    Raises SystemExit with a message on fatal problems.
    """
    try:
        fh = open(path, newline="", encoding="utf-8-sig")
    except OSError as exc:
        sys.exit("dicleak: cannot open %s: %s" % (path, exc))
    with fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            sys.exit("dicleak: %s looks empty (no header row)" % path)
        mapping = {}
        for raw in reader.fieldnames:
            key = _normalize_header(raw)
            if key in COLUMN_ALIASES:
                mapping[raw] = COLUMN_ALIASES[key]
        missing = [c for c in REQUIRED if c not in mapping.values()]
        if missing:
            sys.exit(
                "dicleak: %s is missing required column(s): %s "
                "(need patient id, split and label columns)" % (path, ", ".join(missing))
            )
        rows = []
        warnings = []
        for lineno, raw_row in enumerate(reader, start=2):
            row = {}
            for raw_key, value in raw_row.items():
                if raw_key in mapping:
                    row[mapping[raw_key]] = (value or "").strip()
            if not row.get("patient_id"):
                warnings.append("line %d: empty patient id, skipped" % lineno)
                continue
            split_raw = row.get("split", "").lower()
            row["split"] = SPLIT_ALIASES.get(split_raw, split_raw)
            rows.append(row)
    if not rows:
        sys.exit("dicleak: no usable data rows in %s" % path)
    return rows, warnings
