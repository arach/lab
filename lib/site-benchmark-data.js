import coreCards from '../eval/local_intelligence/v2/core_eval_v2_cards.json' with { type: 'json' }

export function getCoreEvalCardsPreview() {
  const preferred = [
    'memo-auto-title',
    'memo-type-detection',
    'transcript-cleanup-presets',
    'private-redaction-pass',
    'action-item-extraction',
    'reminder-normalization',
    'calendar-intent-detection',
    'follow-up-question-generator',
  ]

  const byId = new Map(coreCards.map((card) => [card.id, card]))
  return preferred.map((id) => byId.get(id)).filter(Boolean)
}

export function getV2AnchorSummary() {
  return {
    provider: 'github_models',
    model: 'openai/gpt-4.1',
    cards: 3,
    passed: 3,
    pass_rate: 1.0,
    average_score: 0.95,
    median_latency_ms: 1363.15,
    exact_parse_rate: 1.0,
    normalized_parse_rate: 0.0,
    parse_failure_rate: 0.0,
    task_score: 1.0,
    usable_score: 1.0,
    contract_score: 0.6667,
  }
}

export function getV1ScoreRows() {
  return [
    {
      model: 'google/gemma-4-E4B-it',
      pass: '13/24',
      avg: '0.62',
      note: 'Best Gemma family result so far',
    },
    {
      model: 'google/gemma-4-E2B-it',
      pass: '8/24',
      avg: '0.49',
      note: 'Smaller open baseline with visible drop',
    },
    {
      model: 'nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1',
      pass: '2/24',
      avg: '0.19',
      note: 'Useful weak-end contrast',
    },
  ]
}
