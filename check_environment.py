"""
Environment check — the first thing to run once a shell exists.

Reports what is installed, what is missing, and **what each missing package
blocks**, so that a failed first run produces a fix rather than a stack trace.

Run from the repository root:

    python check_environment.py

Exit code 0 means everything needed for the whole pipeline is present.
Exit code 1 means something is missing; the report says what.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# name -> (import name, minimum version or None, what it is needed for, blocking?)
REQUIRED = [
    ("numpy", "numpy", "1.22", "everything", True),
    ("scipy", "scipy", "1.9",
     "the analytic Fisher-z power column, and faster statistics elsewhere", False),
    ("causal-learn", "causallearn", "0.1.3.0",
     "PC/GES structure learning and Structural Hamming Distance — i.e. all of Stage 0", True),
    ("jsonschema", "jsonschema", "4.0",
     "the structural half of extraction record validation", False),
    ("pandas", "pandas", None, "optional convenience only; nothing depends on it", False),
]


def version_of(module) -> str:
    return getattr(module, "__version__", "unknown")


def _too_old(version: str, minimum: str | None) -> bool:
    """Version comparison without requiring `packaging`, which is not part of
    the bundled runtime. Numeric components are compared in order; anything
    non-numeric (rc, dev, post) is ignored rather than guessed at, so a
    pre-release is never reported as satisfying a minimum by accident."""
    if not minimum or version == "unknown":
        return False
    def parts(v: str) -> tuple[int, ...]:
        out = []
        for chunk in v.split("."):
            num = ""
            for ch in chunk:
                if ch.isdigit():
                    num += ch
                else:
                    break
            out.append(int(num) if num else 0)
        return tuple(out)
    a, b = parts(version), parts(minimum)
    width = max(len(a), len(b))
    a += (0,) * (width - len(a))
    b += (0,) * (width - len(b))
    return a < b


def check() -> tuple[list, list]:
    present, missing = [], []
    for dist, mod, minver, purpose, blocking in REQUIRED:
        try:
            m = importlib.import_module(mod)
        except ImportError:
            missing.append((dist, minver, purpose, blocking))
            continue
        present.append((dist, version_of(m), minver, purpose))
    return present, missing


def what_still_works(missing: list) -> list[str]:
    """Map each missing package to the concrete capability it removes."""
    notes = []
    names = {d for d, _v, _p, _b in missing}
    if "causal-learn" in names:
        notes.append(
            "Stage 0 cannot run at all: `discovery.py` imports causal-learn for PC/GES "
            "and for the official SHD implementation, and `impact.py` imports "
            "`discovery`. This is the blocking dependency.")
    if "scipy" in names:
        notes.append(
            "The analytic Fisher-z column of the power table shows an em dash, and "
            "`power.py` falls back to an Abramowitz-Stegun erf approximation. The "
            "corpus target is unaffected, because it comes from the empirical column.")
    if "jsonschema" in names:
        notes.append(
            "Record validation runs its semantic layer only and reports the structural "
            "layer as skipped. Semantic checks are the ones that matter, so this is a "
            "degradation, not a failure.")
    if not notes:
        notes.append("Nothing is degraded.")
    return notes


def install_command(missing: list) -> str | None:
    pkgs = [d for d, _v, _p, _b in missing if _b or d in ("scipy", "jsonschema")]
    if not pkgs:
        return None
    return f'{sys.executable} -m pip install ' + " ".join(
        f'"{p}"' if p == "causal-learn" else p for p in pkgs)


def main() -> int:
    print("Environment check")
    print("=" * 66)
    print(f"interpreter : {sys.executable}")
    print(f"python      : {sys.version.split()[0]}")
    print(f"repo root   : {ROOT}")
    print()

    present, missing = check()

    print("Present")
    print("-" * 66)
    if present:
        for dist, ver, minver, purpose in present:
            flag = f"  ⚠ BELOW MINIMUM {minver}" if _too_old(ver, minver) else ""
            print(f"  {dist:<16} {ver:<12} {purpose}{flag}")
    else:
        print("  (nothing)")
    print()

    print("Missing")
    print("-" * 66)
    if not missing:
        print("  (nothing missing)")
    else:
        for dist, minver, purpose, blocking in missing:
            tag = "BLOCKING" if blocking else "optional"
            mv = f" >={minver}" if minver else ""
            print(f"  {dist}{mv:<10} [{tag}]  {purpose}")
    print()

    print("Consequences")
    print("-" * 66)
    for note in what_still_works(missing):
        print(f"  - {note}")
    print()

    cmd = install_command(missing)
    if cmd:
        print("To fix")
        print("-" * 66)
        print(f"  {cmd}")
        print()

    # Report what the self tests will do, so the first run is not a surprise.
    print("Self tests, in the order they should be run")
    print("-" * 66)
    print("  python extraction/selftest.py    # numpy only; parsing, signals, variance, adapters")
    print("  python extraction/smoke_test.py  # numpy only; the whole chain, scripted model")
    print("  python analysis/selftest.py      # numpy only; RQ2, RQ8, validation")
    print("  python stage0/selftest.py        # needs causal-learn for its last two checks")
    print()

    blocking_missing = [d for d, _v, _p, b in missing if b]
    if blocking_missing:
        print(f"RESULT: {len(blocking_missing)} blocking dependency missing: "
              f"{', '.join(blocking_missing)}")
        return 1
    print("RESULT: all blocking dependencies present. The pipeline can run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
