# 我的分流规则（公开仓库，不含节点信息）

多端规则的公开编辑入口。各设备自行配置节点订阅；本仓库只存放规则和
不含凭据的生成脚本，不包含节点、订阅地址或密钥。各端的规则文件需分别维护，
当前并非逐条相同。

## 目录

| 目录 | 用途 | 适用客户端 |
| --- | --- | --- |
| `clash/` | Clash 规则编辑器内容和脚本 | Clash Verge、Clash for Windows；Android 生成器只读取 `rules.yaml` |
| `shadowrocket/` | Shadowrocket 配置片段 | iPhone / iPad 上的 Shadowrocket |
| `build-android.py` | 合成含节点的完整配置，订阅地址从本机私有文件读取 | Clash Meta for Android |

## 修改流程

只在这一台 MacBook Pro 上改，然后推送：

```sh
cd ~/Documents/Codex/2026-09-24/zhe-2/work/proxy-rules
# 编辑 clash/ 或 shadowrocket/ 下的文件
git add -A && git commit -m "更新规则：xxx" && git push
```

Windows 和 iPhone 可以从下面的 URL 获取公开规则文件，更新后仍需在客户端
重新应用配置。另一台 Mac 使用本地覆写文件；Redmi 使用本机生成并传送的
完整配置，都不会因为 GitHub 推送而自动生效。

```
https://cdn.jsdelivr.net/gh/Popcornnnnnnnn/proxy-rules@main/<文件路径>
```

## 当前各端差异

这些是当前文件中的实际规则，不能假定是有意设计；修改时应逐项核对目标设备：

| 流量 | Mac 的 Clash Verge | iPhone 的 Shadowrocket | Redmi 生成配置 |
| --- | --- | --- | --- |
| Steam API / 结算主机 | `DIRECT` | `DIRECT` | `DIRECT` |
| 其他部分 Steam 域名 | `rules.js` 中强制 `PROXY` | 若干域名在 `.conf` 中为 `DIRECT` | 不读取 `rules.js`，交由订阅规则决定 |
| `featureassets.org` | `rules.js` 中为 `DIRECT` | `🤖AI美国节点` | 不读取 `rules.js`，交由订阅规则决定 |

公开仓库只保证各端能取得相应规则文件；设备实际生效还需在客户端重新应用并核验。

## 各端怎么接

见各个子目录里的 README。
