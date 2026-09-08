#!/usr/bin/env python3
"""
A stopwatch for the recording. One line, updated every second, large enough
to read on a screen capture.

    python scripts/stopwatch.py

Start it the moment the contested path files its dispute and leave it on
screen. The elapsed time it shows is the real one; the demo prints its own
measurement at the end and the two should agree to the second.
"""

from __future__ import annotations

import sys
import time

started = time.time()
try:
    while True:
        elapsed = int(time.time() - started)
        sys.stdout.write(f"\r  {elapsed // 60:02d}:{elapsed % 60:02d} since the dispute was filed   ")
        sys.stdout.flush()
        time.sleep(1)
except KeyboardInterrupt:
    elapsed = int(time.time() - started)
    print(f"\n  stopped at {elapsed // 60:02d}:{elapsed % 60:02d}")
