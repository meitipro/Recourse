#!/usr/bin/env python3
"""
The recording, driven from one window: docs/SCRIPT.md's shots, in its order.

    python scripts/record.py --dry-run             walk every shot, run nothing
    python scripts/record.py                       the take
    python scripts/record.py --linter --withdraw   with those OPTIONAL shots

This window is Terminal A. Each shot's label is printed before it runs, in
block figures a screen capture can read. A terminal shot waits for the line
SCRIPT.md says appears in it, and every switch to a browser tab or another
window is a pause that waits for a key, never a timer. Terminal B, the
stopwatch, opens when the dispute line prints and stops when the refund line
does.

It drives what SCRIPT.md lists and nothing else. Every label, instruction and
spoken line printed here is read out of SCRIPT.md, and the plan below is
checked against SCRIPT.md's own table on every run, dry or not, so a shot the
script adds, drops, reorders or rewords stops this before anything starts.
Where the two disagree SCRIPT.md is right, and this file is the one to change.

It never takes a screenshot or records anything, never touches docs/images,
and never runs an OPTIONAL shot without its flag. A step that fails stops the
take, naming the shot and what SCRIPT.md expects there. Nothing is retried.

--dry-run runs nothing and writes nothing to the chain. It prints every shot,
every command, every line it would wait for and every pause. In a terminal it
also waits at each pause, so the three rehearsals SCRIPT.md asks for can be
walked with it.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import typing

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_MD = ROOT / "docs" / "SCRIPT.md"
LOCAL_SITE = "http://localhost:4500"
HOSTED_SITE = "https://recourse-site.vercel.app"
WIDTH = 74

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# The time a shot starts, five rows high, so a label reads on a capture.
GLYPHS = {
    "0": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "  ## ", " #   ", "#####"],
    "3": ["#### ", "    #", " ### ", "    #", "#### "],
    "4": ["#   #", "#   #", "#####", "    #", "    #"],
    "5": ["#####", "#    ", "#### ", "    #", "#### "],
    "6": [" ### ", "#    ", "#### ", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", "  #  "],
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "],
    "9": [" ### ", "#   #", " ####", "    #", " ### "],
    ":": ["     ", "  #  ", "     ", "  #  ", "     "],
}

PRINTING = threading.Lock()


def say(*lines: str) -> None:
    with PRINTING:
        for line in lines:
            print(line, flush=True)


def figures(text: str) -> list[str]:
    return ["  ".join(GLYPHS[c][row] for c in text if c in GLYPHS) for row in range(5)]


def banner(heading: str, start: str = "") -> None:
    lines = [""]
    if start:
        lines += ["  " + row for row in figures(start)] + [""]
    lines += ["  " + "=" * WIDTH, "  " + heading.upper(), "  " + "=" * WIDTH]
    say(*lines)


def field(name: str, text: str) -> None:
    rows = textwrap.wrap(text, WIDTH - 12, break_on_hyphens=False, break_long_words=False) or [""]
    say(f"  {name:<12}{rows[0]}", *(f"  {'':<12}{row}" for row in rows[1:]))


def key() -> None:
    """One key, no Enter. Ctrl+C stops the take like anywhere else."""
    if os.name == "nt":
        import msvcrt

        while msvcrt.kbhit():
            msvcrt.getwch()
        if msvcrt.getwch() == "\x03":
            raise KeyboardInterrupt
        return
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        pressed = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if pressed == "\x03":
        raise KeyboardInterrupt


# --- what SCRIPT.md says ----------------------------------------------------


def plain(text: str) -> str:
    """Markdown emphasis and code marks off, for a terminal."""
    return " ".join(re.sub(r"\*\*|\*|`", "", text).split())


class Shot(typing.NamedTuple):
    time: str
    title: str
    on_screen: str
    words: str
    optional: bool


def table(text: str) -> list[Shot]:
    shots: list[Shot] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("| time | shot"):
            inside = True
            continue
        if not inside or line.startswith("| ---"):
            continue
        if not line.startswith("| "):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split(" | ")]
        if len(cells) != 3:
            raise SystemExit(f"docs/SCRIPT.md has a table row record.py cannot read: {line[:90]}")
        time_range, shot, words = cells
        bold = re.search(r"\*\*(.+?)\*\*", shot)
        title = (bold.group(1) if bold else shot).rstrip(".:")
        shots.append(Shot(time_range, title, plain(shot), plain(words), shot.startswith("OPTIONAL")))
    return shots


def optional_items(text: str) -> dict[str, str]:
    """The OPTIONAL section's bullets, by their bold name."""
    section = text.split("## OPTIONAL shots", 1)[1].split("\n## ", 1)[0]
    items = {}
    for chunk in re.split(r"\n- ", "\n" + section):
        name = re.match(r"\*\*(.+?)\*\*", chunk.strip())
        if name:
            items[name.group(1)] = plain(chunk)
    return items


