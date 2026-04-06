import Link from 'next/link'

export default function ArticleSeriesRail({ pages = [], currentPage }) {
  if (!pages.length) {
    return null
  }

  return (
    <nav className="article-series-rail" aria-label="Article series">
      <p className="section-kicker">Series</p>
      <div className="article-series-rail-row">
        {pages.map((page) => (
          <Link
            key={page.number}
            href={page.href}
            className={`article-series-rail-link${currentPage === page.number ? ' article-series-rail-link-active' : ''}`}
            aria-current={currentPage === page.number ? 'page' : undefined}
          >
            <span className="article-series-rail-label">{page.label}</span>
            <span className="article-series-rail-title">{page.title}</span>
          </Link>
        ))}
      </div>
    </nav>
  )
}
