# best-cf-ips

聚合多个公开 Cloudflare 优选 IP 源，去重、加国家/地区标注与国旗，每 6 小时自动更新。

> 复刻自 [LancelotRar/best-cf-ips](https://github.com/LancelotRar/best-cf-ips) 的数据层思路，独立实现。

## 产物

更新时间为北京时间（UTC+8），在文件第一行标注。

### 聚合版（全量）

```
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-collected.txt
```

格式：

```
# 389 best ips collected at 2026-10-11 18:58
104.16.65.1:443#XX 🇽🇽
162.159.128.253:443#US 🇺🇸
104.17.155.139:443#HK 🇭🇰
```

### 分档版（按国家可辨识度排序，向上包含）

挑**一个**用即可，多选重复：

```
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top20.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top50.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top100.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top200.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top400.txt
```

## 怎么用

### 1. 配到 edgetunnel 自定义订阅

进你 Cloudflare Worker 的 `/自定义订阅` 页面，把上面的 URL **直接粘贴到 IP 输入框**（不要点「订阅接口」按钮），保存。Worker 会把每个 `ip:port` 转成一个代理节点，名字带国家码 + 国旗。

### 2. Mihomo / Clash 客户端

按国家码过滤建策略组，用 `url-test` 只在同区域内浮动 IP，避免区域频繁跳变触发风控：

```yaml
proxy-groups:
  - name: "HK"
    type: url-test
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    filter: "HK"
    use: [订阅名]
```

### 3. 当数据源接入你自己的采集脚本

解析格式很简单：每行 `ip:port#CC`，忽略以 `#` 开头的行。

```python
import re, urllib.request
txt = urllib.request.urlopen(URL).read().decode()
for line in txt.splitlines():
    if line.startswith("#"):
        continue
    m = re.match(r"(\d+\.\d+\.\d+\.\d+):(\d+)#([A-Z]{2})", line)
    if m:
        ip, port, cc = m.group(1), int(m.group(2)), m.group(3)
```

## 国家/地区标注说明

**重要：`#CC` 标的是「地区标签来源」，不是 IP 的物理位置。**

Cloudflare 用的是 anycast，同一个 IP 从不同运营商/地区解析出的落点可能不同，其"位置"本身没有唯一答案。本项目标注优先级：

1. **上游源行内自带的机房代码**（如 WeTest 的 `数据中心` 列 `HKG`/`SEA`）—— 最可靠
2. **上游源自带的国家/地区文字**（如 `香港`、`Singapore`）—— 次之
3. **GeoLite2-City 查库兜底** —— 仅对第三方反代 IP 有效，CF anycast 段在库里多为空
4. 都没有 → 标 `XX`

所以 `XX` 占比高是正常且诚实的，代表"该 IP 无法确定地区"，而不是"没标注"。

## 数据源

| 源 | 说明 |
|---|---|
| cmliu (`cf.090227.xyz`) | 电信/联通/移动三网优选 |
| IPDB (`ipdb.api.030101.xyz`) | 优选官方 IP |
| WeTest (`wetest.vip`) | 带机房代码 + 延迟/带宽实测 |
| UOUIN (`api.uouin.com`) | 带 Colo + 延迟实测 |
| VPS789 / Joname | 聚合型优选列表 |

## 本地运行

```bash
pip install -r requirements.txt

# 下载 GeoLite2（可选，没有则跳过查库）
mkdir -p geo
curl -sL -o geo/GeoLite2-City.mmdb.gz \
  "https://raw.githubusercontent.com/wp-statistics/GeoLite2-City/master/GeoLite2-City.mmdb.gz"
gunzip -f geo/GeoLite2-City.mmdb.gz

# 跑
python collect.py
```

参数：

- `--no-verify` 跳过 TCP 443 存活验证（快速预览）
- `--geo ""` 不加载 GeoLite2

## 文件结构

```
collect.py          采集主脚本
geo_lib.py          地理标注 + 国旗转换
requirements.txt    依赖（maxminddb）
.github/workflows/  定时任务
```

## 许可

MIT
