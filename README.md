# best-cf-ips

[LancelotRar/best-cf-ips](https://github.com/LancelotRar/best-cf-ips) 的**镜像**。

内容与上游逐字节一致（仅首行加 `# mirrored from ...` 来源标记），每 30 分钟检查一次，上游更新即自动跟进。

## 产物

| 文件 | 条数 | 说明 |
|---|---|---|
| `best-cf-ip-collected.txt` | ~76 | 聚合版（多源去重） |
| `best-cf-ip-scanned-top20.txt` | 20 | 分档版（向上包含） |
| `best-cf-ip-scanned-top50.txt` | 50 | |
| `best-cf-ip-scanned-top100.txt` | 100 | |
| `best-cf-ip-scanned-top200.txt` | 200 | |
| `best-cf-ip-scanned-top400.txt` | 400 | |

**分档版每档都是向上包含的，挑一个用即可。**

```
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-collected.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top20.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top50.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top100.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top200.txt
https://raw.githubusercontent.com/lll33lll/best-cf-ips/main/best-cf-ip-scanned-top400.txt
```

## 格式

```
# mirrored from LancelotRar/best-cf-ips at 2026-10-11 19:59
# 76 best ips collected at 2026-10-11 19:03
104.16.65.1:443#US 🇺🇸
104.18.33.225:443#SG 🇸🇬
104.26.3.162:443#DE 🇩🇪
```

首行是镜像标记，第二行起是上游原样内容。

## 怎么用

### edgetunnel 自定义订阅

进 Cloudflare Worker 的 `/自定义订阅` 页面，把 URL **直接粘到 IP 输入框**（不要点「订阅接口」按钮）。

### Mihomo / Clash

按国家码过滤建策略组，`url-test` 只在同区域内浮动：

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

## 关于 `#CC` 标签

**`#CC` 是「解析出口地区」，不是 IP 的物理位置。**

Cloudflare 是 anycast，同一个 IP 在不同地区解析出的落点不同。上游的标签来自**实测 colo**（调探针拿 CF 边缘机房三字码，如 `SJC`/`NRT`/`HKG`）——注意它的**扫描机出口在新加坡**，所以分档版大量标 `#SG`，这反映的是「从扫描机看该 IP 的出口」，不是你本地的实际延迟。

## 维护

自动镜像，无需人工干预：

- `.github/workflows/update.yml` 每 30 分钟跑一次
- `mirror.py` 拉取上游 6 个文件，与原内容比对，有变化才提交
- 手动触发：Actions → `Mirror Best CF IPs` → Run workflow

上游：[LancelotRar/best-cf-ips](https://github.com/LancelotRar/best-cf-ips)

## 许可

镜像内容版权归上游所有。本项目代码（mirror.py）MIT。