def setup_items(text: str) -> tuple[list[str], str]:
    """The numbered shot list before pressing record, and the paragraph after it."""
    section = text.split("## Shot list: before pressing record", 1)[1]
    items: list[str] = []
    tail: list[str] = []
    for line in section.splitlines():
        if re.match(r"\d+\. ", line) and not tail:
            items.append(line.split(". ", 1)[1])
        elif line.startswith("   ") and items and not tail:
            items[-1] += " " + line.strip()
        elif line.strip() and items:
            tail.append(line.strip())
    return [plain(item) for item in items], plain(" ".join(tail))


# --- the plan, which SCRIPT.md is checked against ----------------------------


def starts(prefix: str, *also: str) -> typing.Callable[[str], bool]:
    return lambda line: line.startswith(prefix) and all(part in line for part in also)


def contains(part: str) -> typing.Callable[[str], bool]:
    return lambda line: part in line


def equals(text: str) -> typing.Callable[[str], bool]:
    return lambda line: line == text


class Step(typing.NamedTuple):
    kind: str
    what: str
    #: The words the shot in SCRIPT.md must contain for this step to belong to it.
    anchor: str = ""
    match: typing.Callable[[str], bool] | None = None
    capture: str = ""


PLAN: list[tuple[str, list[Step]]] = [
    ("0:00 to 0:10", [
        Step("pause", "browser tab 1, the site, loaded now", "Browser, the site"),
    ]),
    ("0:10 to 0:18", [
        Step("run", "python scripts/demo.py", "python scripts/demo.py"),
        Step("expect", 'a line starting "promise"', "promise", starts("promise")),
        Step("expect", 'a line with "judgeable True" in it', "judgeable True", contains("judgeable True")),
    ]),
    ("0:18 to 0:30", [
        Step("expect", 'the heading "the honest path"', "the honest path", equals("the honest path")),
        Step("expect", 'a line starting "check"', "check ok", starts("check")),
        Step("expect", 'a line starting "payment p-"', "payment p-000NNN",
             lambda line: re.match(r"payment\s+p-\d{6}", line) is not None, "pid"),
        Step("expect", 'a line starting "outcome"', "outcome", starts("outcome"), "window"),
        Step("expect", 'a line starting "signature"', "signature verified", starts("signature")),
    ]),
    ("0:30 to 0:36", [
        Step("expect", 'the line "The same endpoint switches to stale and still returns 200."',
             "The same endpoint switches to stale and still returns 200.",
             contains("The same endpoint switches to stale and still returns 200.")),
        Step("expect", 'a line starting "check" with "stale:" in it', "stale:", starts("check", "stale:")),
    ]),
    ("0:36 to 0:42", [
        Step("expect", 'a line starting "disputed" with "bond" in it', "disputed", starts("disputed", "bond")),
        Step("stopwatch", "Terminal B", "stopwatch.py"),
    ]),
    ("0:42 to 0:56", [
        Step("pause", "browser tab 3, the case page", "the case page"),
    ]),
    ("0:56 to 1:04", [
        Step("expect", 'a line starting "verdict"', "verdict", starts("verdict")),
        Step("expect", 'a line starting "reason"', "reason", starts("reason")),
    ]),
    ("1:04 to 1:12", [
        Step("expect", 'a line starting "dispute to money back"', "dispute to money back",
             starts("dispute to money back")),
        Step("expect", 'a line starting "refund" with "returned" in it', "refund", starts("refund", "returned")),
        Step("stopwatch_stop", "Terminal B", "Stop the stopwatch"),
        Step("finished", "demo.py finishes and exits 0"),
        Step("pause", "browser tab 2, the feed", "Browser, section 05"),
    ]),
    ("1:12 to 1:18", [
        Step("window", "the honest payment's window", "window (300 s) to have closed"),
        Step("run", "python scripts/withdraw.py {pid}", "python scripts/withdraw.py p-000NNN"),
        Step("expect", 'a line starting "withdrawn"', "withdrawn", starts("withdrawn")),
        Step("expect", 'a line starting "seller balance"', "seller balance", starts("seller balance")),
        Step("expect", 'the line "no judgment ran and nobody paid anything extra"',
             "no judgment ran and nobody paid anything extra",
             contains("no judgment ran and nobody paid anything extra")),
        Step("finished", "withdraw.py finishes and exits 0"),
    ]),
    ("1:18 to 1:28", [
        Step("pause", "browser tab 4, section 06", "section 06"),
    ]),
    ("1:28 to 1:30", [
        Step("pause", "browser tab 1, the hero's strip, then the footer", "hero's strip"),
    ]),
]

