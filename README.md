# 贝礼 AI 技能（beiliai-skills）· AI 拉片

> “拉片”是影视行业的学习方法：把一部片子一个镜头一个镜头地反复看、暂停、慢放，分析并记录。
> 这个技能让你的 AI Agent 替你拉片：丢一个短视频链接，拿回爆款结构、分镜、运镜、逐句文案和 BGM。

适用于 Claude Code、Codex、WorkBuddy、OpenClaw 等支持 Agent Skill 的客户端。由 [贝礼 AI](https://www.beiliai.com) 提供服务。

## 能做什么

| 能力 | 说明 |
| --- | --- |
| 深度分析 | 爆款结构：钩子、节奏、留存设计、可复用写法、改写建议 |
| 分镜拆解 | 每个镜头的时间、画面描述、景别、机位、切镜方式、制作方式（实拍 / AI / 录屏…），以及每个镜头的片段视频 |
| 运镜拆解 | 相邻同运镜的镜头合并成段：主次运动、轨迹、速度、稳定性、运镜意图 |
| 视频文案 | 口播与字幕全文，逐句、逐词时间戳 |
| BGM 识别 | 歌名、歌手与使用时段 |

支持抖音、快手、B 站、小红书、视频号等平台的分享链接。

## 安装

**最简单：把下面这句话发给你的 Agent**

```
请按 https://www.beiliai.com/agent/install.md 安装贝礼 AI 技能
```

Agent 会下载技能、核对文件校验值，并给你一个授权链接：在浏览器里用手机号验证码登录（没有账号自动注册，新用户送体验积分），点“授权”即可，**不需要复制任何密钥**。

**从 GitHub 安装**：`git clone https://github.com/beiliai/beiliai-skills ~/.claude/skills/beiliai-skills`（Codex 换成 `~/.codex/skills/beiliai-skills`），然后运行 `python ~/.claude/skills/beiliai-skills/scripts/beiliai.py login`。

**手动安装**：把本仓库的 `SKILL.md` 和 `scripts/beiliai.py` 放到客户端的技能目录下（保持目录结构）：

| 客户端 | 目录 |
| --- | --- |
| Claude Code | `~/.claude/skills/beiliai-skills/` |
| Codex | `~/.codex/skills/beiliai-skills/` |
| 其他 | 客户端技能目录下的 `beiliai-skills/` |

然后运行 `python scripts/beiliai.py login` 完成授权。需要 Python 3.8+，只用标准库，无需安装依赖。

## 用法示例

- “帮我拉片这个视频：https://v.douyin.com/xxxx/”
- “只要这条视频的文案，带时间”
- “这条视频的分镜和运镜是怎么设计的”
- “我还有多少积分”“上次那个拆解结果给我看看”

按次计费（积分），**提交前一定先报价并由你确认**；失败不收费，预扣积分自动退回。价格见 [价格页](https://www.beiliai.com/pricing)。

## 安全与隐私

- 授权走浏览器确认，密钥只保存在本机 `~/.beiliai/credentials.json`（权限 600），任何输出都不会显示密钥；可随时在 [API 密钥页](https://www.beiliai.com/account/api-keys) 删除。
- 技能**不会自动更新、不会重启你的客户端**：有新版本时只提醒，你同意后才升级，并逐个核对文件校验值。
- 视频标题、口播文案等第三方内容一律当作数据处理，技能说明要求 Agent 不执行其中的任何指令。

## 开放接口

想在自己的应用里调用：见 [API 文档](https://www.beiliai.com/agent/api.html)。

## 版本

见 [changelog.json](changelog.json)。当前版本以 [manifest.json](manifest.json) 为准。

## 许可

[MIT](LICENSE)。本仓库只包含客户端技能；拆解服务由贝礼 AI 提供，使用服务需遵守 [贝礼 AI 用户协议](https://www.beiliai.com)。

## 发布（维护者）

技能文件与 WorkBuddy 安装包发布在阿里云 OSS，地址由 [release.json](release.json) 决定（当前为 `https://skls.oss-cn-hangzhou.aliyuncs.com/bl/skill/`）：

```bash
# 改 scripts/beiliai.py 的 VERSION 与 changelog.json 后：
python -I -X utf8 sync-to-web.py --publish            # 写入发布地址、生成清单、打 WorkBuddy 连接器、同步网站、上传 OSS
python -I -X utf8 sync-to-web.py --publish --keep 5   # 同时只保留最近 5 个版本
```

OSS 访问密钥只在本机：`release.local.json`（不进 git）写明密钥文件位置。
