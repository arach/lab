#!/usr/bin/env bun
import { execSync } from "child_process";

const SYS = "Convert the dictated text into the exact syntax it represents. Output only the result.";

const tests = [
  { id: 1, dictated: "hello dash world", expected: "hello-world" },
  { id: 2, dictated: "dot dot slash dev", expected: "../dev" },
  { id: 3, dictated: "dash dash verbose", expected: "--verbose" },
  { id: 4, dictated: "and and", expected: "&&" },
  { id: 5, dictated: "quote hello world quote", expected: '"hello world"' },
  { id: 6, dictated: "camel case get user name", expected: "getUserName" },
  { id: 7, dictated: "snake case total tokens generated", expected: "total_tokens_generated" },
  { id: 8, dictated: "dot E N V dot local", expected: ".env.local" },
  { id: 9, dictated: "tilde slash dev slash talkie", expected: "~/dev/talkie" },
  { id: 10, dictated: "zero point seven", expected: "0.7" },
  { id: 11, dictated: "git commit dash M quote fix latency quote", expected: 'git commit -m "fix latency"' },
  { id: 12, dictated: "export all caps API underscore KEY equals quote my dash key dash one two three quote", expected: 'export API_KEY="my-key-123"' },
  { id: 13, dictated: "git add dash A and and git commit dash M quote fix typo quote and and git push", expected: 'git add -A && git commit -m "fix typo" && git push' },
  { id: 14, dictated: "shebang slash bin slash bash", expected: "#!/bin/bash" },
  { id: 15, dictated: "HTTPS colon slash slash GitHub dot com slash arach slash talkie", expected: "https://github.com/arach/talkie" },
];

async function runModel(modelId: string, label: string) {
  console.log(`\n=== ${label} ===\n`);

  // Load model
  try {
    execSync(`talkie inference load "${modelId}"`, { timeout: 120000, stdio: "pipe" });
  } catch (e) {
    console.error(`Failed to load ${modelId}`);
    return [];
  }

  const results: { id: number; dictated: string; expected: string; got: string; match: boolean; ms: number }[] = [];

  for (const t of tests) {
    try {
      const escaped = t.dictated.replace(/"/g, '\\"');
      const cmd = `talkie inference generate "${escaped}" --system "${SYS}" --model "${modelId}" --tokens 30 --temp 0.1 --json`;
      const raw = execSync(cmd, { timeout: 30000, stdio: "pipe" }).toString().trim();
      const parsed = JSON.parse(raw);
      const got = (parsed.text || "").trim();
      const ms = Math.round((parsed.timeToFirstToken || 0) * 1000);
      const match = got === t.expected;
      results.push({ id: t.id, dictated: t.dictated, expected: t.expected, got, match, ms });

      const icon = match ? "✓" : "✗";
      console.log(`${icon} ${String(t.id).padStart(2)}. "${t.dictated}"`);
      console.log(`     expected: ${t.expected}`);
      console.log(`     got:      ${got}${ms ? ` (${ms}ms TTFT)` : ""}`);
    } catch (e: any) {
      console.log(`✗ ${String(t.id).padStart(2)}. "${t.dictated}" → ERROR: ${e.message?.slice(0, 80)}`);
      results.push({ id: t.id, dictated: t.dictated, expected: t.expected, got: "ERROR", match: false, ms: 0 });
    }
  }

  const correct = results.filter(r => r.match).length;
  console.log(`\nScore: ${correct}/${results.length} (${Math.round(correct/results.length*100)}%)`);
  return results;
}

// Run both models
const llama = await runModel("mlx-community/Llama-3.2-1B-Instruct-4bit", "LLAMA 3.2 1B");

// Unload before switching
execSync("talkie inference unload", { stdio: "pipe" });

const qwen = await runModel("mlx-community/Qwen2.5-0.5B-Instruct-4bit", "QWEN 2.5 0.5B");

// Summary
console.log("\n=== HEAD TO HEAD ===\n");
console.log(`${"#".padStart(2)}  ${"EXPECTED".padEnd(52)} ${"LLAMA".padEnd(20)} ${"QWEN".padEnd(20)}`);
console.log("─".repeat(96));
for (let i = 0; i < tests.length; i++) {
  const l = llama[i];
  const q = qwen[i];
  const lIcon = l?.match ? "✓" : "✗";
  const qIcon = q?.match ? "✓" : "✗";
  console.log(`${String(tests[i].id).padStart(2)}  ${tests[i].expected.padEnd(52)} ${lIcon} ${(l?.got || "?").padEnd(18)} ${qIcon} ${q?.got || "?"}`);
}
