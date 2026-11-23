"""发布技能：以本目录（D:\\PRO\\AI\\创作\\skills\\beiliai-skills）为准。

1. 读 release.json：把 public_base 写进 scripts/beiliai.py 的 DIST_BASE 行和 docs/ 里的下载地址
   （路径前缀 bl/skill 只由 release.json 决定，不写死在 OSS 权限里）；
2. 技能文件统一 LF，生成 manifest.json（base_url 指向 OSS 上该版本的固定目录）；
3. 打 WorkBuddy 连接器（tools/build_workbuddy.py：pip 包 + 连接器 zip）；
4. 复制到网站 muse-web/src/renderer/public/agent/：安装说明与文档；旧地址 skill/beiliai-skills/ 与
   skill/beiliai-video-breakdown/ 也放一份（v1.6 之前的版本只认网站地址，靠它们收到升级提醒）；
5. 加 --publish 时上传到 OSS：<prefix>/beiliai-skills/<版本>/、<prefix>/beiliai-skills/latest/、
   <prefix>/pkg/、<prefix>/docs/；加 --keep N 时只保留最近 N 个版本目录与安装包（删除更早的历史）。

用法：python -I -X utf8 sync-to-web.py [--publish] [--keep N] [--web <muse-web 根目录>]
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_FILES = ["SKILL.md", "scripts/beiliai.py"]
DOC_FILES = ["install.md", "install.html", "api.html"]
SKILL = "beiliai-skills"


def to_lf(path: Path) -> bytes:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    path.write_bytes(data)
    return data


def apply_release_config(public_base: str) -> None:
    script = HERE / "scripts" / "beiliai.py"
    text = script.read_text(encoding="utf-8")
    text, count = re.subn(r'^DIST_BASE = "[^"]*"', 'DIST_BASE = "%s"' % public_base, text, flags=re.M)
    if count != 1:
        sys.exit("scripts/beiliai.py 里找不到 DIST_BASE 行")
    script.write_text(text, encoding="utf-8", newline="\n")
    latest = "%s/%s/latest" % (public_base, SKILL)
    for rel in ("install.md", "install.html"):
        doc = HERE / "docs" / rel
        content = re.sub(r"https://[^\s\"'`<>)]+/%s/latest" % SKILL, latest, doc.read_text(encoding="utf-8"))
        if latest not in content:
            sys.exit("docs/%s 里没有技能下载地址" % rel)
        doc.write_text(content, encoding="utf-8", newline="\n")


def version_key(value: str):
    return tuple(int(x) if x.isdigit() else 0 for x in value.split("."))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="上传到 OSS")
    parser.add_argument("--keep", type=int, default=0, help="OSS 上只保留最近 N 个版本（0 表示不清理）")
    parser.add_argument("--web", default=str(HERE.parent.parent / "muse-web"))
    args = parser.parse_args()
    release = json.loads((HERE / "release.json").read_text(encoding="utf-8"))
    public_base = release["public_base"].rstrip("/")
    apply_release_config(public_base)

    version = re.search(r'^VERSION = "([^"]+)"', (HERE / "scripts/beiliai.py").read_text(encoding="utf-8"), re.M).group(1)
    changelog = json.loads((HERE / "changelog.json").read_text(encoding="utf-8"))
    if not changelog or changelog[0].get("version") != version:
        sys.exit("changelog.json 第一条的版本号必须是 %s" % version)
    files = []
    for rel in SKILL_FILES:
        data = to_lf(HERE / rel)
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    manifest = {"name": SKILL, "version": version, "base_url": "%s/%s/%s/" % (public_base, SKILL, version),
                "files": files, "changelog": changelog[:10]}
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (HERE / "manifest.json").write_bytes(manifest_bytes)
    subprocess.run([sys.executable, "-I", str(HERE / "tools" / "build_workbuddy.py")], check=True, stdout=subprocess.DEVNULL)
    wheel = HERE / "dist" / ("beiliai_skills-%s-py3-none-any.whl" % version)
    if not wheel.exists():
        sys.exit("缺少 %s" % wheel)

    public = Path(args.web) / "src" / "renderer" / "public" / "agent"
    if not public.is_dir():
        sys.exit("找不到网站发布目录：%s" % public)
    for name in (SKILL, "beiliai-video-breakdown"):
        target = public / "skill" / name
        for rel in SKILL_FILES:
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HERE / rel, target / rel)
        site_manifest = dict(manifest, name=name)
        (target / "manifest.json").write_bytes((json.dumps(site_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    shutil.rmtree(public / "pkg", ignore_errors=True)  # 安装包只放 OSS
    for rel in DOC_FILES:
        to_lf(HERE / "docs" / rel)
        shutil.copyfile(HERE / "docs" / rel, public / rel)
    print("网站：已同步 v%s" % version)

    if not args.publish:
        return
    sys.path.insert(0, str(HERE / "tools"))
    from oss import OSS, content_type  # noqa: E402

    client = OSS(release)
    immutable = "public, max-age=31536000, immutable"
    for folder, cache in ((version, immutable), ("latest", "no-cache")):
        for rel in SKILL_FILES:
            client.put("%s/%s/%s" % (SKILL, folder, rel), (HERE / rel).read_bytes(), content_type(rel), cache)
        client.put("%s/%s/manifest.json" % (SKILL, folder), manifest_bytes, content_type("manifest.json"), cache)
    client.put("pkg/%s" % wheel.name, wheel.read_bytes(), content_type(".whl"), immutable)
    # OSS 默认域名会强制下载 HTML，所以网页版说明只放网站；给 Agent 读的 install.md 两边都放。
    client.put("docs/install.md", (HERE / "docs" / "install.md").read_bytes(), content_type("install.md"), "no-cache")
    print("OSS：已发布 v%s → %s/%s/%s/" % (version, public_base, SKILL, version))

    if args.keep > 0:
        names = client.list(SKILL + "/")
        versions = sorted({n.split("/")[1] for n in names if n.count("/") >= 2 and n.split("/")[1] != "latest"}, key=version_key)
        old = [v for v in versions[:-args.keep] if v != version] if len(versions) > args.keep else []
        for v in old:
            for n in client.list("%s/%s/" % (SKILL, v)):
                client.delete(n)
            for n in client.list("pkg/beiliai_skills-%s-" % v):
                client.delete(n)
            print("OSS：已删除历史版本 v%s" % v)


if __name__ == "__main__":
    main()
