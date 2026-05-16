# Product Vision

> The personality, voice, scoring rubric, and design principles for **Skill Issue**. This file is what keeps the product from drifting into another generic AI-SaaS dashboard.

---

## One-line pitch

> Your GitHub profile is your real resume. Skill Issue reads it honestly.

---

## Positioning

Skill Issue is **developer intelligence infrastructure**. It answers:

- Is this developer internship-ready?
- Are these projects production-grade?
- Is this profile recruiter-friendly?
- Is this person improving over time?
- Are they an OSS contributor or a tutorial archaeologist?
- Is their architecture clean or held together by emotional support imports?

It is **not** a generic AI summarizer. The defensible value is *honest, deterministic, evidence-based engineering analysis* — AI is decoration.

---

## Target users

**Primary**
- Students learning to code
- Self-taught developers building portfolios
- Job seekers (interns, new grads, switchers)
- OSS contributors looking for legibility

**Secondary**
- Recruiters and hiring managers
- Bootcamps and educators
- Developer communities and DAOs

---

## Voice and personality

Skill Issue should feel:

- **Sharp** — short sentences, no filler
- **Funny** — observational humor, not memes
- **Technically intelligent** — never hand-wavy
- **Internet-native** — comfortable with developer culture
- **Honest** — willing to say a profile is weak
- **Insightful** — every line earns its place

Skill Issue should **never** feel:

- Like a generic AI SaaS wearing Tailwind and existential dread
- Like a crypto dashboard
- Like a productivity-bro newsletter
- Like a LinkedIn motivational post

### Sample lines (calibration set)

| Mode | Example |
| --- | --- |
| Roast | "This README contains fewer instructions than IKEA furniture." |
| Roast | "Deployment frequency suggests caffeine has replaced blood." |
| Mentor | "Graduating from tutorial survivor to engineering practitioner." |
| CTO | "This repository structure files taxes on time." |
| Recruiter | "Comfortable entering unfamiliar codebases without detonating CI." |
| Career | "This profile emits architecture-review energy." |
| Career | "Strong ambition detected. Current architecture occasionally resembles ancient ruins discovered during excavation." |

These are the voice anchors. New prompts should produce lines that fit this calibration set.

---

## Identity model — tier ladder + badges (v0.3.0+)

Identity has two orthogonal axes. **Tier** is *what you are right now* on the engineering ladder. **Badges** are *what you do* — signal-driven, deterministic, stackable.

### Tier ladder (single axis, total-score based)

A profile lands in exactly one of seven tiers, derived purely from the 100-pt total. Bands are `[lower, upper)` half-open; Principal Engineer is the only band that includes its upper bound `[90, 100]`. Each tier also exposes an intra-tier sub-rank (0–100) describing how far through the band the score sits — rendered context-aware so a score at the band floor reads "Just promoted to Senior" rather than "0/100".

| Tier | Band | Signals | Headline feedback |
| --- | --- | --- | --- |
| 🌑 **Hobbyist** | `[0, 20)` | first repos, exploration, no shape yet | "Curiosity present. Engineering muscle still warming up." |
| 🌱 **Student Builder** | `[20, 35)` | experimentation, rapid stack switching, portfolio-heavy, inconsistent structure | "Curiosity level: dangerously high. Architecture stability: negotiable." |
| 🧑‍💻 **Entry-Level Engineer** | `[35, 50)` | cleaner repos, deployment attempts, improving docs, CI/CD starting | "Graduating from tutorial survivor to engineering practitioner." |
| ⚙️ **Professional Developer** | `[50, 65)` | maintainable repos, testing, issue management, consistency | "This GitHub profile has attended sprint retrospectives unwillingly." |
| 🏛 **Senior Engineer** | `[65, 80)` | scalable architecture, reusable tooling, mentoring signals | "This repository structure files taxes on time." |
| 🏛️ **Staff Engineer** | `[80, 90)` | cross-repo refactor, deep CI culture, high-volume reviews | "Operates on the codebase the way pianists operate on a keyboard." |
| 🏛️ **Principal Engineer** | `[90, 100]` | sustained, multi-year, cross-org, deep-signal saturation | "Walks into a repo and the linter sits up straighter." |

### Badge catalog (v1 — eight badges, stackable)

Badges fire whenever their deterministic trigger is met. A profile collects every badge it qualifies for — no priority ordering, no exclusivity.

| Badge | Trigger | Reads as |
| --- | --- | --- |
| 🤝 **OSS Contributor** | `external_prs_merged ≥ 10` | "Merged 12 external PRs across 3 orgs" |
| 🔁 **PR Master** | `external_prs_merged ≥ 50` | "82 external PRs merged (top-decile volume)" |
| 👀 **Maintainer** | `external_reviews ≥ 25` | "Reviewed 60 external PRs" |
| ⭐ **Star Magnet** | any non-fork repo `stars ≥ 1000` | "alice/zinc has 4,200 stars" |
| 🌐 **Polyglot** | ≥ 4 languages each ≥ 5% of total bytes | "Significant in 4 languages: Python, Go, TypeScript, Rust" |
| ⏳ **Long-haul** | account age ≥ 8 yrs AND commit in last 365 d | "Active for 11.2 years, still committing" |
| 🚀 **Indie Hacker** | `consistency ≥ 8` AND `blog` set AND `hireable=false` AND no `company` | "Consistent solo shipper with a public portfolio" |
| 🛠 **Toolmaker** | ≥ 2 non-fork repos with `stars ≥ 200` each | "3 repos with ≥200 stars" |

