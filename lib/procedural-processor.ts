/**
 * Procedural dictation → syntax processor.
 *
 * Converts voiced protocol input (e.g., "git space push space dash u") into
 * bash commands ("git push -u") using purely procedural token scanning.
 *
 * No LLM, no ML model. Every output is deterministic.
 *
 * Rules (applied in order):
 *   1. "space" → literal space
 *   2. Three-word symbols → character (e.g., "two redirect ampersand" → "2>&")
 *   3. Casing directives → camelCase, snake_case, PascalCase, kebab-case, SCREAMING_CASE
 *   4. Two-word symbols → character (e.g., "single quote" → "'")
 *   5. "all caps <word>" → WORD
 *   6. "capital <word>" → Word or X
 *   7. Single-word symbols → character (e.g., "dash" → "-")
 *   8. Number words → digits (e.g., "forty two" → "42")
 *   9. Everything else → pass through literally
 *
 * Ported from `datasets/procedural-processor.py`.
 */

// ── Symbol vocabulary ────────────────────────────────────────────────────

/** Single-word symbols. `null` means the word needs lookahead. */
const SYMBOLS: Record<string, string | null> = {
  // Primary protocol words
  dash: "-",
  dot: ".",
  slash: "/",
  pipe: "|",
  redirect: ">",
  append: ">>",
  less: null, // needs "less than"
  star: "*",
  bang: "!",
  hash: "#",
  tilde: "~",
  at: "@",
  dollar: "$",
  percent: "%",
  caret: "^",
  ampersand: "&",
  equals: "=",
  plus: "+",
  colon: ":",
  semicolon: ";",
  underscore: "_",
  comma: ",",
  backslash: "\\",
  quote: '"',
  backtick: "`",
  question: null, // needs "question mark"
  // Synonyms
  minus: "-",
  hyphen: "-",
  period: ".",
  asterisk: "*",
  hashtag: "#",
};

/** Two-word symbols (checked before single-word). Key format: "word1,word2" */
const TWO_WORD_SYMBOLS: Record<string, string> = {
  "single,quote": "'",
  "open,paren": "(",
  "close,paren": ")",
  "open,brace": "{",
  "close,brace": "}",
  "open,bracket": "[",
  "close,bracket": "]",
  "open,angle": "<",
  "close,angle": ">",
  "open,curly": "{",
  "close,curly": "}",
  "less,than": "<",
  "question,mark": "?",
  "dash,dash": "--",
  "double,dash": "--",
  "minus,minus": "--",
  "and,and": "&&",
  "pipe,pipe": "||",
  "dot,dot": "..",
  "two,redirect": "2>",
  "forward,slash": "/",
  "back,slash": "\\",
  "equals,sign": "=",
  "at,sign": "@",
  "dollar,sign": "$",
  "open,parenthesis": "(",
  "close,parenthesis": ")",
  "new,line": "\n",
};

/** Three-word symbols. Key format: "word1,word2,word3" */
const THREE_WORD_SYMBOLS: Record<string, string> = {
  "two,redirect,ampersand": "2>&",
};

// ── Number words ─────────────────────────────────────────────────────────

const ONES: Record<string, number> = {
  zero: 0, one: 1, two: 2, three: 3, four: 4,
  five: 5, six: 6, seven: 7, eight: 8, nine: 9,
  ten: 10, eleven: 11, twelve: 12, thirteen: 13,
  fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17,
  eighteen: 18, nineteen: 19,
};

const TENS: Record<string, number> = {
  twenty: 20, thirty: 30, forty: 40, fifty: 50,
  sixty: 60, seventy: 70, eighty: 80, ninety: 90,
};

const MULTIPLIERS: Record<string, number> = {
  hundred: 100,
  thousand: 1000,
};

const ALL_NUMBER_WORDS = new Set([
  ...Object.keys(ONES),
  ...Object.keys(TENS),
  ...Object.keys(MULTIPLIERS),
]);

// ── Casing directives ───────────────────────────────────────────────────

const CASING_DIRECTIVES = new Set([
  "camel", "snake", "pascal", "kebab", "screaming",
]);

/**
 * Consume a number starting at position i.
 * Returns [digitString, nextIndex] or null.
 */
function consumeNumber(words: string[], i: number): [string, number] | null {
  const w = words[i];

  // Tens word: twenty, thirty, etc.
  if (w in TENS) {
    let val = TENS[w];
    let j = i + 1;
    // "forty two" compound
    if (j < words.length && words[j] in ONES && ONES[words[j]] < 10) {
      val += ONES[words[j]];
      j += 1;
    }
    // Check for multiplier: "forty thousand"
    if (j < words.length && words[j] in MULTIPLIERS) {
      val *= MULTIPLIERS[words[j]];
      j += 1;
    }
    return [String(val), j];
  }

  // Single/teens: zero through nineteen
  if (w in ONES) {
    let val = ONES[w];
    let j = i + 1;

    // Check for multiplier: "three thousand", "one hundred"
    if (j < words.length && words[j] in MULTIPLIERS) {
      val *= MULTIPLIERS[words[j]];
      j += 1;
      return [String(val), j];
    }

    // Check for digit sequence: "one nine two" → "192"
    let result = String(val);
    while (j < words.length && words[j] in ONES && ONES[words[j]] < 10) {
      result += String(ONES[words[j]]);
      j += 1;
    }
    if (j > i + 1) {
      return [result, j];
    }

    return [String(val), i + 1];
  }

  return null;
}

