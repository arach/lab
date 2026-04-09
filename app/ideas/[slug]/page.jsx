import React from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import remarkGfm from 'remark-gfm'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import IdeaArticleLayout from '../../../components/IdeaArticleLayout'
import EvalIntroPanel from '../../../components/EvalIntroPanel'
import BenchmarkSnapshot from '../../../components/BenchmarkSnapshot'
import BenchmarkRepairPanel from '../../../components/BenchmarkRepairPanel'
import SemanticEvalPanel from '../../../components/SemanticEvalPanel'
import ArticleSidebar from '../../../components/ArticleSidebar'
import ArticleSeriesRail from '../../../components/ArticleSeriesRail'
import ScorePill from '../../../components/ScorePill'
import StatGrid from '../../../components/StatGrid'
import { getAllSlugs, getIdeaBySlug, getIdeaOgImagePath } from '../../../lib/blog-content'
import {
  getBenchmarkRepairSummary,
  getCoreEvalCardsPreview,
  getSemanticEvalSummary,
  getV1ScoreRows,
  getV2AnchorSummary,
} from '../../../lib/site-benchmark-data'
import { createLabMetadata } from '../../../lib/site-metadata'

function slugifyHeading(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
}

function textFromChildren(children) {
  return React.Children.toArray(children)
    .map((child) => {
      if (typeof child === 'string') return child
      if (typeof child === 'number') return String(child)
      if (React.isValidElement(child)) return textFromChildren(child.props.children)
      return ''
    })
    .join('')
}

function createMarkdownComponents() {
  return {
  ScorePill,
  StatGrid,
  table({ children }) {
    return (
      <div className="prose-table-wrap">
        <table>{children}</table>
      </div>
    )
  },
  h2({ children }) {
    const text = textFromChildren(children)
    const id = slugifyHeading(text)
    return <h2 id={id}>{children}</h2>
  },
  h3({ children }) {
    const text = textFromChildren(children)
    const id = slugifyHeading(text)
    return <h3 id={id}>{children}</h3>
  },
}
}

export function generateStaticParams() {
  return getAllSlugs().map(slug => ({ slug }))
}

export async function generateMetadata({ params, searchParams }) {
  const { slug } = await params
  const resolvedSearchParams = await searchParams
  const idea = getIdeaBySlug(slug)
  if (!idea) {
    return createLabMetadata({
      title: 'Not Found - Training Lab',
      description: 'This lab page could not be found.',
      pathname: `/ideas/${slug}`,
      imagePath: '/og/lab/ideas.png',
    })
  }

  const page = resolvedSearchParams?.page
  const normalizedContent = stripLeadMatter(idea.content)
  const articlePages = buildArticlePages(slug, normalizedContent)
  const pageNumber = Math.max(1, Number.parseInt(page || '1', 10) || 1)
  const hasMultiplePages = articlePages.length > 1
  const pageSuffix = hasMultiplePages && pageNumber <= articlePages.length ? ` (Part ${pageNumber})` : ''

  return createLabMetadata({
    title: `${idea.title}${pageSuffix} - Training Lab`,
    description: idea.description,
    pathname: `/ideas/${slug}`,
    imagePath: getIdeaOgImagePath(idea.slug),
    type: 'article',
  })
}

function extractArticlePages(content) {
  const matches = content.match(/<section id="page-\d+" class="article-page-section">[\s\S]*?<\/section>/g)
  return matches && matches.length ? matches : [content]
}

