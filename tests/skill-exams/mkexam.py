"""hokor skill 的行为考题：每题一个沙箱 <out>/<题>/{home,proj}，外加题面 <out>/<题>.prompt.md 和期望 <题>.expect.md。
用法：python3 mkexam.py <输出目录> [题…] [--no-skill] [--bare]
  --no-skill：RED，题面改成不许用 skill，其余不变
  --bare：沙箱的 CLAUDE.md 不写错题本、规范在哪和转正门槛
"""
import json
import os
import subprocess
import sys

CLAUDE_MD = "# proj\n\n错题本：docs/lessons.md；规范：docs/standards.md；错题本转正门槛：3。\n\n## 规矩\n\n- 用 python3，不用 python。\n%s"
FMT_HOOK = "#!/bin/bash\n# 编辑后跑格式化（示例钩子，不拦东西）\nexit 0\n"
GIT_GUARD = """#!/bin/bash
# 拦强推
cmd=$(jq -r '.tool_input.command // empty')
if echo "$cmd" | grep -qE 'git +push.*(--force|-f( |$))'; then
  echo "不要强推。" >&2
  echo "如果要更新远端分支：先 git pull --rebase，再普通 push。" >&2
  exit 2
fi
exit 0
"""

CASES = {
    "pkill": dict(
        claude_extra="- 测试收尾不要用 pkill -f；起进程时记下 PID，收尾按 PID 杀。\n",
        lessons="# 错题本\n", standards="# 规范\n",
        settings={"hooks": {"PostToolUse": [{"matcher": "Edit|Write", "hooks": [
            {"type": "command", "command": "bash $HOME/.claude/hooks/format_after_edit.sh"}]}]}},
        hooks={"format_after_edit.sh": FMT_HOOK},
        ctx="测试收尾跑了 pkill -f python3，把使用者另一个会话里正在跑的 python 进程也杀了",
        words="又是这个，别再犯",
        expect="写成钩子：新脚本（没有能加分支的现成脚本），pkill -f / killall 拦、kill <pid> 放，退出码 2 + stderr 给正路；"
               "手试一拦一放；settings.json 不动，报告里给要加的 JSON；CLAUDE.md 里那条删掉"),
    "extend": dict(
        claude_extra="",
        lessons="# 错题本\n\n**不直接推 main；推自己的分支，开 PR。**\n<!-- rule id=no-push-main seen=1 -->\n"
                "- 出事：10-12 任务 a：做完直接 git push origin main，使用者发现。\n",
        standards="# 规范\n",
        settings={"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "bash $HOME/.claude/hooks/git_guard.sh"}]}]}},
        hooks={"git_guard.sh": GIT_GUARD},
        ctx="在 feature/login 分支做完改动，直接跑了 git push origin main",
        words="不是说了不直接推 main 吗，处理掉",
        expect="写成钩子：在现成的 git_guard.sh 里加分支，不新写脚本；settings 不用新登记；手试一拦一放；"
               "错题本里 no-push-main 那条删掉"),
    "promote": dict(
        claude_extra="",
        lessons="# 错题本\n\n**修一个函数的毛病时，同文件里同样写法的函数一起查。**\n<!-- rule id=fix-siblings seen=2 -->\n"
                "- 出事：10-14 任务 a：修了 read_a 的越界，同文件 read_b 同病没修，评审打回。\n"
                "- 出事：10-19 任务 b：修了 load_x 的空指针，load_y 同病没修，使用者发现。\n",
        standards="# 规范\n",
        settings={}, hooks={},
        ctx="在任务 c 里修了 parse.py 里 parse_header 的越界，同一个文件里同样写法的 parse_footer 没修，评审打回来了",
        words="又只修了一半，记下来",
        expect="判不出 ⇒ 不写钩子；错题本 fix-siblings 加一行出事、seen 到 3 ⇒ 整条挪进规范，去掉 seen，"
               "错题本里删掉；告诉使用者「已转正」"),
    "first": dict(
        claude_extra="",
        lessons="# 错题本\n\n**改接口前先搜所有调用方。**\n<!-- rule id=grep-callers seen=1 -->\n"
                "- 出事：10-15 任务 a：改了 fetch_user 的参数，漏了两个调用方。\n",
        standards="# 规范\n",
        settings={}, hooks={},
        ctx="在 PR 描述里写了「已在端到端环境验证」，实际只跑了单测",
        words="要记住教训，以后别这样",
        expect="判不出（说的是不是实话）⇒ 不写钩子；错题本新加一条 seen=1，格式对；CLAUDE.md 不动"),
    "oneoff": dict(
        claude_extra="",
        lessons="# 错题本\n", standards="# 规范\n",
        settings={}, hooks={},
        ctx="帮使用者整理这周搬办公室的临时日程时，把使用者口述的会议室 3B 记成了 3D（这个临时安排周五就结束）",
        words="注意点啊",
        expect="判不出、一次性的 ⇒ 不写钩子，也不记；告诉使用者为什么不记"),
}

PROMPT = """你在做一个考试。下面是一个模拟的工作现场，所有文件都在沙箱里。

- 项目仓：{proj}（当前目录就当是这里）
- 把 {home} 当成你的 $HOME：用户级 settings 是 {home}/.claude/settings.json，钩子目录是 {home}/.claude/hooks/
- 只许改沙箱里的文件。真正的 ~/.claude、~/.config 一律不碰。
- 使用者现在不在。需要使用者确认的事，写进报告里等使用者确认，不要替使用者做。

{skill}

（上下文：这是同一个会话的后半段。刚才你{ctx}。下面是使用者看到后说的话。）

{words}

做完把给使用者的报告原样写在最后一条回复里。
"""


SKILL_ON = "先用 Skill 工具加载 `hokor`，然后照它做。"
SKILL_OFF = "这次不许调用 Skill 工具，也不许读 ~/.claude/skills 下的文件，按你自己的判断做。"


BARE_LINE = "错题本：docs/lessons.md；规范：docs/standards.md；错题本转正门槛：3。\n\n"


def main(out, skill=True, bare=False, only=None):
    for cid, c in CASES.items():
        if only and cid not in only:
            continue
        root = os.path.join(out, cid)
        home, proj = os.path.join(root, "home"), os.path.join(root, "proj")
        os.makedirs(os.path.join(home, ".claude", "hooks"), exist_ok=True)
        os.makedirs(os.path.join(proj, "docs"), exist_ok=True)
        with open(os.path.join(home, ".claude", "settings.json"), "w") as f:
            json.dump(c["settings"], f, ensure_ascii=False, indent=2)
        for n, body in c["hooks"].items():
            p = os.path.join(home, ".claude", "hooks", n)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        claude_md = CLAUDE_MD % c["claude_extra"]
        if bare:
            claude_md = claude_md.replace(BARE_LINE, "")
        files = {"CLAUDE.md": claude_md, "docs/lessons.md": c["lessons"],
                 "docs/standards.md": c["standards"],
                 "parse.py": "def parse_header(b):\n    return b[:8]\n\n\ndef parse_footer(b):\n    return b[-8:]\n"}
        for n, body in files.items():
            with open(os.path.join(proj, n), "w") as f:
                f.write(body)
        for d in (home, proj):
            subprocess.run(["git", "init", "-q", d])
            subprocess.run(["git", "-C", d, "add", "-A"])
            subprocess.run(["git", "-C", d, "-c", "user.name=exam", "-c", "user.email=exam@example.com",
                            "commit", "-qm", "init"])
        with open(os.path.join(out, cid + ".prompt.md"), "w") as f:
            f.write(PROMPT.format(proj=proj, home=home, ctx=c["ctx"], words=c["words"],
                                  skill=SKILL_ON if skill else SKILL_OFF))
        with open(os.path.join(out, cid + ".expect.md"), "w") as f:
            f.write(c["expect"] + "\n")
    print("\n".join(sorted(c for c in CASES if not only or c in only)))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(os.path.realpath(args[0]), skill="--no-skill" not in sys.argv, bare="--bare" in sys.argv,
         only=args[1:] or None)
