// One command for local work: `npm run dev` from the repo root.
// Starts the FastAPI backend (:8000, auto-reload) and the Vite frontend (:5000)
// together, prefixes their output, and stops both on Ctrl+C.
// `npm run app` instead builds the frontend and serves it from the backend
// alone on :8000, which is how the Replit deployment runs.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const win = process.platform === 'win32'
const venvPy = join(root, '.venv', win ? 'Scripts/python.exe' : 'bin/python')
const python = existsSync(venvPy) ? venvPy : (win ? 'python' : 'python3')
const npm = win ? 'npm.cmd' : 'npm'
const mode = process.argv[2] || 'dev'

function run(name, cmd, args, cwd = root) {
  const child = spawn(cmd, args, { cwd, shell: win, env: process.env })
  const tag = `[${name}]`.padEnd(10)
  const pipe = stream => stream.on('data', buf => {
    for (const line of buf.toString().split(/\r?\n/)) if (line.trim()) console.log(tag + line)
  })
  pipe(child.stdout); pipe(child.stderr)
  child.on('exit', code => { console.log(`${tag}stopped (${code})`); shutdown() })
  return child
}

const children = []
let stopping = false
function shutdown() {
  if (stopping) return
  stopping = true
  for (const c of children) { try { c.kill() } catch { /* already gone */ } }
  setTimeout(() => process.exit(0), 300)
}
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)

if (!existsSync(join(root, 'frontend', 'node_modules'))) {
  console.log('[setup]   installing frontend packages (first run only)...')
  spawnSync(npm, ['install'], { cwd: join(root, 'frontend'), stdio: 'inherit', shell: win })
}

if (mode === 'app') {
  const b = spawnSync(npm, ['run', 'build'], { cwd: join(root, 'frontend'), stdio: 'inherit', shell: win })
  if (b.status !== 0) process.exit(b.status || 1)
  console.log('\n  Open http://localhost:8000\n')
  children.push(run('api', python, ['-m', 'uvicorn', 'backend.api.main:app', '--port', '8000']))
} else {
  console.log(`\n  Using ${python}\n  Open http://localhost:5000  (API on :8000)\n`)
  children.push(run('api', python, ['-m', 'uvicorn', 'backend.api.main:app', '--reload', '--port', '8000']))
  children.push(run('web', npm, ['run', 'dev'], join(root, 'frontend')))
}
