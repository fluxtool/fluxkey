#!/usr/bin/env python3
# plus-reset.py
# ─────────────────────────────────────────────────────────────────────────────
#  FluxKey PLUS — developer reset tool
#  FOR PERSONAL USE ONLY. Never ship this with your app.
#
#  What it does:
#    1. Shows current PLUS status
#    2. Revokes PLUS (sets plus: false in fluxkey_license.json)
#    3. Clears the used-codes list (fluxkey_used_codes.json)
#    4. Optionally generates a fresh test code to try immediately
#
#  Usage:
#    python plus-reset.py          — reset + generate 1 fresh test code
#    python plus-reset.py --no-code — reset only, no new code
#    python plus-reset.py --status  — just show current state, no changes
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import json

# Add project root so core.* imports work
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

SEP = "─" * 52

def _find_data_dir() -> str:
    """Return the directory where FluxKey stores its data files."""
    try:
        from core.vault import VAULT_FILE
        return os.path.dirname(VAULT_FILE)
    except Exception as e:
        print(f"  ⚠  Could not import core.vault: {e}")
        print("     Make sure you run this from your FluxKey project root.")
        sys.exit(1)

def _license_path(data_dir: str) -> str:
    return os.path.join(data_dir, "fluxkey_license.json")

def _used_codes_path(data_dir: str) -> str:
    return os.path.join(data_dir, "fluxkey_used_codes.json")

def read_license(data_dir: str) -> dict:
    try:
        with open(_license_path(data_dir)) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"plus": False}
    except Exception as e:
        return {"plus": False, "error": str(e)}

def read_used_codes(data_dir: str) -> list:
    try:
        with open(_used_codes_path(data_dir)) as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        return [f"(error reading: {e})"]

def show_status(data_dir: str):
    lic   = read_license(data_dir)
    used  = read_used_codes(data_dir)
    plus  = lic.get("plus", False)

    print(f"\n{SEP}")
    print(f"  FluxKey PLUS — current state")
    print(SEP)
    print(f"  Data directory : {data_dir}")
    print(f"  PLUS active    : {'YES ✓' if plus else 'NO'}")
    print(f"  Used codes     : {len(used)}")
    if used:
        for c in used:
            print(f"                   {c}")
    print(SEP)

def revoke_plus(data_dir: str):
    path = _license_path(data_dir)
    try:
        try:
            with open(path) as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        data["plus"] = False
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print("  ✓  PLUS revoked  →  fluxkey_license.json set to plus: false")
    except Exception as e:
        print(f"  ✗  Failed to revoke PLUS: {e}")
    # Also clear the in-memory cache inside core.license if already imported
    try:
        import core.license as _lic
        _lic._cache.clear()
    except Exception:
        pass

def clear_used_codes(data_dir: str):
    path = _used_codes_path(data_dir)
    try:
        with open(path, "w") as f:
            json.dump([], f, indent=2)
        print("  ✓  Used-codes list cleared  →  fluxkey_used_codes.json reset to []")
    except Exception as e:
        print(f"  ✗  Failed to clear used codes: {e}")

def generate_test_code() -> str:
    try:
        from core.license_codes import generate_code
        return generate_code()
    except Exception as e:
        return f"(could not generate: {e})"

def main():
    args = sys.argv[1:]

    # ── Status only ───────────────────────────────────────────────────────────
    if "--status" in args:
        data_dir = _find_data_dir()
        show_status(data_dir)
        return

    data_dir = _find_data_dir()

    print(f"\n{SEP}")
    print("  FluxKey PLUS — developer reset")
    print(SEP)

    # Show state before
    lic  = read_license(data_dir)
    used = read_used_codes(data_dir)
    print(f"  BEFORE — PLUS: {'YES' if lic.get('plus') else 'NO'}"
          f"   |   Used codes: {len(used)}")
    print()

    # Perform reset
    revoke_plus(data_dir)
    clear_used_codes(data_dir)

    # Show state after
    lic2  = read_license(data_dir)
    used2 = read_used_codes(data_dir)
    print()
    print(f"  AFTER  — PLUS: {'YES' if lic2.get('plus') else 'NO'}"
          f"   |   Used codes: {len(used2)}")

    # Generate a fresh test code unless suppressed
    if "--no-code" not in args:
        print()
        code = generate_test_code()
        print(f"  Fresh test code (one-time use):")
        print(f"\n      {code}\n")
        print("  Paste this into Settings → FluxKey PLUS → Enter PLUS Code")

    print(SEP)
    print("  Done. Re-run FluxKey to test activation.\n")

if __name__ == "__main__":
    main()