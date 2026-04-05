import Link from 'next/link'

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export default function IdeaArticleLayout({
  title,
  description,
  date,
  tags = [],
  sectionLabel,
  status,
  readingTime,
  evalPanels,
  children,
}) {
  return (
    <div className="site-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link href="/ideas" className="brand">
            ← All Ideas
          </Link>
          <Link href="/" className="nav-link">
            Training Lab
          </Link>
        </div>
      </header>

      <section className="article-hero-wrap">
        <div className="article-hero">
          <div className="hero-meta">
            <span className="meta-pill">{sectionLabel}</span>
            {status ? <span className="meta-pill">{status}</span> : null}
            {tags.map((tag) => (
              <span key={tag} className="meta-pill">
                {tag}
              </span>
            ))}
          </div>
          <h1>{title}</h1>
          {description ? <p>{description}</p> : null}
          {date ? (
            <div className="article-meta">
              <span className="date-chip">{formatDate(date)}</span>
              {readingTime ? (
                <span className="date-chip">{readingTime} min read</span>
              ) : null}
            </div>
          ) : null}
        </div>
      </section>

      <main className="article-body">
        {evalPanels ? (
          <div className="article-panels">{evalPanels}</div>
        ) : null}
        <article className="article-prose">{children}</article>
      </main>

      <footer className="site-footer">
        <Link href="/ideas" className="brand">
          ← Back to index
        </Link>
        <span className="nav-link">Training Lab</span>
      </footer>
    </div>
  )
}
