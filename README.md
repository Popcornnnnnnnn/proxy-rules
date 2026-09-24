# 我的分流规则（公开仓库，不含节点信息）

一套规则，多端共用。所有设备的节点订阅仍各自填 `ckip.uk` 那条，
本仓库只提供**规则覆写**，不包含任何节点、订阅地址或密钥。

## 目录

| 目录 | 用途 | 适用客户端 |
| --- | --- | --- |
| `clash/` | Clash 覆写层（rules / merge / script） | Clash Verge、Clash for Windows、Clash Meta |
| `shadowrocket/` | Shadowrocket 配置片段 | iPhone / iPad 上的 Shadowrocket |

## 修改流程

只在这一台 MacBook Pro 上改，然后推送：

```sh
cd ~/Documents/Codex/2026-09-24/zhe-2/work/proxy-rules
# 编辑 clash/ 或 shadowrocket/ 下的文件
git add -A && git commit -m "更新规则：xxx" && git push
```

其他设备不需要 `git`，它们通过下面的 URL 自动获取：

```
https://cdn.jsdelivr.net/gh/Popcornnnnnnnn/proxy-rules@main/<文件路径>
```

## 各端怎么接

见各个子目录里的 README。
