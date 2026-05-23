"use client";

import { track } from "./posthog";

export type AnalyzeSubmittedProps = {
  tier: string;
  score: number;
  badge_count: number;
};

export function trackAnalyzeSubmitted(props: AnalyzeSubmittedProps): void {
  track("analyze_submitted", props);
}

export type ShareToggledProps = {
  now: "public" | "private";
};

export function trackShareToggled(props: ShareToggledProps): void {
  track("share_toggled", props);
}

export type ShareCardCopiedProps = {
  method: "url" | "png_clipboard" | "png_download";
};

export function trackShareCardCopied(props: ShareCardCopiedProps): void {
  track("share_card_copied", props);
}

export type ModeToggledProps = {
  from: "roast" | "mentor";
  to: "roast" | "mentor";
};

export function trackModeToggled(props: ModeToggledProps): void {
  track("mode_toggled", props);
}

export function trackSignInClicked(): void {
  track("sign_in_clicked", {});
}

export type ForceRefreshClickedProps = {
  target_login: string;
  duration_ms: number;
  success: boolean;
};

export function trackForceRefreshClicked(props: ForceRefreshClickedProps): void {
  track("force_refresh_clicked", props);
}
