# Mac / Windows / Android（Clash 系）怎么接

适用：Clash Verge（另一台 Mac）、Clash for Windows（两台 Windows）、
Clash Meta（Redmi 安卓机）。

思路和 MacBook Pro 上现在这套完全一样：**订阅照旧，规则用本仓库这份覆写挂上去**。

## 各端怎么接

**Clash Verge（另一台 Mac）** — 用「规则覆写」，但**只能粘贴内容，不能填 URL**：

1. 订阅卡片右键 → **编辑规则**
2. 把本仓库 `clash/rules.yaml` 的**内容**整个粘进文本框 → 保存
3. 点一下订阅卡片（或重启 App）让它重新应用一次，规则才生效

脚本覆写 `rules.js` 同理：右键 → **扩展脚本** → 粘贴内容 → 保存。

> ⚠️ Clash Verge 的覆写**只吃本地文件，没有「远程 / URL」选项**，别去找地址填。
> 已对着 2.5.6 源码核过：右键菜单里只有「编辑规则/编辑节点/编辑代理组/
> 扩展覆写配置/扩展脚本」，点开都是本地文本框；后端 `enhance/chain.rs`
> 只按「profiles 目录 + 文件名」读磁盘，文件不存在就直接跳过，全程不发网络请求。
> 所以仓库改了之后**得重新粘贴一次**（不能靠订阅更新自动拉）。

**Clash for Windows** — 用「Merge / 覆写」：

1. Profiles 页，订阅卡片右键 → **Edit File** 旁边的 **Merge**（或 Parsers）
2. 选 **Remote**，填 `clash/rules.yaml` 那个 URL
3. 保存后点一下订阅卡片重新生成配置

**Clash Meta（Redmi）** — **不能用「覆写 / Override」**：

它设置里的 Override 只管全局设置项（端口、DNS、ipv6、mode 等），
源码里的 `ConfigurationOverride` **没有 `rules` 字段**，所以挂不了规则覆写。
它吃规则的唯一入口是**完整配置文件**，用 `build-android.py` 在本机生成：

```sh
python3 build-android.py      # 输出 android/config.yaml
```

生成的配置**含节点信息**，已在 `.gitignore` 排除，不要提交。详见 `android/README.md`。

## 以后规则改了怎么更新

**分两种，别搞混：**

- **填 URL 的端（Clash for Windows、Shadowrocket）** —— 不用做任何操作。
  更新订阅时会重新生成配置，顺手拉到最新规则；想立刻生效就手动点一次「更新订阅」。
- **两台 Mac 的 Clash Verge（填的是内容）** —— **不会自动更新**。
  仓库改了之后要重新粘贴一次，或在本机跑一遍同步：

  ```sh
  cd /path/to/proxy-rules && git pull
  # 覆写文件名以本机 profiles 目录里的为准（本机是 rRHqhlQYiQBo.yaml）
  cp clash/rules.yaml "$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/profiles/rRHqhlQYiQBo.yaml"
  ```

  改完还要回 Clash Verge **点一下订阅卡片重新应用**——只改文件不会热加载。

## 需要留意的

- 本仓库的覆写**只包含规则**，不含节点。所以每台设备仍然要各自填 `ckip.uk` 订阅地址。
- `rules.yaml` 里用的是 `prepend`，规则插在订阅自带规则之前，订阅更新不会冲掉。
- `rules.js` 里有个 `PROCESS-NAME,Texas Poker,DIRECT` 之类的**进程规则**，
  只在桌面端有意义（手机上没有进程概念，会被忽略，无害）。
- 覆写里引用了 `GEOSITE,apple` 和 `PROXY` 这个策略组名，
  要求订阅里存在名为 `PROXY` 的组——你现在的 `ckip.uk` 订阅满足这点。
