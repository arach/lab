import Link from 'next/link'
import SiteHeader from './SiteHeader'
import SiteFooter from './SiteFooter'

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

function groupByYear(ideas) {
  const groups = new Map()
  for (const idea of ideas) {
    const year = new Date(idea.date).getFullYear()
    if (!groups.has(year)) groups.set(year, [])
    groups.get(year).push(idea)
  }
  return [...groups.entries()]
}

export default function IdeasIndexPage({ ideas }) {
  const safeIdeas = (ideas || []).filter(
    (idea) => idea && idea.slug && idea.title && Array.isArray(idea.tags)
  )
  const sections = new Set(safeIdeas.map((idea) => idea.sectionLabel).filter(Boolean))

  return (
    <div className="site-shell lab">
      <SiteHeader current="ideas" />

      <section className="lab-page-hero">
        <div className="lab-shell">
          <p className="lab-kicker lab-rise" style={{ '--d': 0 }}>
            <span>Ideas</span>
            <span className="lab-kicker-rule" aria-hidden="true" />
            <span>{safeIdeas.length} entries{sections.size > 1 ? ` · ${sections.size} kinds` : ''}</span>
          </p>
          <h1 className="lab-rise" style={{ '--d': 1 }}>
            Essays, notes, <em>and benchmark drafts.</em>
          </h1>
          <p className="lab-lede lab-rise" style={{ '--d': 2 }}>
            Longform writeups, benchmark notes, and day-by-day TILs from the same
            bench where the title-plus-intent pack is being built.
          </p>
        </div>
      </section>

      <section className="lab-section lab-ideas">
        <div className="lab-shell">
          {groupByYear(safeIdeas).map(([year, items]) => (
            <div key={year} className="lab-year">
              <p className="lab-year-label">{year}</p>
              <div className="lab-log">
                {items.map((idea) => (
                  <Link key={idea.slug} href={`/ideas/${idea.slug}`} className="lab-log-row">
                    <time dateTime={idea.date}>{formatDate(idea.date)}</time>
                    <div className="lab-log-main">
                      <h3>{idea.title}</h3>
                      {idea.description ? <p>{idea.description}</p> : null}
                      {idea.tags.length ? (
                        <p className="lab-log-tags">
                          {idea.tags.slice(0, 4).map((tag) => (
                            <span key={tag}>{tag}</span>
                          ))}
                        </p>
                      ) : null}
                    </div>
                    <span className="lab-log-type">{idea.sectionLabel}</span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <SiteFooter note="Essays, notes, and drafts" />
    </div>
  )
}
