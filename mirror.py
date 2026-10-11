#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mirror.py — 镜像 LancelotRar/best-cf-ips 的优选 IP 产物。

机制：拉取上游 6 个文件，原样写入本地同名文件（内容保真），
      仅在文件首行加一条来源注释。

产物（内容与上游一致，除首行来源标记）：
  best-cf-ip-collected.txt
  best-cf-ip-scanned-top{20,50,100,200,400}.txt

用法：
  python mirror.py            # 镜像全部
  python mirror.py --check    # 只检查是否有变化（有变化退出码 3，不写文件）
"""
import argparse
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

UPSTREAM = "https://raw.githubusercontent.com/LancelotRar/best-cf-ips/main"

FILES = [
    "best-cf-ip-collected.txt",
    "best-cf-ip-scanned-top20.txt",
    "best-cf-ip-scanned-top50.txt",
    "best-cf-ip-scanned-top100.txt",
    "best-cf-ip-scanned-top200.txt",
    "best-cf-ip-scanned-top400.txt",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bestcf-mirror/1.0)"}
TIMEOUT = 30
CST = timezone(timedelta(hours=8))
RETRIES = 5


def fetch(url: str) -> str:
    last = None
    for i in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            last = e
            if i < RETRIES - 1:
                time.sleep(2 * (i + 1))
    raise last


def strip_source_line(text: str) -> str:
    """去掉我们自己加过的来源行（幂等，防重复叠加）。"""
    lines = text.splitlines()
    if lines and lines[0].startswith("# mirrored from "):
        lines = lines[1:]
    return "\n".join(lines) + ("\n" if lines else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查差异，不写文件")
    a = ap.parse_args()

    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    changed = []
    failed = []

    for name in FILES:
        url = f"{UPSTREAM}/{name}"
        try:
            body = fetch(url)
        except Exception as e:
            print(f"[fail] {name}: {e}")
            failed.append(name)
            continue

        body = strip_source_line(body)
        out = f"# mirrored from LancelotRar/best-cf-ips at {ts}\n" + body

        try:
            cur = open(name, encoding="utf-8").read()
        except FileNotFoundError:
            cur = ""

        if cur == out:
            print(f"[same] {name}")
            continue

        n = sum(1 for l in body.splitlines() if l and not l.startswith("#"))
        print(f"[diff] {name}  ({n} 条)")
        changed.append(name)

        if not a.check:
            with open(name, "w", encoding="utf-8") as f:
                f.write(out)

    if failed and len(failed) == len(FILES):
        sys.exit("错误：所有文件都拉取失败")

    if a.check:
        print(f"差异文件 {len(changed)} 个：{', '.join(changed) or '无'}")
        sys.exit(3 if changed else 0)

    if changed:
        print(f"已写入 {len(changed)} 个文件")
    else:
        print("全部无变化")


if __name__ == "__main__":
    main()
