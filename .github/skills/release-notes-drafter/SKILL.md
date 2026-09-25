---
name: release-notes-drafter
description:
  Drafts structured, audit-friendly release notes for any onetakeda repository.
  Trigger intents:- "draft release notes", "generate changelog", "what changed between
  v1 and v2", "summarize merged PRs", "prepare release notes for this sprint",
  "what's new in this release", "write the CHANGELOG entry",
  "list PRs merged since last release", "get/fetch/show pull requests from a repo",
  "what PRs were merged", "I need PRs from a repository".
  Drafting tool only — does not make compliance determinations.
owner: DevX (ICC / DD&T)
scope: org-wide
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
- Look up Jira tickets or hyperlink to them — keys found in PR titles/bodies are shown as **plain text only**.
- Invent PR numbers, authors, dates, or issue links.

---

## Tool mapping

GitHub data is fetched via the GitHub MCP server. Auth is handled by the MCP connection — no PAT prompt, no Python script, no terminal commands.

### GitHub MCP (`@modelcontextprotocol/server-github`)
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

1. **Collect scope** — Ask the user once for the repository (`owner/repo`) and time window / ref range if not already provided. The only other permitted user interaction is the Deployment Notes confirmation in step 5.

2. **Fetch PRs via MCP** — Call `list_pull_requests(owner, repo, state="closed", base=branch)`. Filter results to PRs where `merged_at` is within the requested window. If result is empty, retry with `search_issues` fallback.

3. **Enrich each PR via MCP** — For each PR number:
   - Call `get_pull_request` (title, body, author, labels, milestone, merge date).
   - Call `get_pull_request_files` (path, status, additions, deletions).
   - Resolve org membership via `get_org_member`.
   - **Jira key extraction (text only):** extract any `[A-Za-z]+-[0-9]+` key from the PR title, body, or head branch name; normalize to uppercase (e.g. `DEVx-899` → `DEVX-899`). Record it as plain text. Do **not** call any Jira/Atlassian tool and do **not** build a URL.

4. **Confirm scope** — Print once:
   > `Analyzing {N} PRs merged between {start} and {end}…`
   If N is 0, halt and ask the user to verify the range.

5. **Check deployment-sensitive files** — Scan changed paths for migrations, dependency manifests, config files, API schemas. If any match, ask the user **once** whether to include a `🗒️ Deployment Notes` section.

6. **Classify** each PR into taxonomy (see Classification section). Record which priority tier produced the result (`classificationTier: 1 | 2 | 3`) in JSON output.

7. **Apply skip rules** (see Skip Rules section). Never silently drop a PR.

8. **Flag** uncertainty, breaking changes, and validation impact (see Flags section). Once a PR is flagged `[???]`, the flag is a property of the PR — it must be rendered on **every** occurrence of that PR in Block 1 (category section, Highlights, All PRs in Scope, Needs Human Review). Never show a flagged PR unflagged anywhere.

9. **Emit** the three output blocks (see Output section).

10. **Save to file** — derive the filename from repo + scope using the table below and write using `create_file`. Resolve shorthand (`last 2 weeks`, `last month`, etc.) to concrete dates **first**, then apply the matching rule. `<REPO>` is the repository name only (no owner), exactly as GitHub spells it.

    | Scope as resolved | Filename |
    |---|---|
    | Ref range | `release-notes-<REPO>-<base>-to-<head>.md` |
    | Whole calendar month (1st → last day) | `release-notes-<REPO>-YYYY-MM.md` |
    | Whole calendar quarter | `release-notes-<REPO>-YYYY-QN.md` |
    | Any other date window (incl. `last N weeks/days`) | `release-notes-<REPO>-YYYY-MM-DD-to-YYYY-MM-DD.md` |

    No other filename patterns are permitted. Write the file as **UTF-8** so emoji headers render intact.
    Write **only Block 1 (Markdown release notes)** into the file — do not include the JSON blocks.
    Confirm in chat with: `Release notes saved to release-notes-<REPO>-<LABEL>.md.`
    Do **not** re-print the full content in chat.

11. **Offer next steps** — After confirming the file save, offer these three options in a single message:
    > Would you like me to:
    > 1. Convert this to a **GitHub Release body** (strip emoji, reformat as plain prose)
    > 2. Generate a **5-sentence stakeholder email** summary
    > 3. Export as a **plain-text summary** (no emoji, no Markdown — suitable for pasting into tickets or chat)

    Wait for user selection. Do not proceed automatically.

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
| Renames / moves of files or folders that are referenced at runtime (MCP server or tool directories, script entry points, config/skill/agent paths, fetch URLs, import paths) | 🚀 Improvements — a rename is **never** Docs & Chores just because the diff has no content changes. If the functional impact cannot be confirmed from the body or referencing files, mark `[???]` with reason "Path rename may affect runtime references" |
| Mixed / production code | Pick dominant signal; classify as 🚀 Improvements if purpose is clear; mark `[???]` only if purpose cannot be determined from any signal |