#: Table rows SCRIPT.md marks OPTIONAL, and the flag that includes each.
OPTIONAL_ROWS = {"1:12 to 1:18": "withdraw"}

#: Shot list items SCRIPT.md marks OPTIONAL, and the flags that include them.
SETUP_GATES = {7: ("withdraw",), 8: ("linter", "clerk")}


class Insert(typing.NamedTuple):
    after: str
    flag: str
    name: str
    #: The words in SCRIPT.md's bullet that put the shot where this puts it.
    placement: str
    where: str


INSERTS = [
    Insert("0:18 to 0:30", "linter", "The promise linter", "Insert as a six second shot after 0:18",
           "browser tab 1, the site's hero"),
    Insert("0:18 to 0:30", "rewrite", "The rewrite", "straight after the refusal",
           "browser, the hero of a site with a key behind its linter"),
    Insert("1:12 to 1:18", "clerk", "The clerk", "It replaces the withdraw shot at 1:12",
           "browser tab 1, the clerk section"),
]


def check_plan(shots: list[Shot], optional: dict[str, str], setup: list[str]) -> None:
    """Stops before anything runs if SCRIPT.md no longer says what this drives."""
    fix = "SCRIPT.md is the script: change record.py to follow it."
    ours = [time_range for time_range, _ in PLAN]
    theirs = [shot.time for shot in shots]
    if ours != theirs:
        raise SystemExit(
            "docs/SCRIPT.md's table and record.py's plan disagree, so nothing runs.\n"
            f"  SCRIPT.md:  {', '.join(theirs)}\n  record.py:  {', '.join(ours)}\n{fix}"
        )
    for (time_range, steps), shot in zip(PLAN, shots):
        for step in steps:
            if step.anchor and step.anchor not in shot.on_screen:
                raise SystemExit(
                    f"docs/SCRIPT.md's shot at {time_range} no longer says {step.anchor!r}, "
                    f"which record.py's {step.kind} step there rests on. {fix}"
                )
    marked = {shot.time for shot in shots if shot.optional}
    if marked != set(OPTIONAL_ROWS):
        raise SystemExit(f"docs/SCRIPT.md marks {sorted(marked)} OPTIONAL and record.py gates {sorted(OPTIONAL_ROWS)}. {fix}")
    for number, item in enumerate(setup, 1):
        if ("OPTIONAL" in item) != (number in SETUP_GATES):
            raise SystemExit(f"docs/SCRIPT.md's shot list item {number} and record.py disagree about whether it is OPTIONAL. {fix}")
    for insert in INSERTS:
        if insert.placement not in optional.get(insert.name, ""):
            raise SystemExit(f"docs/SCRIPT.md's OPTIONAL {insert.name!r} no longer says {insert.placement!r}. {fix}")
    live = optional.get("The live site", "")
    if HOSTED_SITE not in live or LOCAL_SITE not in live:
        raise SystemExit(f"docs/SCRIPT.md's live site item no longer names {HOSTED_SITE} and {LOCAL_SITE}. {fix}")


