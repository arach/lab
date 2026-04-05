#!/usr/bin/env bun
/**
 * Eval runner for the dictation pipeline.
 *
 * Runs the procedural processor against eval-processor.json and reports results.
 *
 * Usage:
 *   bun run datasets/eval/run-eval.ts                    # full eval
 *   bun run datasets/eval/run-eval.ts --tag casing       # filter by tag
 *   bun run datasets/eval/run-eval.ts --category git     # filter by category
 *   bun run datasets/eval/run-eval.ts --verbose          # show all results
 */

import { processDictation } from "../lib/procedural-processor.js";
import { needsLLM, classifyWithProbability } from "../lib/needs-llm-classifier.js";
import { extractSegments } from "../lib/protocol-segment-classifier.js";
import { readFileSync } from "fs";
import { join, dirname } from "path";

interface EvalCase {
  dictated: string;
  expected: string;
  category: string;
  tags: string[];
}

interface Failure {
  index: number;
  category: string;
  dictated: string;
  expected: string;
  got: string;
  tags: string[];
}

// ── Parse args ──────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const tagFilter = args.includes("--tag") ? args[args.indexOf("--tag") + 1] : null;
const catFilter = args.includes("--category") ? args[args.indexOf("--category") + 1] : null;
const verbose = args.includes("--verbose") || args.includes("-v");

// ── Load eval data ──────────────────────────────────────────────────────

const evalPath = join(dirname(new URL(import.meta.url).pathname), "eval-processor.json");
const allCases: EvalCase[] = JSON.parse(readFileSync(evalPath, "utf-8"));

let cases = allCases;
if (tagFilter) {
  cases = cases.filter(c => c.tags.includes(tagFilter));
}
if (catFilter) {
  cases = cases.filter(c => c.category === catFilter);
}

// ── Run eval ────────────────────────────────────────────────────────────

let exact = 0;
let wsNorm = 0;
const failures: Failure[] = [];
const byCategory: Record<string, { exact: number; total: number }> = {};
const byTag: Record<string, { exact: number; total: number }> = {};
const timings: number[] = [];

for (let i = 0; i < cases.length; i++) {
  const c = cases[i];

  // Track per-category
  if (!byCategory[c.category]) byCategory[c.category] = { exact: 0, total: 0 };
  byCategory[c.category].total += 1;

  // Track per-tag
  for (const tag of c.tags) {
    if (!byTag[tag]) byTag[tag] = { exact: 0, total: 0 };
    byTag[tag].total += 1;
  }

  const t0 = performance.now();
  const got = processDictation(c.dictated);
  const elapsed = performance.now() - t0;
  timings.push(elapsed);

  const isExact = got === c.expected;
  const wsGot = got.replace(/\s+/g, " ").trim();
  const wsExp = c.expected.replace(/\s+/g, " ").trim();
  const isWs = wsGot === wsExp;

  if (isExact) {
    exact += 1;
    byCategory[c.category].exact += 1;
    for (const tag of c.tags) {
      byTag[tag].exact += 1;
    }
  } else {
    failures.push({
      index: i,
      category: c.category,
      dictated: c.dictated.slice(0, 80),
      expected: c.expected,
      got,
      tags: c.tags,
    });
  }
  if (isWs) wsNorm += 1;

  if (verbose) {
    const mark = isExact ? "PASS" : "FAIL";
    console.log(`  [${mark}] #${i + 1} [${c.category}] ${c.dictated.slice(0, 60)}`);
    if (!isExact) {
      console.log(`         exp: ${c.expected}`);
      console.log(`         got: ${got}`);
    }
  }
}

// ── Results ─────────────────────────────────────────────────────────────

const total = cases.length;
const filterDesc = [
  tagFilter ? `tag=${tagFilter}` : null,
  catFilter ? `category=${catFilter}` : null,
].filter(Boolean).join(", ");

console.log();
console.log("═".repeat(70));
console.log(`  PROCEDURAL PROCESSOR EVAL (TypeScript)`);
console.log(`  ${total} cases${filterDesc ? ` (filtered: ${filterDesc})` : ""}`);
console.log("═".repeat(70));
console.log(`  Exact match:  ${exact}/${total} (${((exact / total) * 100).toFixed(1)}%)`);
console.log(`  WS-norm:      ${wsNorm}/${total} (${((wsNorm / total) * 100).toFixed(1)}%)`);
console.log(`  Failures:     ${failures.length}`);

// Timings
timings.sort((a, b) => a - b);
const median = timings[Math.floor(timings.length / 2)];
const p95 = timings[Math.floor(timings.length * 0.95)];
console.log();
console.log(`  Median latency:  ${median.toFixed(3)}ms`);
console.log(`  P95 latency:     ${p95.toFixed(3)}ms`);

// Per category
console.log();
console.log("  BY CATEGORY:");
const sortedCats = Object.keys(byCategory).sort();
for (const cat of sortedCats) {
  const r = byCategory[cat];
  const pct = ((r.exact / r.total) * 100).toFixed(0);
  const mark = r.exact === r.total ? "✓" : r.exact >= r.total / 2 ? "~" : "✗";
  console.log(`    ${mark} ${cat.padStart(14)}: ${r.exact}/${r.total} (${pct}%)`);
}

// Per tag
console.log();
console.log("  BY TAG:");
const sortedTags = Object.keys(byTag).sort();
for (const tag of sortedTags) {
  const r = byTag[tag];
  const pct = ((r.exact / r.total) * 100).toFixed(0);
  const mark = r.exact === r.total ? "✓" : r.exact >= r.total / 2 ? "~" : "✗";
  console.log(`    ${mark} ${tag.padStart(18)}: ${r.exact}/${r.total} (${pct}%)`);
}

// Failures
if (failures.length > 0) {
  console.log();
  console.log(`  FAILURES (${failures.length}):`);
  console.log("  " + "─".repeat(68));
  for (const f of failures.slice(0, 20)) {
    console.log(`    #${f.index + 1} [${f.category}] ${f.tags.join(", ")}`);
    console.log(`      exp: ${f.expected}`);
    console.log(`      got: ${f.got}`);
  }
}

console.log();

// Exit with error code if not 100%
if (exact < total) {
  process.exit(1);
}
