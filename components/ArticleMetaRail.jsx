import Link from 'next/link'

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export default function ArticleMetaRail({
  idea,
  pages = [],
  currentPage,
}) {
  return (
    <aside className="article-series-rail">
      <div className="article-sidebar-sticky">
        <div className="article-sidebar-card article-sidebar-card-meta">
          <p className="section-kicker">Article</p>
          <div className="article-meta-rail-stack">
            <p className="article-meta-rail-title">{idea.title}</p>
            {idea.description ? (
              <p className="article-meta-rail-description">{idea.description}</p>
            ) : null}
            <div className="article-meta-rail-pills">
              {idea.sectionLabel ? <span className="meta-pill">{idea.sectionLabel}</span> : null}
              {idea.date ? <span className="meta-pill">{formatDate(idea.date)}</span> : null}
              {idea.readingTime ? <span className="meta-pill">{idea.readingTime} min</span> : null}
            </div>
          </div>
        </div>

        {pages.length ? (
          <div className="article-sidebar-card article-sidebar-card-series">
            <p className="section-kicker">Series</p>
            <div className="article-sidebar-list">
              {pages.map((page) => (
                <Link
                  key={page.number}
                  href={page.href}
                  className={`article-sidebar-link article-sidebar-link-series${currentPage === page.number ? ' article-sidebar-link-active' : ''}`}
                >
                  <span className="article-sidebar-link-label">{page.label}</span>
                  <span className="article-sidebar-link-title">{page.title}</span>
                </Link>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  )
}
