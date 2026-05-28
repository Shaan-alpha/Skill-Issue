import type { Metadata } from "next";
import { LegalProse, LegalSection } from "@/components/legal-prose";

export const metadata: Metadata = {
  title: "Privacy Policy — Skill Issue",
  description: "What Skill Issue collects, how it's used, and your choices.",
};

const EMAIL = "shaansatsangi.cse@gmail.com";

export default function PrivacyPage() {
  return (
    <LegalProse title="Privacy Policy" lastUpdated="2026-05-28">
      <p>
        Skill Issue is operated by Shaan Satsangi (&ldquo;we&rdquo;). This policy explains, in plain
        language, what we collect, why, and the choices you have. We collect as little as we need to
        run the service.
      </p>

      <LegalSection heading="What we collect">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong className="text-foreground">GitHub profile (if you sign in).</strong> We use
            GitHub OAuth with read-only <code>read:user</code> scope to read your public profile
            (login, name, avatar). Your GitHub access token is encrypted at rest.
          </li>
          <li>
            <strong className="text-foreground">Analyses and history.</strong> When signed in, the
            analyses you run are saved to your history until you delete them.
          </li>
          <li>
            <strong className="text-foreground">IP address.</strong> Used transiently to rate-limit
            requests and prevent abuse.
          </li>
          <li>
            <strong className="text-foreground">Usage and error data.</strong> Aggregate product
            analytics and error reports help us keep the service working.
          </li>
          <li>
            <strong className="text-foreground">A session cookie.</strong> Keeps you signed in.
          </li>
        </ul>
      </LegalSection>

      <LegalSection heading="How we use it">
        <p>
          To generate and display your report, save your history when you&rsquo;re signed in, prevent
          abuse, and improve reliability. We do not sell your data or use it for advertising.
        </p>
      </LegalSection>

      <LegalSection heading="Who we share it with">
        <p>We rely on a few service providers to run Skill Issue:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong className="text-foreground">GitHub</strong> — the source of the public data we
            analyze.
          </li>
          <li>
            <strong className="text-foreground">Vercel</strong> — hosting.
          </li>
          <li>
            <strong className="text-foreground">Neon</strong> — database (accounts, saved analyses).
          </li>
          <li>
            <strong className="text-foreground">Upstash</strong> — short-lived caching and
            rate-limit counters.
          </li>
          <li>
            <strong className="text-foreground">Groq</strong> — generates the AI narrative from your
            report.
          </li>
          <li>
            <strong className="text-foreground">Sentry</strong> — error monitoring.
          </li>
          <li>
            <strong className="text-foreground">PostHog</strong> — product analytics.
          </li>
        </ul>
      </LegalSection>

      <LegalSection heading="How long we keep it">
        <p>
          Sign-in sessions expire after about 30 days. Saved analyses stay until you delete them.
          Caches are short-lived and expire automatically.
        </p>
      </LegalSection>

      <LegalSection heading="Your choices">
        <p>
          You can delete saved analyses from your history, sign out at any time, and revoke
          Skill Issue&rsquo;s access from your{" "}
          <a
            href="https://github.com/settings/applications"
            target="_blank"
            rel="noopener noreferrer"
            className="text-foreground underline underline-offset-4 hover:text-accent"
          >
            GitHub application settings
          </a>
          .
        </p>
      </LegalSection>

      <LegalSection heading="Cookies">
        <p>
          We use a session cookie to keep you signed in and a short-lived cookie during the GitHub
          sign-in flow. We do not use advertising or cross-site tracking cookies.
        </p>
      </LegalSection>

      <LegalSection heading="Children">
        <p>Skill Issue is intended for users aged 13 and older, consistent with GitHub.</p>
      </LegalSection>

      <LegalSection heading="Changes">
        <p>
          We may update this policy; the &ldquo;last updated&rdquo; date above reflects the latest
          version.
        </p>
      </LegalSection>

      <LegalSection heading="Contact">
        <p>
          Questions? Email{" "}
          <a
            href={`mailto:${EMAIL}`}
            className="text-foreground underline underline-offset-4 hover:text-accent"
          >
            {EMAIL}
          </a>
          .
        </p>
      </LegalSection>
    </LegalProse>
  );
}
