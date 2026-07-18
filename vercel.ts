import type { VercelConfig } from '@vercel/config/v1';

export const config: VercelConfig = {
  experimentalServices: {
    frontend: {
      entrypoint: 'frontend',
      routePrefix: '/',
      framework: 'nextjs',
    },
    backend: {
      entrypoint: 'backend',
      routePrefix: '/_/backend',
    },
  },
  crons: [
    {
      path: '/_/backend/cron/refresh-saved-analyses',
      schedule: '0 3 * * *',
    },
  ],
  git: {
    // NOTE: these keys are matched with minimatch, where a single `*` does NOT
    // cross a `/`. Branch names are frequently multi-segment — dependabot uses
    // `dependabot/<ecosystem>/<dir>/<pkg>` — so `dependabot/*` never matched and
    // the whole flock still deployed, tripping the concurrent-build limit
    // (canceled/ERROR previews). Use the `**` globstar to match every segment.
    deploymentEnabled: {
      'feat/**': false,
      'fix/**': false,
      'chore/**': false,
      'docs/**': false,
      'ops/**': false,
      'style/**': false,
      'refactor/**': false,
      'test/**': false,
      // Dependabot PRs are validated by CI (GitHub Actions) — they don't need
      // a Vercel preview. CI is the gate.
      'dependabot/**': false,
    },
  },
};
