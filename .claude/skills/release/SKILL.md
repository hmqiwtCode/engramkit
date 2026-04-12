---
name: release
description: Cut a new engramkit release — bump the version in pyproject.toml, update CHANGELOG.md, commit, wait for CI, tag, and let the GitHub Actions Release workflow publish to PyPI + GitHub Releases. Use whenever the user says "release", "cut a release", "publish to pypi", "bump the version", "ship a new version", or otherwise wants to ship engramkit.
---

# Release engramkit

This skill captures the exact release flow wired up for this repo:

- Repo: `hmqiwtCode/engramkit` on GitHub
- PyPI project: `engramkit`
- CI workflow: `.github/workflows/ci.yml` (must be green on `main`)
- Release workflow: `.github/workflows/release.yml` (fires on `v*` tag push)
- Environment `pypi` on GitHub has **required reviewer protection** — the publish job will pause for approval

## Invariants — do not break these

- **Never skip CI.** If the CI run on `main` fails, stop and report. A broken `main` must not be released.
- **Never `--force` push, never `--amend`.** Every release commit is a new commit. The only destructive operation that's ever OK is deleting a mistakenly-pushed tag before anything shipped; ask first.
- **Version must match the tag.** `pyproject.toml` has `version = "X.Y.Z"`. The tag must be `vX.Y.Z`. The release workflow has a guard that aborts on mismatch — respect it, don't work around it.
- **The publish step needs manual approval.** Remind the user to click *Review deployments → Approve* in the Actions UI.
- **PyPI versions are immutable.** If a bad version ships, bump to the next patch rather than trying to re-upload.

## Steps

### 1. Confirm the version

Ask the user for the new version in `X.Y.Z` form (no `v` prefix). Suggest the next patch bump if they don't know — read the current version from `pyproject.toml`:

```bash
grep '^version' pyproject.toml
```

If they propose a version that is not a strict increase over the current one, push back before proceeding.

### 2. Confirm the changelog entry

Ask for a one-line summary of what's in the release. Then prepend a new section to `CHANGELOG.md` — keep existing entries below untouched. Use today's date in the file.

Template for the new section (place it directly after `# EngramKit Changelog`):

```markdown
## v<VERSION> -- <YYYY-MM-DD>

<one-line summary from the user, or a bullet list if they give multiple items>
```

### 3. Bump `pyproject.toml`

Edit the `version = "..."` line to the new version. Leave everything else alone.

### 3b. Sync the plugin manifests

```bash
python scripts/sync-version.py
```

`pyproject.toml` is the single source of truth. The script rewrites the
`version` field inside `.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json` to match. CI fails if these drift, so
never skip this step.

### 4. Show the diff, then commit

Run `git diff` and show the user. Proceed only on explicit confirmation (treat anything short of "yes / do it / lgtm / ship it" as a *no*).

On confirmation:

```bash
git add pyproject.toml CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: release <VERSION>"
git push
```

Do **not** sign as a co-author. Do **not** use `--amend` or `--force`.

### 5. Wait for CI to go green

```bash
RUN_ID=$(gh run list --workflow ci.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status
```

If CI fails, stop here. Show the failing job's summary (`gh run view "$RUN_ID" --log-failed | head -60`) and tell the user the release is on hold until `main` is green. Do not tag a broken `main`.

### 6. Tag and push

Only after CI is green:

```bash
git tag v<VERSION>
git push origin v<VERSION>
```

### 7. Watch the Release workflow

```bash
RELEASE_RUN=$(gh run list --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RELEASE_RUN" --exit-status
```

The `publish-pypi` job will pause at "Waiting for review". Tell the user:

> The release workflow is waiting for your approval. Open https://github.com/hmqiwtCode/engramkit/actions/runs/<RELEASE_RUN> and click *Review deployments → pypi → Approve and deploy*.

Keep watching until the workflow completes.

### 8. Verify and report

```bash
curl -s "https://pypi.org/pypi/engramkit/<VERSION>/json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('PyPI:', d['info']['version'], 'author:', d['info'].get('author_email'))"
```

Report to the user:

- PyPI: `https://pypi.org/project/engramkit/<VERSION>/`
- GitHub Release: `https://github.com/hmqiwtCode/engramkit/releases/tag/v<VERSION>`
- Install command the user can hand out: `pipx install engramkit==<VERSION>`

## When things go wrong

- **Workflow says `invalid-publisher` on PyPI step** — the pending publisher on PyPI isn't registered (or has a typo). Fix the entry at https://pypi.org/manage/account/publishing/ and re-run the failed job from the Actions UI; no retag needed.
- **Version guard fails with "Version mismatch"** — `pyproject.toml` and the tag disagree. Delete the tag locally + remotely (`git tag -d vX.Y.Z && git push origin :vX.Y.Z`), fix the version in `pyproject.toml`, commit, push, then retag. Check with the user before deleting any tag.
- **PyPI upload fails with "File already exists"** — that version is already on PyPI (even if yanked). Bump to the next patch and start over; never try to overwrite.
- **User wants to cancel after tagging but before approval** — just don't approve the `publish-pypi` job. Let the workflow time out. Then delete the tag so the guard doesn't fire again on re-push.
