import IdeasIndexPage from '../../components/IdeasIndexPage'
import { getAllIdeas } from '../../lib/blog-content'
import { createLabMetadata } from '../../lib/site-metadata'

export const metadata = createLabMetadata({
  title: 'Ideas - Training Lab',
  description: 'Longform notes, daily scoreboards, and experiments from the lab.',
  pathname: '/ideas',
  imagePath: '/og/lab/ideas.png',
})

export default function IdeasPageRoute() {
  const ideas = getAllIdeas()
  return <IdeasIndexPage ideas={ideas} />
}
