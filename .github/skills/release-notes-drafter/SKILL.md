---
name: release-notes-drafter
description: >
  Drafts structured, audit-friendly release notes for any onetakeda repository.
  Trigger intents: "draft release notes", "generate changelog", "what changed between
  v1 and v2", "summarize merged PRs", "prepare release notes for this sprint",
  "what's new in this release", "write the CHANGELOG entry",
  "list PRs merged since last release", "get/fetch/show pull requests from a repo",
  "what PRs were merged", "I need PRs from a repository".
  Drafting tool only — does not make compliance determinations.
owner: DevX (ICC / DD&T)
scope: org-wide
version: 5.0.0
contact: devx@takeda.com
---

# Skill: Release Notes Drafter — onetakeda

## What this skill does

Analyzes merged Pull Requests between two refs or over a time window, classifies
them into a fixed taxonomy, flags validation-impact items for human QA review, and
produces three structured output blocks: Markdown release notes, JSON metadata, and
JSON skipped PRs.

## What this skill does NOT do

- Make compliance or validation determinations.
- Edit source code.
- Call external systems beyond GitHub.
- Invent PR numbers, authors, dates, or issue links.

---

## Tool mapping

All GitHub data is fetched via the **GitHub MCP server** (`@modelcontextprotocol/server-github`). Auth is handled by the MCP connection — no PAT prompt, no Python script, no terminal commands.

| MCP tool | Purpose |
|---|---|
| `list_pull_requests(owner, repo, state="closed", base=branch)` | List merged PRs; filter by `merged_at` within window |
| `get_pull_request(owner, repo, pull_number)` | PR detail — title, body, author, labels, milestone, merge date |
| `get_pull_request_files(owner, repo, pull_number)` | File-level diff — path, status, additions, deletions |
| `search_issues(q="is:pr is:merged repo:owner/repo merged:since..until")` | Fallback when primary returns 0 results |
| `list_org_members(org)` / `get_org_member(org, username)` | Resolve org membership for external-contributor detection |

---

## Inputs

### Authentication

No PAT prompt. Auth is handled entirely by the MCP server configured in `.vscode/mcp.json`.
If MCP returns a 401/403, tell the user to check their `GITHUB_PERSONAL_ACCESS_TOKEN` env var and restart VS Code.

### Scope inputs

Accept any **one** of:

| Input type | Example |
|---|---|
| Ref range | `base-ref` + `head-ref` (tag, branch, or SHA) |
| Time window | `since` + `until` (ISO dates) |
| Shorthand | `last 2 weeks`, `last month`, `last quarter` |

**Ref-range resolution:** Resolve both refs to SHAs via `GET /repos/{owner}/{repo}/commits/{ref}`, compare via `GET /repos/{owner}/{repo}/compare/{base}...{head}`, map each commit to its PR via `GET /repos/{owner}/{repo}/commits/{sha}/pulls`. Retain only PRs where `merged_at` is not null.

If none is provided, ask the user **once**. Do not guess.
Also confirm the **repository** (`owner/repo` format, e.g. `onetakeda/my-service`).

---

## Workflow

1. **Collect scope** — Ask the user once for the repository (`owner/repo`) and time window / ref range if not already provided. This is the **only** user interaction in the workflow.

2. **Fetch PRs via MCP** — Call `list_pull_requests(owner, repo, state="closed", base=branch)`. Filter results to PRs where `merged_at` is within the requested window. If result is empty, retry with `search_issues` fallback.

3. **Enrich each PR via MCP** — For each PR number call `get_pull_request` (title, body, author, labels, milestone, merge date) and `get_pull_request_files` (path, status, additions, deletions). Resolve org membership via `get_org_member`.

4. **Confirm scope** — Print once:
   > `Analyzing {N} PRs merged between {start} and {end}…`
   If N is 0, halt and ask the user to verify the range.

5. **Check deployment-sensitive files** — Scan changed paths for migrations, dependency manifests, config files, API schemas. If any match, ask the user **once** whether to include a `🗒️ Deployment Notes` section.

6. **Classify** each PR into taxonomy (see Classification section).

7. **Apply skip rules** (see Skip Rules section). Never silently drop a PR.

8. **Flag** uncertainty, breaking changes, and validation impact (see Flags section).

9. **Emit** the three output blocks (see Output section).

10. **Save to file** — derive the filename from repo + scope and write using `create_file`:
    - Month window → `release-notes-<REPO>-YYYY-MM.md`
    - Ref range → `release-notes-<REPO>-<base>-to-<head>.md`
    - Quarter shorthand → `release-notes-<REPO>-YYYY-QN.md`

    Write **only Block 1 (Markdown release notes)** into the file — do not include the JSON blocks.
    Confirm in chat with: `Release notes saved to release-notes-<REPO>-<LABEL>.md.`
    Do **not** re-print the full content in chat.

---

## Classification

Every PR goes into **exactly one** category, in this priority order:

### Priority 1 — GitHub label
| Label | Category |
|---|---|
| `bug` | 🐛 Fixes |
| `feature` | ✨ Features |
| `security` | 🔒 Security |
| `breaking-change` | ⚠️ Breaking Changes |
| `dependencies` | 📦 Dependencies |
| `documentation`, `chore` | 📚 Docs & Chores |

### Priority 2 — Conventional commit prefix in PR title
| Prefix | Category |
|---|---|
| `feat:` | ✨ Features |
| `feat!:` | ⚠️ Breaking Changes |
| `fix:` | 🐛 Fixes |
| `perf:`, `refactor:` | 🚀 Improvements |
| `docs:`, `chore:`, `test:`, `ci:` | 📚 Docs & Chores |

### Priority 3 — Diff heuristic
| Changed files | Category |
|---|---|
| Only `*.md`, `docs/**` | 📚 Docs & Chores |
| Only `package*.json`, `go.mod`, `requirements.txt`, `pom.xml`, `*.csproj` | 📦 Dependencies |
| Only `**/*test*`, `**/__tests__/**` | 📚 Docs & Chores |
| Mixed / production code | Pick dominant signal; classify as 🚀 Improvements if purpose is clear; mark `[???]` only if purpose cannot be determined from any signal |

### Breaking Changes override
If a PR matches any category above but also carries any breaking signal (label `breaking-change`, `!` in title prefix, or `BREAKING CHANGE:` in body), reclassify it to ⚠️ **Breaking Changes** regardless of other signals.

---

## Entry format

```
- <description> by @<author> in #<pr>[ — closes #<issue>[, #<issue>]][ — Thanks @<external>!]
  > <pr-summary>
```

Rules:
- **description**: Present tense, imperative voice (`Add`, `Fix`, `Improve`, `Remove`). 10–120 characters. Write for **users**, not implementers.
- **pr-summary**: 1–2 sentences extracted or summarized from the PR body describing what changed and its impact on the codebase. Omit the `> <pr-summary>` line entirely if the PR body is empty or contains only template boilerplate. Max 200 characters. Apply secret scrubbing.
- Backticks for commands, flags, env vars, file paths, package names.
- Append `— closes #<issue>` only when body contains `Closes|Fixes|Resolves #NNN`.
- Append `— Thanks @<handle>!` only when author is not an onetakeda org member.

---

## Skip rules

The following PR types are **skipped from release notes** but must appear in Block 3 (skipped JSON) with a reason. Never silently drop them.

- Pure CI/CD config changes (`.github/workflows/**`, no behavior change)
- Test-only changes (`**/*test*`, `**/__tests__/**`)
- No-behavior refactors (label `refactor`, no public API surface change)
- Build tooling (`Makefile`, `Dockerfile` build-only, lint configs)
- Non-security `devDependencies`-only bumps

**Exception:** if a skip candidate touches a GxP/SOX path (see Flags), do **not** skip — surface it under `🔍 Needs Human Review` instead.

---

## Flags

### Uncertainty
- Prefix with `[???]` and copy to `## 🔍 Needs Human Review` with a one-line reason.
- Set `confidence: "low"` in JSON output.

### Validation impact (GxP / SOX path detection)

**↓↓↓ EDITABLE BLOCK — QA / subchapter leads may PR updates here ↓↓↓**

```yaml
gxp_sox_globs:
  - "validation/**"
  - "gxp/**"
  - "sox/**"
  - "pipelines/qualified/**"
  - "qualified/**"
  - "regulatory/**"
  - "**/validated/**"
```

**↑↑↑ END EDITABLE BLOCK ↑↑↑**

If any PR file matches a glob above:
- Append `[Validation Impact]` to the entry.
- Copy to `## 🔍 Needs Human Review` with the matching path listed.
- Set `validationImpact: true` in JSON output.

### Deployment Notes (deployment-sensitive file detection)

Scan all changed file paths for these patterns (Workflow step 5):

| Pattern | Concern | Action hint |
|---------|---------|-------------|
| `migrations/**`, `db/migrate/**`, `*.sql` | Database migrations | Run DB migration |
| `package.json`, `requirements.txt`, `Gemfile`, `go.mod`, `pom.xml` | Dependency changes | Run install command |
| `.env.example`, `config/*.yaml`, `docker-compose.yml` | Config changes | Review env vars |
| `openapi.yaml`, `schema.graphql`, `*.proto` | API schema changes | Check API clients |
| `.github/workflows/**`, `Jenkinsfile`, `Dockerfile` | CI/CD changes | Review pipeline |

Include `🗒️ Deployment Notes` in Block 1 only when matches are found **and** the user confirms.

### Breaking changes
Mark `breaking: true` when any of:
- Label `breaking-change` present.
- PR title contains `!` (e.g., `feat!:`, `fix!:`).
- PR body contains `BREAKING CHANGE:`.

Always list in `## ⚠️ Breaking Changes`. Include a 1-line migration hint if the body provides one.

### Safety — secret scrubbing
Strip from all quoted PR content anything matching:
`ghp_[A-Za-z0-9]{36}`, `github_pat_[A-Za-z0-9_]{82}`, `AKIA[0-9A-Z]{16}`,
`aws_secret_access_key`, `xox[baprs]-[A-Za-z0-9-]+`, `password=`, `token=`, `secret=`

