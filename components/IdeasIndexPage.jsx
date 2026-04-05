import Link from 'next/link'

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export default function IdeasIndexPage({ ideas }) {
  const safeIdeas = (ideas || []).filter(
    (idea) => idea && idea.slug && idea.title && Array.isArray(idea.tags)
  )

  return (
    <div className="site-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link href="/" className="brand">
            Training Lab
          </Link>
          <span className="nav-link">Ideas</span>
        </div>
      </header>

      <section className="hero-wrap">
        <div className="hero">
          <p className="eyebrow">Ideas</p>
          <h1>Experiments worth reading twice.</h1>
          <p>
            Longform writeups, benchmark notes, and day-by-day TILs from the same
            bench where the models are being tested.
          </p>
        </div>
      </section>

      <section className="ideas-list">
        <div className="ideas-grid">
          {safeIdeas.map((idea) => (
            <Link key={idea.slug} href={`/ideas/${idea.slug}`} className="idea-card">
              <div>
                <div className="idea-meta-row">
                  <span className="section-chip section-chip-strong">{idea.sectionLabel}</span>
                  <span className="date-chip">{formatDate(idea.date)}</span>
                  {idea.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="tag-chip">
                      {tag}
                    </span>
                  ))}
                </div>
                <h2>{idea.title}</h2>
                {idea.description ? <p>{idea.description}</p> : null}
              </div>
              <div className="arrow-wrap">
                <div className="arrow">↗</div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <footer className="site-footer">
        <span className="brand">Training Lab</span>
        <span className="nav-link">Built from markdown, not a CMS</span>
      </footer>
    </div>
  )
}
