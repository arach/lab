# Dictation Pipeline Evaluation

Evaluation datasets and runners for the Talkie dictation pipeline.

## Components Under Test

### 1. Procedural Processor (`eval/independent.json`)
Deterministic token scanner. Converts protocol words to syntax.

- **Input**: Dictated text with protocol vocabulary ("dash", "dot", "space", etc.)
- **Output**: Bash command
- **Metric**: Exact string match
- **Expected**: 100% on clean protocol input

### 2. NeedsLLM Classifier (`eval/eval-processor.json` and `eval/fuzzy.json`)
Binary classifier. Gates whether input needs LLM normalization.

- **Input**: Dictated text (clean, fuzzy, natural, or chaotic)
- **Output**: Boolean (needs LLM or not)
- **Metric**: Accuracy, precision, recall, F1
- **Expected**: >95% accuracy, minimize false negatives (skipping LLM when needed)

### 3. Protocol Segment Classifier (`eval/segment-classifier.json`)
Per-word classifier. Segments mixed dictation into passthrough and protocol.

- **Input**: Mixed text ("I want to check ls dash la")
- **Output**: Array of segments with kind labels
- **Metric**: Per-segment classification accuracy

## Running Evals

### TypeScript (Bun)
```bash
bun run eval/run-eval.ts
```

### Python
```bash
python3 processor/procedural.py eval/independent.json
python3 scripts/eval-segment-classifier.py
```

### Swift
```bash
cd macOS/TalkieKit && swift test --filter ProceduralProcessorTests
```

## Dataset Format

### Processor Eval (`eval/independent.json`)
```json
{
  "dictated": "git space push space dash u space origin space main",
  "expected": "git push -u origin main",
  "category": "git",
  "tags": ["basic", "flags"]
}
```

### Classifier Eval (`eval/eval-processor.json`)
```json
{
  "text": "git space push space dash u space origin space main",
  "label": "clean",
  "expectedNeedsLLM": false,
  "category": "git"
}
```

## Categories

git, docker, kubernetes, npm, curl, ssh, filesystem, python, rust, env, brew,
grep, swift, xcode, database, sed, awk, pipeline, redirect, build, go,
terraform, aws, github, network, systemd, bun, deno, media, json, cloudflare

## Tags

- `basic` — simple commands with few tokens
- `flags` — single-letter flags (-u, -v, -r)
- `long-flags` — double-dash flags (--recursive, --env)
- `multi-char-flags` — merged flag characters (-sL, -lah, -avz)
- `paths` — file paths with slashes
- `urls` — full URLs with protocol
- `ip-addresses` — numeric IP addresses
- `quoting` — single or double quotes
- `nested-quotes` — quotes within quotes or adjacent quote pairs
- `numbers` — number word conversion
- `casing` — capital, all caps directives
- `casing-directives` — camelCase, snake_case, etc.
- `pipes` — pipe chains
- `redirects` — output redirection
- `compound-words` — dash-joined words (cask-fonts, create-next-app)
- `special-chars` — @, $, %, ^, etc.
- `colons` — colon-joined tokens (main:app, user:pass)
- `underscores` — underscore-joined tokens (s_client, id_rsa)
- `env-vars` — environment variable patterns
- `complex` — long commands with many token types
