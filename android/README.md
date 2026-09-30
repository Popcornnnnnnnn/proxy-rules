# 红米（Clash Meta for Android）怎么接

## 先说结论：它不能用「规则覆写」

Clash Meta for Android 的设置里确实有「覆写 / Override」，但那**只管全局设置项**
（端口、DNS、ipv6、mode 等）。查它的源码 `ConfigurationOverride`，
字段列表里**根本没有 `rules`**，所以不存在「规则覆写」这个东西。

它吃规则的唯一入口是**完整配置文件**（必须含 `proxies` + `proxy-groups` + `rules`）。

## 做法

用 `build-android.py` 在本机生成完整配置（订阅 + 自定义规则合并）：

首次使用时，把你自己的订阅 URL 单独放入 `android/subscription-url.txt`，
文件仅一行，并将权限设为仅自己可读（`chmod 600 android/subscription-url.txt`）。
该文件已被 Git 忽略；不要把地址写进脚本或提交到公开仓库。

```sh
cd /path/to/proxy-rules
python3 build-android.py
# 输出 android/config.yaml，自定义规则已插在 rules 最前面
```

生成的 `config.yaml` **含节点信息**，已在 `.gitignore` 排除，不要提交。
脚本会将其权限设为 `600`。生成器只合并 `clash/rules.yaml` 的 `prepend`，
不会运行 `clash/rules.js`；检查两者差异后再导入手机。

然后把该完整配置传到红米，在 Clash Meta for Android 中导入并选中。
以后每次规则或订阅变化，都需要重新生成、传送和应用。
