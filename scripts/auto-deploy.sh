#!/usr/bin/env bash
# Non-interactive production deploy, executed by GitHub Actions over SSH.

set -Eeuo pipefail

log() {
    printf '[deploy] %s\n' "$*"
}

fail() {
    printf '[deploy] ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Required command is missing: $1"
}

wait_for_url() {
    local name="$1"
    local url="$2"
    local attempts="${3:-60}"

    log "Waiting for ${name}: ${url}"
    for ((attempt = 1; attempt <= attempts; attempt++)); do
        if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; then
            log "${name} is healthy"
            return 0
        fi
        sleep 2
    done

    return 1
}

DEPLOY_PATH="${DEPLOY_PATH:-${HOME}/castleweb}"
case "$DEPLOY_PATH" in
    "~") DEPLOY_PATH="$HOME" ;;
    "~/"*) DEPLOY_PATH="${HOME}/${DEPLOY_PATH#\~/}" ;;
esac

[ -n "${DEPLOY_SHA:-}" ] || fail "DEPLOY_SHA is not set"
[[ "$DEPLOY_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "DEPLOY_SHA must be a full 40-character Git commit SHA"
[ -d "$DEPLOY_PATH" ] || fail "Deployment directory does not exist: $DEPLOY_PATH"

cd "$DEPLOY_PATH"
ROOT_DIR="$(pwd -P)"
[ "$ROOT_DIR" != "/" ] || fail "Refusing to deploy from the filesystem root"

COMPOSE_FILE="${ROOT_DIR}/docker-compose.prod.yml"
BACKEND_ENV="${ROOT_DIR}/apps/backend/.env"
PARSER_ENV="${ROOT_DIR}/apps/parser/.env"
FRONTEND_SOURCE_DIR="${ROOT_DIR}/apps/frontend"
DEPLOY_STATE_DIR="${ROOT_DIR}/.deploy"
FRONTEND_RELEASE_DIR="${DEPLOY_STATE_DIR}/frontend"
NGINX_CONFIG="${ROOT_DIR}/nginx/conf.d/default.conf"
CASES_DATA_FILE="${ROOT_DIR}/apps/backend/data/cases.json"
LOCK_FILE="${DEPLOY_LOCK_FILE:-/tmp/castleweb-deploy.lock}"

for command_name in git docker curl flock mktemp tar; do
    require_command "$command_name"
done
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "DEPLOY_PATH is not a Git repository"

exec 9>"$LOCK_FILE"
flock -n 9 || fail "Another deployment is already running"

BUILD_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/castleweb-deploy.XXXXXX")"
DEPLOYMENT_STARTED=0
DEPLOYMENT_SUCCEEDED=0
FRONTEND_SWAPPED=0
OLD_BACKEND_ID=""
OLD_BACKEND_REF=""
OLD_PARSER_ID=""
OLD_PARSER_REF=""
HAD_NGINX=0

cleanup_temp() {
    case "$BUILD_ROOT" in
        "${TMPDIR:-/tmp}"/castleweb-deploy.*) rm -rf -- "$BUILD_ROOT" ;;
        *) log "Skipping cleanup of unexpected temporary path: $BUILD_ROOT" ;;
    esac
}

restore_previous_runtime() {
    log "Deployment failed; restoring the previous frontend and container images"

    if [ "$FRONTEND_SWAPPED" -eq 1 ]; then
        if [ -d "$FRONTEND_RELEASE_DIR" ]; then
            mv "$FRONTEND_RELEASE_DIR" "$BUILD_ROOT/failed-dist"
        fi
        if [ -d "$BUILD_ROOT/previous-dist" ]; then
            mv "$BUILD_ROOT/previous-dist" "$FRONTEND_RELEASE_DIR"
        elif [ -d "$BUILD_ROOT/failed-dist" ]; then
            mv "$BUILD_ROOT/failed-dist" "$FRONTEND_RELEASE_DIR"
        fi
    fi

    if [ -f "$BUILD_ROOT/previous-nginx.conf" ]; then
        cp "$BUILD_ROOT/previous-nginx.conf" "$NGINX_CONFIG"
    fi

    local services=()
    if [ -n "$OLD_BACKEND_ID" ] && [ -n "$OLD_BACKEND_REF" ]; then
        docker image tag "$OLD_BACKEND_ID" "$OLD_BACKEND_REF" >/dev/null 2>&1 || true
        services+=(backend)
    fi
    if [ -n "$OLD_PARSER_ID" ] && [ -n "$OLD_PARSER_REF" ]; then
        docker image tag "$OLD_PARSER_ID" "$OLD_PARSER_REF" >/dev/null 2>&1 || true
        services+=(leadhunter)
    fi
    if [ "$HAD_NGINX" -eq 1 ]; then
        services+=(nginx)
    fi

    if [ "${#services[@]}" -gt 0 ] && [ -f "$BACKEND_ENV" ] && [ -f "$COMPOSE_FILE" ]; then
        docker compose --env-file "$BACKEND_ENV" -f "$COMPOSE_FILE" \
            up -d --no-build --no-deps --force-recreate "${services[@]}" || true
    fi
}

