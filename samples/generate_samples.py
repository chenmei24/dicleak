"""Regenerate public examples using synthetic identifiers and manifest-only paths."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADERS = ("patient_id", "split", "label", "filepath")


def write(name, rows):
    with (ROOT / name).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(HEADERS)
        writer.writerows(rows)


clean = []
for number in range(1, 101):
    split = "train" if number <= 60 else "val" if number <= 80 else "test"
    for image in (1, 2):
        clean.append(("SYN%04d" % number, split, str(number % 2), "synthetic/SYN%04d_%d.dcm" % (number, image)))
write("clean_splits.csv", clean)
flawed = clean + [
    ("SYN0001", "test", "1", "synthetic/leaked_observation.dcm"),
    clean[0],
    ("Synthetic Name", "train", "1", "synthetic/name_pattern.dcm"),
    ("", "test", "1", "synthetic/missing_patient.dcm"),
    ("SYN9002", "typo", "0", "synthetic/unknown_split.dcm"),
    ("SYN9003", "test", "", "synthetic/missing_label.dcm"),
]
write("flawed_splits.csv", flawed)
cv = []
for number in range(1, 61):
    fold = "fold%d" % ((number - 1) // 20 + 1)
    for image in (1, 2):
        cv.append(("SYN%04d" % number, fold, str(number % 2), "synthetic/SYN%04d_%d.dcm" % (number, image)))
write("cv_folds.csv", cv)
