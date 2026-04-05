/**
 * Binary classifier: does this dictated input need LLM normalization?
 *
 * Uses hand-crafted features + logistic regression (10 weights + bias).
 * Returns true if the input is fuzzy/natural/chaotic and needs LLM.
 * Returns false if the input is clean protocol and the procedural processor can handle it.
 *
 * Ported from `scripts/needs-llm-classifier.py`.
 * Model weights from `pipeline/needs-llm-model.json`.
 */

// ── Model Parameters ────────────────────────────────────────────────────

const WEIGHTS = [
  -1.7262899181892912,  // space_ratio
  -4.262508378155058,   // space_present
  -0.9437095996085207,  // protocol_ratio
   2.1420661962764926,  // filler_count
   3.324701471305833,   // intent_count
   0.14425229651354413, // correction_count
  -3.2102164965682594,  // starts_casing
   0.30804019879345856, // word_count
   0.9174257808985996,  // non_protocol_ratio
  -0.09508729183500425, // avg_word_len
];

const BIAS = 2.6924004765246026;
const THRESHOLD = 0.5;

// ── Vocabulary Sets ─────────────────────────────────────────────────────

const PROTOCOL_VOCAB = new Set([
  // Symbol words
  "dash", "dot", "slash", "pipe", "redirect", "append", "less", "star",
  "bang", "hash", "tilde", "at", "dollar", "percent", "caret", "ampersand",
  "equals", "plus", "colon", "semicolon", "underscore", "comma", "backslash",
  "quote", "backtick", "question",
  // Synonyms
  "minus", "hyphen", "period", "asterisk", "hashtag",
  // Two-word symbol components
  "single", "open", "close", "paren", "brace", "bracket", "angle", "curly",
  "than", "mark", "double", "and", "forward", "back", "sign", "new", "line",
  "parenthesis",
  // Casing
  "capital", "all", "caps", "camel", "snake", "pascal", "kebab", "screaming",
  "case",
  // Space
  "space",
  // Number words
  "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
  "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
  "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty",
  "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand",
]);

const FILLER_WORDS = new Set([
  "okay", "ok", "so", "um", "uh", "umm", "like", "basically",
  "actually", "right", "alright", "yeah", "well", "hmm",
]);

const INTENT_PHRASES = [
  "i want", "i wanna", "can you", "let's", "let me", "we need",
  "type out", "should be", "go ahead", "i need", "i think",
  "we want", "the command", "just do", "run it", "make it",
  "change", "set the", "for the", "use the", "add the",
];

const CORRECTION_PHRASES = [
  "no wait", "wait no", "scratch", "not that", "go back",
  "actually no", "never mind", "hold on", "start over",
];

const CASING_STARTERS = new Set([
  "camel", "snake", "pascal", "kebab", "screaming",
]);

// ── Feature Names (for documentation) ───────────────────────────────────

export const FEATURE_NAMES = [
  "space_ratio",
  "space_present",
  "protocol_ratio",
  "filler_count",
  "intent_count",
  "correction_count",
  "starts_casing",
  "word_count",
  "non_protocol_ratio",
  "avg_word_len",
];

// ── Feature Extraction ──────────────────────────────────────────────────

/** Extract 10 numeric features from dictated text. */
export function extractFeatures(text: string): number[] {
  const words = text.toLowerCase().split(/\s+/).filter(Boolean);
  const n = words.length;
  if (n === 0) return new Array(10).fill(0);

  // 1. space_ratio
  const spaceCount = words.filter(w => w === "space").length;
  const spaceRatio = spaceCount / n;

  // 2. space_present
  const spacePresent = spaceCount > 0 ? 1.0 : 0.0;

  // 3. protocol_ratio
  const protocolCount = words.filter(w => PROTOCOL_VOCAB.has(w)).length;
  const protocolRatio = protocolCount / n;

  // 4. filler_count
  const fillerCount = words.filter(w => FILLER_WORDS.has(w)).length;

  // 5. intent_count
  const textLower = text.toLowerCase();
  const intentCount = INTENT_PHRASES.filter(p => textLower.includes(p)).length;

  // 6. correction_count
  const correctionCount = CORRECTION_PHRASES.filter(p => textLower.includes(p)).length;

  // 7. starts_casing
  const startsCasing = CASING_STARTERS.has(words[0]) ? 1.0 : 0.0;

  // 8. word_count (normalized)
  const wordCount = n / 20.0;

  // 9. non_protocol_ratio
  const nonProtocolRatio = 1.0 - protocolRatio;

  // 10. avg_word_len
  const totalChars = words.reduce((sum, w) => sum + w.length, 0);
  const avgWordLen = totalChars / n;

  return [
    spaceRatio,
    spacePresent,
    protocolRatio,
    fillerCount,
    intentCount,
    correctionCount,
    startsCasing,
    wordCount,
    nonProtocolRatio,
    avgWordLen,
  ];
}

// ── Classification ──────────────────────────────────────────────────────

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

/**
 * Does this dictated input need LLM normalization?
 *
 * @returns true if the input is fuzzy/natural and needs LLM,
 *          false if clean protocol that the procedural processor can handle.
 */
export function needsLLM(text: string): boolean {
  const features = extractFeatures(text);
  const logit = dot(features, WEIGHTS) + BIAS;
  return sigmoid(logit) >= THRESHOLD;
}

/**
 * Classify with probability.
 *
 * @returns { needsLLM: boolean, probability: number }
 */
export function classifyWithProbability(text: string): {
  needsLLM: boolean;
  probability: number;
} {
  const features = extractFeatures(text);
  const logit = dot(features, WEIGHTS) + BIAS;
  const prob = sigmoid(logit);
  return { needsLLM: prob >= THRESHOLD, probability: prob };
}
