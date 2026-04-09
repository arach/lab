import Link from 'next/link'
import TitleIntentPackPanel from '../components/TitleIntentPackPanel'
import { createLabMetadata } from '../lib/site-metadata'
import {
  getTitleIntentCardsPreview,
  getTitleIntentPackSummary,
} from '../lib/site-benchmark-data'

export const metadata = createLabMetadata({
  title: 'Training Lab',
  description: 'Field notes from a narrow benchmark for auto-title and tiny intent extraction.',
  pathname: '',
  imagePath: '/og/lab/index.png',
})

export default function HomePage() {
  const summary = getTitleIntentPackSummary()
  const cards = getTitleIntentCardsPreview()

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
        <div className="home-surface">
          <div className="hero home-copy">
            <p className="eyebrow">Training Lab</p>
            <h1>Auto-title and tiny intent, from messy voice notes.</h1>
            <p className="lede">
              The current lab focus is a deliberately small benchmark: can a short
              voice note get a useful title and only the clearest action label
              without the model guessing past the note?
            </p>
            <div className="home-actions">
              <Link href="/ideas" className="button button-primary">
                Read The Essays
              </Link>
            </div>
          </div>

          <div className="home-panel-column">
            <div className="home-preview-frame">
              <p className="home-preview-kicker">Current Benchmark</p>
              <TitleIntentPackPanel summary={summary} cards={cards} compact />
            </div>
          </div>
        </div>
      </section>

      <section className="ideas-list">
        <div className="home-detail-shell">
          <TitleIntentPackPanel summary={summary} cards={cards} detailOnly />
        </div>
      </section>

      <footer className="site-footer">
        <span className="brand">Training Lab</span>
        <span className="nav-link">Older dictation experiments still live here as foundation work</span>
      </footer>
    </div>
  )
}
