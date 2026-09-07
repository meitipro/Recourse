# Hosting

Three Vercel projects from two repositories. The token available to the build
that wrote this could list the team's projects but not create one, so each is
a dashboard import. Every setting that matters is below; nothing else needs
changing.

The project names matter. `recourse-skill/reference/07-addresses.json` and
`recourse-skill/.claude-plugin/plugin.json` already name the URLs the projects
will have if they are called exactly `recourse-linter` and `recourse-mcp`. Use
those names, or update both files afterwards.

## 1. The linter

| | |
| --- | --- |
| Repository | `meitipro/Recourse` |
| Project name | `recourse-linter` |
| Root directory | `.` (the repository root; the function is `api/lint.py`) |
| Framework | Other |
| Environment | `ANTHROPIC_API_KEY` (stage 2 and the rewrite; without it stage 1 still answers and stage 2 says 503) |

Smoke test:

```bash
curl -s https://recourse-linter.vercel.app/api/lint                        # {"ok": true, "backend": ..., "stage2": ...}
curl -s -X POST https://recourse-linter.vercel.app/api/lint \
  -H "Content-Type: application/json" -d '{"promise": "Accurate market data."}'
# {"judgeable": false, ..., "failed_check": "no measurable term", "stage": 1}
```

## 2. The site

| | |
| --- | --- |
| Repository | `meitipro/Recourse` |
| Project name | `recourse` |
| Root directory | `web` |
| Framework | Next.js (detected) |
| Include source files outside the root directory | **on** (the page reads `../eval/*.json` and `../contracts/FROZEN.json`; `web/next.config.mjs` traces them into the function) |
| Environment | `LINTER_URL` = `https://recourse-linter.vercel.app/api/lint`, `NEXT_PUBLIC_RECOURSE_NETWORK` = `studionet`, `NEXT_PUBLIC_RECOURSE_ESCROW` = `0x5125De939F7373eAE741B133FB32B7E9915C8F78`, `NEXT_PUBLIC_RECOURSE_DISPUTE` = `0x80A98929EcA334804dbB04d31F6050bca42C0Cc4` |

`LINTER_URL` is not optional here. In production the lint route answers 503
"linter not configured" without it, by design, and the panel is the first
thing a visitor tries.

Smoke test:

```bash
curl -s -o /dev/null -w "%{http_code} first byte %{time_starttransfer}s\n" https://recourse.vercel.app/
curl -s https://recourse.vercel.app/case/RC-2026-0003 | grep -c "not honored"     # 1
curl -s -X POST https://recourse.vercel.app/api/lint \
  -H "Content-Type: application/json" -d '{"promise": "High quality results."}'
```

## 3. The MCP server

| | |
| --- | --- |
| Repository | `meitipro/recourse-skill` |
| Project name | `recourse-mcp` |
| Root directory | `mcp` |
| Framework | Next.js (detected) |
| Environment | `LINTER_URL` = `https://recourse-linter.vercel.app/api/lint` (defaults to the same value from `addresses.json`; set it anyway) |

Smoke test, with a real MCP client:

```bash
cd recourse-skill/mcp && node test/probe.mjs https://recourse-mcp.vercel.app/api/mcp
# lists five tools, calls each; "every tool answered"
```

## After all three are live

1. Put the three URLs in `README.md` under Install, replacing the local ones.
2. Replace `docs/images/linter.png`, captured idle, with the panel in its NOT
   JUDGEABLE state on the live site (any vague promise; thirty seconds with
   the OS screenshot tool). Update the caption.
3. `git push` on either repository redeploys its projects; the Recourse
   push also runs CI.
