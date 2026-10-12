# dicleak launch kit / 发布材料

Prepared for the next checked release. These are publication drafts, not evidence that a post has been sent. Verify the current release and commands before copying. All examples are synthetic.

## Positioning / 一句话定位

**EN:** Audit a medical-imaging dataset CSV for patient overlap and split problems before training.

**中文：** 在训练前检查医学影像数据集 CSV：发现跨划分的患者重叠及数据划分问题。

Primary audience: medical-imaging ML researchers who already have patient IDs and train/validation/test membership in a CSV. This tool checks the supplied manifest. It does not scan DICOM headers, identify patients from images, prove anonymization, or establish model validity.

## Reproducible tutorial / 可复现教程

### Same patient in train and test: a small manifest audit

From a clone of this repository, install the checked source release and run:

```bash
python -m pip install -e .
dicleak docs/launch/synthetic_leakage.csv --report synthetic-audit.md --show-ids
```

The committed [synthetic manifest](synthetic_leakage.csv) contains **101 rows and 100 distinct patient IDs**. There are 60 train rows, 20 validation rows, and 21 test rows. Each split contains `class_0` and `class_1`. The intentional defect is `SYN-001`, present in both train and test; its two file-path strings differ.

Inspect the `CRITICAL` patient-overlap finding and the report's evidence. `--show-ids` is used only because this sample is synthetic; identifiers are hidden by default, and real identifiers require careful review before sharing. With the corrected gate, a critical finding makes the command fail even if the heuristic score is otherwise high. A nonzero exit is the expected result for this deliberately flawed example, not an installation failure.

To see the exit code, run the appropriate command immediately after the audit:

```bash
# Bash / Zsh
printf '%s\n' "$?"
```

```powershell
# PowerShell
$LASTEXITCODE
```

The `.nii.gz` paths are illustrative strings. No actual image files are included or scanned. To try a disjoint version, create a copy of the CSV and remove the final repeated-patient row. Keep the flawed sample intact. Passing configured checks does not prove the dataset or the resulting research is valid.

**中文解读：** 这个合成示例有 101 行、100 个不同患者编号，训练集 60 行、验证集 20 行、测试集 21 行。三个划分均有两类标签。`SYN-001` 同时进入训练集与测试集，这是故意加入的患者重叠。修复后的门控应使该 `CRITICAL` 问题返回非零退出码；即使评分较高，也应判为审计失败。路径只是示例字符串，不代表扫描了影像。复制 CSV 并删除最后一行，可比较患者互不重叠时的报告。

### How to interpret a finding / 如何处理发现

1. Confirm that the patient identifier really represents one patient, not a slice, scan, or visit.
2. Inspect the source split-generation procedure; investigate before changing any membership.
3. If independence is intended, rebuild splits by patient and rerun the audit.
4. For cross-validation, `--split-mode cv --folds fold_0 fold_1` expects one held-out fold assignment per patient, not an expanded table repeating each patient across every fold's train/test roles. Audit an individual fold as a holdout manifest or create the expected assignment mapping. Repeated measures can share a patient ID within the same partition. Document the design; do not describe a split audit as proof of independent validation.

## Copy-ready launch posts / 可复制发布文案

### Chinese tutorial post

**标题：同一患者进入训练集和测试集：用 CSV 在训练前检查**

做医学影像机器学习时，按图像随机划分可能让同一患者出现在训练集和测试集。我做了一个本地命令行工具 dicleak：读取包含患者编号、划分和标签的 CSV，检查患者重叠及其他划分问题，并输出可复核的 Markdown 报告。

仓库中有一个 100 名合成患者的示例：故意让 `SYN-001` 出现在 train 和 test。可以直接运行并查看 `CRITICAL` 发现；修复后的门控会使这类问题审计失败。

它只检查提供的 manifest，不读取 DICOM，不保证发现所有数据问题，也不能证明模型有效。欢迎试用合成示例，反馈不同 CSV 表头、划分设计或误报情况。请勿在公开 Issue 上传患者信息。

代码与教程：https://github.com/chenmei24/dicleak

### English technical post

**Title: Check patient overlap before training a medical-imaging model**

I built **dicleak**, a local CLI that audits a medical-imaging dataset manifest for patient overlap and split problems. Input: a CSV with patient ID, split, and label. Output: findings with inspectable evidence and an optional Markdown report.