Replace with `[REDACTED — potential secret]`.

---

## Output

Emit three fenced blocks in this order.

### Block 1 — Markdown release notes

Category order (fixed): 🌟 Highlights → ⚠️ Breaking Changes → ✨ Features → 🚀 Improvements → 🐛 Fixes → 🔒 Security → 📚 Docs & Chores → 📦 Dependencies → �️ Deployment Notes → �🔍 Needs Human Review.

Within each category: **merge date descending**.
Omit any category that has no entries — do **not** render the heading or a `_None_` placeholder.

````markdown
# Release Notes — <repo> — <head-ref or window>

_Range: <base-ref> → <head-ref>  (or <since> → <until>)_
_Generated: <UTC timestamp>_

## 🌟 Highlights
- Up to 5 hand-picked items from Features and Breaking Changes.

## ⚠️ Breaking Changes
- <entry> — Migration: <hint if available>
  > <pr-summary>

## ✨ Features
- <entry>
  > <pr-summary>

## 🚀 Improvements
- <entry>
  > <pr-summary>

## 🐛 Fixes
- <entry>
  > <pr-summary>

## 🔒 Security
- <entry>
  > <pr-summary>

## 📚 Docs & Chores
- <entry>
  > <pr-summary>

## 📦 Dependencies
- <entry>
  > <pr-summary>

## �️ Deployment Notes

> *(Included only when deployment-sensitive files were detected and the user confirmed.)*

| File | PR | Action Required |
|------|----|------------------|
| `migrations/example.sql` | #N | Run DB migration |
| `package.json` | #N | Run `npm install` |

## 🔍 Needs Human Review
- [???] <entry> — Reason: <one line>
- <entry> [Validation Impact] — Paths: `validation/foo.py`

---
_Draft — pending human QA review. Not a validation signoff. Generated by the onetakeda Release Notes Drafter skill (v5.0.0)._
````

### Block 2 — JSON release note metadata

```json
[
  {
    "pr": 1421,
    "title": "Cache PR diffs to halve release-notes runtime",
    "author": "mzajko",
    "mergeDate": "2026-06-28T14:22:00Z",
    "category": "Improvements",
    "labels": ["enhancement"],
    "linkedIssues": [1387],
    "breaking": false,
    "validationImpact": false,
    "confidence": "high",
    "entry": "Cache PR diffs to halve release-notes runtime by @mzajko in #1421",
    "prSummary": "Caches PR diff payloads to disk so repeated runs skip redundant API calls, reducing runtime by ~50%."
  }
]
```

### Block 3 — JSON skipped PRs

```json
[
  {
    "pr": 1418,
    "title": "ci: update node version in workflow",
    "author": "devbot",
    "mergeDate": "2026-06-27T09:10:00Z",
    "skipReason": "Pure CI/CD config change — `.github/workflows/` only, no behavior change"
  }
]
```

---

## Error handling

| Condition | Behaviour |
|---|---|
| PAT not provided | Halt — do not run the Python script. Re-prompt the user to supply their PAT |
| Python script exits non-zero | Show the stderr output and halt. Do not produce partial release notes |
| HTTP 401 Unauthorized | Script raises `HTTPError 401` — tell the user their PAT is invalid or expired |
| HTTP 403 insufficient scope | Script raises `HTTPError 403` — tell the user to add `repo` / `public_repo` and `read:org` scopes |
| HTTP 403/429 rate-limited | Script raises `HTTPError 403/429` — surface `X-RateLimit-Reset`, halt |
| HTTP 404 on repo | Script raises `HTTPError 404` — confirm owner/repo with the user |
| PR list returns 0 results | Ask user to verify the range/time-window |
| PR body empty / unparseable | Use title + diff heuristic only; set `confidence: "low"` |
| Author org-membership `HTTPError 404` | Treat as external; append `— Thanks @<handle>!`; set `"orgMember": false` |

---

## Self-check before responding

- [ ] PAT collected via MCP env var or user prompt — Python script or MCP tools used, not PowerShell.
- [ ] No confirmation prompt shown after PAT/MCP collection.
- [ ] Scope confirmation "Analyzing N PRs…" printed before drafting.
- [ ] Deployment-sensitive files checked; Deployment Notes included only if user confirmed.
- [ ] All three fenced blocks present and valid.
- [ ] Output saved to `release-notes-<REPO>-<LABEL>.md` via `create_file` — full content not re-printed in chat.
- [ ] Every PR in scope is in Block 2 **or** Block 3 — none silently dropped.
- [ ] No invented PR numbers, authors, or issue links.
- [ ] Mandatory footer present in Block 1.
- [ ] `[???]` entries appear in their category **and** in `🔍 Needs Human Review`.
- [ ] Breaking-change entries appear in their primary category **and** in `⚠️ Breaking Changes`.
- [ ] Secret scrubbing ran on all quoted PR content.
