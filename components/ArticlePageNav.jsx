import Link from 'next/link'

export default function ArticlePageNav({ pages, currentPage }) {
  return (
    <section className="article-series-intro" aria-label="Article structure">
      <p className="section-kicker">In Three Parts</p>
      <div className="article-page-nav">
        {pages.map((page) => (
          <Link
            key={page.label}
            href={page.href}
            className={`article-page-chip${currentPage === page.number ? ' article-page-chip-active' : ''}`}
          >
            <span className="article-page-label">{page.label}</span>
            <span className="article-page-title">{page.title}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
