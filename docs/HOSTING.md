# Hosting

Three Vercel projects from two repositories. The token available to the build
that wrote this could list the team's projects but not create one, so each is
a dashboard import. Every setting that matters is below; nothing else needs
changing.

The project names matter. `recourse-skill/reference/07-addresses.json` and
`recourse-skill/.claude-plugin/plugin.json` already name the URLs the projects
will have if they are called exactly `recourse-linter` and `recourse-mcp`. Use
those names, or update both files afterwards.

`ANTHROPIC_API_KEY` goes on `recourse-linter` and nowhere else. The site and
the MCP server call no model themselves: every stage 2 lint and every dry run
of the judge happens in the linter, which both reach through `LINTER_URL`. One
copy of the key is one place to cap its spend. The bot, if it runs, needs the
key on whatever machine runs it.

## One command

After the imports, from this repository:

```bash
python scripts/smoke.py
```

Nine checks against the three live URLs, each naming the dashboard setting that
fixes it when it fails. Run it yourself rather than through an agent: every
failure it can find is a setting, and the person who reads the failure should be
the one who can change it. When all nine pass it lists the sentences in this
repository written for a world with no hosting, which became false at that
moment and would otherwise say nothing.

Two things a hand check gets wrong, and the script does not:

- **A vague promise cannot test the key.** Stage 1 refuses it before any model
  is asked, so the refusal is the same with or without `ANTHROPIC_API_KEY`, and
  no rewrite ever follows a stage 1 refusal. The key shows only on a promise
  that passes stage 1: the script sends "Prices aggregated from at least three
  venues, refreshed within five seconds." and expects a stage 2 answer.
- **`grep` on the page's HTML misses rendered text.** React separates adjacent
  text with comment markers and inline tags, so "fixed bond of 1 GEN" is on the
  page and not in the source. The script strips tags before it looks. The case
  page's "not honored" happens to survive a raw grep; most sentences do not.

## 1. The linter

| | |
| --- | --- |
| Repository | `meitipro/Recourse` |
| Project name | `recourse-linter` |
| Root directory | `.` (the repository root; the functions are `api/lint.py` and `api/judge.py`) |
| Framework | Other. Not Python: the first import used the Python preset, which looks for a single app entrypoint, and failed with "No python entrypoint found" |
| Environment | `ANTHROPIC_API_KEY`, for Production and not only Preview. Without it stage 1 still answers, and stage 2 and the judge say 503 |

`api/judge.py` is what the site's clerk reaches: the clerk turns `LINTER_URL`'s
`/api/lint` into `/api/judge`. Before that file existed the clerk worked
locally, because `linter/serve.py` answers `/judge` itself, and would have
failed hosted with nothing to show for it but "Could not reach the clerk".

Smoke test by hand:

```bash
curl -s https://recourse-linter.vercel.app/api/lint                        # {"ok": true, "backend": ..., "stage2": ...}
curl -s -X POST https://recourse-linter.vercel.app/api/lint \
  -H "Content-Type: application/json" -d '{"promise": "Accurate market data."}'
# {"judgeable": false, ..., "failed_check": "no measurable term", "stage": 1}
curl -s -X POST https://recourse-linter.vercel.app/api/lint \
  -H "Content-Type: application/json" -d '{"promise": "Prices aggregated from at least three venues, refreshed within five seconds."}'
# "stage": 2 means the key reached the linter; a 503 means it did not
```

## 2. The site

**`recourse.vercel.app` is not ours.** It serves an unrelated project called
Recourse Language, checked on 11 September. A project named `recourse` gets a
team scoped address instead, and every smoke test aimed at the short name
would be testing a stranger's site, where a case permalink returns nothing and
reads as our bug. `recourse-site.vercel.app` was unclaimed the same day, and so
were `recourse-linter` and `recourse-mcp`. If `recourse-site` is taken by the
time you import, pick any free name and pass its address to the smoke script
with `--site`.

| | |
| --- | --- |
| Repository | `meitipro/Recourse` |
| Project name | `recourse-site`. Not `recourse`: see the note above this table |
| Root directory | `web` |
| Framework | Next.js (detected) |
| Include source files outside the root directory | **on** (the page reads `../eval/*.json`, `../contracts/FROZEN.json` and `../evidence/snapshot.json`; `web/next.config.mjs` traces them into the function) |
| Environment | `LINTER_URL` = `https://recourse-linter.vercel.app/api/lint`. No key: the site calls no model. `NEXT_PUBLIC_RECOURSE_NETWORK` can stay unset: it defaults to `studionet`, the only deployment, and the addresses come from `contracts/FROZEN.json` for it and need no variable. |

`LINTER_URL` is not optional here. In production the lint route answers 503
"linter not configured" without it, by design, and the panel is the first
thing a visitor tries. It must end in `/api/lint`, because the clerk derives
the judge's address from it.

Smoke test by hand:

```bash
curl -s -o /dev/null -w "%{http_code} first byte %{time_starttransfer}s\n" https://recourse-site.vercel.app/
curl -s https://recourse-site.vercel.app/case/RC-2026-0003 | grep -c "not honored"     # 1
curl -s -X POST https://recourse-site.vercel.app/api/lint \
  -H "Content-Type: application/json" -d '{"promise": "High quality results."}'
# a stage 1 refusal, not a 503 saying the linter is not configured
```

Then scroll the live page to section 06. If the evaluation is not there, the
outside root switch is off: the results files and `FROZEN.json` did not ship,
and the same miss leaves the How section's bond unnamed.

## 3. The MCP server

| | |
| --- | --- |
| Repository | `meitipro/recourse-skill` |
| Project name | `recourse-mcp` |
| Root directory | `mcp` |
| Framework | Next.js (detected) |
| Environment | `LINTER_URL` = `https://recourse-linter.vercel.app/api/lint` (defaults to the same value from `addresses.json`; set it anyway). No key: every tool is a chain read or a call to the linter. |

Smoke test, with a real MCP client:

```bash
cd recourse-skill/mcp && node test/probe.mjs https://recourse-mcp.vercel.app/api/mcp
# lists five tools, calls each; "every tool answered"
```

## After all three are live

1. `python scripts/smoke.py` passes all nine and lists the sentences that are
   now false.
2. Put the three URLs in `README.md` under Install, replacing the local ones,
   and fix every sentence the script listed.
3. Replace `docs/images/linter.png`, captured idle, with the panel in its NOT
   JUDGEABLE state on the live site (any vague promise; thirty seconds with
   the OS screenshot tool). Update the caption.
4. `git push` on either repository redeploys its projects; the Recourse push
   also runs CI.
