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
    // We do not use preview deployments at all — GitHub Actions CI is the gate,
    // and previews only ever cost build minutes and produce noise. This map is
    // how that intent is expressed, and it is deny-by-enumeration rather than
    // deny-by-default for one reason: the boolean form `deploymentEnabled:
    // false` disables *every* branch including `main`, which would stop
    // production shipping entirely. In the object form, any branch NOT listed
    // here defaults to `true`. `main` is therefore deliberately absent — that
    // omission is what keeps production deploying.
    //
    // The cost of that design is that an unlisted prefix silently gets a
    // preview. That is exactly what happened on 2026-07-31: `release/**` was
    // missing, so the v1.0.11 release-prep PR (#65) was the first branch in
    // months to trigger a preview, and it failed at resource provisioning.
    // Keep this list in step with the branch prefixes actually in use.
    //
    // NOTE: keys are matched with minimatch, where a single `*` does NOT cross
    // a `/`. Branch names are frequently multi-segment — dependabot uses
    // `dependabot/<ecosystem>/<dir>/<pkg>` — so `dependabot/*` never matched and
    // the whole flock still deployed, tripping the concurrent-build limit
    // (canceled/ERROR previews). Use the `**` globstar to match every segment.
    // For the same reason a bare `'*': false` is wrong here: it would match the
    // single-segment `main` and kill production.
    deploymentEnabled: {
      'feat/**': false,
      'fix/**': false,
      'chore/**': false,
      'docs/**': false,
      'ops/**': false,
      'style/**': false,
      'refactor/**': false,
      'test/**': false,
      'release/**': false,
      'hotfix/**': false,
      'revert/**': false,
      'perf/**': false,
      'build/**': false,
      'ci/**': false,
      // Dependabot PRs are validated by CI (GitHub Actions) — they don't need
      // a Vercel preview. CI is the gate.
      'dependabot/**': false,
    },
  },
};
