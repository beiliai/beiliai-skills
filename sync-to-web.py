"""把技能源文件同步到网站发布目录（muse-web/src/renderer/public/agent/）。

源文件以本目录（D:\\PRO\\AI\\创作\\skills\\beiliai-skills）为准：
1. 技能文件统一转成 LF 换行（网站按文件直出，manifest 校验值按 LF 计算）；
2. 重新生成 manifest.json（版本号取 scripts/beiliai.py 的 VERSION）；
3. 复制到 muse-web：技能文件 → public/agent/skill/beiliai-skills/，
   安装说明与文档（install.md、install.html、api.html）→ public/agent/。
用法：python -I sync-to-web.py [muse-web 根目录]
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_FILES = ["SKILL.md", "scripts/beiliai.py"]
DOC_FILES = ["install.md", "install.html", "api.html"]


def to_lf(path: Path) -> bytes:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    path.write_bytes(data)
    return data


def main() -> None:
    web_root = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent.parent / "muse-web"
    public = web_root / "src" / "renderer" / "public" / "agent"
    if not public.is_dir():
        sys.exit("找不到网站发布目录：%s" % public)
    version = re.search(r'^VERSION = "([^"]+)"', (HERE / "scripts/beiliai.py").read_text(encoding="utf-8"), re.M).group(1)
    files = []
    for rel in SKILL_FILES:
        data = to_lf(HERE / rel)
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    changelog = json.loads((HERE / "changelog.json").read_text(encoding="utf-8"))
    if not changelog or changelog[0].get("version") != version:
        sys.exit("changelog.json 第一条的版本号必须是 %s" % version)
    manifest = {"name": "beiliai-skills", "version": version,
                "base_url": "https://www.beiliai.com/agent/skill/beiliai-skills/", "files": files,
                "changelog": changelog[:10]}
    (HERE / "manifest.json").write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    target = public / "skill" / "beiliai-skills"
    for rel in SKILL_FILES + ["manifest.json"]:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / rel, dest)
    # 旧名称 beiliai-video-breakdown（v1.0–1.3）的安装仍会检查旧地址：在旧地址放同一套文件和一份
    # name 为旧名称的清单，让旧版本也能收到“有新版本”的提醒并升级到新文件。
    legacy = public / "skill" / "beiliai-video-breakdown"
    legacy_manifest = dict(manifest, name="beiliai-video-breakdown",
                           base_url="https://www.beiliai.com/agent/skill/beiliai-video-breakdown/")
    for rel in SKILL_FILES:
        dest = legacy / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / rel, dest)
    (legacy / "manifest.json").write_bytes((json.dumps(legacy_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    for rel in DOC_FILES:
        to_lf(HERE / "docs" / rel)
        shutil.copyfile(HERE / "docs" / rel, public / rel)
    print("已同步 v%s 到 %s" % (version, public))


if __name__ == "__main__":
    main()
