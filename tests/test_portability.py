from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from scripts.compare_schedule_methods import canonical_input, digest, input_digest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def session():
    return json.loads((ROOT/"frontend/src/demo/observed-snapshot.json").read_text(encoding="utf-8"))["approved"]


def test_platform_noise_and_derived_hash_are_canonical_without_mutation(session):
    original = deepcopy(session)
    changed = deepcopy(session)
    changed["risks"][0]["inputs"]["wind_2m_ms"] += 1e-12
    changed["risks"][0]["inputs_hash"] = "f" * 64
    assert input_digest(changed) == input_digest(session)
    assert session == original
    assert changed["risks"][0]["inputs_hash"] == "f" * 64


@pytest.mark.parametrize("field", ["temperature", "wind", "risk", "policy", "age", "time", "offset", "schedule"])
def test_meaningful_inputs_remain_distinct(session, field):
    changed = deepcopy(session)
    if field == "temperature": changed["weather"][0]["ta_c"] += 0.00001
    if field == "wind": changed["risks"][0]["inputs"]["wind_2m_ms"] += 0.00001
    if field == "risk": changed["risks"][0]["decision_wbgt_c"] += 0.001
    if field == "policy": changed["policy"]["boundaries"][0] += 0.001
    if field == "age": changed["tournament"]["age_group"] = "adult"
    if field == "time": changed["matches"][0]["scheduled_start"] = "2026-07-10T19:00:00+09:00"
    if field == "offset": changed["venues"][0]["field_offset_c"] += 0.001
    if field == "schedule": changed["schedule_settings"]["cleanup_min"] += 1
    assert input_digest(changed) != input_digest(session)


def test_signed_zero_and_nested_containers_are_normalized():
    assert digest(canonical_input({"v": [-0.0, (1.12345600001,)]})) == digest(canonical_input({"v": [0.0, [1.123456]]}))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_comparison_inputs_are_rejected(value):
    with pytest.raises(ValueError): canonical_input({"v": [value]})


def test_artifact_digest_remains_exact_not_rounded():
    assert digest({"v": 1.12345600001}) != digest({"v": 1.123456})


def test_missing_provenance_is_rejected(session):
    del session["risks"][0]["inputs_hash"]
    with pytest.raises(ValueError): input_digest(session)


def test_migration_receipt_preserves_all_result_bodies():
    from scripts.migrate_comparison_fingerprints import result_payload
    packet = json.loads((ROOT/"docs/competition-evidence/portability-migration.json").read_text(encoding="utf-8"))
    assert packet["all_result_payloads_unchanged"] and packet["fresh_input_cases"] == 93
    assert len(packet["mapping"]) == 93 and len(packet["files"]) == 7
    for entry in packet["files"]:
        value = json.loads((ROOT/entry["path"]).read_text(encoding="utf-8"))
        assert digest(result_payload(value)) == entry["unchanged_result_payload_sha256"]


def test_one_core_runner_restricts_actual_child_process(tmp_path):
    check = tmp_path/"test_child_affinity.py"
    check.write_text('''import os,sys,ctypes
def test_actual_one_cpu():
    if sys.platform == "linux": assert len(os.sched_getaffinity(0)) == 1
    else:
        api=ctypes.WinDLL("kernel32",use_last_error=True)
        api.GetCurrentProcess.restype=ctypes.c_void_p
        api.GetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
        mask,system=ctypes.c_size_t(),ctypes.c_size_t()
        assert api.GetProcessAffinityMask(api.GetCurrentProcess(),ctypes.byref(mask),ctypes.byref(system))
        assert mask.value.bit_count() == 1
''', encoding="utf-8")
    run = subprocess.run([sys.executable, str(ROOT/"scripts/run_single_core_tests.py"), "--", "-q", str(check)],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert '"allowed_cpu_count": 1' in run.stdout
