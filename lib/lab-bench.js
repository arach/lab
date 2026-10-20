// Experiments queued for the landing page. Keep each one small enough to run locally.
export const nextExperiments = [
  {
    id: 'EXP-09',
    title: 'Fix the target grader, rescore every run',
    question: 'Two intent cards fail for all seven models because short, correct targets lose on word overlap. What do the rankings look like once that is fixed?',
    size: '2h',
  },
  {
    id: 'EXP-10',
    title: 'Title and intent, fully on-device',
    question: 'Run the 12-card pack through MLX on sub-4B models, three seeds each, with latency and memory. Does restraint fall apart below 2B?',
    size: '3h',
  },
  {
    id: 'EXP-11',
    title: 'Make title scoring mean something',
    question: 'Every model scores .92 to .98 on titles. Hand-rate sixty saved titles and find a metric that agrees with a human.',
    size: '4h',
  },
  {
    id: 'EXP-12',
    title: 'Grow the pack to forty cards',
    question: 'Add restraint cards for self-corrections and undecided channels. Do the rankings survive more cards?',
    size: '6h',
  },
  {
    id: 'EXP-13',
    title: 'Let the model say “needs review”',
    question: 'If a tiny model over-claims intent but flags its own uncertainty reliably, the app can ship drafts instead of actions.',
    size: '3h',
  },
  {
    id: 'EXP-14',
    title: 'LoRA a 0.5B model for title and intent',
    question: 'Train on synthetic notes kept apart from the eval cards. Can a tiny adapter match a hosted small model on restraint?',
    size: '10h',
  },
]
