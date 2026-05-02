import base64
import re
from pathlib import Path

INPUT_FILE = Path("dns_log.txt")
OUTPUT_FILE = Path("decoded_output.txt")

def try_base64(data):
    try:
        return base64.b64decode(data + "==").decode("utf-8", errors="ignore")
    except:
        return None

if not INPUT_FILE.exists():
    print("dns_log.txt not found")
    exit(1)

results = []

with open(INPUT_FILE, "r") as f:
    for line in f:
        match = re.search(r"DNS Query:\s(.+)", line)
        if not match:
            continue

        domain = match.group(1).strip()
        results.append(f"[RAW] {domain}")

        for part in domain.split("."):
            decoded = try_base64(part)
            if decoded:
                results.append(f"[B64?] {part} -> {decoded}")

with open(OUTPUT_FILE, "w") as f:
    f.write("\n".join(results))

print(f"Done → {OUTPUT_FILE}")