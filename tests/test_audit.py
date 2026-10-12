import csv
import json
import os
from pathlib import Path

import pytest

from dicleak.checks import AuditConfig, gate_passes, run_all, score
from dicleak.cli import main
from dicleak.readers import ManifestError, read_manifest
from dicleak.report import render_json, render_markdown, render_terminal

ROOT = Path(__file__).resolve().parents[1]


def write_manifest(tmp_path, rows, header=("patient_id", "split", "label", "filepath")):
    path = tmp_path / "manifest.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def clean_rows():
    return [("P%03d" % n, "train" if n < 80 else "test", str(n % 2), "image%03d.dcm" % n) for n in range(100)]


def test_leakage_fails_even_when_score_is_90(tmp_path, capsys):
    rows = clean_rows() + [("P000", "test", "0", "different-path.dcm")]
    path = write_manifest(tmp_path, rows)
    manifest = read_manifest(path)
    findings = run_all(manifest.rows)
    assert score(findings) == 90
    assert not gate_passes(findings)
    assert main([str(path)]) == 1
    output = capsys.readouterr().out
    assert "Gate: FAIL" in output
    assert "90/100" in output
    assert "publishable" not in output


def test_clean_sample_passes_and_reports_row_and_patient_counts(tmp_path):
    out = tmp_path / "clean.json"
    assert main([str(ROOT / "samples/clean_splits.csv"), "--json", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["gate"] == "pass"
    assert data["dataset"]["input_rows"] == 200
    assert data["dataset"]["unique_patients"] == 100
    assert data["dataset"]["partitions"]["train"]["rows"] == 120
    assert data["dataset"]["partitions"]["train"]["patients"] == 60
    assert data["dataset"]["partitions"]["train"]["labels"]["0"] == {"rows": 60, "patients": 30}


@pytest.mark.parametrize("field", ("patient_id", "split", "label"))
def test_missing_required_values_fail_and_preserve_input_count(tmp_path, field):
    rows = clean_rows()
    invalid = list(rows[0])
    invalid[("patient_id", "split", "label").index(field)] = "   "
    rows.append(invalid)
    manifest = read_manifest(write_manifest(tmp_path, rows))
    assert manifest.input_rows == 101
    assert manifest.invalid_rows == 1
    assert len(manifest.rows) == 100
    assert manifest.diagnostics[0].line == 102
    findings = run_all(manifest.rows, diagnostics=manifest.diagnostics)
    assert not gate_passes(findings)


def test_unknown_split_is_not_silently_accepted(tmp_path):
    manifest = read_manifest(write_manifest(tmp_path, clean_rows() + [("P999", "fold1", "0", "x")]))
    assert manifest.invalid_rows == 1
    assert manifest.diagnostics[0].code == "unknown_split"


@pytest.mark.parametrize("headers", [
    ("patient_id", "patient_id", "split", "label"),
    ("patient_id", "patient-id", "split", "label"),
    ("patient", "subject", "split", "label"),
    ("patient_id", "split", "label", "class"),
    ("patient_id", "split", "label", ""),
])
def test_duplicate_or_ambiguous_headers_rejected(tmp_path, headers):
    with pytest.raises(ManifestError):
        read_manifest(write_manifest(tmp_path, [tuple("x" for _ in headers)], header=headers))


def test_wrong_column_count_is_counted(tmp_path):
    manifest = read_manifest(write_manifest(tmp_path, clean_rows() + [("P999", "test", "0", "x", "extra")]))
    assert manifest.input_rows == 101
    assert manifest.invalid_rows == 1
    assert manifest.diagnostics[0].code == "column_count"


def test_holdout_requires_test_even_with_balanced_labels(tmp_path):
    rows = [(patient, "train", label, path) for patient, _, label, path in clean_rows()]
    findings = run_all(read_manifest(write_manifest(tmp_path, rows)).rows)
    assert any(f.check_id == "partition_presence" for f in findings)
    assert not gate_passes(findings)


def test_cv_explicit_fold_assignments_pass():
    config = AuditConfig(split_mode="cv", folds=("fold1", "fold2", "fold3"))
    manifest = read_manifest(ROOT / "samples/cv_folds.csv", config.split_mode, config.folds)
    assert gate_passes(run_all(manifest.rows, config))


def test_cv_leakage_and_missing_fold_fail(tmp_path):
    config = AuditConfig(split_mode="cv", folds=("fold1", "fold2", "fold3"))
    rows = [(patient, "fold1" if split == "train" else "fold2", label, path) for patient, split, label, path in clean_rows()]
    rows.append(("P000", "fold2", "0", "new"))
    manifest = read_manifest(write_manifest(tmp_path, rows), "cv", config.folds)
    findings = run_all(manifest.rows, config)
    assert {f.check_id for f in findings} >= {"partition_presence", "leakage"}
    assert not gate_passes(findings)


def test_cv_names_are_case_sensitive_and_need_config(tmp_path):
    path = write_manifest(tmp_path, [("P1", "Fold1", "0", "x")])
    manifest = read_manifest(path, "cv", ("fold1", "fold2"))
    assert manifest.invalid_rows == 1
    with pytest.raises(ManifestError):
        read_manifest(path, "cv")
    with pytest.raises(SystemExit) as exc:
        main([str(path), "--split-mode", "cv"])
    assert exc.value.code == 2


def test_row_labels_allowed_but_patient_label_mode_fails(tmp_path):
    rows = clean_rows() + [("P000", "train", "1", "additional.dcm")]
    manifest = read_manifest(write_manifest(tmp_path, rows))
    assert gate_passes(run_all(manifest.rows))
    findings = run_all(manifest.rows, AuditConfig(label_mode="patient"))
    assert any(f.check_id == "patient_labels" for f in findings)
    assert not gate_passes(findings)


def test_intentional_single_class_requires_opt_in(tmp_path):
    rows = [(patient, split, "lesion", path) for patient, split, _, path in clean_rows()]
    manifest = read_manifest(write_manifest(tmp_path, rows))
    assert not gate_passes(run_all(manifest.rows))
    assert gate_passes(run_all(manifest.rows, AuditConfig(allow_single_class=True)))


def test_patient_weighted_drift_detects_hidden_row_balance(tmp_path):
    rows = []
    for split in ("train", "test"):
        for label in ("0", "1"):
            patients = 9 if (split, label) in (("train", "0"), ("test", "1")) else 1
            for n in range(9):
                rows.append(("%s%s%d" % (split, label, n % patients), split, label, "%s%s%d" % (split, label, n)))
    manifest = read_manifest(write_manifest(tmp_path, rows))
    findings = run_all(manifest.rows)
    assert any(f.check_id == "stratification" for f in findings)


def test_no_patient_ids_in_default_reports(tmp_path):
    private_id = "Private Person"
    rows = clean_rows() + [(private_id, "train", "0", "a"), (private_id, "test", "0", "b")]
    manifest = read_manifest(write_manifest(tmp_path, rows))
    config = AuditConfig()
    findings = run_all(manifest.rows, config)
    for report in (render_terminal(findings, score(findings), manifest.rows),
                   render_markdown(findings, score(findings), manifest.rows),
                   render_json(findings, score(findings), manifest.rows)):
        assert private_id not in report
    shown = run_all(manifest.rows, AuditConfig(show_ids=True))
    assert private_id in render_json(shown, score(shown), manifest.rows, config=AuditConfig(show_ids=True))


def test_markdown_escapes_labels_and_explicit_ids(tmp_path):
    identifier = "<script>alert(1)</script>\x1b[31m"
    rows = clean_rows() + [(identifier, "train", "x|<b>y</b>\n#title", "a"), (identifier, "test", "0", "b")]
    manifest = read_manifest(write_manifest(tmp_path, rows))
    config = AuditConfig(show_ids=True)
    findings = run_all(manifest.rows, config)
    md = render_markdown(findings, score(findings), manifest.rows, config=config)
    assert "<script>" not in md
    assert "<b>" not in md
    assert "x\\|" in md
    assert "\x1b" not in render_terminal(findings, score(findings), manifest.rows, config=config)


def test_cross_partition_filepath_is_manifest_failure(tmp_path):
    rows = clean_rows()
    rows[-1] = (rows[-1][0], rows[-1][1], rows[-1][2], rows[0][3])
    findings = run_all(read_manifest(write_manifest(tmp_path, rows)).rows)
    assert any(f.check_id == "cross_partition_filepath" for f in findings)
    assert not gate_passes(findings)


def test_repeated_observations_without_paths_are_expected(tmp_path):
    rows = [(patient, split, label) for patient, split, label, _ in clean_rows()]
    rows.append(rows[0])
    manifest = read_manifest(write_manifest(tmp_path, rows, ("patient_id", "split", "label")))
    assert gate_passes(run_all(manifest.rows))


def test_input_and_outputs_cannot_overwrite_each_other(tmp_path):
    path = write_manifest(tmp_path, clean_rows())
    before = path.read_bytes()
    assert main([str(path), "--report", str(path)]) == 2
    assert path.read_bytes() == before
    output = tmp_path / "same.txt"
    assert main([str(path), "--report", str(output), "--json", str(output)]) == 2
    assert not output.exists()


def test_hardlink_output_cannot_overwrite_input(tmp_path):
    path = write_manifest(tmp_path, clean_rows())
    output = tmp_path / "alias.csv"
    try:
        os.link(path, output)
    except (OSError, NotImplementedError):
        pytest.skip("hard links unavailable")
    before = path.read_bytes()
    assert main([str(path), "--report", str(output)]) == 2
    assert path.read_bytes() == before


def test_invalid_cta_is_rejected_without_output(tmp_path):
    path = write_manifest(tmp_path, clean_rows())
    out = tmp_path / "report.md"
    assert main([str(path), "--report", str(out), "--cta", "javascript:alert(1)"]) == 2
    assert not out.exists()


def test_empty_unreadable_and_all_invalid_input(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert main([str(empty)]) == 2
    assert main([str(tmp_path / "missing.csv")]) == 2
    invalid = write_manifest(tmp_path, [("", "", "", "")])
    json_path = tmp_path / "invalid.json"
    assert main([str(invalid), "--json", str(json_path)]) == 1
    data = json.loads(json_path.read_text())
    assert data["dataset"]["input_rows"] == 1
    assert data["dataset"]["valid_rows"] == 0
    assert data["dataset"]["invalid_rows"] == 1
    assert data["gate"] == "fail"


def test_aliases_and_bom(tmp_path):
    path = tmp_path / "aliases.csv"
    path.write_text("\ufeffSubject ID,Subset,Diagnosis\nP1,Training,0\nP2,Testing,1\n", encoding="utf-8")
    manifest = read_manifest(path)
    assert [row["split"] for row in manifest.rows] == ["train", "test"]


def test_packaged_flawed_sample_fails(tmp_path):
    output = tmp_path / "audit.md"
    assert main([str(ROOT / "samples/flawed_splits.csv"), "--report", str(output)]) == 1
    assert "Gate: FAIL" in output.read_text()
    assert "Synthetic Name" not in output.read_text()


def test_launch_tutorial_has_high_score_failure():
    manifest = read_manifest(ROOT / "docs/launch/synthetic_leakage.csv")
    findings = run_all(manifest.rows)
    assert manifest.input_rows == 101
    assert len({row["patient_id"] for row in manifest.rows}) == 100
    assert score(findings) == 90
    assert not gate_passes(findings)
