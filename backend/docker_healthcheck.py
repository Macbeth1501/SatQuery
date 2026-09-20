"""Container HEALTHCHECK: exits 0 only if /v1/health answers 200 (it is 503 when the database is unusable)."""
import os
import sys
import urllib.request

port = os.environ.get("SATQUERY_PORT", "8000")
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/health", timeout=4) as response:
        sys.exit(0 if response.status == 200 else 1)
except Exception:
    sys.exit(1)
