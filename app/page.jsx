import Link from 'next/link'

export default function HomePage() {
  return (
    <main className="home-shell">
      <div className="home-grid" />
      <section className="home-card">
        <p className="eyebrow">Training Lab</p>
        <h1>Field notes for models, evals, and tiny systems.</h1>
        <p className="lede">
          This repo now has a site shell modeled on Talkie Ideas. The content lives in markdown,
          and the reading experience is tuned for longform experiments plus daily TIL-style updates.
        </p>
        <div className="home-actions">
          <Link href="/ideas" className="button button-primary">
            Open Ideas
          </Link>
        </div>
      </section>
    </main>
  )
}
