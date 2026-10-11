#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""地理标注 + 国旗转换工具。

国旗转换与上游标签解析本文件负责；GeoLite2 查库由调用方注入 reader。
"""
import re

# ISO 3166-1 alpha-2 -> regional indicator symbol（旗帜 emoji）
_A = 0x1F1E6


def flag_of(cc: str) -> str:
    """'US' -> 🇺🇸；非法/未知返回空串。"""
    if not cc or len(cc) != 2 or not cc.isalpha():
        return ""
    cc = cc.upper()
    return chr(_A + ord(cc[0]) - 65) + chr(_A + ord(cc[1]) - 65)


# 常见地区中文/英文 -> 国家码。上游源里会出现这些，用于继承标签。
NAME_TO_CC = {
    # 中文
    "香港": "HK", "澳门": "MO", "台湾": "TW", "日本": "JP",
    "新加坡": "SG", "韩国": "KR", "美国": "US", "德国": "DE",
    "荷兰": "NL", "英国": "GB", "法国": "FR", "加拿大": "CA",
    "俄罗斯": "RU", "印度": "IN", "越南": "VN", "泰国": "TH",
    "马来西亚": "MY", "菲律宾": "PH", "印尼": "ID", "澳大利亚": "AU",
    "巴西": "BR", "土耳其": "TR", "以色列": "IL", "沙特": "SA",
    # 英文别名
    "hongkong": "HK", "hong kong": "HK", "macau": "MO", "taiwan": "TW",
    "japan": "JP", "tokyo": "JP", "osaka": "JP",
    "singapore": "SG", "korea": "KR", "seoul": "KR",
    "united states": "US", "usa": "US", "germany": "DE", "frankfurt": "DE",
    "netherlands": "NL", "amsterdam": "NL", "united kingdom": "GB",
    "london": "GB", "france": "FR", "paris": "FR", "canada": "CA",
    "russia": "RU", "india": "IN", "vietnam": "VN", "thailand": "TH",
    "malaysia": "MY", "philippines": "PH", "indonesia": "ID",
    "australia": "AU", "brazil": "BR", "turkey": "TR", "israel": "IL",
}

# 匹配行尾可能出现的裸两位大写码
_CC_RE = re.compile(r"(?:^|\s)([A-Z]{2})(?:\s|$)")
# 匹配 ip:port#CC 里的 #CC（LancelotRar 等源的输出格式，最标准）
_HASH_CC_RE = re.compile(r"#([A-Za-z]{2})(?:\s|$)")

# 会被误判成国家码的单位/杂项词，出现则排除
_STOP_CC = {"MB", "KB", "GB", "TB", "MS", "IP", "CF", "OK", "NA", "ID"}

# CF 数据中心（IATA 三字码）-> 国家码。这是最可靠的真实位置来源。
# 来源：Cloudflare 官方 colo 列表常见项 + WeTest/UOUIN 表格实测值。
COLO_TO_CC = {
    # 大中华
    "HKG": "HK", "MFM": "MO", "TPE": "TW", "KHH": "TW", "TSA": "TW",
    "PEK": "CN", "PVG": "CN", "CAN": "CN", "SZX": "CN", "CTU": "CN",
    "WUH": "CN", "XIY": "CN", "HGH": "CN", "TSN": "CN", "CGO": "CN",
    "NKG": "CN", "FOC": "CN", "CSX": "CN", "KMG": "CN", "URC": "CN",
    "SHA": "CN", "SHE": "CN", "TAO": "CN", "DLC": "CN", "HAK": "CN",
    # 亚太
    "NRT": "JP", "HND": "JP", "KIX": "JP", "ITM": "JP", "FUK": "JP", "OKA": "JP",
    "ICN": "KR", "GMP": "KR", "PUS": "KR",
    "SIN": "SG", "BKK": "TH", "KUL": "MY", "CGK": "ID", "MNL": "PH",
    "HAN": "VN", "SGN": "VN", "BOM": "IN", "DEL": "IN", "MAA": "IN",
    "SYD": "AU", "MEL": "AU", "AKL": "NZ", "DAC": "BD", "KTM": "NP",
    # 美洲
    "SEA": "US", "LAX": "US", "SFO": "US", "SJC": "US", "PDX": "US",
    "DEN": "US", "DFW": "US", "ORD": "US", "ATL": "US", "MIA": "US",
    "IAD": "US", "EWR": "US", "JFK": "US", "BOS": "US", "PHX": "US",
    "LAS": "US", "MSP": "US", "DTW": "US", "CLT": "US", "PHL": "US",
    "YYZ": "CA", "YVR": "CA", "YUL": "CA", "GRU": "BR", "EZE": "AR",
    "SCL": "CL", "BOG": "CO", "MEX": "MX", "LIM": "PE",
    # 欧洲
    "LHR": "GB", "LGW": "GB", "MAN": "GB", "CDG": "FR", "MRS": "FR",
    "AMS": "NL", "FRA": "DE", "MUC": "DE", "BER": "DE", "DUS": "DE",
    "HAM": "DE", "MAD": "ES", "BCN": "ES", "MXP": "IT", "FCO": "IT",
    "ZRH": "CH", "VIE": "AT", "BRU": "BE", "CPH": "DK", "ARN": "SE",
    "OSL": "NO", "HEL": "FI", "WAW": "PL", "PRG": "CZ", "BUD": "HU",
    "OTP": "RO", "IST": "TR", "DUB": "IE", "LIS": "PT", "ATH": "GR",
    "SVO": "RU", "DME": "RU", "LED": "RU", "KBP": "UA",
    # 中东 / 非洲
    "DXB": "AE", "AUH": "AE", "DOH": "QA", "RUH": "SA", "JED": "SA",
    "TLV": "IL", "KWI": "KW", "BAH": "BH", "MCT": "OM", "AMM": "JO",
    "CAI": "EG", "JNB": "ZA", "CPT": "ZA", "NBO": "KE", "LOS": "NG",
}


def cc_from_text(text: str) -> str:
    """从上游一行的注释/尾巴里猜国家码。

    优先级：#CC 标准格式 > Colo 三字码 > 地区名 > 裸两位码。
    """
    if not text:
        return ""
    up = text.upper()
    # 0) 标准 ip:port#CC 格式（源直接给了国家码，最可靠）
    hm = _HASH_CC_RE.search(up)
    if hm and hm.group(1) not in _STOP_CC:
        return hm.group(1)
    # 1) Colo IATA 三字码（次准）
    for code, cc in COLO_TO_CC.items():
        if re.search(rf"(?:^|[\s>]){code}(?:[\s<]|$)", up):
            return cc
    # 2) 地区名（中英）
    low = text.lower()
    for name, cc in NAME_TO_CC.items():
        if name in low:
            return cc
    # 3) 裸两位大写码，排除单位词
    m = _CC_RE.search(text.strip())
    if m and m.group(1) not in _STOP_CC:
        return m.group(1)
    return ""


def lookup_cc(reader, ip: str, inherited: str = "") -> str:
    """标签优先级：上游继承 > GeoLite2 > ''。

    reader 可为 None（不查库）。
    """
    if inherited:
        return inherited
    if reader is None:
        return ""
    try:
        d = reader.get(ip) or {}
    except Exception:
        return ""
    c = d.get("country", {}).get("iso_code")
    if c:
        return c.upper()
    return ""


def fmt_line(ip: str, port: int, cc: str) -> str:
    """输出一行 ip:port#CC 国旗（无国家码则 ip:port#XX）"""
    cc = (cc or "XX").upper()
    f = flag_of(cc)
    return f"{ip}:{port}#{cc} {f}".rstrip()
