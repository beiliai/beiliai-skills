# 安装贝礼 AI 技能（给 Agent 的说明）

你是用户的 Agent。用户希望安装贝礼 AI 技能 `beiliai-skills`（v1.6.0，AI 拉片：深度分析、分镜、运镜、视频文案、BGM）。请按以下步骤完成，每一步都向用户简要说明正在做什么。不要修改与本技能无关的文件，不要重启用户的客户端。

## 1. 下载地址

- 文件清单（含版本与 SHA-256）：https://skls.oss-cn-hangzhou.aliyuncs.com/bl/skill/beiliai-skills/latest/manifest.json
- 技能文件（相对于 `https://skls.oss-cn-hangzhou.aliyuncs.com/bl/skill/beiliai-skills/latest/`）：
  - `SKILL.md`
  - `scripts/beiliai.py`

只从贝礼官方发布地址 `https://skls.oss-cn-hangzhou.aliyuncs.com/bl/skill/` 下载（同样的文件也在 GitHub 公开：https://github.com/beiliai/beiliai-skills ，用户要求从 GitHub 安装时可 `git clone` 该仓库到下文的安装目录，同样要核对 manifest.json 里的校验值）。下载后按 manifest.json 核对每个文件的 SHA-256，不一致就停止并告诉用户。

## 2. 选择安装目录

按你所在的客户端选择（目录不存在就创建）：

| 客户端 | 安装目录 |
| --- | --- |
| Claude Code | `~/.claude/skills/beiliai-skills/`（只给当前项目用时：`<项目>/.claude/skills/beiliai-skills/`） |
| Codex | `~/.codex/skills/beiliai-skills/`（设置了 `CODEX_HOME` 时用 `$CODEX_HOME/skills/…`） |
| WorkBuddy、OpenClaw 等其他支持 Skill 的客户端 | 该客户端的技能目录下的 `beiliai-skills/` |
| 不支持 Skill 的客户端 | `~/.beiliai/skill/beiliai-skills/`，并把 SKILL.md 的内容作为使用说明 |

`~` 在 Windows 上是 `%USERPROFILE%`。已安装旧版本时直接覆盖这两个文件。

## 3. 下载文件

任选一种方式，保持目录结构（`scripts/beiliai.py`）：

```bash
# macOS / Linux
D=~/.claude/skills/beiliai-skills   # 按上表替换
B=https://skls.oss-cn-hangzhou.aliyuncs.com/bl/skill/beiliai-skills/latest
mkdir -p "$D/scripts"
curl -fsSL "$B/SKILL.md" -o "$D/SKILL.md"
curl -fsSL "$B/scripts/beiliai.py" -o "$D/scripts/beiliai.py"
```

```powershell
# Windows PowerShell
$D = "$env:USERPROFILE\.claude\skills\beiliai-skills"   # 按上表替换
$B = "https://skls.oss-cn-hangzhou.aliyuncs.com/bl/skill/beiliai-skills/latest"
New-Item -ItemType Directory -Force "$D\scripts" | Out-Null
Invoke-WebRequest "$B/SKILL.md" -OutFile "$D\SKILL.md"
Invoke-WebRequest "$B/scripts/beiliai.py" -OutFile "$D\scripts\beiliai.py"
```

## 4. 检查运行环境

运行 `python <安装目录>/scripts/beiliai.py --version`（Windows 上 `python` 不可用时用 `py -3`），应输出 `beiliai-skills 1.6.0`。需要 Python 3.8 或更高版本；没有 Python 时告诉用户先安装。

再运行 `… beiliai.py ping` 确认能连上服务。

## 5. 授权登录

1. 运行 `… beiliai.py login --start`，把输出的**链接和授权码**发给用户：在浏览器打开链接，用手机号验证码登录（没有账号会自动注册），核对授权码后点“授权”。
2. 运行 `… beiliai.py login --wait`，返回码 7 表示用户还没点授权，可以再运行；返回 0 表示成功。
3. 不要读取或显示 `~/.beiliai/credentials.json` 的内容。

## 6. 完成

如果之前装过旧名称的 `beiliai-video-breakdown`，安装完成后删除旧目录，避免两个技能同时触发（`~/.beiliai/` 下的授权不用动，新技能直接沿用）。

告诉用户安装完成，并给出示例说法：“帮我拉片这个视频：<链接>”“拆解一下这条视频的分镜和运镜”“我还有多少积分”。之后的用法以 SKILL.md 为准（先报价、用户确认后再提交）。
