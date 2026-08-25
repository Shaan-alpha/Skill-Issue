"use client";

import { useEffect, useRef, useState } from "react";
import { NarrativeMode } from "@/types";
import { createNarrativeEventSource } from "@/lib/sse";
import { closeOffTruncated, stripMarkdownEmphasis } from "@/lib/narrative-text";
import { AnimatePresence, m } from "framer-motion";
import { AlertCircle, Loader2, RotateCcw, Sparkles, WifiOff } from "lucide-react";

// Kept in sync with `_HEADER_BY_REASON` in backend/app/narrative/fallback.py.
const FALLBACK_HEADERS = [
  "[AI narrator offline — daily cap reached]",
  "[AI narrator offline — upstream hiccup]",
] as const;

interface NarrativeStreamProps {
  username: string;
  mode: NarrativeMode;
}

export function NarrativeStream({ username, mode }: NarrativeStreamProps) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<
    "idle" | "streaming" | "complete" | "error"
  >("streaming");
  const [truncated, setTruncated] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  // With `cacheComponents: true`, Next 16 hides a route behind
  // React's <Activity> instead of unmounting it. Effects tear down and re-run
  // on every hide→show transition while useState survives, so a browser
  // back-then-forward re-ran this effect on top of the text it had already
  // accumulated — the narrative doubled, then tripled, once per round trip.
  // The ref records which stream already finished (refs survive the same
  // transitions), so a re-show reuses the completed text instead of reopening
  // the stream and appending the backend's cached replay.
  const streamId = `${username}:${mode}:${retryKey}`;
  const completedStreamRef = useRef<string | null>(null);

  useEffect(() => {
    if (completedStreamRef.current === streamId) return;

    // Accumulate per connection rather than off the previous render's state:
    // a restarted stream must replace what a torn-down one left behind.
    let buffer = "";
    setText("");
    setTruncated(false);
    setStatus("streaming");

    const cleanup = createNarrativeEventSource(
      username,
      mode,
      (chunk) => {
        buffer += chunk;
        setText(buffer);
      },
      () => {
        setStatus("error");
      },
      ({ truncated: wasTruncated }) => {
        completedStreamRef.current = streamId;
        setTruncated(wasTruncated);
        setStatus("complete");
      }
    );

    return () => cleanup();
  }, [username, mode, streamId]);

  // Both fallback headers, not just the budget one: the error header used to
  // fall through and render as literal bracketed text inside the narrative,
  // with no offline badge to explain it.
  const fallbackHeader = FALLBACK_HEADERS.find((h) => text.includes(h));
  const isFallback = fallbackHeader !== undefined;

  // Strip markdown the model emitted despite the prompt saying not to — there
  // is no markdown renderer here, so `**like this**` reaches the reader as
  // literal asterisks. Then close off a narrative cut short at the token
  // ceiling, once the stream is done and the text has stopped growing.
  const withoutHeader = isFallback
    ? text.replace(`${fallbackHeader}\n\n`, "")
    : text;
  const cleaned = stripMarkdownEmphasis(withoutHeader);
  const displayText =
    status === "complete" && truncated ? closeOffTruncated(cleaned) : cleaned;

  // A stream that finished having produced nothing used to render an empty
  // box: `displayText` was falsy and the spinner was gated on `streaming`.
  const isEmptyResult = status === "complete" && displayText.trim() === "";

  return (
    <div className="relative rounded-2xl bg-white/5 border border-white/10 p-6 backdrop-blur-md min-h-[140px] flex flex-col justify-between overflow-hidden shadow-xl">
      {/* Background ambient glow based on mode */}
      <div
        className={`absolute -top-24 -right-24 w-48 h-48 rounded-full blur-3xl opacity-20 pointer-events-none transition-all duration-700 ${
          mode === "roast" ? "bg-red-500" : "bg-blue-500"
        }`}
      />

      {status === "error" ? (
        <div className="flex flex-col items-center justify-center py-6 text-center space-y-3 z-10">
          <AlertCircle className="w-8 h-8 text-red-400" />
          <div className="text-sm font-medium text-white">
            Connection Interrupted
          </div>
          <p className="text-xs text-muted-foreground max-w-sm">
            We encountered a hiccup while streaming your AI analysis.
          </p>
          <button
            onClick={() => {
              setText("");
              setStatus("streaming");
              setRetryKey((k) => k + 1);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/15 text-xs text-white font-medium transition-colors border border-white/10"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Retry Streaming</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4 z-10">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5 font-medium tracking-wide uppercase text-[11px] text-white/80">
              <Sparkles
                className={`w-3.5 h-3.5 ${
                  mode === "roast" ? "text-red-400" : "text-blue-400"
                }`}
              />
              <span>AI {mode === "roast" ? "Roast" : "Mentorship"}</span>
            </div>

            {isFallback ? (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 font-mono text-[10px] uppercase tracking-wider animate-pulse">
                <WifiOff className="w-3 h-3" />
                <span>Narrator Offline (Fallback Mode)</span>
              </div>
            ) : (
              status === "streaming" && (
                <div className="flex items-center gap-1.5 text-accent animate-pulse">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span className="text-[10px] uppercase font-semibold tracking-wider">
                    Analyzing
                  </span>
                </div>
              )
            )}
          </div>

          <div className="text-sm leading-relaxed text-white/90 font-sans whitespace-pre-wrap selection:bg-accent selection:text-white">
            {displayText ? (
              <AnimatePresence mode="popLayout">
                <m.span
                  key="content-text"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  {displayText}
                </m.span>
                {status === "streaming" && (
                  <m.span
                    key="cursor-blink"
                    animate={{ opacity: [1, 0.2, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                    className="inline-block w-2 h-3 ml-1 bg-white/70 align-middle"
                  />
                )}
              </AnimatePresence>
            ) : isEmptyResult ? (
              <div className="flex flex-col items-center justify-center py-6 text-center space-y-3">
                <AlertCircle className="w-6 h-6 text-yellow-400" />
                <div className="text-xs text-muted-foreground max-w-sm">
                  The narrator returned nothing this time. That is usually a
                  blip — try again.
                </div>
                <button
                  onClick={() => {
                    setText("");
                    setTruncated(false);
                    setStatus("streaming");
                    setRetryKey((k) => k + 1);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/15 text-xs text-white font-medium transition-colors border border-white/10"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Try Again</span>
                </button>
              </div>
            ) : (
              status === "streaming" && (
                <div className="flex flex-col items-center justify-center py-8 text-center space-y-2">
                  <div className="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin" />
                  <div className="text-xs text-muted-foreground animate-pulse">
                    Examining commit patterns and engineering depth...
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}