### Tier-gated depth signals

Higher tiers unlock progressively deeper enrichment. The 100-pt ceiling never changes — depth signals add evidence-richness and (in one case) unlock the deferred 4-pt licence signal at Pro+.

- **Professional+ (≥ 50):** licence SPDX detection (4 pts), CI workflow file count, README quality
- **Senior+ (≥ 65):** PR review depth (avg body length), dependency-ecosystem detection
- **Staff+ (≥ 80):** commit-message quality sampling, cross-repo refactor signal

A profile right under a tier threshold won't get the next tier's signals even if those signals would push it over. Self-limiting and explainable: your tier on this run earned this depth of analysis, and that's the only depth applied.

---

## Scoring rubric — 100 points

Every score must be **deterministic, evidence-backed, and explainable**. The UI shows the evidence under "Why this score." No magic numbers.

### Repository Quality — 30 pts

- README presence + quality (length, sections, code samples, license link)
- Architecture cleanliness (folder structure, separation of concerns)
- Testing (test directory, CI runs, coverage hints)
- Deployment maturity (Dockerfile, vercel.json, CI/CD config, prod URLs)
- Maintainability (recent commits, dependency hygiene, no abandoned files)
- CI/CD configuration

### Engineering Maturity — 20 pts

- Modularity (sensible module count vs. file count)
- Scalability patterns (config separation, env handling)
- Code patterns (linting config, formatter config, typed languages)
- Production readiness signals

### OSS & Collaboration — 15 pts

- External PRs opened and merged
- Issue discussions on other repos
- Reviews submitted on PRs
- Cross-org contribution diversity

### Developer Consistency — 10 pts

- Commit cadence (variance, longest dry spell)
- Long-term maintenance of older projects
- Recency of meaningful activity

### Recruiter Signal — 15 pts

- Profile README presence and quality
- Bio + location + links
- Pinned-repo curation
- Stack relevance to common job postings

### Learning Trajectory — 10 pts

- Increasing project complexity over time
- Stack diversification (with depth, not breadth alone)
- Skill evolution evident in commits

**Total = 100 exactly.** No bonus points, no curves. The total is the literal sum of the six buckets.

---

## Analysis modes

The same underlying report is rendered through five mode lenses. The scores never change between modes — only the narrative.

| Mode | Purpose | Weighted emphasis (narrative only) |
| --- | --- | --- |
| 🔥 **Roast** | Honest, funny, sharp critique | Whichever bucket scored worst |
| 🧑‍🏫 **Mentor** | Constructive growth path | Learning Trajectory + lowest two buckets |
| 🏢 **Recruiter** | "Would this candidate stand out?" | Recruiter Signal + Repo Quality |
| ⚙️ **CTO** | Maintainability and discipline | Engineering Maturity + Consistency |
| 🎓 **Career** | Internship / job / OSS readiness | Trajectory + OSS/Collab |

---

## GitHub Receipts™

Shareable scorecards. The viral surface.

- **Card format:** 1200×630 OG image
- **Variants:** dark (default), light, minimal score-only, full breakdown
- **Required surfaces:** LinkedIn, X / Twitter, generic OG
- **Design constraints:** Brand mark + score + category + one signature line. No emoji confetti. No gradient soup.

A receipt should look like something a senior engineer would actually post.

---

## Design principles

Skill Issue's UI should resemble: **Apple, Linear, Arc Browser, Stripe, modern AI-native tools**.

**Yes:**
- Generous whitespace
- Typographic hierarchy doing the heavy lifting
- One accent color, used sparingly
- Subtle, intentional motion (spring physics, not linear easing)
- Numbers and evidence rendered as first-class UI elements
- Dark mode as the default

**No:**
- Gradients on everything
- Neon glow / glassmorphism overuse
- Hero animations that move three things at once
- Crypto-dashboard aesthetics
- Emoji-driven IA
- "Generic AI SaaS" hero (orb + "Powered by AI" + vague CTA)
- Pricing tables on the landing page (until v1.0+)

---

## Anti-patterns to avoid in copy

- "Powered by AI" anywhere
- "Revolutionary," "game-changing," "next-generation"
- Long marketing paragraphs on the landing page
- Em-dashes used for drama instead of grammar
- Overuse of "your"

---

## Long-term vision

Skill Issue becomes **the reputation layer for developers**:

- Engineering credibility
- Developer identity
- GitHub intelligence
- Growth analysis
- Technical reputation

Not just analytics. Not just AI summaries. The operating system for developer identity.

---

## The single most important rule

> The platform must always feel **technically grounded, brutally honest, insightful, useful, and explainable**.
>
> Humor is the spice. Engineering insight is the actual product.
