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
    deploymentEnabled: {
      'feat/*': false,
      'fix/*': false,
      'chore/*': false,
      'docs/*': false,
      'ops/*': false,
      'style/*': false,
      'refactor/*': false,
      'test/*': false,
      // Dependabot PRs are validated by CI (GitHub Actions) — they don't need
      // a Vercel preview, and letting the whole flock deploy at once trips the
      // concurrent-build limit (canceled/ERROR previews). CI is the gate.
      'dependabot/*': false,
    },
  },
};
