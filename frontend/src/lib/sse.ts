import { NarrativeMode } from "@/types";

export function createNarrativeEventSource(
  username: string,
  mode: NarrativeMode,
  onChunk: (text: string) => void,
  onError: (err: unknown) => void,
  onComplete: () => void
): () => void {
  const baseUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const url = `${baseUrl}/narrative/${encodeURIComponent(
    username
  )}?mode=${mode}`;
  const es = new EventSource(url);

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.chunk) {
        onChunk(data.chunk);
      }
    } catch (err) {
      onError(err);
    }
  };

  es.onerror = () => {
    es.close();
    onComplete();
  };

  return () => {
    es.close();
  };
}