on_exit() {
    local status=$?
    trap - EXIT
    set +e

    if [ "$status" -ne 0 ] && [ "$DEPLOYMENT_STARTED" -eq 1 ] && [ "$DEPLOYMENT_SUCCEEDED" -eq 0 ]; then
        docker compose --env-file "$BACKEND_ENV" -f "$COMPOSE_FILE" \
            logs --tail=120 backend leadhunter nginx 2>/dev/null || true
        restore_previous_runtime
    fi

    # The production Nginx file is server-specific. Restore its backup even when
    # Git fetch/merge fails before the runtime rollback phase starts.
    if [ -f "$BUILD_ROOT/previous-nginx.conf" ]; then
        cp "$BUILD_ROOT/previous-nginx.conf" "$NGINX_CONFIG"
    fi

    cleanup_temp
    exit "$status"
}
trap on_exit EXIT

if [ -f "$NGINX_CONFIG" ]; then
    cp "$NGINX_CONFIG" "$BUILD_ROOT/previous-nginx.conf"
fi

current_branch="$(git branch --show-current)"
[ "$current_branch" = "main" ] || fail "Server checkout must be on the main branch (current: ${current_branch:-detached})"

# Backend startup can recreate the bind-mounted seed file with executable mode.
# Normalize only its permissions before the dirty-tree guard. Real content edits
# remain protected and still stop the deployment.
if [ -f "$CASES_DATA_FILE" ]; then
    chmod 0644 "$CASES_DATA_FILE"
fi

# Generated frontend files and the server-rendered Nginx config may legitimately differ.
# Any other tracked server-side edit is protected from being overwritten.
if ! git diff --quiet -- . ':(exclude)apps/frontend/dist/**' ':(exclude)nginx/conf.d/default.conf'; then
    printf '[deploy] Protected tracked changes:\n' >&2
    git diff --name-status -- . ':(exclude)apps/frontend/dist/**' ':(exclude)nginx/conf.d/default.conf' >&2 || true
    fail "Tracked server-side changes detected outside generated deployment files"
fi
if ! git diff --cached --quiet -- . ':(exclude)apps/frontend/dist/**' ':(exclude)nginx/conf.d/default.conf'; then
    printf '[deploy] Protected staged changes:\n' >&2
    git diff --cached --name-status -- . ':(exclude)apps/frontend/dist/**' ':(exclude)nginx/conf.d/default.conf' >&2 || true
    fail "Staged server-side changes detected outside generated deployment files"
fi

# A manual frontend build can change tracked dist files. They are generated again
# below, so restore only this known path before the fast-forward. Preserve the
# server-specific Nginx config from the backup made above and restore it after Git
# reaches the requested commit.
log "Normalizing generated files before updating the server checkout"
git restore --source=HEAD --staged --worktree -- apps/frontend/dist
if git ls-files --error-unmatch nginx/conf.d/default.conf >/dev/null 2>&1; then
    git restore --source=HEAD --staged --worktree -- nginx/conf.d/default.conf
fi

log "Fetching main and verifying commit ${DEPLOY_SHA}"
git fetch --no-tags origin main
git cat-file -e "${DEPLOY_SHA}^{commit}" 2>/dev/null || fail "Requested commit is not available after fetch"
git merge-base --is-ancestor "$DEPLOY_SHA" origin/main || fail "Requested commit is not part of origin/main"

if [ "$(git rev-parse HEAD)" != "$DEPLOY_SHA" ]; then
    git merge --ff-only "$DEPLOY_SHA"
fi
[ "$(git rev-parse HEAD)" = "$DEPLOY_SHA" ] || fail "Server did not reach the requested commit"

if [ -f "$BUILD_ROOT/previous-nginx.conf" ]; then
    cp "$BUILD_ROOT/previous-nginx.conf" "$NGINX_CONFIG"
