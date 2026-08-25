/**
 * Presentation repairs for streamed narrative text.
 *
 * The narrative is rendered verbatim inside a `whitespace-pre-wrap` block —
 * there is no markdown parser in the bundle and adding one for three
 * paragraphs of prose would be a poor trade. The prompts tell both voices to
 * emit plain text, but prompt compliance is probabilistic, so these are the
 * belt to the prompt's braces: whatever markdown slips through gets unwrapped
 * here rather than reaching the reader as literal punctuation.
 */

// Bold before italic: matching `*` first would eat `**x**` as two empty
// italics and swallow the word between them.
const BOLD = /\*\*([^*]+)\*\*/g;
const ITALIC = /\*([^*\n]+)\*/g;
const CODE_SPAN = /`([^`\n]+)`/g;
const HEADING = /^#{1,6}[ \t]+/gm;
// A marker whose closing partner has not streamed in yet.
const DANGLING_MARKER = /[*`]+$/;

/**
 * Unwrap markdown emphasis, keeping the words inside it.
 *
 * Underscores are deliberately left alone: they are load-bearing in the
 * identifiers these narratives quote (`engineering_maturity`, `__init__`), and
 * mangling those is worse than the rare `_italic_` surviving.
 */
export function stripMarkdownEmphasis(text: string): string {
  if (!text) return text;
  return text
    .replace(BOLD, "$1")
    .replace(ITALIC, "$1")
    .replace(CODE_SPAN, "$1")
    .replace(HEADING, "")
    .replace(DANGLING_MARKER, "");
}

// A sentence ending, optionally followed by a closing quote or bracket.
const ENDS_A_SENTENCE = /[.!?…]["'”’)\]]?$/;
const SENTENCE_STOPS = [".", "!", "?", "…"];

/**
 * Close off a narrative the model stopped mid-sentence.
 *
 * Called only when the backend reports `truncated` on the done sentinel. Text
 * with no sentence boundary at all is returned unchanged — a ragged last line
 * still beats an empty card.
 */
export function closeOffTruncated(text: string): string {
  const trimmed = text.trimEnd();
  if (!trimmed || ENDS_A_SENTENCE.test(trimmed)) return trimmed;

  const lastStop = Math.max(...SENTENCE_STOPS.map((s) => trimmed.lastIndexOf(s)));
  if (lastStop === -1) return trimmed;
  return trimmed.slice(0, lastStop + 1);
}
