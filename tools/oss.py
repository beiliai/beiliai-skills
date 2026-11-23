"""阿里云 OSS 最小客户端（只用标准库，V1 签名）：上传、下载、列举、删除。

配置来自仓库根目录的 release.json（bucket、endpoint、prefix）；访问密钥从 release.local.json（不进 git）
的 oss_credentials_glob 或环境变量 BEILIAI_OSS_CREDENTIALS 指向的 CSV 读取（或环境变量 BEILIAI_OSS_ACCESS_KEY_ID / BEILIAI_OSS_ACCESS_KEY_SECRET），任何输出都不包含密钥。
所有对象名都由调用方给出相对路径，这里统一加上 prefix——路径前缀由代码配置控制，不写死在 OSS 权限里。

用法：
  python -I tools/oss.py probe                 # 写入/公开读取/列举/删除一个探测文件，验证权限
  python -I tools/oss.py ls [相对前缀]
  python -I tools/oss.py rm <相对路径>...       # 删除（历史版本清理）
  python -I tools/oss.py rmtree <相对前缀>      # 删除前缀下所有对象
"""
import base64
import csv
import glob
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import formatdate
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    return json.loads((ROOT / "release.json").read_text(encoding="utf-8"))


class OSS:
    def __init__(self, config: dict):
        oss = config["oss"]
        self.bucket = oss["bucket"]
        self.endpoint = oss["endpoint"]
        self.prefix = oss["prefix"].strip("/")
        self.public_base = config["public_base"].rstrip("/")
        local = ROOT / "release.local.json"  # 本机私有配置（不进 git）：OSS 访问密钥文件的位置
        pattern = os.environ.get("BEILIAI_OSS_CREDENTIALS", "").strip()
        if not pattern and local.exists():
            pattern = json.loads(local.read_text(encoding="utf-8")).get("oss_credentials_glob", "")
        self.key_id, self.key_secret = self._credentials(pattern)

    @staticmethod
    def _credentials(pattern: str):
        key_id = os.environ.get("BEILIAI_OSS_ACCESS_KEY_ID", "").strip()
        secret = os.environ.get("BEILIAI_OSS_ACCESS_KEY_SECRET", "").strip()
        if key_id and secret:
            return key_id, secret
        files = sorted(glob.glob(pattern)) if pattern else []
        if not files:
            sys.exit("找不到 OSS 访问密钥文件（release.local.json 的 oss_credentials_glob 或 BEILIAI_OSS_CREDENTIALS），也没有设置环境变量。")
        with open(files[-1], encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            sys.exit("OSS 访问密钥文件是空的。")
        row = {k.strip(): (v or "").strip() for k, v in rows[0].items() if k}
        key_id = next((v for k, v in row.items() if k.lower().replace(" ", "") in ("accesskeyid",)), "")
        secret = next((v for k, v in row.items() if k.lower().replace(" ", "") in ("accesskeysecret",)), "")
        if not key_id or not secret:
            sys.exit("OSS 访问密钥文件里没有 AccessKey ID / AccessKey Secret 列。")
        return key_id, secret

    def key(self, rel: str) -> str:
        rel = rel.strip("/")
        if ".." in rel.split("/"):
            raise ValueError("非法路径：%s" % rel)
        return "%s/%s" % (self.prefix, rel) if rel else self.prefix + "/"

    def public_url(self, rel: str) -> str:
        return "%s/%s" % (self.public_base, urllib.parse.quote(rel.strip("/")))

    def _request(self, method: str, key: str = "", body: bytes = b"", headers=None, query: str = "", sub: str = ""):
        headers = dict(headers or {})
        date = formatdate(usegmt=True)
        content_type = headers.get("Content-Type", "")
        content_md5 = base64.b64encode(hashlib.md5(body).digest()).decode() if body else ""
        if content_md5:
            headers["Content-MD5"] = content_md5
        oss_headers = "".join("%s:%s\n" % (k.lower(), v) for k, v in sorted(headers.items()) if k.lower().startswith("x-oss-"))
        resource = "/%s/%s%s" % (self.bucket, key, ("?" + sub) if sub else "")
        to_sign = "\n".join([method, content_md5, content_type, date, oss_headers + resource])
        signature = base64.b64encode(hmac.new(self.key_secret.encode(), to_sign.encode("utf-8"), hashlib.sha1).digest()).decode()
        headers.update({"Date": date, "Authorization": "OSS %s:%s" % (self.key_id, signature)})
        url = "https://%s.%s/%s" % (self.bucket, self.endpoint, urllib.parse.quote(key))
        if query:
            url += "?" + query
        req = urllib.request.Request(url, data=body if method in ("PUT", "POST") else None, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as err:
            data = err.read()
            code = (ET.fromstring(data).findtext("Code") if data.startswith(b"<?xml") else "") or ""
            raise RuntimeError("OSS %s %s → HTTP %d %s" % (method, key, err.code, code)) from None

    def put(self, rel: str, data: bytes, content_type: str, cache_control: str = "no-cache") -> str:
        self._request("PUT", self.key(rel), data, {"Content-Type": content_type, "Cache-Control": cache_control})
        return self.public_url(rel)

    def delete(self, rel: str) -> None:
        self._request("DELETE", self.key(rel))

    def list(self, rel_prefix: str = "") -> list:
        prefix = self.key(rel_prefix) if rel_prefix else self.prefix + "/"
        names, marker = [], ""
        while True:
            query = urllib.parse.urlencode({"prefix": prefix, "max-keys": "1000", "marker": marker})
            _, raw = self._request("GET", "", query=query)
            root = ET.fromstring(raw)
            ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
            for item in root.iter(ns + "Contents"):
                names.append(item.findtext(ns + "Key")[len(self.prefix) + 1:])
            if root.findtext(ns + "IsTruncated") != "true":
                return names
            marker = root.findtext(ns + "NextMarker") or names[-1]


CONTENT_TYPES = {".md": "text/markdown; charset=utf-8", ".py": "text/x-python; charset=utf-8", ".json": "application/json; charset=utf-8",
                 ".html": "text/html; charset=utf-8", ".whl": "application/zip", ".zip": "application/zip", ".png": "image/png", ".txt": "text/plain; charset=utf-8"}


def content_type(name: str) -> str:
    return CONTENT_TYPES.get(Path(name).suffix.lower(), "application/octet-stream")


def main(argv) -> int:
    client = OSS(load_config())
    cmd = argv[0] if argv else "probe"
    if cmd == "probe":
        rel = "_probe/permission-check.txt"
        url = client.put(rel, b"ok\n", content_type(rel))
        print("写入：成功")
        with urllib.request.urlopen(url, timeout=30) as resp:
            print("公开读取：%s" % ("成功" if resp.read() == b"ok\n" else "内容不对"))
        print("列举：%s" % ("成功" if rel in client.list("_probe/") else "没看到文件"))
        client.delete(rel)
        print("删除：%s" % ("成功" if rel not in client.list("_probe/") else "仍然存在"))
        return 0
    if cmd == "ls":
        for name in client.list(argv[1] if len(argv) > 1 else ""):
            print(name)
        return 0
    if cmd == "rm":
        for rel in argv[1:]:
            client.delete(rel)
            print("已删除", rel)
        return 0
    if cmd == "rmtree":
        if len(argv) < 2 or not argv[1].strip("/"):
            sys.exit("rmtree 必须给出相对前缀")
        for rel in client.list(argv[1]):
            client.delete(rel)
            print("已删除", rel)
        return 0
    sys.exit("未知命令：%s" % cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
