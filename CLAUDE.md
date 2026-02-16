# Claude Code Project Notes

## Environment Setup

**CRITICAL**: This agent runs in a sandboxed environment (`/home/user/zavislinkedInmarketingtool/`) that is separate from the user's machine. Local file edits are NOT visible to the user or their Docker/tooling until committed and pushed.

### Workflow for ALL changes:
1. Edit files
2. `git add` + `git commit`
3. `git push -u origin <branch>`
4. **Tell the user to `git pull` before running any local commands** (docker-compose, npm, etc.)

Never assume the user can see uncommitted file changes. Always commit, push, and instruct them to pull.

## Docker
- `docker-compose.yml` — development (uses `Dockerfile`)
- `docker-compose.prod.yml` — production (uses `Dockerfile.prod`)
- Backend build context: `./backend`
- Docker is not available in this sandbox; cannot test builds directly

## Stack
- Backend: FastAPI + Celery + PostgreSQL + Redis
- Frontend: Vite (port 5173)
- Python 3.12
