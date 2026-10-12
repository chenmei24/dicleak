# dicleak manifest audit report

**Gate: PASS (configured checks only)**

**Heuristic score: 100/100.** Unvalidated deduction heuristic; not a clinical or statistical quality score.

Version: 0.1.1. Mode: holdout. Label mode: row. Patient identifiers: hidden.

## Input accounting

| Metric | Count |
|---|---:|
| Input rows | 200 |
| Valid rows | 200 |
| Invalid rows | 0 |
| Unique patients in valid rows | 100 |

## Partition and label counts

| Partition | Label | Rows | Patients |
|---|---|---:|---:|
| test | All labels | 40 | 20 |
| test | 0 | 20 | 10 |
| test | 1 | 20 | 10 |
| train | All labels | 120 | 60 |
| train | 0 | 60 | 30 |
| train | 1 | 60 | 30 |
| val | All labels | 40 | 20 |
| val | 0 | 20 | 10 |
| val | 1 | 20 | 10 |

Patient label counts are incidences: one patient may contribute to multiple labels. Patients in multiple partitions are counted in each partition.

## Findings (0)

No findings from the configured manifest checks.
## Scope

Manifest checks only. No images, DICOM metadata, content hashes, model predictions, or external validation were inspected. A passing gate is not evidence of clinical validity, de-identification, regulatory compliance, or publication readiness.

Patient identifiers are hidden by default, but labels, fold names, and any custom link remain visible. Review reports before sharing.
