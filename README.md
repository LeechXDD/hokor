# Hokor

[中文](README.zh.md)

A Claude Code skill. When an agent makes a mistake that can be detected from the tool call, it turns the mistake into a hook in your settings: the next time the agent makes it, the hook blocks the call and tells the agent the right way. Mistakes a hook can't detect are triaged instead: not recorded, or recorded in CLAUDE.md, a standards file or a lessons file.

## Why

Rare mistakes written into CLAUDE.md cost context in every session and dilute the rules you actually need. Claude Code hooks can already hand the reason to the model when they block (exit code 2, stderr goes to the model), so a hook is the cheaper home for these: it costs nothing until the mistake happens, then gives the way forward at exactly that moment.

In one of the author's projects, moving 15 rules into hooks cut the rule text that stays in every session's context by about a sixth. The cost: when the agent does make the mistake, that step is blocked and it takes one more turn to do it the right way. A hook that blocks without giving the right path tends to leave the agent retrying one rewrite after another.

Hooks can't block 100% of variants, and this doesn't chase rewrites that slip past. Giving the right path the time it does block is enough.

## Install

With the [skills CLI](https://github.com/vercel-labs/skills) (needs Node):

```
npx skills add LeechXDD/hokor -g -a claude-code
```

`-g` installs to `~/.claude/skills/` for all projects; drop it to install into the current project's `.claude/skills/`. Update later with `npx skills update`.

Or by hand:

```
git clone https://github.com/LeechXDD/hokor.git
mkdir -p ~/.claude/skills
cp -r hokor/skills/hokor ~/.claude/skills/
```

To follow updates, use `ln -s "$PWD/hokor/skills/hokor" ~/.claude/skills/hokor` instead of `cp -r`.

## Use

Correct the agent the way you normally would ("don't do that again", "deal with it", "remember this", "make it a hook") and it invokes the skill itself. You can also type `/hokor`.

It will:

1. Decide whether the mistake shows in the tool call itself: the command, arguments, paths, or the content about to be written.
2. If it does: look for an existing script in your settings that handles the same kind of thing and add a branch, otherwise write a new one, in project settings if the mistake can only happen in this repo, in user settings if it can happen anywhere; try it on one call that should be blocked and one that should pass; show you the JSON to add to settings and register it only after you confirm; once the hook is live, remove the entry from CLAUDE.md, the lessons file or the standards file.
3. If it doesn't: skip one-offs; put what every session needs in CLAUDE.md; put what a certain kind of task needs, once it has recurred, in the standards file; put first or rare occurrences in the lessons file, promoting an entry to the standards file once the same kind of mistake reaches the threshold (3 by default).

If the project already has a lessons file and a standards file, it uses them. Otherwise, the first time it needs one, it asks you once and suggests `.claude/rules/lessons.md` (and `.claude/rules/standards.md` at the first promotion): files under `.claude/rules/` load every session without editing CLAUDE.md, and the `<!-- seen -->` comments are stripped from context. You can instead keep them private (gitignored, this worktree only) or skip the lessons file and keep everything as one-line entries in CLAUDE.md.

## What a hook looks like

```bash
#!/bin/bash
# Block pkill -f: it matches the whole command line and kills processes from other sessions
cmd=$(jq -r '.tool_input.command // empty')
if echo "$cmd" | grep -qE '(^|[;&|] *)pkill +(-[a-zA-Z]*f|--full)'; then
  echo "Don't use pkill -f; it kills processes with similar command lines in other sessions." >&2
  echo "If you started the process: record its PID when starting it and kill that PID when cleaning up." >&2
  echo "If you didn't start it: ask the user first." >&2
  exit 2
fi
exit 0
```

This example reads the call's JSON with [jq](https://jqlang.org/) (`brew install jq` or `apt install jq`). The skill doesn't require it; the agent can write hooks in Python or anything else.

Registered in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash ~/.claude/hooks/no_pkill_f.sh"}]}
    ]
  }
}
```

The reason must go to stderr (with exit code 2) or `permissionDecisionReason` for the model to see it. A reason only in `systemMessage` reaches you, not the model.

## Tested

See [tests/skill-exams](tests/skill-exams/README.md): 5 behavior exams and a trigger test, with results from 2026-10-26, plus a controlled experiment comparing what the agent does next when a hook only says "Blocked." versus when it gives the right path. The exams and their write-up are in Chinese.

## License

MIT