# --- Terminal B ---------------------------------------------------------------


def stopwatch_mechanism() -> str:
    if os.environ.get("WT_SESSION") and shutil.which("wt"):
        return "a Windows Terminal pane split beside this one, with the focus handed back here"
    if os.name == "nt":
        return "a new console window, because this window is not Windows Terminal and cannot split; drag it beside this one"
    if os.environ.get("TMUX") and shutil.which("tmux"):
        return "a tmux pane split beside this one"
    return "nothing: this terminal cannot open another, so run record.py in Windows Terminal or tmux"


def open_stopwatch(stop_file: pathlib.Path) -> str:
    command = [sys.executable, str(ROOT / "scripts" / "stopwatch.py"), "--stop-file", str(stop_file)]
    how = stopwatch_mechanism()
    if os.environ.get("WT_SESSION") and shutil.which("wt"):
        subprocess.Popen(["wt", "-w", "0", "split-pane", "-V", "-s", "0.35", "-d", str(ROOT), *command, ";", "move-focus", "left"])
    elif os.name == "nt":
        subprocess.Popen(command, cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE)
    elif os.environ.get("TMUX") and shutil.which("tmux"):
        subprocess.Popen(["tmux", "split-window", "-h", "-l", "35%", "-c", str(ROOT), shlex.join(command)])
    else:
        raise RuntimeError(how)
    return how


# --- the take -----------------------------------------------------------------


