# GitHub Copilot Instructions — onetakeda

You are an AI assistant for Takeda's onetakeda repositories (DevX / ICC / DD&T).

---

## Available skills

When the user's intent matches a skill below, read the linked `SKILL.md` and follow
its workflow exactly. Do not improvise — the skill defines the rules.

### Release Notes Drafter

**Skill file:** `.github/skills/release-notes-drafter/SKILL.md`

**Trigger when the user asks to:**
- Draft, generate, create, or write release notes
- Generate a changelog or CHANGELOG entry
- Summarize merged PRs
- Describe what changed between two versions/tags/branches
- Prepare release notes for a sprint or milestone
- List PRs merged since the last release
- Get, fetch, show, or list pull requests / PRs from a repo
- What PRs were merged in a given period or sprint
- I need PRs / pull requests from a repository

**On trigger:**
1. Read `.github/skills/release-notes-drafter/SKILL.md` fully.
2. Follow the workflow defined there — inputs, classification, skip rules, flags, and output format.
3. Do not respond until you have confirmed scope with the user (per the skill's §1).
