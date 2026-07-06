---
name: verify
description: Run Skill Issue locally (FastAPI backend + Next.js frontend) and verify UI changes at real breakpoints via headless-Chrome CDP screenshots and geometry probes.
---

# Verifying Skill Issue changes locally

Full-stack app: Next.js frontend (`frontend/`, port 3000) renders report pages
by server-fetching the FastAPI backend (`backend/`, port 8000). Report pages
(`/u/{username}`) need **both** processes.

## Launch

```powershell
# Backend — backend/.env already holds GITHUB_TOKEN (enough for /analyze).
# No DATABASE_URL locally => auth/share/history routes degrade gracefully;
# pages render in the signed-out state.
cd backend; uv run uvicorn app.main:app --port 8000

# Frontend — MUST raise the heap or next dev OOM-crashes on cold compile.
cd frontend; $env:NODE_OPTIONS='--max-old-space-size=2048'; npm run dev
```

Ready when `curl localhost:8000/health` and `curl localhost:3000/` are both 200.

## Drive + capture

Headless Chrome CDP, no extra deps beyond `pip install websocket-client`
(already present). Chrome lives at
`C:\Program Files\Google\Chrome\Application\chrome.exe`.

Existing recipe scripts (copy + adapt):
- `frontend/scripts/check_overflow.py` — launches headless Chrome with
  `--remote-debugging-port`, sets `Emulation.setDeviceMetricsOverride`,
  navigates, evaluates JS. Extend the same skeleton with
  `Page.captureScreenshot` (base64 PNG) and
  `getBoundingClientRect` probes to assert element geometry per width.
- Standard widths: 1440 / 1024 / 768 / 390. Overflow check:
  `document.documentElement.scrollWidth - window.innerWidth` must be ≤ 0.

Useful targets:
- `/u/octocat` — small profile, fast analyze, good default page.
- `/u/<uncached-user>` — analysis takes seconds; screenshot ~1.2s after
  `Page.navigate` to capture the `loading.tsx` skeleton, then wait for
  `input[aria-label="GitHub username"]` to exist for the real page.

## Gotchas

- First navigation compiles the route in dev — allow up to ~150s before
  declaring the page dead; poll with `Runtime.evaluate` every 2s.
- Backend caches analyses 6h in-process; without Upstash env every cold
  process re-analyzes (GitHub API calls) — keep target users small.
- Signed-in and `/share/{slug}` variants are NOT drivable locally (no
  DATABASE_URL / OAuth credentials in `backend/.env`) — say so in the
  report instead of faking them.
- The dev overlay shows a red "N Issues" bubble; known pre-existing dev
  console errors (auth `getServerSnapshot`, uncached-promise suspension,
  Base UI `nativeButton` warning, anonymous 401 on `/me`) — don't pin
  them on an unrelated diff, but do check the count didn't grow.
