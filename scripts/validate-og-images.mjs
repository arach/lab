import { access } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { getAllIdeas } from '../lib/blog-content.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')

async function exists(filePath) {
  try {
    await access(filePath)
    return true
  } catch {
    return false
  }
}

async function main() {
  const ideas = getAllIdeas()
  const expected = [
    path.join(root, 'public', 'og', 'lab', 'index.png'),
    path.join(root, 'public', 'og', 'lab', 'ideas.png'),
    ...ideas.map((idea) =>
      path.join(root, 'public', 'og', 'lab', 'ideas', `${idea.slug}.png`)
    ),
  ]

  const missing = []
  for (const filePath of expected) {
    if (!(await exists(filePath))) {
      missing.push(path.relative(root, filePath))
    }
  }

  if (missing.length) {
    console.error('Missing OG images:')
    for (const filePath of missing) {
      console.error(`- ${filePath}`)
    }
    console.error('\nRun `bun run og:generate` and commit the updated public/og assets before publishing.')
    process.exit(1)
  }

  console.log(`Validated ${expected.length} OG image paths.`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
