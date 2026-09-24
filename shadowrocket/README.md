# iPhone / iPad（Shadowrocket）怎么接

Shadowrocket 的「节点订阅」和「配置」是两个独立的东西：

- **节点订阅**：还是你自己的 `ckip.uk` 那条，不用改
- **配置**：规则和策略组，用本仓库这份

## 第一次配置

1. 打开 Shadowrocket → 底部 **配置** 标签
2. 右上角 **+** → 类型选 **URL**（或 "从 URL 下载"）
3. URL 填：

   ```
   https://cdn.jsdelivr.net/gh/Popcornnnnnnnn/proxy-rules@main/shadowrocket/shadowrocket.conf
   ```

4. 保存后，**点一下这条配置让它打勾选中**（选中才会生效）
5. 回到 **首页**，确认节点订阅已经导入（这一步是你原有的 `ckip.uk` 订阅）
6. 打开首页顶部的开关

## 以后规则改了怎么更新

规则改动推送到 GitHub 后：

1. 打开 Shadowrocket → **配置**
2. 向左滑动你的那条配置 → **更新**（或长按 → 更新）
3. 更新完保持它处于「选中」状态

也可以在配置列表下拉刷新；Shadowrocket 会在你打开 App 时自动检查。

## 需要留意的

- **策略组名字要能对上**：这份配置里 `🌏全球低延迟`、`🤖AI美国节点` 这些组，
  靠 `policy-regex-filter` 从你的节点订阅里自动匹配节点名（比如带「美国」「US」的）。
  如果你的订阅节点名变了导致匹配不到，组里会空，这时去 **配置 → 编辑** 里
  看一下组的正则，或者直接在 App 里手动给组选节点。
- **`ipv6 = true`**：Shadowrocket 里的 IPv6 和 Mac 上那个开关是两回事，
  手机这份保持 `true` 没问题（真机流量走 Shadowrocket 自己的 TUN）。
- 这份配置**不含任何节点信息**，所以放在公开仓库里是安全的。
