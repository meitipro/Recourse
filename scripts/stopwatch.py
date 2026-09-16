#!/usr/bin/env python3
"""
A stopwatch for the recording. One line, updated every second, large enough
to read on a screen capture.

    python scripts/stopwatch.py
    python scripts/stopwatch.py --stop-file PATH

What it measures is the time from the dispute line to the line that ends the
shot. scripts/record.py starts it when the agent prints that its dispute was
accepted and stops it at the verdict line, where the take on Studio Next ends,
because the settlement does not move there. The agent's own "dispute to
verdict" starts earlier, as the dispute transaction is sent, so this reads
about five seconds less: the time that transaction takes to be accepted. The
two do not agree to the second.

With --stop-file it stops by itself when that file appears, and keeps its last
reading on screen until the window is closed.
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
            sys.stdout.write(f"\r  {now} since the dispute was accepted   ")
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
