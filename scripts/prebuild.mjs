const isCI = process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true'
const isVercel = Boolean(process.env.VERCEL)

if (isCI || isVercel) {
  console.log('Skipping OG generation in CI/Vercel build environment.')
  process.exit(0)
}

const { spawnSync } = await import('node:child_process')

const result = spawnSync('bun', ['run', 'generate:og'], {
  stdio: 'inherit',
  env: process.env,
})

if (result.status !== 0) {
  process.exit(result.status ?? 1)
}
