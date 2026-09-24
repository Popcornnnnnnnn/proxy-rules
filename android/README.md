# 红米（Clash Meta for Android）怎么接

## 先说结论：它不能用「规则覆写」

Clash Meta for Android 的设置里确实有「覆写 / Override」，但那**只管全局设置项**
（端口、DNS、ipv6、mode 等）。查它的源码 `ConfigurationOverride`，
字段列表里**根本没有 `rules`**，所以不存在「规则覆写」这个东西。

它吃规则的唯一入口是**完整配置文件**（必须含 `proxies` + `proxy-groups` + `rules`）。

## 做法

用 `build-android.py` 在本机生成完整配置（订阅 + 自定义规则合并）：

```sh
cd /path/to/proxy-rules
python3 build-android.py
# 输出 android/config.yaml，自定义规则已插在 rules 最前面
```

生成的 `config.yaml` **含节点信息**，已在 `.gitignore` 排除，不要提交。

然后把它送到红米，两种方式见仓库根 README 的「红米」一节。
