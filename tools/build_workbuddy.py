"""打包 WorkBuddy 连接器：生成 pip 安装包（wheel）和连接器 zip，输出到 dist/。

用法：python -I tools/build_workbuddy.py
- dist/beiliai_skills-<版本>-py3-none-any.whl：WorkBuddy 托管的 Python 里用 pip 安装（包含 python -m beiliai_skills 命令）；
  发布到 https://www.beiliai.com/agent/pkg/ 下（sync-to-web.py 会一起复制）。
- dist/beiliai-workbuddy-connector-<版本>.zip：上传到 WorkBuddy 开放平台的连接器包
  （connector-meta.json、cli.json、icon.png、skills/beiliai-skills/SKILL.md，单一顶层目录）。
只用 Python 标准库。
"""
import base64
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DIST = HERE / "dist"
WHEEL_BASE_URL = "https://www.beiliai.com/agent/pkg/"
PLATFORMS = ("darwin", "linux", "win32")


def version() -> str:
    text = (HERE / "scripts" / "beiliai.py").read_text(encoding="utf-8")
    return re.search(r'^VERSION = "([^"]+)"', text, re.M).group(1)


def record_line(name: str, data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return "%s,sha256=%s,%d" % (name, digest, len(data))


def zip_bytes(entries) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    return buf.getvalue()


def build_wheel(ver: str) -> Path:
    cli = (HERE / "scripts" / "beiliai.py").read_text(encoding="utf-8")
    cli = cli.replace('DISTRIBUTION = "skill"', 'DISTRIBUTION = "workbuddy"', 1)
    assert 'DISTRIBUTION = "workbuddy"' in cli
    dist_info = "beiliai_skills-%s.dist-info" % ver
    files = [
        ("beiliai_skills/__init__.py", ('"""贝礼 AI 技能命令行。"""\n__version__ = "%s"\n' % ver).encode()),
        ("beiliai_skills/__main__.py", b"import sys\n\nfrom .cli import main\n\nsys.exit(main())\n"),
        ("beiliai_skills/cli.py", cli.encode("utf-8")),
        (dist_info + "/METADATA", ("Metadata-Version: 2.1\nName: beiliai-skills\nVersion: %s\n"
                                   "Summary: Beiliai AI skill CLI: AI shot-by-shot short-video breakdown\n"
                                   "Home-page: https://github.com/beiliai/beiliai-skills\nLicense: MIT\n"
                                   "Requires-Python: >=3.8\n" % ver).encode()),
        (dist_info + "/WHEEL", b"Wheel-Version: 1.0\nGenerator: beiliai-build\nRoot-Is-Purelib: true\nTag: py3-none-any\n"),
        (dist_info + "/entry_points.txt", b"[console_scripts]\nbeiliai = beiliai_skills.cli:main\n"),
        (dist_info + "/top_level.txt", b"beiliai_skills\n"),
    ]
    record = "\n".join(record_line(n, d) for n, d in files) + "\n%s/RECORD,,\n" % dist_info
    files.append((dist_info + "/RECORD", record.encode()))
    path = DIST / ("beiliai_skills-%s-py3-none-any.whl" % ver)
    path.write_bytes(zip_bytes(files))
    return path


def workbuddy_skill_md(ver: str) -> bytes:
    text = (HERE / "SKILL.md").read_text(encoding="utf-8")
    old_alias = "通过 `scripts/beiliai.py`（只用 Python 3.8+ 标准库）调用贝礼 AI 的视频拆解服务。下文用 `beiliai` 代表 `python <本技能目录>/scripts/beiliai.py`；Windows 上 `python` 不可用时改用 `py -3`。"
    assert old_alias in text
    text = text.replace(old_alias, "本技能由 WorkBuddy 连接器“贝礼 AI”安装。下文用 `beiliai` 代表命令 `python -m beiliai_skills`（在 WorkBuddy 托管的 Python 环境里运行）。")
    start = text.index("## 首次使用：授权登录")
    end = text.index("## 拆解流程")
    text = text[:start] + (
        "## 首次使用：授权登录\n\n"
        "1. 运行 `beiliai status`。显示“已授权”就跳过本节。\n"
        "2. 未授权（返回码 3）时，请用户在 WorkBuddy 的连接器列表里找到“贝礼 AI”，点“连接”：会打开贝礼 AI 的授权页，"
        "没有账号用手机号验证码登录即自动注册（新用户赠送体验积分），核对授权码后点“授权”。\n"
        "3. 用户无法使用连接按钮时，也可以运行 `beiliai login --start`，把输出的链接和授权码发给用户，用户授权后运行 `beiliai login --wait`。\n"
        "4. 授权会在用户账号下生成一把 API 密钥，可在 https://www.beiliai.com/account/api-keys 查看或删除；在 WorkBuddy 里断开连接也会作废这把密钥。\n\n"
    ) + text[end:]
    return text.encode("utf-8")


def build_connector(ver: str, wheel: Path) -> Path:
    wheel_sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
    wheel_url = "%s%s#sha256=%s" % (WHEEL_BASE_URL, wheel.name, wheel_sha)
    run = "python -m beiliai_skills"
    meta = {
        "name": "贝礼 AI",
        "name_zh": "贝礼 AI",
        "name_en": "Beiliai AI",
        "description": "AI 拉片：逐镜头拆解短视频的爆款结构、分镜、运镜、逐句文案和 BGM。",
        "description_zh": "AI 拉片：发一个抖音、快手、B 站、小红书或视频号链接，逐镜头拆解爆款结构、分镜、运镜、逐句文案和 BGM。",
        "description_en": "AI shot-by-shot breakdown of short videos: viral structure, shots, camera moves, timed script, BGM.",
        "source": "beiliai",
        "type": "cli",
        "minWorkbuddyVersion": "5.0.0",
        "version": ver,
        "examples_zh": [
            "帮我拉片这个视频：https://v.douyin.com/xxxxxx/",
            "这条视频的分镜和运镜是怎么设计的？",
            "只要这条视频的文案，标出每句话的时间",
        ],
        "examples_en": [
            "Break down this video shot by shot: https://v.douyin.com/xxxxxx/",
            "How are the shots and camera moves designed in this video?",
            "Give me only the script of this video with a timestamp for each sentence",
        ],
    }
    cli = {
        "runtime": {"type": "python"},
        "init": {p: 'python -m pip install --upgrade --disable-pip-version-check "%s"' % wheel_url for p in PLATFORMS},
        "auth": {p: "%s login --no-browser --client workbuddy --timeout 290" % run for p in PLATFORMS},
        "authDeviceFlow": {
            "uriPattern": "(https://www\\.beiliai\\.com/agent-authorize\\?code=[A-Z]{4}-[A-Z]{4})",
            "defaultExpiresInSeconds": 600,
            "codeEmbeddedInUri": True,
        },
        "authUrlDomain": "www.beiliai.com",
        "status": {p: "%s status --check" % run for p in PLATFORMS},
        "statusMatch": "authenticated: yes",
        "unAuth": {p: "%s logout --revoke" % run for p in PLATFORMS},
        "versionCheck": {
            "command": {p: "%s --version" % run for p in PLATFORMS},
            "minVersion": ver,
        },
    }
    for name, value in (("connector-meta.json", meta), ("cli.json", cli)):
        (DIST / "workbuddy" / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    icon = (HERE / "assets" / "icon.png").read_bytes()
    top = "beiliai-workbuddy-connector"
    entries = [
        (top + "/connector-meta.json", (DIST / "workbuddy" / "connector-meta.json").read_bytes()),
        (top + "/cli.json", (DIST / "workbuddy" / "cli.json").read_bytes()),
        (top + "/icon.png", icon),
        (top + "/skills/beiliai-skills/SKILL.md", workbuddy_skill_md(ver)),
    ]
    path = DIST / ("beiliai-workbuddy-connector-%s.zip" % ver)
    path.write_bytes(zip_bytes(entries))
    return path


def main() -> None:
    ver = version()
    (DIST / "workbuddy").mkdir(parents=True, exist_ok=True)
    for old in DIST.glob("*.whl"):
        old.unlink()
    for old in DIST.glob("*.zip"):
        old.unlink()
    wheel = build_wheel(ver)
    connector = build_connector(ver, wheel)
    print(wheel.name, hashlib.sha256(wheel.read_bytes()).hexdigest())
    print(connector.name)


if __name__ == "__main__":
    main()
