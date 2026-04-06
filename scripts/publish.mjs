import { spawnSync } from 'node:child_process'

function run(command, args) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    env: process.env,
  })

  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

const status = spawnSync('git', ['status', '--porcelain'], {
  encoding: 'utf8',
  env: process.env,
})

if (status.status !== 0) {
  process.exit(status.status ?? 1)
}

if (status.stdout.trim()) {
  console.error('Working tree is not clean. Commit or stash changes before publishing.')
  process.exit(1)
}

run('bun', ['run', 'og:validate'])
run('git', ['push', 'origin', 'main'])
