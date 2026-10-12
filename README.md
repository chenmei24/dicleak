# dicleak

Dataset integrity auditor for medical-imaging AI. Point it at a dataset manifest
CSV and it catches the flaws that sink models and papers **before** you train:
patient-level data leakage across splits, single-class splits, broken
stratification, tiny test sets, duplicate files, un-deidentified IDs.

医学影像 AI 数据集完整性审计工具。对 manifest CSV 跑一遍，在训练**之前**
揪出致命缺陷：病人级数据泄露、单类别数据划分、分布失衡、测试集过小、
文件重复、未脱敏的 ID。

## Install

```bash
pip install dicleak
```

## Usage

```bash
dicleak splits.csv
dicleak splits.csv --report audit.md
dicleak splits.csv --report audit.md --cta "https://your-service.example/audit"
```

The manifest CSV needs three columns (headers are flexible):

| concept | accepted headers |
|---|---|
| patient id | `patient_id`, `patientid`, `patient`, `subject_id`, `subject`, `pid` |
| split | `split`, `subset`, `fold`, `partition`, `set` (`train`/`val`/`test` and common aliases) |
| label | `label`, `class`, `target`, `diagnosis`, `annotation` |
| file path (optional) | `filepath`, `file_path`, `path`, `filename` |

Exit code is `0` when the score is 60+, `1` otherwise — handy for CI gates.

## The 7 checks

| # | check | severity |
|---|---|---|
| 1 | patient-level leakage across splits | CRITICAL |
| 2 | split containing a single class | CRITICAL |
| 3 | label distribution drift between splits | HIGH |
| 4 | test split < 10% (or any split < 5%) | MEDIUM |
| 5 | duplicate files in the manifest | MEDIUM |
| 6 | patient IDs that look like real names | HIGH |
| 7 | too few unique patients | LOW/MEDIUM |

## Why this exists

A disturbing share of medical-AI papers report inflated accuracy because the
same patient ended up in both the training and test sets. Reviewers now check
for this. `dicleak` makes the check a one-liner.

## Sample

`samples/flawed_splits.csv` is a deliberately broken manifest (leaked patients,
single-class val split, tiny test set, name-like IDs...). It scores 26/100:

```bash
dicleak samples/flawed_splits.csv
```

## License

MIT
