"use client";

import { useEffect, useState } from "react";
import { NarrativeMode } from "@/types";
import { createNarrativeEventSource } from "@/lib/sse";
import { AnimatePresence, m } from "framer-motion";
import { AlertCircle, Loader2, RotateCcw, Sparkles } from "lucide-react";

interface NarrativeStreamProps {
  username: string;
  mode: NarrativeMode;
}

export function NarrativeStream({ username, mode }: NarrativeStreamProps) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<
    "idle" | "streaming" | "complete" | "error"
  >("idle");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    setText("");
    setStatus("streaming");

    const cleanup = createNarrativeEventSource(
      username,
      mode,
      (chunk) => {
        setText((prev) => prev + chunk);
      },
      () => {
        setStatus("error");
      },
      () => {
        setStatus("complete");
      }
    );

    return () => cleanup();
  }, [username, mode, retryKey]);

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
            onClick={() => setRetryKey((k) => k + 1)}
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

            {status === "streaming" && (
              <div className="flex items-center gap-1.5 text-accent animate-pulse">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span className="text-[10px] uppercase font-semibold tracking-wider">
                  Analyzing
                </span>
              </div>
            )}
          </div>

          <div className="text-sm leading-relaxed text-white/90 font-sans whitespace-pre-wrap selection:bg-accent selection:text-white">
            {text ? (
              <AnimatePresence mode="popLayout">
                <m.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  {text}
                </m.span>
                {status === "streaming" && (
                  <m.span
                    animate={{ opacity: [1, 0.2, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                    className="inline-block w-2 h-3 ml-1 bg-white/70 align-middle"
                  />
                )}
              </AnimatePresence>
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