/**
 * Consume a casing directive and its arguments.
 * Returns [result, nextIndex] or null.
 */
function consumeCasing(words: string[], i: number): [string, number] | null {
  const w = words[i].toLowerCase();
  if (!CASING_DIRECTIVES.has(w)) return null;
  if (i + 1 >= words.length || words[i + 1].toLowerCase() !== "case") return null;

  const style = w;
  let j = i + 2;
  const parts: string[] = [];

  while (j < words.length) {
    const next = words[j];
    if (next === "space") break;
    if (next in SYMBOLS) break;
    if (CASING_DIRECTIVES.has(next.toLowerCase()) && j + 1 < words.length && words[j + 1].toLowerCase() === "case") break;
    if (next === "all" || next === "capital") break;
    if (j + 1 < words.length && `${next},${words[j + 1]}` in TWO_WORD_SYMBOLS) break;
    parts.push(next.toLowerCase());
    j += 1;
  }

  if (parts.length === 0) return null;

  let result: string;
  switch (style) {
    case "camel":
      result = parts[0] + parts.slice(1).map(p => p[0].toUpperCase() + p.slice(1)).join("");
      break;
    case "pascal":
      result = parts.map(p => p[0].toUpperCase() + p.slice(1)).join("");
      break;
    case "snake":
      result = parts.join("_");
      break;
    case "kebab":
      result = parts.join("-");
      break;
    case "screaming":
      result = parts.map(p => p.toUpperCase()).join("_");
      break;
    default:
      return null;
  }

  return [result, j];
}

/**
 * Process dictated text into syntax using purely procedural rules.
 *
 * @param text - Dictated input using the protocol vocabulary
 * @returns Reconstructed bash/syntax output
 */
export function processDictation(text: string): string {
  // Normalize alternative casing/caps forms before splitting
  let normalized = text;
  normalized = normalized.replace(/\bcamel[-_]?case\b/gi, "camel case");
  normalized = normalized.replace(/\bpascal[-_]?case\b/gi, "pascal case");
  normalized = normalized.replace(/\bsnake[-_]?case\b/gi, "snake case");
  normalized = normalized.replace(/\bkebab[-_]?case\b/gi, "kebab case");
  normalized = normalized.replace(/\bscreaming[-_]?case\b/gi, "screaming case");
  normalized = normalized.replace(/\ball[-_]caps\b/gi, "all caps");

  const words = normalized.split(/\s+/).filter(Boolean);
  const output: string[] = [];
  let i = 0;
  const n = words.length;
  let inQuote = false;
  let lastWasWord = false;

  while (i < n) {
    const w = words[i];

    // ── "space" → literal space ──
    if (w === "space") {
      output.push(" ");
      lastWasWord = false;
      i += 1;
      continue;
    }

    // ── Three-word symbols ──
    if (i + 2 < n) {
      const key = `${words[i]},${words[i + 1]},${words[i + 2]}`;
      if (key in THREE_WORD_SYMBOLS) {
        output.push(THREE_WORD_SYMBOLS[key]);
        lastWasWord = false;
        i += 3;
        continue;
      }
    }

    // ── Casing directives ──
    const casingResult = consumeCasing(words, i);
    if (casingResult !== null) {
      output.push(casingResult[0]);
      lastWasWord = false;
      i = casingResult[1];
      continue;
    }

    // ── Two-word symbols ──
    if (i + 1 < n) {
      const key = `${words[i]},${words[i + 1]}`;
      if (key in TWO_WORD_SYMBOLS) {
        const sym = TWO_WORD_SYMBOLS[key];
        output.push(sym);
        if (sym === '"' || sym === "'") {
          inQuote = !inQuote;
        }
        lastWasWord = false;
        i += 2;
        continue;
      }
    }

    // ── "all caps <word>" ──
    if (w === "all" && i + 2 < n && words[i + 1] === "caps") {
      output.push(words[i + 2].toUpperCase());
      lastWasWord = false;
      i += 3;
      continue;
    }

    // ── "capital <letter or word>" ──
    if (w === "capital" && i + 1 < n) {
      const next = words[i + 1];
      if (next.length === 1) {
        output.push(next.toUpperCase());
      } else {
        output.push(next[0].toUpperCase() + next.slice(1));
      }
      lastWasWord = false;
      i += 2;
      continue;
    }

    // ── Single-word symbols ──
    if (w in SYMBOLS && SYMBOLS[w] !== null) {
      const sym = SYMBOLS[w]!;
      output.push(sym);
      if (sym === '"' || sym === "'") {
        inQuote = !inQuote;
      }
      lastWasWord = false;
      i += 1;
      continue;
    }

    // ── Number words ──
    if (ALL_NUMBER_WORDS.has(w)) {
      const numResult = consumeNumber(words, i);
      if (numResult !== null) {
        output.push(numResult[0]);
        lastWasWord = false;
        i = numResult[1];
        continue;
      }
    }

    // ── Regular word → pass through ──
    if (inQuote && lastWasWord) {
      output.push(" ");
    }
    output.push(w);
    lastWasWord = true;
    i += 1;
  }

  return output.join("");
}
