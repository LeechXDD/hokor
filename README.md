# Hokor

[English](README.en.md)

skill 正文是英文写的；你跟 agent 说中文照样用。

一个 Claude Code skill。Agent 撞过的错，能从工具调用判出来的，写成 settings 里的钩子：下次撞上那一刻拦下，告诉它正确做法。判不出来的，再决定记不记、记进 CLAUDE.md、规范还是错题本。名字取 hook + record。

## 为什么

不常撞的错写进 CLAUDE.md，每次会话都占上下文，写多了反而稀释真正常用的规矩。Claude Code 的钩子本来就能在拦下时把理由交给模型（退出码 2，stderr 给模型看），所以这类错写成钩子更划算：平时不占地方，撞上时正好给出正路。

钩子防不到百分之百，换个写法绕过去的不追。被拦下那次给了正路就够。

## 安装

```
git clone https://github.com/LeechXDD/hokor.git
mkdir -p ~/.claude/skills
cp -r hokor/skills/hokor ~/.claude/skills/
```

想跟着仓库更新，把 `cp -r` 换成 `ln -s "$PWD/hokor/skills/hokor" ~/.claude/skills/hokor`。

## 用法

Agent 犯了错，你照平时那样纠正就行，比如「别再犯」「处理掉」「记下来」「写成钩子」，它会自己调用这个 skill。也可以直接输入 `/hokor`。

它会：

1. 判这个错能不能从工具调用本身（命令、参数、路径、要写进文件的内容）判出来。
2. 能：先找 settings 里有没有管同一类事的现成脚本，有就加个分支，没有才新写，只在本仓会犯的进项目级 settings，到哪都会犯的进用户级；手试一拦一放；把要加进 settings 的那段 JSON 给你看，你确认后再登记；钩子生效后，从 CLAUDE.md、错题本或规范里删掉那条。
3. 不能：一次性的不记；每次会话都用得上的进 CLAUDE.md；做某类事才用、撞过几次的进规范；头一回或少见的进错题本，同类问题撞满门槛（默认 3 次）就转进规范。

项目里已有错题本和规范就用现成的。没有的话，第一次要记时它会问你一次，默认建议 `.claude/rules/lessons.md`（第一次转正时再建 `.claude/rules/standards.md`）：`.claude/rules/` 下的文件每次会话自动加载，不用改 CLAUDE.md，`<!-- seen -->` 这类注释也不进上下文。也可以选私用（加进 `.gitignore`，只在当前 worktree 有效），或者不要错题本，全写成 CLAUDE.md 里的一句话。

## 写出来的钩子长什么样

```bash
#!/bin/bash
# 拦 pkill -f：按整条命令行匹配，会杀到别的会话里的进程
cmd=$(jq -r '.tool_input.command // empty')
if echo "$cmd" | grep -qE '(^|[;&|] *)pkill +(-[a-zA-Z]*f|--full)'; then
  echo "不要用 pkill -f，它会杀到别的会话里命令行相似的进程。" >&2
  echo "如果是自己起的进程：起的时候记下 PID，收尾按 PID kill。" >&2
  echo "如果不是你起的：先问使用者。" >&2
  exit 2
fi
exit 0
```

登记进 `~/.claude/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash ~/.claude/hooks/no_pkill_f.sh"}]}
    ]
  }
}
```

理由要写在 stderr（退出码 2）或 `permissionDecisionReason` 里，模型才看得到；只写进 `systemMessage` 的话，只有你看得到。

## 考过什么

见 [tests/skill-exams](tests/skill-exams/README.md)：5 道行为题、一套触发测试，附 10-26 的结果；另有一个对照实验，比较钩子拦下时只说「Blocked.」和给出正路，agent 的下一步有什么不同。

## 许可

MIT
