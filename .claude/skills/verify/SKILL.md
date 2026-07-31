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
- The dev overlay shows a red "N Issues" bubble. **Treat console errors as
  defects until proven otherwise — this list was wrong.** Three of the four
  entries it used to carry were real bugs, not noise:
  - auth `getServerSnapshot` + uncached-promise suspension — one root cause,
    `getServerSnapshot` minting a fresh promise per call. React's own wording
    ("to avoid an infinite loop") said so all along. Fixed.
  - Base UI `nativeButton` warning — the badge trigger was reaching the
    accessibility tree as `generic`, so badge evidence was unreachable to a
    screen reader. Fixed.
  - anonymous 401 on `/me` — genuinely benign. An anonymous visitor has no
    session; `fetchSessionFresh` handles the 401 and returns null. The browser
    logs the failed request; nothing is broken.

  So the baseline is now **one** expected entry (the 401), not four. Anything
  else is a regression or an undiagnosed bug — investigate before shipping,
  and only add to this list with a written reason it is inert.
- Verify anything involving portals, layout, or paint in this browser
  harness, not in vitest. happy-dom does not compute layout and handles
  portals differently from Chrome; a jsdom-only failure is evidence about
  the test environment, not the product. (An `<Activity>` popover "leak" was
  chased and a fix written on jsdom evidence before Chrome showed the bug
  did not exist.)
- Drive route changes through the app's own UI (fill the search bar, click
  its button) rather than `Page.navigate`. `Page.navigate` is a full document
  load, so it tears down client state and the App Router's `<Activity>`
  boundaries — any test about back/forward or preserved state silently passes
  under it while proving nothing.
