# forkflow

Small git helpers for **forked service repos**: `upstream` (the org), `origin` (your fork), and named coworker
remotes (`mohit`, `nishchay`, …). They cover the steps **before** you run [`git sync`](https://github.com/maaroofunbxd/gland#pre-push-and-git-sync) and push
([gland](https://github.com/maaroofunbxd/gland) provides `git sync` and the pre-push hook that keeps your branch on
the upstream primary).

- **`forkflow fetch`** — `git fetch` the primary remote's primary branch, then `origin`, then every other remote.
- **`forkflow borrow`** — start a branch from `upstream/<primary>`, check out selected paths from a coworker's
  branch, stop before commit (unless `--commit`).
- **`forkflow pr`** — thin `gh pr create` on the upstream repo after you have pushed to `origin`.

Nothing here pushes by itself except what `gh` does when opening a PR.

## Install

```bash
uv tool install "forkflow @ git+https://github.com/maaroofunbxd/forkflow"   # tag v0.1.0 when released
# or: pip install git+https://github.com/maaroofunbxd/forkflow@v0.1.0
```

Puts `forkflow` and `forkflow-git-dir` on PATH. Python 3.9+, git, bash; `forkflow pr` needs [GitHub CLI](https://cli.github.com/) (`gh`).

## Recipe

```bash
forkflow fetch
forkflow borrow mohit/feat src/foo.py          # staged on borrow-mohit-feat
# review, test, commit
git sync                                         # from gland
git push -u origin HEAD                        # or --force-with-lease if git sync says so
forkflow pr -t "Take foo from mohit" -b "Borrowed src/foo.py from mohit/feat."
```

## forkflow fetch

Same primary detection as gland's `git sync`: `upstream` / `dev.local` | `main` | `master`, unless
`GIT_PRIMARY_BRANCH` or `GIT_PRIMARY_REMOTE` are set.

## forkflow borrow

```bash
forkflow borrow <remote>/<branch> <path> [<path>…]
```

The first `/` splits remote from branch (`mohit/feature/foo` → remote `mohit`, branch `feature/foo`). Requires a
clean **tracked** tree and **at least one path**. `-b NAME`, `--dry-run`, optional `--commit -m MSG`. Does not push.

## forkflow pr

```bash
forkflow pr -t TITLE [-b BODY | -F FILE] [--draft]
```

`--repo` from the `upstream` URL, `--base` the primary branch, `--head` `<origin owner>:<current branch>`.
Refuses if `gh` is missing, there is no `upstream`, or `origin/<branch>` does not match HEAD. Run `forkflow fetch`
and `git sync` first.

Tests: `tests/test_fork.py`.