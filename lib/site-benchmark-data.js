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

export function getBenchmarkRepairSummary() {
  return {
    model: 'Hermes-4-70B',
    provider: 'Nous',
    v1: {
      pass: '7/24',
      note: 'Original broad pack with brittle criteria',
    },
    v1_1: {
      pass: '20/24',
      note: 'Corrected broad pack',
      task: '0.875',
      usable: '0.854',
      contract: '0.813',
      delta_note:
        'Same model, same broad task surface, much better benchmark behavior.',
    },
    ship_soon: {
      before: '3/8',
      after: '8/8',
      note:
        'The first corrected slice still missed obvious aliases. Once those were fixed, the practical pack became fully winnable.',
    },
  }
}

export function getSemanticEvalSummary() {
  return {
    principles: [
      {
        label: 'Capability First',
        text: 'Ask whether the model understood the memo and gave the right help, not whether it emitted our favorite wrapper object.',
      },
      {
        label: 'Plain Answers',
        text: 'Use natural-language prompts for titles, summaries, next actions, reminders, and follow-up questions unless the product truly needs structure.',
      },
      {
        label: 'Auditable',
        text: 'Keep the pack small and concrete enough that a human can quickly decide whether the answer was actually useful.',
      },
    ],
    cards: [
      'Give this memo a useful title',
      'What kind of memo is this?',
      'What should the user do next?',
      'Rewrite this memo more clearly',
      'What matters most?',
      'Should this become a reminder?',
      'Should this become a calendar event?',
      'What follow-up question should we ask?',
      'Which old memo is most similar?',
    ],
    exclusions: [
      'Exact JSON obedience',
      'Nested schema reliability',
      'Agent-loop orchestration',
      'Routing policy output',
      'Knowledge graph packets',
      'Voice OS action plans',
    ],
    results: [
      {
        model: 'Qwen2.5 0.5B Instruct 4bit',
        pass: '6/9',
        task: '0.759',
        clarity: '0.926',
        discipline: '1.000',
        note: 'Best first local result. Misses were semantic, not parser-shaped.',
      },
      {
        model: 'Llama 3.2 1B Instruct 4bit',
        pass: '5/9',
        task: '0.648',
        clarity: '0.852',
        discipline: '0.889',
        note: 'Different family, similar shape. Still useful, but less consistent.',
      },
      {
        model: 'Qwen2.5 1.5B Instruct 4bit',
        pass: '4/9',
        task: '0.611',
        clarity: '0.870',
        discipline: '1.000',
        note: 'Interesting underperformer. Useful reminder that bigger is not automatically better here.',
      },
    ],
  }
}