**Path-sensitivity check (applies to every Priority 3 result):** for each `renamed` file, check whether the old path appears in any other file in the repo (configs, `mcp.json`, instructions, scripts, READMEs). A hit means functional impact — do not classify as 📚 Docs & Chores.

### PR hygiene advisory
If **any** PR in scope reached Priority 3 because it had no taxonomy label and no conventional-commit prefix (e.g., titles like `Feature/devx 976`, `Fix/coding standards`), or has no extractable Jira key, add a single advisory bullet at the end of `## 🔍 Needs Human Review`:

```
- ℹ️ PR hygiene: {X} of {N} PRs lacked a conventional-commit prefix or taxonomy label (#N, #M); {Y} lacked a Jira key (#N). Consider enforcing `feat:`/`fix:`/`docs:`/`chore:` prefixes and a `KEY-123` reference in PR titles.
```

### Breaking Changes override
If a PR matches any category above but also carries any breaking signal (label `breaking-change`, `!` in title prefix, or `BREAKING CHANGE:` in body), reclassify it to ⚠️ **Breaking Changes** regardless of other signals.

### Jira key / milestone / label grouping
When two or more PRs share the **same Jira key** (e.g., `DEVX-899`), the **same GitHub milestone**, or a **shared non-taxonomy label** (e.g., `qtest`, `figma`), group them under a single parent entry with sub-bullets:

```
- <parent description> in #N, #M
  > <combined summary>
  - #N — <sub-entry for PR N>
  - #M — <sub-entry for PR M>
```

Grouping is **optional when only 2 PRs share a signal** and **required when 3 or more** share the same signal. Grouped PRs still appear individually in `## 📋 All PRs in Scope`.

---

## Entry format

```
- <description> by @<author> in #<pr>[ — closes #<issue>[, #<issue>]][ — Thanks @<external>!]
  > <pr-summary>
```

Rules:
- **description**: Present tense, imperative voice (`Add`, `Fix`, `Improve`, `Remove`). 10–120 characters. Write for **users**, not implementers.
- **pr-summary**: 1–2 sentences extracted or summarized from the PR body describing what changed and its impact on the codebase. If the PR body is empty or contains only template boilerplate, summarize from the title and changed files instead. Omit the `> <pr-summary>` line entirely only when nothing meaningful can be derived. Max 200 characters. Apply secret scrubbing.
- Backticks for commands, flags, env vars, file paths, package names.
- Append `— closes #<issue>` only when body contains `Closes|Fixes|Resolves #NNN`.
- Append `— <KEY>` as **plain text** (e.g. `— DEVX-899`) when a Jira key was extracted in Workflow step 3. Never wrap the key in a Markdown link or add a URL.
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
- The `[???]` prefix is **global** for that PR: render it in the category entry, in 🌟 Highlights (if selected), in the `Category` column of 📋 All PRs in Scope (e.g., `✨ Features [???]`), and in 🔍 Needs Human Review. A PR must never appear flagged in one section and unflagged in another.
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

Category order (fixed): 📋 Executive Summary → 🌟 Highlights → ⚠️ Breaking Changes → ✨ Features → 🚀 Improvements → 🐛 Fixes → 🔒 Security → 📚 Docs & Chores → 📦 Dependencies → 🗒️ Deployment Notes → 🔗 Linked Work Items → 📋 All PRs in Scope → 🔍 Needs Human Review.

Within each category: **merge date descending**.
Omit any category that has no entries — do **not** render the heading or a `_None_` placeholder.

**🌟 Highlights is mandatory** whenever ✨ Features or ⚠️ Breaking Changes has at least one entry. Omit it only when both are empty.

**Encoding:** all section headings must use the exact emoji shown in the template below (`📋 🌟 ⚠️ ✨ 🚀 🐛 🔒 📚 📦 🗒️ 🔗 📋 🔍`). Before saving, verify no heading contains a replacement character (`�`) or a missing emoji; if it does, rewrite the heading from the template.

````markdown
# Release Notes — <repo> — <head-ref or window>

_Range: <base-ref> → <head-ref>  (or <since> → <until>)_
_Generated: <UTC timestamp>_
_Scope: {N} PRs analyzed — {B} breaking · {V} validation-impact · {S} skipped_

## 📋 Executive Summary
_2–3 sentences identifying the dominant delivery theme, major areas changed, and any risk signals (breaking changes, GxP-touched PRs, uncertain classifications). Written for a non-technical stakeholder audience._

