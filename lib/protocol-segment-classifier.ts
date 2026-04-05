/**
 * Per-word logistic regression classifier that detects protocol segments
 * in mixed dictations (e.g., "I want to check the directory ls dash la").
 *
 * Identifies protocol anchor words (dash, dot, slash, space, etc.), then
 * expands ±2 words to capture adjacent command tokens (ls, git, etc.).
 * Natural speech passes through untouched.
 *
 * Ported from `macOS/TalkieKit/Sources/TalkieKit/ProtocolSegmentClassifier.swift`.
 * Model weights from `pipeline/segment-classifier-model.json`.
 */

// ── Model Parameters ────────────────────────────────────────────────────

const WEIGHTS = [
  +0.33411720958159186,  // is_strong_protocol
  -0.01883618036579912,  // is_weak_protocol
  +0.00000000000000000,  // is_expanded_symbol
  +0.00000000000000000,  // has_syntax_chars
  -0.09512784613770699,  // word_length_norm
  -0.27082908357760427,  // is_short_word
  +0.25826009349206092,  // context_strong_density
  +0.24189819020570574,  // context_any_density
  +0.35690881474192121,  // left_is_strong
  +0.33751703709094505,  // right_is_strong
  +0.09194955109384083,  // is_number_like
  +1.05151196243534240,  // strong_neighbor_count
  -0.17715608130670168,  // is_all_lower
  -0.11667765899752854,  // position_ratio
];

const BIAS = -1.126425236495759;
const THRESHOLD = 0.5;

// ── Vocabulary Sets ─────────────────────────────────────────────────────

/** Strong protocol words — almost never appear in natural speech */
const STRONG_PROTOCOL = new Set([
  "dash", "dot", "slash", "pipe", "tilde", "hash", "dollar",
  "caret", "ampersand", "equals", "underscore", "backslash",
  "backtick", "semicolon", "colon",
  "minus", "hyphen", "asterisk", "hashtag",
  "paren", "brace", "bracket", "parenthesis", "curly",
  "capital", "caps", "camel", "snake", "pascal", "kebab", "screaming",
  "space",
  "redirect", "append",
]);

/** Weak protocol words — frequently appear in natural speech */
const WEAK_PROTOCOL = new Set([
  "at", "star", "bang", "exclamation", "question", "comma", "quote",
  "period", "plus", "percent",
  "single", "open", "close", "angle", "forward", "back", "sign",
  "double", "mark", "than", "less", "new", "line", "all", "case",
]);

/** Expanded symbols (after symbolic mapping) */
const EXPANDED_SYMBOLS = new Set([
  "-", ".", "/", "\\", "_", "|", "~", "@", "#", "*",
  "+", "=", ":", ";", "&", "%", "^", "!", "?", "`",
  "$", "<", ">", "--", "&&", "||",
]);

const SYNTAX_CHARS = new Set([
  "-", ".", "/", "\\", "_", "|", "~", "@", "#", ":", "=",
]);

const NUMBER_WORDS = new Set([
  "zero", "one", "two", "three", "four", "five", "six",
  "seven", "eight", "nine", "ten",
]);

// ── Segment Types ───────────────────────────────────────────────────────

export type SegmentKind = "passthrough" | "protocol";

export interface TextSegment {
  kind: SegmentKind;
  text: string;
}

// ── Feature Names ───────────────────────────────────────────────────────

export const FEATURE_NAMES = [
  "is_strong_protocol",
  "is_weak_protocol",
  "is_expanded_symbol",
  "has_syntax_chars",
  "word_length_norm",
  "is_short_word",
  "context_strong_density",
  "context_any_density",
  "left_is_strong",
  "right_is_strong",
  "is_number_like",
  "strong_neighbor_count",
  "is_all_lower",
  "position_ratio",
];

// ── Helpers ─────────────────────────────────────────────────────────────

function sigmoid(x: number): number {
  return 1.0 / (1.0 + Math.exp(-x));
}

function dot(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) {
    sum += a[i] * b[i];
  }
  return sum;
}

function stripPunctuation(s: string): string {
  return s.replace(/^[^\w]+|[^\w]+$/g, "");
}

function isStrongProtocol(word: string): boolean {
  const lower = stripPunctuation(word.toLowerCase());
  if (STRONG_PROTOCOL.has(lower)) return true;
  return EXPANDED_SYMBOLS.has(word.trim());
}

function isAnyProtocol(word: string): boolean {
  const lower = stripPunctuation(word.toLowerCase());
  if (STRONG_PROTOCOL.has(lower) || WEAK_PROTOCOL.has(lower)) return true;
  return EXPANDED_SYMBOLS.has(word.trim());
}

function isAllDigits(s: string): boolean {
  return /^\d+$/.test(s);
}

function isAllLowerAlpha(s: string): boolean {
  return /^[a-z]+$/.test(s);
}

// ── Feature Extraction ──────────────────────────────────────────────────

