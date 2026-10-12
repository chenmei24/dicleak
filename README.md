# dicleak

**Catch patient overlap between training and evaluation data before you train.**

A dependency-free Python CLI that audits a medical-imaging **CSV manifest** and
writes readable Markdown or machine-readable JSON reports. Designed for researchers
who split multiple images, examinations, or lesions from the same patient.

[中文说明](https://github.com/chenmei24/dicleak/blob/master/README.zh-CN.md) · [Passing example report](https://github.com/chenmei24/dicleak/blob/master/docs/clean-audit.md) ·
[Failing example report](https://github.com/chenmei24/dicleak/blob/master/docs/flawed-audit.md) · [Report preview](https://github.com/chenmei24/dicleak/blob/master/docs/audit-preview.svg)

![Synthetic manifest audit: passing and failing examples](https://raw.githubusercontent.com/chenmei24/dicleak/master/docs/audit-preview.png)

## Quick start

Install the released package:

```bash
python -m pip install dicleak
```

To use the features documented here from this source checkout:

```bash
git clone https://github.com/chenmei24/dicleak.git
cd dicleak
python -m pip install .
dicleak samples/clean_splits.csv --report audit.md --json audit.json
```

The checked-in source is version **0.1.1**. A package installed from PyPI may be an
older release; check `dicleak --version` until 0.1.1 is published.

The clean synthetic sample produces:

```text
Gate: PASS (configured checks only)
Heuristic score: 100/100. Unvalidated deduction heuristic; not a clinical or statistical quality score.
Input rows: 200; valid rows: 200; invalid rows: 0; unique patients: 100
```

Try the deliberately flawed sample:

```bash
dicleak samples/flawed_splits.csv --report flawed-audit.md --json flawed-audit.json
```

It reports **FAIL** and exits with code **1**, even though its heuristic score is
62/100. The sample contains patient overlap, repeated filepath strings, a synthetic
name-pattern identifier, and three invalid rows. All example data are synthetic;
no image files or patient data are included. See the [generated report](https://github.com/chenmei24/dicleak/blob/master/docs/flawed-audit.md).

## Manifest format

```csv
patient_id,split,label,filepath
SYN001,train,0,synthetic/image_001.dcm
SYN002,train,1,synthetic/image_002.dcm
SYN003,test,0,synthetic/image_003.dcm
SYN004,test,1,synthetic/image_004.dcm
```

| Field | Accepted headers | Meaning |
|---|---|---|
| Patient | `patient_id`, `patientid`, `patient`, `subject_id`, `subjectid`, `subject`, `pid` | Nonempty pseudonymous patient key |
| Partition | `split`, `subset`, `fold`, `partition`, `set`, `phase` | Holdout partition or explicitly configured CV fold |
| Label | `label`, `class`, `target`, `diagnosis`, `annotation` | Nonempty observation label |
| Filepath (optional) | `filepath`, `file_path`, `path`, `filename`, `file` | Exact string comparison only; files are not opened |

Headers are case-insensitive; spaces and hyphens become underscores. A UTF-8 BOM
is accepted. **Duplicate normalized headers and two aliases for the same field are
rejected**, so a second label or patient column cannot silently overwrite the first.
Each record must have the same column count as the header. Invalid records remain
in input accounting, are excluded from distribution checks, and fail the gate;
reports include physical CSV line numbers (the ending line for a multiline record).

Keep the same pseudonymous patient key across examinations. Different keys for the
same person cannot be detected. Whitespace around values is stripped; label values
and patient keys are otherwise case-sensitive.

## Holdout and cross-validation

The default `--split-mode holdout` requires **train and test**, with optional val.
Common aliases (`training`, `trn`, `validation`, `valid`, `dev`, `testing`, `tst`)
are normalized. Blank or unrecognized partition names fail input validation.
A training-only manifest does not pass.

For CV, give each observation its **one held-out fold assignment**, then explicitly
list all fold names (case-sensitive):

```bash
dicleak samples/cv_folds.csv --split-mode cv --folds fold1 fold2 fold3 --report cv-audit.md
```

Each configured fold must be present, and a patient must belong to exactly one fold.
A `fold` header alone does not switch modes. This format is **not** a long table of
train/validation memberships repeated for each CV round; legitimate reuse across
rounds would fail this assignment check. Nested or repeated CV and independent
external test sets require separate manifests and design-specific review.

## Labels and intentional single-class tasks

By default, `--label-mode row` permits different observation labels within a patient
(e.g. lesions or time points). Label counts include both rows and **patient label
incidences**: a patient with two different labels is counted once for each label,
so patient label proportions can exceed 100% in total. Composite labels are treated
as opaque values; this CLI does not parse or validate multi-label encodings.

Use strict patient-level labels when appropriate:

```bash
dicleak samples/clean_splits.csv --label-mode patient
```

By default, a single-class partition fails the classification checks. For an
intentional one-class, segmentation, or other task where this check is unsuitable:

```bash
dicleak samples/clean_splits.csv --allow-single-class
```

This disables only the single-class failure; all other checks remain active.
It does not assess the adequacy of task-specific evaluation.

## Checks and exit codes

| Check | Severity | Interpretation |
|---|---|---|
| Missing/invalid required values or row shape | CRITICAL | Correct the manifest; invalid rows are counted |
| Required partitions missing | CRITICAL | Train + test, or all configured CV folds, must be present |
| Patient assigned to multiple partitions | CRITICAL | Patient-level holdout or fold assignment conflict |
| Same filepath string across partitions | CRITICAL | Manifest path assignment conflict; content identity unverified |
| Single-class partition | CRITICAL | Classification-mode check; explicit opt-out available |
| Conflicting patient labels | CRITICAL | Enabled only with `--label-mode patient` |
| Label share differs by >20 percentage points | HIGH | Row and patient incidence review heuristic |
| Name-like patient identifier | HIGH | Limited Latin-pattern heuristic, not de-identification verification |
| Small partition share | MEDIUM | <10% for holdout test; <5% otherwise, at row or patient level |
| Repeated filepath string | MEDIUM | Exact strings only; no image comparison |
| Small patient count | LOW / MEDIUM | <50 / <20 patients; design-dependent review flag |

| Exit code | Meaning |
|---|---|
| `0` | No CRITICAL findings **and** heuristic score ≥60 |
| `1` | Any CRITICAL finding, or heuristic score <60 |
| `2` | Usage error, unreadable/structurally invalid file, or report write failure |

**CRITICAL always fails, including a 90/100 leakage result.** The retained score is
an unvalidated deduction heuristic for sorting review effort. It does not indicate
publication readiness, model validity, statistical power, or regulatory compliance.

A CI command can simply rely on the exit code:

```bash
dicleak splits.csv --json audit.json
```

## Reports and privacy

```bash
dicleak splits.csv --report audit.md --json audit.json
dicleak splits.csv --report private-audit.md --show-ids
```

Patient identifiers are hidden by default in terminal, Markdown, and JSON findings.
`--show-ids` includes a limited number of identifiers in findings; use it only for
private investigation. **This is not a de-identification tool:** labels, configured
fold names, and optional links remain visible. Review outputs before sharing.
Markdown text is escaped, and terminal control characters are replaced.

Input, Markdown output, and JSON output paths must be distinct, including existing
symlinks and hardlinks. Reports are replaced atomically after rendering. An existing
output report is overwritten intentionally; the input manifest is never an allowed
report destination.

The original optional footer remains available:

```bash
dicleak splits.csv --report audit.md --cta "https://your-service.example/audit"
```

## Scope

The tool reads only the manifest. It does **not** inspect DICOM metadata, image
pixels, content hashes, model predictions, hidden aliases for one patient, scanner/site
confounding, or external validation. Different paths can refer to identical images;
repeated paths can be legitimate repeat observations. Neither condition proves image
content duplication. Threshold flags require study-specific interpretation.

## Development and contributions

Python 3.9+; runtime dependencies: none. CI covers Linux and Windows on Python
3.9, 3.11, and 3.13.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
python samples/generate_samples.py
```

See [CONTRIBUTING.md](https://github.com/chenmei24/dicleak/blob/master/CONTRIBUTING.md), [CHANGELOG.md](https://github.com/chenmei24/dicleak/blob/master/CHANGELOG.md), and the
[issue tracker](https://github.com/chenmei24/dicleak/issues). Bug reports with a small
synthetic manifest are especially useful. Please never attach patient data.

MIT licensed. If this catches a real workflow issue, an anonymized description of
the issue and your split design can help improve the checks.

## Related tools / 相关工具

- [Manuscript rule checks](https://github.com/chenmei24/manulint)
- [Traceable clinical CSV QA](https://github.com/chenmei24/clinical-imaging-data-qa-demo)

[Launch tutorials and share images / 推广教程与展示图](docs/launch/README.md)
