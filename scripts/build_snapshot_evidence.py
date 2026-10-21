"""Project existing frozen sessions into supplemental offline detail assets."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.evidence import schedule_evidence
from backend.input_evidence import input_evidence
from backend.original_issues import original_issues


def build():
    output = ROOT / "frontend/src/demo"
    for prefix in ("snapshot", "observed-snapshot"):
        bundle = json.loads((output / f"{prefix}.json").read_text(encoding="utf-8"))
        s = bundle["approved"]
        data = {"input_fingerprint": bundle["input_fingerprint"], "session_id": s["id"],
                "session_sha256": hashlib.sha256(json.dumps(s, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "matches": {m["id"]: schedule_evidence(s, m["id"]) for m in s["matches"]},
                "original_issues": original_issues(s)}
        path = output / f"{prefix}-evidence.json"
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"{prefix}: {len(data['matches'])} 경기 상세 / {path.stat().st_size} bytes")
        inputs = {"input_fingerprint": bundle["input_fingerprint"], "session_id": s["id"],
                  "inputs": {r["venue_id"] + "|" + r["valid_time"]: input_evidence(s, r["venue_id"], r["valid_time"])
                             for r in s["risks"]}}
        path = output / f"{prefix}-input-evidence.json"
        path.write_text(json.dumps(inputs, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"{prefix}: {len(inputs['inputs'])} 시간 입력 근거 / {path.stat().st_size} bytes")


if __name__ == "__main__":
    build()
