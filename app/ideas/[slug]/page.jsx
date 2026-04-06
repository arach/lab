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
import ArticleMetaRail from '../../../components/ArticleMetaRail'
import ScorePill from '../../../components/ScorePill'
import StatGrid from '../../../components/StatGrid'
import { getAllSlugs, getIdeaBySlug } from '../../../lib/blog-content'
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
  const pageSuffix = slug === 'designing-a-semantic-eval-for-tiny-models' && page ? ` (Page ${page})` : ''

  return createLabMetadata({
    title: `${idea.title}${pageSuffix} - Training Lab`,
    description: idea.description,
    pathname: `/ideas/${slug}`,
    imagePath: `/og/lab/ideas/${idea.slug}.png`,
    type: 'article',
  })
}

function extractArticlePages(content) {
  const matches = content.match(/<section id="page-\d+" class="article-page-section">[\s\S]*?<\/section>/g)
  return matches && matches.length ? matches : [content]
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
  const semanticPageNumber = Math.max(1, Number.parseInt(resolvedSearchParams?.page || '1', 10) || 1)
  const semanticPages = [
    { href: `/ideas/${slug}?page=1`, label: 'Part I', title: 'Why this eval exists', number: 1 },
    { href: `/ideas/${slug}?page=2`, label: 'Part II', title: 'How the scores work', number: 2 },
    { href: `/ideas/${slug}?page=3`, label: 'Part III', title: 'What the local runs show', number: 3 },
  ]
  const semanticSections = showSemanticPanel ? extractArticlePages(idea.content) : []
  const semanticIndex = Math.min(semanticSections.length, semanticPageNumber) - 1
  const articleContent = showSemanticPanel ? semanticSections[semanticIndex] : idea.content
  const articleHeadings = extractHeadings(articleContent)
  const previousPage = showSemanticPanel && semanticPageNumber > 1 ? semanticPages[semanticPageNumber - 2] : null
  const nextPage = showSemanticPanel && semanticPageNumber < semanticPages.length ? semanticPages[semanticPageNumber] : null

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
      leftAside={<ArticleMetaRail idea={idea} pages={showSemanticPanel ? semanticPages : []} currentPage={semanticPageNumber} />}
      aside={
        <ArticleSidebar headings={articleHeadings} />
      }
      evalPanels={
        showSemanticPanel ? (
          <SemanticEvalPanel summary={getSemanticEvalSummary()} />
        ) : showRepairPanel ? (
          <BenchmarkRepairPanel summary={getBenchmarkRepairSummary()} />
        ) : showEvalPanels ? (
          <>
            <EvalIntroPanel cards={getCoreEvalCardsPreview()} />
            <BenchmarkSnapshot summary={getV2AnchorSummary()} v1Rows={getV1ScoreRows()} />
          </>
        ) : null
      }
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={createMarkdownComponents()}
      >
        {articleContent}
      </ReactMarkdown>
      {showSemanticPanel ? (
        <div className="article-series-footer">
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
        </div>
      ) : null}
    </IdeaArticleLayout>
  )
}
