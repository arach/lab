import fs from 'fs'
import path from 'path'

const blogDirectory = path.join(process.cwd(), 'blog')
const dailyDirectory = path.join(blogDirectory, 'daily')

function readFile(filePath) {
  return fs.readFileSync(filePath, 'utf8')
}

function readingTime(content) {
  const words = content.replace(/```[\s\S]*?```/g, '').replace(/<[^>]*>/g, '').trim().split(/\s+/).length
  return Math.max(1, Math.round(words / 200))
}

function extractMetadata(raw) {
  const match = raw.match(/<!--\s*METADATA([\s\S]*?)-->/)
  if (!match) {
    return {}
  }

  const metadata = {}
  for (const line of match[1].split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || !trimmed.includes(':')) {
      continue
    }
    const [key, ...rest] = trimmed.split(':')
    const value = rest.join(':').trim()
    if (key.trim() === 'tags') {
      metadata.tags = value
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean)
    } else {
      metadata[key.trim()] = value
    }
  }
  return metadata
}

function stripMetadata(raw) {
  return raw.replace(/<!--\s*METADATA[\s\S]*?-->\s*/m, '').trim()
}

function firstBlockDescription(content) {
  const lines = content.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if (trimmed.startsWith('#')) continue
    if (trimmed === '---') continue
    if (trimmed.startsWith('<!--')) continue
    return trimmed.replace(/^>\s*/, '')
  }
  return ''
}

function cleanTitle(rawTitle) {
  return rawTitle
    .replace(/^\d{4}-\d{2}-\d{2}:\s*/, '')
    .trim()
}

function extractDateFromFilename(filePath) {
  const fileName = path.basename(filePath)
  const match = fileName.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) {
    return null
  }
  return `${match[1]}-${match[2]}-${match[3]}`
}

function dateValue(value) {
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? 0 : timestamp
}

function toRecord(filePath, sectionLabel) {
  const raw = readFile(filePath)
  const metadata = extractMetadata(raw)
  const content = stripMetadata(raw)
  const fileSlug = path.basename(filePath, path.extname(filePath))
  const slug = metadata.slug || fileSlug

  return {
    slug,
    baseSlug: slug,
    fileSlug,
    filePath,
    title: cleanTitle(content.match(/^#\s+(.+)$/m)?.[1]?.trim() || slug),
    description: metadata.description || firstBlockDescription(content),
    date: metadata.date || fs.statSync(filePath).mtime.toISOString(),
    tags: metadata.tags || [],
    author: metadata.author || null,
    status: metadata.status || null,
    readingTime: readingTime(content),
    sectionLabel,
    sortDate:
      (sectionLabel === 'Daily' && extractDateFromFilename(filePath)) ||
      metadata.date ||
      fs.statSync(filePath).mtime.toISOString(),
    content,
  }
}

function readMarkdownFiles(directory, sectionLabel) {
  if (!fs.existsSync(directory)) return []
  return fs
    .readdirSync(directory)
    .filter((file) => file.endsWith('.md'))
    .map((file) => toRecord(path.join(directory, file), sectionLabel))
}

export function getAllIdeas() {
  const longform = readMarkdownFiles(blogDirectory, 'Essay')
  const daily = readMarkdownFiles(dailyDirectory, 'Daily')

  const uniqueified = []
  const counts = new Map()

  for (const entry of [...longform, ...daily]) {
    if (!entry || !entry.slug || !entry.title) {
      continue
    }

    if (entry.slug.toLowerCase() === 'readme') {
      continue
    }

    const seen = counts.get(entry.slug) || 0
    counts.set(entry.slug, seen + 1)

    uniqueified.push({
      ...entry,
      slug: seen === 0 ? entry.slug : `${entry.slug}--${entry.fileSlug}`,
    })
  }

  return uniqueified
    .filter(Boolean)
    .sort((a, b) => {
      const sortDiff = dateValue(b.sortDate) - dateValue(a.sortDate)
      if (sortDiff !== 0) {
        return sortDiff
      }

      const datediff = dateValue(b.date) - dateValue(a.date)
      if (datediff !== 0) {
        return datediff
      }

      return a.title.localeCompare(b.title)
    })
}

export function getIdeaBySlug(slug) {
  return getAllIdeas().find((entry) => entry.slug === slug)
}

export function getAllSlugs() {
  return getAllIdeas().map((entry) => entry.slug)
}
