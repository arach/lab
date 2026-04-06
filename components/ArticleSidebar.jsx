'use client'

import { useEffect, useState } from 'react'

export default function ArticleSidebar({ headings = [] }) {
  const [activeHeading, setActiveHeading] = useState(headings[0]?.id || null)

  useEffect(() => {
    if (!headings.length) return

    const headingElements = headings
      .map((heading) => document.getElementById(heading.id))
      .filter(Boolean)

    if (!headingElements.length) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)

        if (visible.length) {
          setActiveHeading(visible[0].target.id)
        }
      },
      {
        rootMargin: '-18% 0px -62% 0px',
        threshold: [0, 1],
      }
    )

    headingElements.forEach((element) => observer.observe(element))

    const onScroll = () => {
      let current = headingElements[0]?.id || null
      for (const element of headingElements) {
        const rect = element.getBoundingClientRect()
        if (rect.top <= 160) {
          current = element.id
        }
      }
      if (current) {
        setActiveHeading(current)
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()

    return () => {
      observer.disconnect()
      window.removeEventListener('scroll', onScroll)
    }
  }, [headings])

  return (
    <aside className="article-sidebar">
      <div className="article-sidebar-sticky">
        <div className="article-sidebar-card article-sidebar-card-toc">
          <p className="section-kicker">On This Page</p>
          <div className="article-sidebar-list">
            {headings.map((heading) => (
              <a
                key={heading.id}
                href={`#${heading.id}`}
                className={`article-sidebar-link article-sidebar-link-toc article-sidebar-link-level-${heading.level}${activeHeading === heading.id ? ' article-sidebar-link-active' : ''}`}
              >
                <span className="article-sidebar-link-title">{heading.title}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </aside>
  )
}
