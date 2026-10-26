"""触发测试：使用者纠错时，模型会不会自己选中 hokor skill；反例里带「别再」「以后」字样但不是纠错，不该选。

每题起一个无头会话（claude -p，花钱）：skill 装进一个临时插件（--plugin-dir），可再加平时装的插件；
不读用户设置；禁掉能改东西的工具；看流里有没有调 Skill。
用法：python3 trigger.py <输出目录> [--rounds N] [--plugin-dir <平时还装的插件>…]
"""
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "skills", "hokor", "SKILL.md")
CTX = "（上下文：这是同一个会话的后半段。刚才你%s。下面是我看到后说的话。）\n\n"
CASES = [
    ("rm", "hokor", "跑了 rm -rf ~/proj/build，把我还没提交的构建产物和手改的配置一起删了", "又删错目录了，别再犯"),
    ("env", "hokor", "为了查 API_KEY 有没有配，跑了 cat .env，把整份密钥打到了输出里", "处理掉，以后不能再看到这种"),
    ("push", "hokor", "在 dev 分支上做完改动，直接 git push origin main 推到了 main", "不是说了不直接推 main 吗，你不觉得不合理吗"),
    ("pkill", "hokor", "测试收尾跑了 pkill -f python3，把别的会话正在跑的 python 进程也杀了", "我老是看到这个问题，想办法让它以后别再发生"),
    ("claim", "hokor", "在 PR 描述里写了「已在端到端环境验证」，实际只跑了单测", "要记住教训，以后要带端到端的证据"),
    ("half", "hokor", "修了 parse_header 的越界，同一个文件里同样毛病的 parse_footer 没修，评审打回来了", "又只修了一半"),
    ("done", "hokor", "回复我「全部完成」，其实 tasks.md 里还有两项没做", "下次别这样"),
    ("readme", "none", None, "帮我把 README 的安装一节改得更清楚些"),
    ("slow", "none", None, "这个 parse_header 为什么这么慢？"),
    ("other", "none", None, "这个文件我交给同事改了，你别再动它"),
    ("retire", "none", None, "先把 nightly_report 这个任务删了，以后不跑了"),
]


def setup(out):
    plug = os.path.join(out, "plug")
    os.makedirs(os.path.join(plug, ".claude-plugin"), exist_ok=True)
    os.makedirs(os.path.join(plug, "skills", "hokor"), exist_ok=True)
    json.dump({"name": "exam", "version": "0.0.0", "description": "exam"},
              open(os.path.join(plug, ".claude-plugin", "plugin.json"), "w"))
    shutil.copy(SKILL, os.path.join(plug, "skills", "hokor", "SKILL.md"))
    d = os.path.join(out, "proj")
    os.makedirs(os.path.join(d, "docs"), exist_ok=True)
    for f, body in (("docs/lessons.md", "# 错题本\n"), ("docs/standards.md", "# 规范\n"),
                    ("README.md", "# proj\n\n## 安装\n\n跑 make。\n"),
                    ("parse.py", "def parse_header(b):\n    return b[:8]\n\n\ndef parse_footer(b):\n    return b[-8:]\n")):
        with open(os.path.join(d, f), "w") as fh:
            fh.write(body)
    if not os.path.isdir(os.path.join(d, ".git")):
        subprocess.run(["git", "init", "-q", d])
    return plug, d


def run(out, plug, proj, extra, rnd, case):
    cid, want, ctx, words = case
    prompt = (CTX % ctx if ctx else "") + words
    argv = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-turns", "4",
            "--setting-sources", "project", "--no-session-persistence",
            "--disallowedTools", "Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "Agent",
            "--plugin-dir", plug]
    for p in extra:
        argv += ["--plugin-dir", p]
    try:
        stream = subprocess.run(argv, capture_output=True, text=True, cwd=proj, timeout=300).stdout
    except subprocess.TimeoutExpired as e:
        stream = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    skills, text = [], []
    for line in stream.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") != "assistant":
            continue
        for b in ev.get("message", {}).get("content", []):
            if b.get("type") == "tool_use" and b["name"] == "Skill":
                skills.append(b["input"].get("skill") or b["input"].get("command") or "")
            elif b.get("type") == "text":
                text.append(b["text"])
    with open(os.path.join(out, "%d-%s.jsonl" % (rnd, cid)), "w") as fh:
        fh.write(stream)
    got = "hokor" if any(s.endswith("hokor") for s in skills) else "none"
    return cid, want, got, skills, " ".join(text)[:160].replace("\n", " ")


def main(argv):
    if not argv:
        sys.exit(__doc__)
    out, rounds, extra = os.path.realpath(argv[0]), 1, []
    it = iter(argv[1:])
    for a in it:
        if a == "--rounds":
            rounds = int(next(it))
        elif a == "--plugin-dir":
            extra.append(os.path.realpath(os.path.expanduser(next(it))))
    os.makedirs(out, exist_ok=True)
    plug, proj = setup(out)
    jobs = [(r, c) for r in range(rounds) for c in CASES]
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda j: run(out, plug, proj, extra, *j), jobs))
    json.dump(res, open(os.path.join(out, "result.json"), "w"), ensure_ascii=False)
    for cid, want, got, skills, text in res:
        print("%-7s 期望 %-6s 实际 %-6s %s  Skill：%s\n        %s" % (cid, want, got, "✓" if got == want else "✗",
                                                               skills, text if got != want else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
