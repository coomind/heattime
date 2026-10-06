"""Restrict this test process and children to one allowed CPU, never the engine."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def restrict_to_one_cpu():
    if sys.platform == "linux":
        allowed = os.sched_getaffinity(0)
        selected = min(allowed)
        os.sched_setaffinity(0, {selected})
        actual = sorted(os.sched_getaffinity(0))
    elif sys.platform == "win32":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.GetCurrentProcess.restype = ctypes.c_void_p
        api.GetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
        api.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        process = api.GetCurrentProcess()
        mask, system = ctypes.c_size_t(), ctypes.c_size_t()
        if not api.GetProcessAffinityMask(process, ctypes.byref(mask), ctypes.byref(system)):
            raise ctypes.WinError(ctypes.get_last_error())
        selected_mask = mask.value & -mask.value
        if not api.SetProcessAffinityMask(process, selected_mask):
            raise ctypes.WinError(ctypes.get_last_error())
        if not api.GetProcessAffinityMask(process, ctypes.byref(mask), ctypes.byref(system)):
            raise ctypes.WinError(ctypes.get_last_error())
        actual = [i for i in range(mask.value.bit_length()) if mask.value & (1 << i)]
    else:
        raise RuntimeError("This runner supports Linux and Windows only")
    if len(actual) != 1:
        raise RuntimeError("One-core affinity was not applied")
    return {"platform": sys.platform, "allowed_cpu_ids": actual, "allowed_cpu_count": 1,
            "scope": "test process and its children; engine worker count and 10s unchanged"}


if __name__ == "__main__":
    print(json.dumps(restrict_to_one_cpu()), flush=True)
    args = sys.argv[1:]
    if args[:1] == ["--"]:
        args = args[1:]
    raise SystemExit(subprocess.run([sys.executable, "-m", "pytest", *args], cwd=ROOT).returncode)