The repository includes a synthetic example with 100 patient IDs and one intentional train/test overlap. A critical finding fails the corrected audit gate, even when the heuristic score would otherwise look reassuring.

Scope: manifest checks only. It does not scan DICOM files, prove de-identification, or validate a model. I would welcome feedback on real-world CSV conventions and false positives using minimal synthetic reproductions.

Code and reproducible walkthrough: https://github.com/chenmei24/dicleak

### Short release announcement

**中文：** dicleak 更新：患者跨划分重叠等 `CRITICAL` 问题会使审计失败。新增输入校验和回归测试；用仓库中的合成 CSV 即可复现。医学影像 CSV manifest 检查，非 DICOM 扫描器。

**EN:** dicleak update: critical split findings fail the audit gate. Includes input validation and regression coverage. Try the committed synthetic CSV. A manifest audit, not a DICOM scanner.

Confirm each release claim against the actual release notes before posting. No package version or test count is claimed here.

## Assets / 展示图

- [Vector social card](../../assets/launch/social-preview.svg), 1280 × 640.
- [PNG social card](../../assets/launch/social-preview.png), rendered from the SVG.
- The card is an explanatory illustration, not a screenshot of a real dataset or a claimed validation result.

Use the PNG for the repository's social preview and posts. Do not add confidential examples to a public preview.

## 30-day execution calendar / 30天执行日历

Day 1 means the first day the corrected release is public. Share one useful walkthrough at a time; choose communities that permit relevant project posts and follow their rules. Posting itself is not performed by this kit.

| Days | Action / 行动 | Evidence to record / 留存证据 |
| --- | --- | --- |
| 1–2 | Verify clean installation, the synthetic failure, and report links; publish a tagged release | Release URL, command, observed result |
| 3–4 | Set repository description/topics/social image; pin the project on the profile | Repository page and working image |
| 5–7 | Publish one Chinese walkthrough with the synthetic CSV and actual report excerpt | Post URL, substantive questions |
| 8–10 | Publish the English walkthrough to one relevant, permitted research/developer venue | Post URL, referrer where available |
| 11–14 | Respond to questions; turn reproducible false positives into tests and documented limits | Issue/PR links, weekly traffic snapshot |
| 15–17 | Add a practical guide to patient versus row counts and grouping by patient | Guide URL, review by one target user if available |
| 18–21 | Compare the original and disjoint synthetic manifests in a short demo | Actual outputs; no accuracy or patient-data claims |
| 22–24 | Ask existing interested users which manifest convention blocks adoption; implement one supported change | Reproduction, test, release note |
| 25–27 | Cross-link the clinical QA portfolio where it answers an actual need; avoid repetitive promotion | Relevant discussion or documentation link |
| 28–30 | Review channel performance and feedback; choose the next improvement based on evidence | 30-day review with weekly snapshots and next decision |

## Measurement / 衡量方式

| Metric | How to measure | Decision it supports |
| --- | --- | --- |
| Visitors and unique visitors | Save dated GitHub Traffic snapshots weekly; retain each period's counts separately | Which posts bring readers |
| Clones and unique cloners | Record the same traffic windows as visitors | Whether interest reaches source-code exploration |
| Substantive issues | Count unique issues with a concrete bug, supported workflow request, or synthetic reproduction | Which compatibility work is useful |
| First successful run | Voluntary report from a tester, recording release and command; no tracking is built in | Whether instructions are usable |
| Qualified service inquiries | Record inquiries requesting a scoped audit, separate from general support | Whether related service demand exists |
| Responses resolved | Record resolved reproducible reports and time to first helpful response | Maintenance quality |

GitHub traffic uses rolling windows; overlapping unique-visitor windows must **not** be summed into a 30-day unique-user total. Clones are not confirmed installs, and stars are not the main success measure. Establish a baseline before promotion; do not promise visitor, star, or revenue outcomes.

Suggested private tracking fields: date, release, channel/post URL, traffic window, visitors, unique visitors, clones, unique cloners, substantive issues, first-run reports, qualified inquiries, lesson/next action. Avoid personal or patient data.

## Publication check / 发布前核对

- [ ] Current installation and walkthrough reproduce the stated critical failure.
- [ ] The release description matches implemented features; PyPI publication is verified separately.
- [ ] Links and preview image work; no invented benchmark or testimonial is present.
- [ ] The target venue permits this type of post; the author relationship is explicit.
- [ ] Replies request minimal synthetic examples rather than private patient data.
