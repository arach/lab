import Link from 'next/link'

export default function ArticleSeriesRail({ pages, currentPage }) {
  return (
    <aside className="article-series-rail">
      <div className="article-sidebar-sticky">
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
      </div>
    </aside>
  )
}
