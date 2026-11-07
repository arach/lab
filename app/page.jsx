import Link from 'next/link'
import { createLabMetadata } from '../lib/site-metadata'
import { getAllIdeas } from '../lib/blog-content'
import { getSemanticEvalSummary } from '../lib/site-benchmark-data'
import { nextExperiments } from '../lib/lab-bench'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'

export const metadata = createLabMetadata({
  title: 'Training Lab',
  description: 'Building Parakeet for Core ML, small-model evals, and notes from the training lab.',
  pathname: '',
  imagePath: '/og/lab/index.png',
})

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

const BUILD_STEPS = [
  { title: 'Trace', script: 'export.py', detail: 'NVIDIA checkpoint to PyTorch traces.' },
  { title: 'Build', script: 'build.py', detail: 'Core ML conversion and a six-bit encoder.' },
  { title: 'Check', script: 'check.py', detail: 'Compare each piece with NVIDIA’s outputs.' },
  { title: 'Score', script: 'score.py', detail: 'Measure word error rate on LibriSpeech.' },
]

const THREADS = [
  {
    id: 'A',
    status: 'Eval thread',
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

function BuildSequence() {
  return (
    <ol className="lab-build-flow" aria-label="Four steps to build and verify Parakeet">
      {BUILD_STEPS.map((step, index) => (
        <li key={step.script}>
          <span className="lab-build-index" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
          <div>
            <div className="lab-build-step">
              <strong>{step.title}</strong>
              <code>{step.script}</code>
            </div>
            <p>{step.detail}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}

export default function HomePage() {
  const allIdeas = getAllIdeas()
  const featured = allIdeas.find((idea) => idea.slug === 'parakeet-recipe')
  const ideas = allIdeas.slice(0, 6)
  const { results } = getSemanticEvalSummary()
  const totalCards = Number(results[0]?.pass.split('/')[1] ?? 9)

  return (
    <div className="site-shell lab">
      <SiteHeader />

      <section className="lab-hero">
        <div className="lab-shell">
          <div className="lab-head-bar lab-rise" style={{ '--d': 0 }}>
            <p className="lab-fig">( 00 ) Latest build · Parakeet</p>
            <time className="lab-fig" dateTime={featured.date}>{formatDate(featured.date)}</time>
          </div>
        </div>
        <div className="lab-shell lab-hero-grid">
          <div className="lab-hero-copy">
            <h1 className="lab-rise" style={{ '--d': 1 }}>
              {featured.title}
            </h1>
            <p className="lab-lede lab-rise" style={{ '--d': 2 }}>
              {featured.description}
            </p>
            <div className="lab-actions lab-rise" style={{ '--d': 3 }}>
              <Link href={`/ideas/${featured.slug}`} className="lab-button lab-button-primary">
                Read the build recipe <span aria-hidden="true">→</span>
              </Link>
              <a href="https://huggingface.co/arach/parakeet-tdt-0.6b-v3-coreml" className="lab-button">Parakeet weights</a>
              <a href="https://huggingface.co/arach/parakeet-coreml-recipe" className="lab-button">Build scripts</a>
            </div>
          </div>

          <figure className="lab-schematic lab-rise" style={{ '--d': 2 }}>
            <BuildSequence />
            <figcaption>
              <span>Fig. 1</span>
              A Core ML build checked against NVIDIA’s outputs and scored on LibriSpeech.
            </figcaption>
          </figure>
        </div>

        <div className="lab-shell">
          <dl className="lab-spec lab-rise" style={{ '--d': 4 }}>
            <div>
              <dt>Source model</dt>
              <dd>Parakeet TDT 0.6B v3</dd>
            </div>
            <div>
              <dt>Built artifact</dt>
              <dd>477 MB · Core ML</dd>
            </div>
            <div>
              <dt>Encoder</dt>
              <dd>Six-bit palettes</dd>
            </div>
            <div>
              <dt>Used in</dt>
              <dd>Talkie, through Vox</dd>
            </div>
          </dl>

          <section className="lab-cleanup" aria-labelledby="cleanup-title">
            <h2 id="cleanup-title">Transcript cleanup pilot</h2>
            <div>
              <p>
                A 4.37M-parameter KEEP/DELETE model for optional cleanup of completed transcripts.
                Trained and evaluated on synthetic examples; app integration is still ahead.
              </p>
              <ul className="lab-artifact-links" aria-label="Published cleanup resources">
                <li><a href="https://huggingface.co/arach/transcript-cleanup-tiny">Cleanup weights</a></li>
                <li><a href="https://huggingface.co/arach/parakeet-coreml-recipe/tree/main/cleanup">Runtime + training recipe</a></li>
                <li><a href="https://huggingface.co/arach/parakeet-coreml-recipe/blob/main/cleanup/experiment/TAGGER.md">Results + limitations</a></li>
              </ul>
            </div>
          </section>
        </div>
      </section>

      <section className="lab-section" id="log">
        <div className="lab-shell">
          <div className="lab-section-head">
            <div className="lab-head-bar">
              <p className="lab-fig">( 01 ) Log</p>
              <Link href="/ideas" className="lab-fig lab-section-aside">All ideas →</Link>
            </div>
            <h2>Recent notes and writeups</h2>
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

      <section className="lab-section" id="bench">
        <div className="lab-shell">
          <div className="lab-section-head">
            <div className="lab-head-bar">
              <p className="lab-fig">( 02 ) On the bench</p>
              <p className="lab-fig lab-section-aside">
                {totalCards} app-moment cards · MLX · 4-bit · on-device
              </p>
            </div>
            <h2>Semantic eval v1, first local runs</h2>
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
            <div className="lab-head-bar">
              <p className="lab-fig">( 03 ) Threads</p>
            </div>
            <h2>Two threads that keep feeding each other</h2>
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
            <div className="lab-head-bar">
              <p className="lab-fig">( 04 ) Next on the bench</p>
              <p className="lab-fig lab-section-aside">Queued, not done. Small enough to finish on a Mac.</p>
            </div>
            <h2>Experiments I want to run next</h2>
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

      <SiteFooter />
    </div>
  )
}
