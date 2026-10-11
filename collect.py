#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cloudflare 优选 IP 聚合工具 —— 复刻 LancelotRar/best-cf-ips 的数据层。

流程：
  1. 拉取多个上游源（纯文本 / HTML 表格 / CSV）
  2. 解析出 (ip, port) 对，去重
  3. TCP 443 存活验证
  4. 地理标注：上游标签继承 > GeoLite2 查库兜底
  5. 排序后输出分档文件

产物：
  best-cf-ip-collected.txt        全量聚合（带 #CC 国旗）
  best-cf-ip-scanned-top{N}.txt   N ∈ 20/50/100/200/400（向上包含）

用法：
  python collect.py                  # 全跑
  python collect.py --no-verify      # 跳过 TCP 存活验证（快速预览）
  python collect.py --geo path.mmdb  # 指定 GeoLite2 库
  python collect.py --max 100        # 只取前 N（快速预览）
"""
import argparse
import re
import socket
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

import geo_lib

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bestcf-ips/1.0)"}
TIMEOUT = 20
CST = timezone(timedelta(hours=8))

# ============ 上游数据源 ============
# kind: text 纯文本 / html HTML 表格
SOURCES = [
    {"name": "cmliu ct",   "url": "https://cf.090227.xyz/ct?ips=80",
     "kind": "text", "carriers": ["电信"]},
    {"name": "cmliu cu",   "url": "https://cf.090227.xyz/cu?ips=80",
     "kind": "text", "carriers": ["联通"]},
    {"name": "cmliu cmcc", "url": "https://cf.090227.xyz/cmcc?ips=80",
     "kind": "text", "carriers": ["移动"]},
    {"name": "IPDB bestcf", "url": "https://ipdb.api.030101.xyz/?type=bestcf",
     "kind": "text"},
    {"name": "WeTest v4",
     "url": "https://www.wetest.vip/page/cloudflare/address_v4.html",
     "kind": "html"},
    {"name": "UOUIN", "url": "https://api.uouin.com/cloudflare.html",
     "kind": "html"},
    {"name": "VPS789", "url": "https://bestcf.pages.dev/vvhan/ipv4.txt",
     "kind": "text"},
    {"name": "Joname", "url": "https://raw.githubusercontent.com/joname1/BestCFip/refs/heads/main/ipv4.txt",
     "kind": "text"},
]

# 分档
TIERS = [20, 50, 100, 200, 400]

_IPPORT_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})(?::(\d+))?")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "ignore")


def extract(text: str):
    """返回 [(ip, port, cc_hint), ...]"""
    out = []
    if "<tr" in text.lower():                     # HTML 表格：逐行切
        chunks = re.split(r"<tr\b", text, flags=re.I)
    else:
        chunks = text.splitlines()
    for chunk in chunks:
        # 去除 HTML 标签，保留文字（可能含机房代码 / 地区名）
        plain = re.sub(r"<[^>]+>", " ", chunk)
        m = _IPPORT_RE.search(plain)
        if not m:
            continue
        ip, port = m.group(1), int(m.group(2) or 443)
        if not _valid_ip(ip):
            continue
        cc = geo_lib.cc_from_text(plain)
        out.append((ip, port, cc))
    return out


def _valid_ip(ip: str) -> bool:
    p = ip.split(".")
    if len(p) != 4:
        return False
    try:
        return all(0 <= int(x) <= 255 for x in p)
    except ValueError:
        return False


def alive(ip: str, port: int = 443, t: float = 3.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=t):
            return True
    except OSError:
        return False


def run(no_verify: bool, geo_path: str):
    reader = None
    if geo_path:
        try:
            import maxminddb
            reader = maxminddb.open_database(geo_path)
            print(f"[geo] 已加载 {geo_path}")
        except Exception as e:
            print(f"[geo] 加载失败，跳过查库：{e}")

    # 1. 采集
    pool = {}          # ip -> {"port":.., "cc":.., "src":set()}
    ok_src = 0
    for s in SOURCES:
        try:
            txt = fetch(s["url"])
            rows = extract(txt)
            for ip, port, cc in rows:
                if port != 443:
                    continue
                e = pool.setdefault(ip, {"port": port, "cc": "", "src": set()})
                e["src"].add(s["name"])
                if cc and not e["cc"]:
                    e["cc"] = cc
            ok_src += 1
            print(f"[src] {s['name']:14} {len(rows):5} 行")
        except Exception as e:
            print(f"[src] {s['name']:14} 失败：{e}")
        time.sleep(0.3)

    print(f"[src] 可用 {ok_src}/{len(SOURCES)}，去重后 {len(pool)} 个 IP")
    if not pool:
        sys.exit("错误：没有任何 IP")

    # 2. 存活验证
    ips = list(pool.keys())
    if not no_verify:
        print(f"[verify] TCP 443 检测 {len(ips)} 个（并发 64）...")
        with ThreadPoolExecutor(max_workers=64) as ex:
            flags = list(ex.map(lambda x: alive(x, 443), ips))
        ips = [ip for ip, ok in zip(ips, flags) if ok]
        print(f"[verify] 存活 {len(ips)}")

    # 3. 地理标注
    for ip in ips:
        pool[ip]["cc"] = geo_lib.lookup_cc(reader, ip, pool[ip]["cc"])
    if reader:
        reader.close()

    # 4. 排序：有地区标注的优先（分档才有意义），其次多源共识，再次 IP 稳定序
    ips.sort(key=lambda ip: (
        0 if pool[ip]["cc"] else 1,      # 有国家码的排前
        -len(pool[ip]["src"]),           # 多源共识优先
        ip,
    ))

    # 5. 输出
    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    lines = []
    for ip in ips:
        e = pool[ip]
        lines.append(geo_lib.fmt_line(ip, e["port"], e["cc"]))

    with open("best-cf-ip-collected.txt", "w", encoding="utf-8") as f:
        f.write(f"# {len(lines)} best ips collected at {ts}\n")
        f.write("\n".join(lines) + "\n")
    print(f"[out] best-cf-ip-collected.txt  {len(lines)} 条")

    for n in TIERS:
        sub = lines[:n]
        if not sub:
            continue
        with open(f"best-cf-ip-scanned-top{n}.txt", "w", encoding="utf-8") as f:
            f.write(f"# {len(sub)} best cf ips scanned at {ts}\n")
            f.write("\n".join(sub) + "\n")
        print(f"[out] best-cf-ip-scanned-top{n}.txt  {len(sub)} 条")

    # 地区分布统计
    from collections import Counter
    dist = Counter(pool[ip]["cc"] or "XX" for ip in ips)
    print("[stat] 地区分布:", dict(dist.most_common(12)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--geo", default="geo/GeoLite2-City.mmdb")
    a = ap.parse_args()
    run(a.no_verify, a.geo)
