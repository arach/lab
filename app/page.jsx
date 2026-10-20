import Link from 'next/link'
import { createLabMetadata } from '../lib/site-metadata'
import { getAllIdeas } from '../lib/blog-content'
import { getSemanticEvalSummary } from '../lib/site-benchmark-data'
import { nextExperiments } from '../lib/lab-bench'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'


export const metadata = createLabMetadata({
  title: 'Training Lab',
  description: 'Experiments with models and training: evals, notes, and local runs.',
  pathname: '',
  imagePath: '/og/lab/index.png',
})

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

// Line lengths for the input note in the schematic, as fractions of the column.
const NOTE = [0.92, 0.78, 0.96, 0.64, 0.88, 0.71, 0.84, 0.42]

const THREADS = [
  {
    id: 'A',
    status: 'Current thread',
    title: 'Small-model extraction',
    body: "Turning short, messy notes into cleaner, more usable artifacts without pretending a tiny model knows more than it does.",
    items: ['Auto-title and tiny intent extraction', 'Evaluation for restraint and review behavior', 'Hosted and local model comparisons'],
  },
  {
    id: 'B',
    status: 'Foundation',
    title: 'Text to structured output',
    body: 'Started with commands and shell syntax. It still shapes how I think about cleanup, normalization, and where models should stop and code should take over.',
    items: ['Normalization and protocol formatting', 'Split architecture between model and processor', 'On-device training and evaluation loops'],
  },
]

function Schematic() {
  const mid = 92
  return (
    <svg className="lab-schematic-svg" viewBox="0 0 560 196" role="img" aria-label="A short note goes into a 0.5B model, which returns a title, intent none, and no target">
      <g className="sx-crop">
        <path d="M8 40v-8h8M184 40v-8h-8M8 144v8h8M184 144v8h-8" />
      </g>
      <text className="sx-label" x="16" y="24">note.txt</text>
      <text className="sx-label" x="176" y="24" textAnchor="end">41 tok</text>
      <g className="sx-text">
        {NOTE.map((w, i) => (
          <line key={i} x1="24" x2={24 + w * 144} y1={mid - 42 + i * 12} y2={mid - 42 + i * 12} />
        ))}
      </g>
      <line className="sx-axis" x1="16" x2="16" y1={mid - 48} y2={mid + 48} />

      <path className="sx-line" d={`M192 ${mid}H236`} />
      <path className="sx-line" d={`M231 ${mid - 4}l5 4l-5 4`} />

      <rect className="sx-box" x="236.5" y={mid - 30.5} width="96" height="61" />
      <text className="sx-model" x="284.5" y={mid - 3} textAnchor="middle">qwen2.5</text>
      <text className="sx-label" x="284.5" y={mid + 15} textAnchor="middle">0.5B · 4-bit</text>

      <path className="sx-line" d={`M332.5 ${mid}H356.5M356.5 ${mid - 50}V${mid + 50}M356.5 ${mid - 50}H380M356.5 ${mid}H380M356.5 ${mid + 50}H380`} />
      {[
        ['title', 'Share deck with Maya', ''],
        ['intent', 'none', ' sx-hit'],
        ['target', '—', ''],
      ].map(([key, value, cls], i) => (
        <g key={key} className={`sx-out${cls}`}>
          <circle cx="382.5" cy={mid - 50 + i * 50} r="2.5" />
          <text className="sx-label" x="394" y={mid - 54 + i * 50}>{key}</text>
          <text className="sx-value" x="394" y={mid - 40 + i * 50}>{value}</text>
        </g>
      ))}

      <path className="sx-dim" d={`M16 172H176M16 168v8M176 168v8`} />
      <text className="sx-label" x="96" y="190" textAnchor="middle">input</text>
      <path className="sx-dim" d={`M380 172H548M380 168v8M548 168v8`} />
      <text className="sx-label" x="464" y="190" textAnchor="middle">extraction</text>
    </svg>
  )
}

