import Link from 'next/link'
import { createLabMetadata } from '../lib/site-metadata'
import { getAllIdeas } from '../lib/blog-content'

export const metadata = createLabMetadata({
  title: 'Training Lab',
  description: 'Training experiments around voice notes, dictation, extraction, and tiny local models.',
  pathname: '',
  imagePath: '/og/lab/index.png',
})

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export default function HomePage() {
  const ideas = getAllIdeas().slice(0, 4)

  return (
    <div className="site-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link href="/" className="brand">
            Training Lab
          </Link>
          <Link href="/ideas" className="nav-link">
            Ideas
          </Link>
        </div>
      </header>

      <section className="hero-wrap">
        <div className="lab-home-shell">
          <div className="lab-home-hero">
            <div className="lab-home-copy">
              <p className="eyebrow">Training Lab</p>
              <h1>Stuff I&apos;m working on around voice notes and tiny models.</h1>
              <p className="lede">
                This page is a running home for training experiments, eval ideas,
                half-finished notes, and the older dictation work that led into
                the current voice memo stuff.
              </p>
              <div className="home-actions">
                <Link href="/ideas" className="button button-primary">
                  Read The Writing
                </Link>
              </div>
            </div>

            <div className="lab-home-summary">
              <p className="lab-home-summary-kicker">What this is</p>
              <div className="lab-home-summary-card">
                <h2>Mostly DIY learning in public</h2>
                <p>
                  I&apos;m using this route to keep the work in one place while I learn.
                  Some of it is careful benchmark design, some of it is me trying
                  things, getting them wrong, and writing down what changed.
                </p>
                <p>
                  Right now the main thread is voice memo extraction. The older
                  dictation work is still here because it explains how I ended up
                  caring about these smaller note-shaped tasks.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="lab-home-section">
        <div className="lab-home-shell">
          <div className="lab-section-head">
            <div>
              <p className="section-kicker">Stuff I&apos;m Working On</p>
              <h2>Two threads that keep feeding each other</h2>
            </div>
          </div>

          <div className="lab-thread-grid">
            <article className="lab-thread-card">
              <p className="lab-thread-kicker">Current thread</p>
              <h3>Voice memo extraction</h3>
              <p>
                This is the newer thread. I&apos;m trying to turn short voice memos
                into cleaner, more usable artifacts without pretending a tiny
                model knows more than it does.
              </p>
              <ul className="lab-thread-list">
                <li>Auto-title and tiny intent extraction</li>
                <li>Evaluation for restraint and review behavior</li>
                <li>Hosted and local model comparisons</li>
              </ul>
            </article>

            <article className="lab-thread-card">
              <p className="lab-thread-kicker">Foundation</p>
              <h3>Dictation to structured output</h3>
              <p>
                This is the older thread. It started with spoken commands and
                shell syntax, but it still shapes how I think about cleanup,
                normalization, and where models should stop and code should take over.
              </p>
              <ul className="lab-thread-list">
                <li>Speech normalization and protocol formatting</li>
                <li>Split architecture between model and processor</li>
                <li>On-device training and evaluation loops</li>
              </ul>
            </article>
          </div>
        </div>
      </section>

      <section className="lab-home-section">
        <div className="lab-home-shell">
          <div className="lab-section-head">
            <div>
              <p className="section-kicker">One Current Example</p>
              <h2>A small thing I&apos;m testing right now</h2>
            </div>
          </div>

          <div className="lab-example-grid">
            <div className="lab-example-card">
              <span className="lab-example-label">Voice memo</span>
              <pre>{`Need to talk to Maya about the deck or maybe just send it over first,\nI'm not sure which is less annoying.`}</pre>
            </div>

            <div className="lab-example-card">
              <span className="lab-example-label">Extraction</span>
              <pre>{`{\n  "title": "Decide how to share deck with Maya",\n  "intent": "none",\n  "target": ""\n}`}</pre>
            </div>
          </div>
        </div>
      </section>

      <section className="lab-home-section">
        <div className="lab-home-shell">
          <div className="lab-section-head">
            <div>
              <p className="section-kicker">Recent Writing</p>
              <h2>Recent notes and writeups</h2>
            </div>
            <Link href="/ideas" className="nav-link">
              All Ideas
            </Link>
          </div>

          <div className="lab-reading-list">
            {ideas.map((idea) => (
              <Link key={idea.slug} href={`/ideas/${idea.slug}`} className="lab-reading-row">
                <div className="lab-reading-meta">
                  <span className="section-chip section-chip-strong">{idea.sectionLabel}</span>
                  <span className="date-chip">{formatDate(idea.date)}</span>
                </div>
                <div className="lab-reading-main">
                  <h3>{idea.title}</h3>
                  <p>{idea.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <span className="brand">Training Lab</span>
        <span className="nav-link">Voice notes, evals, and older dictation experiments</span>
      </footer>
    </div>
  )
}