**Generation rules:**
- Identify the 1–2 dominant delivery pillars from the classified PRs (e.g., "agent catalog expansion", "pipeline hardening").
- Name the major feature areas by their user-facing purpose, not implementation detail.
- If any breaking changes exist, state the count and nature in one sentence.
- If any GxP/SOX-touched or `[???]`-flagged PRs exist, mention that human review is required.
- Tone: confident, past-tense, stakeholder-appropriate. No bullet points — prose only.

## 🌟 Highlights
_Required when ✨ Features or ⚠️ Breaking Changes is non-empty. Up to 5 hand-picked items from those two categories. Items listed here must **not** be repeated in their category section — use `→ See #N in ✨ Features` in the category instead. Keep the `[???]` prefix on any flagged item._
- <entry>

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

## 🗒️ Deployment Notes

> *(Included only when deployment-sensitive files were detected and the user confirmed.)*

| File | PR | Action Required |
|------|----|------------------|
| `migrations/example.sql` | #N | Run DB migration |
| `package.json` | #N | Run `npm install` |

## 🔗 Linked Work Items
_Populated only when at least one Jira key was extracted from PR titles, bodies, or branch names. Omit this section entirely if no keys were found. Keys are **plain text — never hyperlinked**, and no title/status is fetched. Every non-skipped PR **without** a key gets a `— (no Jira key)` row so traceability gaps are visible._

| Jira Ticket | PR(s) |
|-------------|-------|
| DEVX-899 | #N, #M |
| — (no Jira key) | #N |

## 📋 All PRs in Scope
_Every PR analyzed — skipped PRs marked ⏭️. Required for audit traceability._

| # | Title | Author | Merged | Category |
|---|-------|--------|--------|----------|
| #N | <title> | @handle | YYYY-MM-DD | ✨ Features |
| #N | <title> | @handle | YYYY-MM-DD | ✨ Features [???] |
| #N | <title> | @handle | YYYY-MM-DD | ⏭️ Skipped — <reason> |

## 🔍 Needs Human Review
- [???] <entry> — Reason: <one line>
- <entry> [Validation Impact] — Paths: `validation/foo.py`
- <entry> — Reason: No Jira key in PR title, body, or branch name
- ℹ️ PR hygiene: <advisory line per Classification § PR hygiene advisory, if applicable>

---
_Draft — pending human QA review. Not a validation signoff. Generated by the onetakeda Release Notes Drafter skill (v7.0.0)._
````


---

## Error handling

| Condition | Behaviour |
|---|---|
| GitHub MCP 401 Unauthorized | Tell the user their `GITHUB_PERSONAL_ACCESS_TOKEN` is invalid or expired — restart VS Code after updating |
| GitHub MCP 403 insufficient scope | Tell the user to add `repo` / `public_repo` and `read:org` scopes to their PAT |
| GitHub MCP 403/429 rate-limited | Surface `X-RateLimit-Reset` header value, halt |
| GitHub MCP 404 on repo | Confirm owner/repo spelling with the user |
| PR list returns 0 results | Ask user to verify the range/time-window |
| PR body empty / unparseable | Use title + diff heuristic only; set `confidence: "low"` |
| Author org-membership 404 | Treat as external; append `— Thanks @<handle>!`; set `"orgMember": false` |

---

## Self-check before responding

- [ ] Auth handled entirely via MCP connections — no PAT prompt, no Python script, no terminal commands.
- [ ] No confirmation prompt shown after MCP auth.
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
- [ ] Jira keys rendered as plain text only — no `[KEY](url)` links, no `atlassian.net` URLs anywhere in the output; no Jira/Atlassian tool was called.
- [ ] `## 🔗 Linked Work Items` table present when Jira keys were found; omitted when none.
- [ ] `## 📋 All PRs in Scope` table includes every PR in scope including skipped ones.
- [ ] Highlights items NOT repeated verbatim in their category section.
- [ ] `## 🌟 Highlights` present whenever ✨ Features or ⚠️ Breaking Changes is non-empty.
- [ ] `## 📋 Executive Summary` present and describes dominant theme + risk signals.
- [ ] Every `[???]` PR carries the flag in **all** sections where it appears (category, Highlights, All PRs in Scope, Needs Human Review).
- [ ] No section heading contains `�` or a missing emoji; file written as UTF-8.
- [ ] Renames touching runtime-referenced paths classified as 🚀 Improvements or `[???]` — never 📚 Docs & Chores.
- [ ] Non-skipped PRs without a Jira key listed in Linked Work Items as `— (no Jira key)` and in Needs Human Review.
- [ ] PR hygiene advisory added when any PR lacked a prefix/label or Jira key.
- [ ] Filename matches exactly one pattern from Workflow step 10 (shorthand resolved to dates first).
- [ ] `classificationTier` recorded per PR in JSON output.
