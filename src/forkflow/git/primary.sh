# Sourced by forkflow-fetch, forkflow-borrow and forkflow-pr. Not a command.
# Sets PRIMARY and PRIMARY_REMOTE the same way git-sync does.
# Caller defines die(). Overrides: GIT_PRIMARY_BRANCH, GIT_PRIMARY_REMOTE.

detect_primary() {
  local b
  PRIMARY="${GIT_PRIMARY_BRANCH:-}"
  if [[ -z "$PRIMARY" ]]; then
    for b in dev.local main master; do
      if git show-ref --verify --quiet "refs/heads/$b"; then
        PRIMARY="$b"
        break
      fi
    done
  fi
  [[ -n "$PRIMARY" ]] || die "no primary branch (dev.local/main/master); set GIT_PRIMARY_BRANCH"

  PRIMARY_REMOTE="${GIT_PRIMARY_REMOTE:-}"
  if [[ -z "$PRIMARY_REMOTE" ]]; then
    if git remote get-url upstream >/dev/null 2>&1; then
      PRIMARY_REMOTE=upstream
    elif git remote get-url origin >/dev/null 2>&1; then
      PRIMARY_REMOTE=origin
    else
      die "no 'upstream' or 'origin' remote"
    fi
  fi
}
