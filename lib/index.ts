/**
 * Talkie Dictation Pipeline — TypeScript Library
 *
 * Three components for converting voiced dictation to bash commands:
 *
 * 1. **ProceduralProcessor** — Deterministic token scanner. Converts protocol
 *    words ("dash", "dot", "space") to syntax characters. 100% accuracy on
 *    clean protocol input. Zero hallucination. 11μs median latency.
 *
 * 2. **NeedsLLMClassifier** — Binary logistic regression (10 features).
 *    Determines whether input is clean protocol (processor handles it) or
 *    fuzzy/natural (would need LLM normalization). Gating classifier.
 *
 * 3. **ProtocolSegmentClassifier** — Per-word logistic regression (14 features).
 *    Segments mixed dictation into passthrough (natural speech) and protocol
 *    (command fragments). Enables hybrid processing.
 *
 * Production pipeline: Whisper → ProceduralProcessor → Bash
 * No ML model in the hot path.
 */

export { processDictation } from "./procedural-processor.js";
export {
  needsLLM,
  classifyWithProbability,
  extractFeatures,
  FEATURE_NAMES,
} from "./needs-llm-classifier.js";
export {
  extractSegments,
  hasProtocolSegments,
  classifyWord,
  FEATURE_NAMES as SEGMENT_FEATURE_NAMES,
  type TextSegment,
  type SegmentKind,
} from "./protocol-segment-classifier.js";
