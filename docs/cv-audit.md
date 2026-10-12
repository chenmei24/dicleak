# dicleak manifest audit report

**Gate: PASS (configured checks only)**

**Heuristic score: 100/100.** Unvalidated deduction heuristic; not a clinical or statistical quality score.

Version: 0.1.1. Mode: cv. Label mode: row. Patient identifiers: hidden.

## Input accounting

| Metric | Count |
|---|---:|
| Input rows | 120 |
| Valid rows | 120 |
| Invalid rows | 0 |
| Unique patients in valid rows | 60 |

## Partition and label counts

| Partition | Label | Rows | Patients |
|---|---|---:|---:|
| fold1 | All labels | 40 | 20 |
| fold1 | 0 | 20 | 10 |
| fold1 | 1 | 20 | 10 |
| fold2 | All labels | 40 | 20 |
| fold2 | 0 | 20 | 10 |
| fold2 | 1 | 20 | 10 |
| fold3 | All labels | 40 | 20 |
| fold3 | 0 | 20 | 10 |
| fold3 | 1 | 20 | 10 |

Patient label counts are incidences: one patient may contribute to multiple labels. Patients in multiple partitions are counted in each partition.

## Findings (0)

No findings from the configured manifest checks.
## Scope

Manifest checks only. No images, DICOM metadata, content hashes, model predictions, or external validation were inspected. A passing gate is not evidence of clinical validity, de-identification, regulatory compliance, or publication readiness.

Patient identifiers are hidden by default, but labels, fold names, and any custom link remain visible. Review reports before sharing.
