import { NarrativeMode } from "@/types";

export function createNarrativeEventSource(
  username: string,
  mode: NarrativeMode,
  onChunk: (text: string) => void,
  onError: (err: unknown) => void,
  onComplete: (info: { truncated: boolean }) => void
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
      // v1.0.7 SI-33: the backend ends the stream with an explicit done sentinel.
      // Receiving it is the ONLY signal of a successful completion.
      if (data.done) {
        es.close();
        // `truncated` means the model hit its token ceiling mid-sentence, so
        // the caller should close the narrative off rather than render the
        // ragged edge. Absent on older backends — treat that as not truncated.
        onComplete({ truncated: data.truncated === true });
        return;
      }
      if (data.chunk) {
        onChunk(data.chunk);
      }
    } catch (err) {
      onError(err);
    }
  };

  es.onerror = () => {
    // A connection error before the done sentinel is a genuine failure — surface
    // it instead of masquerading as a completed stream (SI-33).
    es.close();
    onError(new Error("narrative stream connection failed"));
  };

  return () => {
    es.close();
  };
}