function stripLeadMatter(content) {
  return content
    .replace(/^#\s+.+\n+/, '')
    .replace(/^>\s+.+\n+/, '')
    .trim()
}

function wordCount(content) {
  return content
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length
}

function extractHeadings(content) {
  const headings = []
  const htmlHeadingRegex = /<h([23])>(.*?)<\/h\1>/g
  let htmlMatch
  while ((htmlMatch = htmlHeadingRegex.exec(content)) !== null) {
    const level = Number.parseInt(htmlMatch[1], 10)
    const rawTitle = htmlMatch[2]
      .replace(/<[^>]+>/g, '')
      .replace(/&amp;/g, '&')
      .trim()
    if (rawTitle) {
      headings.push({ level, title: rawTitle, id: slugifyHeading(rawTitle) })
    }
  }
  if (headings.length) {
    return headings
  }

  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (trimmed.startsWith('## ')) {
      const title = trimmed.replace(/^##\s+/, '').trim()
      headings.push({ level: 2, title, id: slugifyHeading(title) })
    } else if (trimmed.startsWith('### ')) {
      const title = trimmed.replace(/^###\s+/, '').trim()
      headings.push({ level: 3, title, id: slugifyHeading(title) })
    }
  }
  return headings
}

function extractPageLabel(content, number) {
  return `Part ${number}`
}

function extractPageTitle(content, number) {
  const headingMatch = content.match(/<h2>([\s\S]*?)<\/h2>/)
  const title = headingMatch?.[1]
    ?.replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&')
    .trim()
  return title || `Part ${number}`
}

function buildArticlePages(slug, content) {
  const sections = extractArticlePages(content)
  if (sections.length <= 1) {
    return []
  }

  const minimumPartWords = 450
  const significantSections = sections.every((section) => wordCount(section) >= minimumPartWords)
  if (!significantSections) {
    return []
  }

  return sections.map((section, index) => {
    const number = index + 1
    return {
      href: `/ideas/${slug}?page=${number}`,
      label: extractPageLabel(section, number),
      shortLabel: String(number),
      title: extractPageTitle(section, number),
      number,
    }
  })
}

export default async function IdeaPage({ params, searchParams }) {
  const { slug } = await params
  const resolvedSearchParams = await searchParams
  const idea = getIdeaBySlug(slug)
  if (!idea) {
    notFound()
  }

  const showEvalPanels =
    slug === 'benchmark-scoreboard' ||
    slug === 'designing-evals-for-small-workflow-intelligence'
  const showRepairPanel = slug === 'fixing-v1-with-v1-1'
  const showSemanticPanel = slug === 'designing-a-semantic-eval-for-tiny-models'
  const normalizedContent = stripLeadMatter(idea.content)
  const articlePages = buildArticlePages(slug, normalizedContent)
  const pageNumber = Math.max(1, Number.parseInt(resolvedSearchParams?.page || '1', 10) || 1)
  const articleSections = articlePages.length ? extractArticlePages(normalizedContent) : []
  const pageIndex = articleSections.length ? Math.min(articleSections.length, pageNumber) - 1 : 0
  const articleContent = articleSections.length ? articleSections[pageIndex] : normalizedContent
  const articleHeadings = extractHeadings(articleContent)
  const previousPage = articlePages.length && pageNumber > 1 ? articlePages[pageNumber - 2] : null
  const nextPage = articlePages.length && pageNumber < articlePages.length ? articlePages[pageNumber] : null
  const semanticSummary = showSemanticPanel ? getSemanticEvalSummary() : null
  const semanticContext =
    showSemanticPanel && semanticSummary ? (
      pageNumber === 1 ? (
        <section className="article-context-section" aria-label="Semantic eval context">
          <div className="article-context-section-header">
            <p className="section-kicker">Semantic Eval Context</p>
            <p>
              This supporting benchmark panel sits below the essay so the article
              can introduce itself before dropping into the scorecard.
            </p>
          </div>
          <SemanticEvalPanel summary={semanticSummary} />
        </section>
      ) : (
        <details className="article-context-toggle">
          <summary>Open semantic eval context</summary>
          <div className="article-context-toggle-body">
            <p className="article-context-toggle-copy">
              The full benchmark panel is still here if you want to cross-check
              the framing while reading later parts.
            </p>
            <SemanticEvalPanel summary={semanticSummary} />
          </div>
        </details>
      )
    ) : null

  return (
    <IdeaArticleLayout
      title={idea.title}
      description={idea.description}
      date={idea.date}
      tags={idea.tags}
      sectionLabel={idea.sectionLabel}
      status={idea.status}
      readingTime={idea.readingTime}
      showEvalPanels={showEvalPanels || showRepairPanel || showSemanticPanel}
      seriesNav={
        articlePages.length ? (
          <ArticleSeriesRail pages={articlePages} currentPage={pageNumber} />
        ) : null
      }
      aside={
        <ArticleSidebar headings={articleHeadings} />
      }
      postArticleNav={
        articlePages.length ? (
          <nav className="article-series-footer" aria-label="Series footer navigation">
            {previousPage ? (
              <Link href={previousPage.href} className="article-series-link">
                ← {previousPage.label}
              </Link>
            ) : (
              <span className="article-series-link article-series-link-muted">Start</span>
            )}
            {nextPage ? (
              <Link href={nextPage.href} className="article-series-link">
                {nextPage.label} →
              </Link>
            ) : (
              <span className="article-series-link article-series-link-muted">End</span>
            )}
          </nav>
        ) : null
      }
      evalPanels={
        showRepairPanel ? (
          <BenchmarkRepairPanel summary={getBenchmarkRepairSummary()} />
        ) : showEvalPanels ? (
          <>
            <EvalIntroPanel cards={getCoreEvalCardsPreview()} />
            <BenchmarkSnapshot summary={getV2AnchorSummary()} v1Rows={getV1ScoreRows()} />
          </>
        ) : null
      }
      afterContent={semanticContext}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={createMarkdownComponents()}
      >
        {articleContent}
      </ReactMarkdown>
    </IdeaArticleLayout>
  )
}
