import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import remarkGfm from 'remark-gfm'
import { notFound } from 'next/navigation'
import IdeaArticleLayout from '../../../components/IdeaArticleLayout'
import EvalIntroPanel from '../../../components/EvalIntroPanel'
import BenchmarkSnapshot from '../../../components/BenchmarkSnapshot'
import ScorePill from '../../../components/ScorePill'
import StatGrid from '../../../components/StatGrid'
import { getAllSlugs, getIdeaBySlug } from '../../../lib/blog-content'
import {
  getCoreEvalCardsPreview,
  getV1ScoreRows,
  getV2AnchorSummary,
} from '../../../lib/site-benchmark-data'

const markdownComponents = {
  ScorePill,
  StatGrid,
  table({ children }) {
    return (
      <div className="prose-table-wrap">
        <table>{children}</table>
      </div>
    )
  },
}

export function generateStaticParams() {
  return getAllSlugs().map(slug => ({ slug }))
}

export async function generateMetadata({ params }) {
  const { slug } = await params
  const idea = getIdeaBySlug(slug)
  if (!idea) {
    return {
      title: 'Not Found - Training Lab',
    }
  }

  return {
    title: `${idea.title} - Training Lab`,
    description: idea.description,
  }
}

export default async function IdeaPage({ params }) {
  const { slug } = await params
  const idea = getIdeaBySlug(slug)
  if (!idea) {
    notFound()
  }

  const showEvalPanels =
    slug === 'benchmark-scoreboard' ||
    slug === 'designing-evals-for-small-workflow-intelligence'

  return (
    <IdeaArticleLayout
      title={idea.title}
      description={idea.description}
      date={idea.date}
      tags={idea.tags}
      sectionLabel={idea.sectionLabel}
      status={idea.status}
      readingTime={idea.readingTime}
      showEvalPanels={showEvalPanels}
      evalPanels={showEvalPanels ? (
        <>
          <EvalIntroPanel cards={getCoreEvalCardsPreview()} />
          <BenchmarkSnapshot summary={getV2AnchorSummary()} v1Rows={getV1ScoreRows()} />
        </>
      ) : null}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={markdownComponents}
      >
        {idea.content}
      </ReactMarkdown>
    </IdeaArticleLayout>
  )
}