class Take:
    def __init__(self, args: argparse.Namespace, shots: list[Shot], optional: dict[str, str],
                 setup: list[str], tail: str) -> None:
        self.args = args
        self.dry = args.dry_run
        self.shots = {shot.time: shot for shot in shots}
        self.optional = optional
        self.setup = setup
        self.tail = tail
        self.site = HOSTED_SITE if args.hosted else LOCAL_SITE
        # A person at a terminal has both ends on it. Output captured to a file
        # or another program means nobody is there to press a key.
        self.interactive = sys.stdin.isatty() and sys.stdout.isatty()
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.process: subprocess.Popen | None = None
        self.running = ""
        self.stop_file = pathlib.Path(tempfile.gettempdir()) / f"recourse-stopwatch-{os.getpid()}.stop"
        self.stopwatch = ""
        self.stopwatch_error = ""
        self.stopped = False
        self.pid = ""
        self.window_ends = 0
        self.shot: Shot | None = None

    def go(self) -> None:
        if self.dry:
            banner("dry run: nothing below runs, and nothing is written to the chain")
            field("SCRIPT.md", f"{len(self.shots)} shots in its table, checked against record.py's plan before this printed, shot for shot, in order")
            flags = [f"--{name}" for name in ("linter", "rewrite", "clerk", "withdraw", "hosted") if getattr(self.args, name)]
            field("OPTIONAL", ", ".join(flags) if flags else "none in this run; each has its own flag")
            field("Terminal B", f"opens at 0:36 in {stopwatch_mechanism()}")
            field("the site", self.site)
        self.before()
        for time_range, steps in PLAN:
            shot = self.shots[time_range]
            self.shot = shot
            flag = OPTIONAL_ROWS.get(time_range)
            included = flag is None or getattr(self.args, flag)
            if included or self.dry:
                self.play(shot, steps, skipped="" if included else flag)
            else:
                say(f"  {shot.time}  OPTIONAL, not in this take")
            for insert in INSERTS:
                if insert.after == time_range:
                    self.insert(insert)
        self.after()

    def before(self) -> None:
        banner("before pressing record: the shot list in docs/SCRIPT.md")
        for number, item in enumerate(self.setup, 1):
            gate = SETUP_GATES.get(number)
            if gate and not any(getattr(self.args, flag) for flag in gate):
                field(f"{number}.", f"OPTIONAL and not in this take: pass {' or '.join('--' + flag for flag in gate)} to include it")
                continue
            field(f"{number}.", item)
            if number == 1:
                field("", f"record.py opens Terminal B itself when the dispute line prints, in {stopwatch_mechanism()}.")
        if not self.dry:
            self.pause("the screen recorder", "Start recording the screen now. The take begins at 0:00.")

    def play(self, shot: Shot, steps: list[Step], skipped: str = "") -> None:
        banner(f"{shot.time}   {'OPTIONAL: ' if shot.optional else ''}{shot.title}", shot.time.split(" to ")[0])
        if self.dry:
            field("on screen", shot.on_screen)
            field("read aloud", shot.words)
            if skipped:
                field("skipped", f"OPTIONAL in SCRIPT.md, so not in this take: pass --{skipped} to include it. It would run:")
        for step in steps:
            getattr(self, "step_" + step.kind)(shot, step)

    def insert(self, insert: Insert) -> None:
        if not getattr(self.args, insert.flag):
            if self.dry:
                field("OPTIONAL", f"{insert.name}, which SCRIPT.md places here ({insert.placement}), is not in this take: pass --{insert.flag} to include it")
            return
        banner(f"OPTIONAL, {insert.placement}: {insert.name}")
        self.pause(insert.where, self.optional[insert.name])

    def after(self) -> None:
        banner("the take is done: stop recording the screen")
        field("then", self.tail)
        if self.dry:
            field("dry run", "Every shot above was printed and nothing ran or was written to the chain. SCRIPT.md asks for three clean rehearsals before the take.")

    # --- steps ----------------------------------------------------------------

    def step_run(self, shot: Shot, step: Step) -> None:
        command = step.what.format(pid=self.pid or "p-000NNN")
        if self.dry:
            field("runs", f"{command}   (dry run: not run)")
            return
        argv = shlex.split(command)
        argv[0] = sys.executable
        self.running = pathlib.Path(argv[1]).name
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        try:
            self.process = subprocess.Popen(
                argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
        except OSError as error:
            self.fail(shot, f"{command} could not start: {error}")
        threading.Thread(target=self.read, args=(self.process,), daemon=True).start()

    def step_expect(self, shot: Shot, step: Step) -> None:
        if self.dry:
            field("waits for", f"Terminal A to print {step.what}")
            return
        while True:
            line = self.lines.get()
            if line is None:
                code = self.process.wait() if self.process else "?"
                self.fail(shot, f"record.py waited for {step.what}, and {self.running} ended, exit {code}, without printing it")
            if step.match and step.match(line):
                if step.capture == "pid":
                    self.pid = re.match(r"payment\s+(p-\d{6})", line).group(1)
                elif step.capture == "window":
                    found = re.search(r"window ends (\d+)", line)
                    self.window_ends = int(found.group(1)) if found else 0
                return

    def step_stopwatch(self, shot: Shot, step: Step) -> None:
        if self.dry:
            field("then", f"Terminal B opens the moment that line prints, running python scripts/stopwatch.py, in {stopwatch_mechanism()}")
            return
        # The reader opened it on the line itself, so the count starts with the
        # dispute line rather than with whenever this thread got to it.
        if self.stopwatch_error:
            self.fail(shot, f"Terminal B could not be opened: {self.stopwatch_error}")

    def step_stopwatch_stop(self, shot: Shot, step: Step) -> None:
        if self.dry:
            field("then", "Terminal B stops the moment that line prints, and keeps its last reading in frame")

    def step_finished(self, shot: Shot, step: Step) -> None:
        if self.dry:
            field("then", step.what)
            return
        while self.lines.get() is not None:
            pass
        code = self.process.wait() if self.process else 1
        if code != 0:
            self.fail(shot, f"{self.running} exited {code}")

    def step_pause(self, shot: Shot, step: Step) -> None:
        text = shot.on_screen
        if step.anchor.startswith("Browser, section"):
            text = text[text.index(step.anchor):]
        self.pause(step.what, text)

    def step_window(self, shot: Shot, step: Step) -> None:
        if self.dry:
            field("pause", "until the honest payment's window has closed: record.py prints when it closes, read off Terminal A at 0:18, and waits for a key")
            return
        if not self.window_ends:
            self.fail(shot, "the honest payment's window end was never printed at 0:18")
        while (left := self.window_ends - time.time()) > 0:
            closes = datetime.datetime.fromtimestamp(self.window_ends).strftime("%H:%M:%S")
            self.pause("nowhere yet", f"The honest payment's window closes at {closes} local time, {int(left)} seconds from now, and SCRIPT.md needs it closed before the withdraw.")

    # --- plumbing -------------------------------------------------------------

    def pause(self, where: str, text: str) -> None:
        say("")
        field(">>> switch", f"{where} ({self.site})" if where.startswith("browser") else where)
        field("", text)
        field(">>> then", "press any key here when the shot is done")
        if self.dry and not self.interactive:
            field("", "(dry run, not a terminal: not waiting)")
            return
        key()

    def read(self, process: subprocess.Popen) -> None:
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.rstrip("\r\n")
            say(line)
            self.watch(line.strip())
            self.lines.put(line.strip())
        self.lines.put(None)

    def watch(self, line: str) -> None:
        """Terminal B follows the lines themselves, so a pause never delays it."""
        if not self.stopwatch and line.startswith("disputed") and "bond" in line:
            try:
                self.stopwatch = open_stopwatch(self.stop_file)
            except Exception as error:  # noqa: BLE001 - the 0:36 step reports it
                self.stopwatch, self.stopwatch_error = "failed", str(error)
        elif self.stopwatch and not self.stopped and line.startswith("refund") and "returned" in line:
            self.stop_file.touch()
            self.stopped = True

    def cleanup(self) -> None:
        if self.process and self.process.poll() is None:
            if os.name == "nt":
                # demo.py's child is the seller on 4501; /T takes it too, so the
                # next take does not find the port held.
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.process.pid)], capture_output=True)
            else:
                self.process.terminate()
        if self.stopwatch and not self.stopped:
            self.stop_file.touch()

    def fail(self, shot: Shot, what: str) -> typing.NoReturn:
        self.cleanup()
        banner(f"the take stopped at {shot.time}: {shot.title}")
        field("SCRIPT.md", shot.on_screen)
        field("happened", what)
        field("", "Nothing was retried. Fix the cause, then start the take again from the top.")
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="walk every shot and pause, run nothing")
    parser.add_argument("--linter", action="store_true", help="OPTIONAL: the promise linter shot, after 0:18")
    parser.add_argument("--rewrite", action="store_true", help="OPTIONAL: the rewrite, straight after the refusal; needs a key behind the linter")
    parser.add_argument("--clerk", action="store_true", help="OPTIONAL: the clerk at 1:12; needs a key behind the linter")
    parser.add_argument("--withdraw", action="store_true", help="OPTIONAL: the withdraw at 1:12, once the honest window has closed")
    parser.add_argument("--hosted", action="store_true", help=f"the live site at {HOSTED_SITE} instead of {LOCAL_SITE}")
    args = parser.parse_args()

    text = SCRIPT_MD.read_text(encoding="utf-8")
    shots = table(text)
    optional = optional_items(text)
    setup, tail = setup_items(text)
    check_plan(shots, optional, setup)
    if not args.dry_run and not sys.stdin.isatty():
        raise SystemExit("The take waits for keys, so it needs a terminal. --dry-run walks it without one.")

    take = Take(args, shots, optional, setup, tail)
    try:
        take.go()
    except KeyboardInterrupt:
        take.cleanup()
        banner(f"stopped by hand{' at ' + take.shot.time if take.shot else ''}")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
