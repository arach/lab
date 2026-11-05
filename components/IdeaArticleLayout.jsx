import Link from 'next/link'
import SiteHeader from './SiteHeader'
import SiteFooter from './SiteFooter'

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
  postArticleNav,
  afterContent,
  seriesNav,
  aside,
  children,
}) {
  const layoutClassName = aside ? 'article-main-grid' : 'article-content-single'

  return (
    <div className="site-shell lab lab-article">
      <SiteHeader current="ideas" />

      <section className="article-hero-wrap">
        <div className="article-hero">
          <div className="article-hero-inner">
            <div className="article-hero-copy">
              <div className="lab-head-bar lab-rise" style={{ '--d': 0 }}>
                <p className="lab-fig">
                  <Link href="/ideas">← Ideas</Link>
                  {sectionLabel ? <> · {sectionLabel}</> : null}
                </p>
                {status ? <p className="lab-fig lab-fig-accent">{status}</p> : null}
              </div>
              <h1 className="lab-rise" style={{ '--d': 1 }}>{title}</h1>
              {description ? (
                <p className="lab-rise" style={{ '--d': 2 }}>{description}</p>
              ) : null}
              <div className="article-meta lab-rise" style={{ '--d': 3 }}>
                {date ? <time dateTime={date}>{formatDate(date)}</time> : null}
                {readingTime ? <span>{readingTime} min read</span> : null}
                {tags.length ? (
                  <span className="article-meta-tags">
                    {tags.map((tag) => (
                      <span key={tag}>{tag}</span>
                    ))}
                  </span>
                ) : null}
              </div>
              {seriesNav ? <div className="article-hero-series">{seriesNav}</div> : null}
            </div>
          </div>
        </div>
      </section>

      <main className="article-body">
        <div className={layoutClassName}>
          <div className="article-main-column">
            {evalPanels ? (
              <div className="article-panels">{evalPanels}</div>
            ) : null}
            <article className="article-prose">{children}</article>
            {afterContent ? (
              <div className="article-context-wrap">{afterContent}</div>
            ) : null}
            {postArticleNav}
          </div>
          {aside ? (
            <div className="article-rail-column">{aside}</div>
          ) : null}
        </div>
      </main>

      <SiteFooter />
    </div>
  )
}