function extractFeatures(
  word: string,
  position: number,
  words: string[]
): number[] {
  const lower = stripPunctuation(word.toLowerCase());
  const stripped = word.trim();
  const total = words.length;

  // Build context window ±2
  const ctxStart = Math.max(0, position - 2);
  const ctxEnd = Math.min(total, position + 3);
  const context = words.slice(ctxStart, ctxEnd);

  // Feature 0: is_strong_protocol
  const fStrong = STRONG_PROTOCOL.has(lower) ? 1.0 : 0.0;

  // Feature 1: is_weak_protocol
  const fWeak = WEAK_PROTOCOL.has(lower) ? 1.0 : 0.0;

  // Feature 2: is_expanded_symbol
  const fSymbol = EXPANDED_SYMBOLS.has(stripped) ? 1.0 : 0.0;

  // Feature 3: has_syntax_chars
  let fSyntax = 0.0;
  if ([...lower].some(c => SYNTAX_CHARS.has(c))) {
    const isContraction = word.includes("'") || word.includes("\u2019");
    const isTrailingPeriod =
      word.endsWith(".") && !word.slice(0, -1).includes(".");
    if (!isContraction && !isTrailingPeriod) {
      fSyntax = 1.0;
    }
  }

  // Feature 4: word_length_norm
  const fLen = word.length / 10.0;

  // Feature 5: is_short_word
  const fShort = lower.length <= 3 ? 1.0 : 0.0;

  // Feature 6: context_strong_density
  const ctxStrongCount = context.filter(isStrongProtocol).length;
  const fCtxStrong = ctxStrongCount / Math.max(context.length, 1);

  // Feature 7: context_any_density
  const ctxAnyCount = context.filter(isAnyProtocol).length;
  const fCtxAny = ctxAnyCount / Math.max(context.length, 1);

  // Feature 8: left_is_strong
  const fLeft =
    position > 0 && isStrongProtocol(words[position - 1]) ? 1.0 : 0.0;

  // Feature 9: right_is_strong
  const fRight =
    position < total - 1 && isStrongProtocol(words[position + 1]) ? 1.0 : 0.0;

  // Feature 10: is_number_like
  const fNumber =
    NUMBER_WORDS.has(lower) || isAllDigits(lower) ? 1.0 : 0.0;

  // Feature 11: strong_neighbor_count
  const fStrongNeighbors = ctxStrongCount;

  // Feature 12: is_all_lower
  const fLower =
    /^[a-zA-Z]+$/.test(word) && word === word.toLowerCase() ? 1.0 : 0.0;

  // Feature 13: position_ratio
  const fPos = position / Math.max(total - 1, 1);

  return [
    fStrong, fWeak, fSymbol, fSyntax,
    fLen, fShort,
    fCtxStrong, fCtxAny,
    fLeft, fRight,
    fNumber, fStrongNeighbors,
    fLower, fPos,
  ];
}

// ── Classification ──────────────────────────────────────────────────────

/**
 * Classify a single word in context. Returns probability of being a protocol word.
 */
export function classifyWord(
  word: string,
  position: number,
  words: string[]
): number {
  const features = extractFeatures(word, position, words);
  const logit = dot(features, WEIGHTS) + BIAS;
  return sigmoid(logit);
}

/**
 * Extract protocol segments from mixed dictation text.
 * Returns segments split into passthrough (natural speech) and protocol (needs processing).
 */
export function extractSegments(text: string): TextSegment[] {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];

  // Step 1: Classify each word as protocol anchor
  const isAnchor = words.map((w, i) => classifyWord(w, i, words) >= THRESHOLD);

  // No anchors → entire text is passthrough
  if (!isAnchor.some(Boolean)) {
    return [{ kind: "passthrough", text }];
  }

  // Step 2: Expand ±2 around anchors
  const inProtocol = new Array(words.length).fill(false);
  for (let i = 0; i < words.length; i++) {
    if (isAnchor[i]) {
      const start = Math.max(0, i - 2);
      const end = Math.min(words.length - 1, i + 2);
      for (let j = start; j <= end; j++) {
        inProtocol[j] = true;
      }
    }
  }

  // Step 3: Build contiguous segments
  const segments: TextSegment[] = [];
  let currentKind: SegmentKind = inProtocol[0] ? "protocol" : "passthrough";
  let currentWords: string[] = [words[0]];

  for (let i = 1; i < words.length; i++) {
    const kind: SegmentKind = inProtocol[i] ? "protocol" : "passthrough";
    if (kind === currentKind) {
      currentWords.push(words[i]);
    } else {
      segments.push({ kind: currentKind, text: currentWords.join(" ") });
      currentKind = kind;
      currentWords = [words[i]];
    }
  }
  segments.push({ kind: currentKind, text: currentWords.join(" ") });

  return segments;
}

/**
 * Returns true if the text contains any protocol segments.
 */
export function hasProtocolSegments(text: string): boolean {
  return extractSegments(text).some(s => s.kind === "protocol");
}
