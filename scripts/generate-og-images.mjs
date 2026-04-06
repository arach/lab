import { access, mkdir, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { getAllIdeas } from '../lib/blog-content.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')
const ogSource = path.join(root, 'node_modules', '@arach', 'og', 'src', 'index.ts')
const template = path.join(root, 'og-templates', 'lab.html')
const outputRoot = path.join(root, 'public', 'og', 'lab')
const { generateOGBatch } = await import(ogSource)
const localChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

const SITE_META = {
  accent: '#0c8a63',
  accentSecondary: '#47c79c',
  background: '#f5f4ef',
  textColor: '#191610',
}

function trimDescription(text, maxLength = 140) {
  if (!text) return 'Ideas, experiments, benchmark notes, and daily field reports from the lab.'
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength - 1).trimEnd()}...`
}

function buildJob({ output, title, subtitle, eyebrow, section, pathLabel, sideNote }) {
  return {
    template,
    output,
    width: 1200,
    height: 630,
    scale: 1,
    ...SITE_META,
    vars: {
      title,
      subtitle,
      eyebrow,
      section,
      path: pathLabel,
      sideNote,
    },
  }
}

async function main() {
  try {
    await access(localChrome)
    process.env.PUPPETEER_EXECUTABLE_PATH ||= localChrome
  } catch {
    // No local Chrome available; let Puppeteer resolve its own browser.
  }

  const ideas = getAllIdeas()
  await rm(outputRoot, { recursive: true, force: true })
  await mkdir(path.join(outputRoot, 'ideas'), { recursive: true })

  const jobs = [
    buildJob({
      output: path.join(outputRoot, 'index.png'),
      title: 'Field notes for models, evals, and tiny systems.',
      subtitle: 'A running lab notebook for benchmark design, model experiments, and the boring parts of making small AI actually work.',
      eyebrow: 'Arach.dev',
      section: 'Lab Home',
      pathLabel: '/lab',
      sideNote: 'Code, content, and experiments live together here.',
    }),
    buildJob({
      output: path.join(outputRoot, 'ideas.png'),
      title: 'Ideas, scoreboards, and practical experiments.',
      subtitle: 'Longform essays, TIL-style notes, and benchmark results from the same working repository.',
      eyebrow: 'Training Lab',
      section: 'Ideas',
      pathLabel: '/lab/ideas',
      sideNote: `${ideas.length} posts and growing.`,
    }),
  ]

  for (const idea of ideas) {
    jobs.push(
      buildJob({
        output: path.join(outputRoot, 'ideas', `${idea.slug}.png`),
        title: idea.title,
        subtitle: trimDescription(idea.description),
        eyebrow: 'Training Lab',
        section: idea.sectionLabel || 'Idea',
        pathLabel: `/lab/ideas/${idea.slug}`,
        sideNote: `${idea.readingTime} min read`,
      })
    )
  }

  await generateOGBatch(jobs)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
