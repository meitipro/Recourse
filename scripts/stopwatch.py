#!/usr/bin/env python3
"""
A stopwatch for the recording. One line, updated every second, large enough
to read on a screen capture.

    python scripts/stopwatch.py
    python scripts/stopwatch.py --stop-file PATH

Start it the moment the contested path files its dispute and leave it on
screen. The elapsed time it shows is the real one; the demo prints its own
measurement at the end and the two should agree to the second.

With --stop-file it stops by itself when that file appears, which is how
scripts/record.py stops it at the refund line, and it keeps its last reading
on screen until the window is closed.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--stop-file", default="", help="stop when this file exists")
args = parser.parse_args()

started = time.time()


def reading() -> str:
    elapsed = int(time.time() - started)
    return f"{elapsed // 60:02d}:{elapsed % 60:02d}"


stopped = ""
try:
    shown = ""
    while not (args.stop_file and os.path.exists(args.stop_file)):
        now = reading()
        if now != shown:
            sys.stdout.write(f"\r  {now} since the dispute was filed   ")
            sys.stdout.flush()
            shown = now
        time.sleep(0.1)
    stopped = reading()
    print(f"\n  stopped at {stopped}", flush=True)
    # Stopped from outside: keep the reading in frame until the window closes.
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    if not stopped:
        print(f"\n  stopped at {reading()}")