export default function HomePage() {
  const ideas = getAllIdeas().slice(0, 6)
  const { results } = getSemanticEvalSummary()
  const totalCards = Number(results[0]?.pass.split('/')[1] ?? 9)

  return (
    <div className="site-shell lab">
      <SiteHeader />

      <section className="lab-hero">
        <div className="lab-shell lab-hero-grid">
          <div className="lab-hero-copy">
            <p className="lab-kicker lab-rise" style={{ '--d': 0 }}>
              <span>NB.01</span>
              <span>Notebook</span>
              <span className="lab-kicker-rule" aria-hidden="true" />
              <span>Models · training</span>
            </p>
            <h1 className="lab-rise" style={{ '--d': 1 }}>
              Experiments with models <em>and training.</em>
            </h1>
            <p className="lab-lede lab-rise" style={{ '--d': 2 }}>
              A running home for training experiments, eval ideas, half-finished
              notes, and small models doing narrow jobs on-device. Mostly DIY
              learning in public: trying things, getting
              them wrong, and writing down what changed.
            </p>
            <div className="lab-actions lab-rise" style={{ '--d': 3 }}>
              <Link href="/ideas" className="lab-button lab-button-primary">
                Read the writing <span aria-hidden="true">→</span>
              </Link>
              <a href="#bench" className="lab-button">Latest run</a>
            </div>
          </div>

          <figure className="lab-schematic lab-rise" style={{ '--d': 2 }}>
            <Schematic />
            <figcaption>
              <span>Fig. 1</span>
              An undecided note. The right intent is <em>none</em>, and restraint is the thing being measured.
            </figcaption>
          </figure>
        </div>

        <div className="lab-shell">
          <dl className="lab-spec lab-rise" style={{ '--d': 4 }}>
            <div>
              <dt>Eval</dt>
              <dd>semantic v1 · {totalCards} cards</dd>
            </div>
            <div>
              <dt>Best local</dt>
              <dd>{results[0]?.model} · {results[0]?.pass}</dd>
            </div>
            <div>
              <dt>Runtime</dt>
              <dd>MLX · 4-bit · on-device</dd>
            </div>
            <div>
              <dt>Up next</dt>
              <dd>{nextExperiments[0].id} · {nextExperiments[0].size}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="lab-section" id="bench">
        <div className="lab-shell">
          <div className="lab-section-head">
            <p className="lab-section-index">01</p>
            <div>
              <p className="lab-section-kicker">On the bench</p>
              <h2>Semantic eval v1, first local runs</h2>
            </div>
            <p className="lab-section-aside">
              {totalCards} app-moment cards · MLX · 4-bit · on-device
            </p>
          </div>

          <div className="lab-bench">
            {results.map((row, index) => {
              const passed = Number(row.pass.split('/')[0])
              return (
                <article key={row.model} className="lab-bench-row">
                  <div className="lab-bench-rank">{String(index + 1).padStart(2, '0')}</div>
                  <div className="lab-bench-model">
                    <h3>{row.model}</h3>
                    <p>{row.note}</p>
                  </div>
                  <div className="lab-bench-pass" aria-label={`${row.pass} cards passed`}>
                    <div className="lab-pips" aria-hidden="true">
                      {Array.from({ length: totalCards }, (_, i) => (
                        <span key={i} className={i < passed ? 'is-on' : ''} />
                      ))}
                    </div>
                    <span>{row.pass} pass</span>
                  </div>
                  <dl className="lab-bench-scores">
                    {['task', 'clarity', 'discipline'].map((key) => (
                      <div key={key} style={{ '--v': Number(row[key]) }}>
                        <dt>{key}</dt>
                        <dd>{row[key]}</dd>
                        <span className="lab-meter" aria-hidden="true" />
                      </div>
                    ))}
                  </dl>
                </article>
              )
            })}
          </div>

          <p className="lab-bench-foot">
            Card score = 75% task + 25% average of clarity and discipline. Task is the signal to trust.{' '}
            <Link href="/ideas/designing-a-semantic-eval-for-tiny-models">How the eval works →</Link>
          </p>
        </div>
      </section>

      <section className="lab-section">
        <div className="lab-shell">
          <div className="lab-section-head">
            <p className="lab-section-index">02</p>
            <div>
              <p className="lab-section-kicker">Threads</p>
              <h2>Two threads that keep feeding each other</h2>
            </div>
          </div>

          <div className="lab-threads">
            {THREADS.map((thread) => (
              <article key={thread.id} className="lab-thread">
                <div className="lab-thread-id" aria-hidden="true">{thread.id}</div>
                <p className="lab-thread-status">{thread.status}</p>
                <h3>{thread.title}</h3>
                <p>{thread.body}</p>
                <ul>
                  {thread.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="lab-section" id="next">
        <div className="lab-shell">
          <div className="lab-section-head">
            <p className="lab-section-index">03</p>
            <div>
              <p className="lab-section-kicker">Next on the bench</p>
              <h2>Experiments I want to run next</h2>
            </div>
            <p className="lab-section-aside">Queued, not done. Small enough to finish on a Mac.</p>
          </div>

          <ol className="lab-queue">
            {nextExperiments.map((exp) => (
              <li key={exp.id} className="lab-queue-item">
                <span className="lab-queue-id">{exp.id}</span>
                <div>
                  <h3>{exp.title}</h3>
                  <p>{exp.question}</p>
                </div>
                <span className="lab-queue-size">{exp.size}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="lab-section">
        <div className="lab-shell">
          <div className="lab-section-head">
            <p className="lab-section-index">04</p>
            <div>
              <p className="lab-section-kicker">Log</p>
              <h2>Recent notes and writeups</h2>
            </div>
            <Link href="/ideas" className="lab-section-aside lab-link">All ideas →</Link>
          </div>

          <div className="lab-log">
            {ideas.map((idea) => (
              <Link key={idea.slug} href={`/ideas/${idea.slug}`} className="lab-log-row">
                <time dateTime={idea.date}>{formatDate(idea.date)}</time>
                <div className="lab-log-main">
                  <h3>{idea.title}</h3>
                  <p>{idea.description}</p>
                </div>
                <span className="lab-log-type">{idea.sectionLabel}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  )
}