fi

[ -f "$COMPOSE_FILE" ] || fail "Missing $COMPOSE_FILE"
[ -f "$BACKEND_ENV" ] || fail "Missing server secret file: $BACKEND_ENV"
[ -f "$PARSER_ENV" ] || fail "Missing server secret file: $PARSER_ENV"

for required_key in DOMAIN_NAME POSTGRES_PASSWORD REDIS_PASSWORD SECRET_KEY INTERNAL_API_SECRET; do
    grep -Eq "^[[:space:]]*${required_key}[[:space:]]*=[[:space:]]*.+" "$BACKEND_ENV" || \
        fail "${required_key} is missing or empty in apps/backend/.env"
done

mkdir -p "$DEPLOY_STATE_DIR"
export FRONTEND_DIST_PATH="$FRONTEND_RELEASE_DIR"
COMPOSE=(docker compose --env-file "$BACKEND_ENV" -f "$COMPOSE_FILE")
"${COMPOSE[@]}" config --quiet

if docker inspect castleweb_prod_backend >/dev/null 2>&1; then
    OLD_BACKEND_ID="$(docker inspect --format '{{.Image}}' castleweb_prod_backend)"
    OLD_BACKEND_REF="$(docker inspect --format '{{.Config.Image}}' castleweb_prod_backend)"
fi
if docker inspect castleweb_prod_leadhunter >/dev/null 2>&1; then
    OLD_PARSER_ID="$(docker inspect --format '{{.Image}}' castleweb_prod_leadhunter)"
    OLD_PARSER_REF="$(docker inspect --format '{{.Config.Image}}' castleweb_prod_leadhunter)"
fi
if docker inspect castleweb_prod_nginx >/dev/null 2>&1; then
    HAD_NGINX=1
fi

log "Building frontend in an isolated temporary directory"
git archive "$DEPLOY_SHA" -- apps/frontend | tar -x -C "$BUILD_ROOT"
docker run --rm \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp/node-home \
    --volume "$BUILD_ROOT/apps/frontend:/app" \
    --workdir /app \
    node:22-alpine \
    sh -c 'mkdir -p "$HOME" && npm ci --no-audit --no-fund && npm run build'
[ -f "$BUILD_ROOT/apps/frontend/dist/index.html" ] || fail "Frontend build did not produce dist/index.html"

log "Building backend and LeadHunter images"
"${COMPOSE[@]}" build backend leadhunter

if [ ! -d "$FRONTEND_RELEASE_DIR" ] && [ -d "$FRONTEND_SOURCE_DIR/dist" ]; then
    cp -a "$FRONTEND_SOURCE_DIR/dist" "$FRONTEND_RELEASE_DIR"
fi
if [ -d "$FRONTEND_RELEASE_DIR" ]; then
    mv "$FRONTEND_RELEASE_DIR" "$BUILD_ROOT/previous-dist"
fi
mv "$BUILD_ROOT/apps/frontend/dist" "$FRONTEND_RELEASE_DIR"
FRONTEND_SWAPPED=1
DEPLOYMENT_STARTED=1

log "Starting production services"
"${COMPOSE[@]}" up -d --remove-orphans

wait_for_url "backend" "http://127.0.0.1:8000/api/v1/health" 75 || fail "Backend health check failed"
wait_for_url "LeadHunter" "http://127.0.0.1:8080/health" 75 || fail "LeadHunter health check failed"

log "Verifying migrations and Nginx configuration"
"${COMPOSE[@]}" exec -T backend alembic upgrade head
"${COMPOSE[@]}" exec -T nginx nginx -t
"${COMPOSE[@]}" exec -T nginx nginx -s reload

if [ -n "${PUBLIC_HEALTH_URL:-}" ]; then
    wait_for_url "public endpoint" "$PUBLIC_HEALTH_URL" 30 || fail "Public health check failed"
fi

# Backend seeding can recreate this bind-mounted JSON file with an executable
# mode. Normalize only its permissions so the next deploy still detects real
# content changes instead of failing on harmless mode drift.
if [ -f "$CASES_DATA_FILE" ]; then
    chmod 0644 "$CASES_DATA_FILE"
fi

"${COMPOSE[@]}" ps
docker image prune -f >/dev/null 2>&1 || true

DEPLOYMENT_SUCCEEDED=1
log "Deployment ${DEPLOY_SHA} completed successfully"
