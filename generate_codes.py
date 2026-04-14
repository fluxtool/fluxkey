#!/usr/bin/env python3
# generate_codes.py — FluxKey PLUS code generator

# Usage:
#   python generate_codes.py            -> 10 codes printed to terminal
#   python generate_codes.py 50         -> 50 codes
#   python generate_codes.py 100 out.txt -> saves to file
#
# Format: FLUX-XXXX-XXXX-XXXX-XXXX  (one-time use each)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.license_codes import generate_code

def main():
    count   = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    outfile = sys.argv[2]      if len(sys.argv) > 2 else None

    codes = [generate_code() for _ in range(count)]
    output = "\n".join(codes)

    print(f"\n{'─'*44}")
    print(f"  FluxKey PLUS — {count} activation code{'s' if count != 1 else ''}")
    print(f"{'─'*44}")
    for code in codes:
        print(f"  {code}")
    print(f"{'─'*44}\n")

    if outfile:
        with open(outfile, "w") as f:
            f.write(output + "\n")
        print(f"  Saved to {outfile}\n")

if __name__ == "__main__":
    main()
