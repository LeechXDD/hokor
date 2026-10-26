---
name: hokor
description: Use when an agent mistake was just corrected or flagged in review and the user wants it handled ("don't do that again", "deal with it", "remember this", "make it a hook", "别再犯", "处理掉", "记下来", "写成钩子"); also when an entry in CLAUDE.md, a lessons file (错题本) or a standards file (规范) might now be catchable by a hook.
---

# Mistakes already made: hook them if you can, record them only if you can't

## Principle

A mistake doesn't happen every session, but writing it into CLAUDE.md, a lessons file or a standards file costs context in every session. If it can be detected from the tool call, make it a hook in settings: it blocks the call at the moment the mistake happens and tells the agent the right way.
Hooks can't stop every variant. Don't chase rewrites that slip past: giving the right path the time it does block is enough. Prefer narrow over broad, so it rarely blocks the wrong thing.

## Step 1: can it be a hook?

Ask whether the mistake shows in **the tool call itself**: the command, its arguments, the paths, the content about to be written.

- Yes (ran a command it shouldn't, edited a file it shouldn't, used the wrong tool or argument): go to step 2.
- No (whether the code is right, whether a claim is true, whether the work is complete): go to step 3.
- Partly: hook the part that shows; take the rest to step 3.

## Step 2: write the hook

1. Read `hooks` in `~/.claude/settings.json` and the project's `.claude/settings*.json`. If a script already handles the same kind of thing, add a branch to it; write a new one only if none does. If that script is user-level and the mistake was recorded in the project, still add it there.
2. Pick the level by where the mistake can happen: only in this repo → the project's `.claude/settings.json` (shared with the team) or `.claude/settings.local.json` (just this user), script under the project's `.claude/hooks/`, referenced via `$CLAUDE_PROJECT_DIR`; in any repo → `~/.claude/settings.json`, script in the user's existing hook directory (see the paths of existing hooks), otherwise `~/.claude/hooks/`.
3. Script rules:
   - read the call's JSON from stdin (`tool_name`, `tool_input`, `cwd`);
   - not its business: print nothing, exit 0;
   - block: exit 2; on stderr, one sentence of reason, then the right path, each line as "If …: do …";
   - never put the reason only in `systemMessage`: that reaches the user, not the model;
   - the right path never explains how to get around the hook;
   - block only the form that was hit and its direct variants (same command with reordered arguments, with sudo, chained after `&&`); don't extend it to other commands of the same kind. Whether to extend is a question for the user in the report.
4. Try it: feed one call that should be blocked and one that looks similar but should pass; check the exit code and stderr. Write the call JSON to a temp file with Write first, then run `<script> < <file>`: dangerous command text on the command line itself gets blocked by existing hooks first.
5. Register: show the user the JSON to add to settings, and change settings only after they confirm. This holds for user-level and project-level settings alike; creating a new project settings file counts as a change. The matcher is a tool name, e.g. `Bash` or `Edit|Write`.
6. Once the hook is live (added to an existing script, or the user confirmed the registration), delete the entry from CLAUDE.md, the lessons file or the standards file. Until then leave it exactly as it is: it is the only reminder. If the project keeps an archive of rules now enforced by hooks, move the entry there instead of deleting it.

| When you're tempted to | Do this |
|---|---|
| "It's only project settings, low impact, no need to ask" | Project settings are settings; show the user first |
| "The lesson lives in this project, so write a new hook here" | Look for existing user-level and project-level scripts first; add a branch if one fits |
| "Keep the entry and note that a hook covers it, to be safe" | A kept entry still costs context; delete it once the hook is live |
| "It happened again, bump seen first" | Mistakes turned into hooks aren't counted; delete the entry once the hook is live |
| "Similar commands are risky too, block them while I'm at it" | Block only the form that was hit; ask the user about extending |

## Step 3: can't be a hook — record it or not, and where

Where the files live: whatever the project's CLAUDE.md, CLAUDE.local.md or `.claude/rules/` already uses. If there is none yet, the first time you need one, ask the user once:

- default: `.claude/rules/lessons.md`, and `.claude/rules/standards.md` at the first promotion. Files there load every session without touching CLAUDE.md, and HTML comments (the `seen` lines) are stripped from context. They are committed, so the team sees them;
- private: the same files, added to `.gitignore`. They then exist only in this worktree;
- no lessons file: record what is worth keeping as one sentence in CLAUDE.md, with no counting or promotion, and add `<!-- hokor: no lessons file -->` to CLAUDE.md so you don't ask again.

| The mistake | Do |
|---|---|
| One-off; won't come up in another task | Don't record; tell the user why |
| Relevant to every session | CLAUDE.md, one sentence |
| Relevant to a certain kind of task, already hit several times | Standards file |
| First time, or rare | Lessons file |

Before writing to the lessons file, look for an existing entry of **the same kind** (same root cause counts, even if worded differently):

- found, and its latest incident is from this same task: add an incident line; don't bump `seen`;
- found, from a different task: add an incident line and bump `seen`; on reaching the threshold (as stated in the project's instructions, otherwise 3), move the whole entry to the standards file, drop `seen`, and tell the user "Promoted: <rule>";
- already in the standards file: just add an incident line;
- none: add a new entry with `seen=1`.

| When you're tempted to | Do this |
|---|---|
| "It's in the lessons file and still keeps happening; move it to CLAUDE.md so every session sees it" | At the threshold, move it to the standards file; only what every session needs goes in CLAUDE.md |
| "Keep the original entry and mark it promoted" | Move the whole entry; delete it from the lessons file |

Entry format:

```
**In PRs and reports, claim only verification that actually ran; write "not verified" for the rest.**
<!-- rule id=claim-only-what-ran seen=1 -->
- Incident: 10-21 PR #212 said "verified on the real stack" in its summary; only unit tests ran; reviewer caught it, sent back.
```

The title is an imperative; `id` is lowercase with hyphens; `seen` appears only in the lessons file; one line per incident: date, where, what happened, who caught it. If the file already has entries, follow their language and wording. Edit files with Write / Edit.

## Report to the user

Hooked: what it blocks, what it lets through, the test results, the JSON to add to settings, which entry was deleted from which file.
Not hooked: why it can't be detected, which file it went into (or why it wasn't recorded).
