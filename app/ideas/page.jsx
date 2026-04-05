import IdeasIndexPage from '../../components/IdeasIndexPage'
import { getAllIdeas } from '../../lib/blog-content'

export const metadata = {
  title: 'Ideas - Training Lab',
  description: 'Longform notes, daily scoreboards, and experiments from the lab.',
}

export default function IdeasPageRoute() {
  const ideas = getAllIdeas()
  return <IdeasIndexPage ideas={ideas} />
}
