# Mac / Windows / Android（Clash 系）怎么接

适用：Clash Verge（另一台 Mac）、Clash for Windows（两台 Windows）、
Clash Meta（Redmi 安卓机）。

思路和 MacBook Pro 上现在这套完全一样：**订阅照旧，规则用本仓库这份覆写挂上去**。

## 各端的 URL

**Clash Verge（另一台 Mac）** — 用「规则覆写」：

```
https://cdn.jsdelivr.net/gh/Popcornnnnnnnn/proxy-rules@main/clash/rules.yaml
```

做法：订阅卡片右键 → **编辑规则** → 选「远程」/「URL」→ 填上面的地址 → 保存。
（脚本覆写 `rules.js` 同理，在「编辑脚本」里填：
`https://cdn.jsdelivr.net/gh/Popcornnnnnnnn/proxy-rules@main/clash/rules.js`）

**Clash for Windows** — 用「Merge / 覆写」：

1. Profiles 页，订阅卡片右键 → **Edit File** 旁边的 **Merge**（或 Parsers）
2. 选 **Remote**，填 `clash/rules.yaml` 那个 URL
3. 保存后点一下订阅卡片重新生成配置

**Clash Meta（Redmi）** — 用「覆写 / Override」：

1. 配置页 → 你的订阅 → **覆写** / **Override**
2. 添加一条 **Rule Override**，类型选远程 URL，填 `clash/rules.yaml` 那个地址

## 以后规则改了怎么更新

不用做任何操作。各客户端在**更新订阅**时会重新生成配置，
这时会去拉一次覆写 URL，拿到最新规则。

想立刻生效就手动点一次「更新订阅」。

## 需要留意的

- 本仓库的覆写**只包含规则**，不含节点。所以每台设备仍然要各自填 `ckip.uk` 订阅地址。
- `rules.yaml` 里用的是 `prepend`，规则插在订阅自带规则之前，订阅更新不会冲掉。
- `rules.js` 里有个 `PROCESS-NAME,Texas Poker,DIRECT` 之类的**进程规则**，
  只在桌面端有意义（手机上没有进程概念，会被忽略，无害）。
- 覆写里引用了 `GEOSITE,apple` 和 `PROXY` 这个策略组名，
  要求订阅里存在名为 `PROXY` 的组——你现在的 `ckip.uk` 订阅满足这点。
