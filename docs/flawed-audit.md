# dicleak manifest audit report

**Gate: FAIL**

**Heuristic score: 62/100.** Unvalidated deduction heuristic; not a clinical or statistical quality score.

Version: 0.1.1. Mode: holdout. Label mode: row. Patient identifiers: hidden.

## Input accounting

| Metric | Count |
|---|---:|
| Input rows | 206 |
| Valid rows | 203 |
| Invalid rows | 3 |
| Unique patients in valid rows | 101 |

## Partition and label counts

| Partition | Label | Rows | Patients |
|---|---|---:|---:|
| test | All labels | 41 | 21 |
| test | 0 | 20 | 10 |
| test | 1 | 21 | 11 |
| train | All labels | 122 | 61 |
| train | 0 | 60 | 30 |
| train | 1 | 62 | 31 |
| val | All labels | 40 | 20 |
| val | 0 | 20 | 10 |
| val | 1 | 20 | 10 |

Patient label counts are incidences: one patient may contribute to multiple labels. Patients in multiple partitions are counted in each partition.

## Findings (6)

### CRITICAL: Input line 205: empty required field: patient\_id

Check: input_validation. Heuristic deduction: 5.

Invalid input rows are excluded from distribution checks but always fail the audit gate\. Correct the manifest and rerun\.

### CRITICAL: Input line 206: unrecognized split; use the configured split names

Check: input_validation. Heuristic deduction: 5.

Invalid input rows are excluded from distribution checks but always fail the audit gate\. Correct the manifest and rerun\.

### CRITICAL: Input line 207: empty required field: label

Check: input_validation. Heuristic deduction: 5.

Invalid input rows are excluded from distribution checks but always fail the audit gate\. Correct the manifest and rerun\.

### CRITICAL: 1 patient\(s\) occur in multiple partitions

Check: leakage. Heuristic deduction: 10.

One patient must remain in one partition \(or one held\-out fold assignment\)\. Rebuild the split at patient level\.

### HIGH: 1 patient identifier\(s\) match a name\-like pattern

Check: phi_risk. Heuristic deduction: 8.

A limited Latin\-character name\-pattern heuristic matched these identifiers\. False positives and false negatives are expected\. This check does not establish de\-identification or regulatory compliance\. Review source data privately\.

### MEDIUM: 1 filepath value\(s\) repeat in the manifest

Check: duplicates. Heuristic deduction: 5.

This compares exact path strings only\. Repeated paths may overweight observations, but no files, hashes, DICOM headers, or image pixels are inspected; equal or different paths do not establish content identity\.

## Scope

Manifest checks only. No images, DICOM metadata, content hashes, model predictions, or external validation were inspected. A passing gate is not evidence of clinical validity, de-identification, regulatory compliance, or publication readiness.

Patient identifiers are hidden by default, but labels, fold names, and any custom link remain visible. Review reports before sharing.
