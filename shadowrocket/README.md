# How to connect iPhone / iPad (Shadowrocket)

Shadowrocket's "node subscription" and "configuration" are two separate things:

- **Node subscription**: still your own `ckip.uk` one, no change needed
- **Configuration**: rules and policy groups, from this repository

## First-time setup

1. Open Shadowrocket → the **配置** (Config) tab at the bottom
2. **+** in the top right → choose type **URL** (or "Download from URL")
3. Enter the URL:

   ```
   https://cdn.jsdelivr.net/gh/Popcornnnnnnnn/proxy-rules@main/shadowrocket/shadowrocket.conf
   ```

4. After saving, **tap the configuration to select it** (it only takes effect when selected)
5. Go back to the **首页** (Home) page and confirm the node subscription has been imported (this step is your existing `ckip.uk` subscription)
6. Turn on the switch at the top of the Home page

## Updating after rule changes

After rule changes are pushed to GitHub:

1. Open Shadowrocket → **配置** (Config)
2. Swipe left on your configuration → **更新** (Update) (or long-press → Update)
3. Keep it selected afterwards

You can also pull to refresh in the configuration list; Shadowrocket checks automatically
when you open the app.

## Things to watch

- **Policy group names must match**: groups such as `🌏全球低延迟` and `🤖AI美国节点` in this
  configuration match node names from your node subscription automatically via
  `policy-regex-filter` (for example names containing 「美国」 or `US`). If your subscription's
  node names change and nothing matches, the group will be empty; then look at the group's
  regex under **配置 → 编辑** (Config → Edit), or pick a node for the group manually in the app.
- **`ipv6 = true`**: IPv6 in Shadowrocket is a different thing from that switch on the Mac;
  keeping `true` for the phone is fine (real traffic goes through Shadowrocket's own TUN).
- This configuration **contains no node information**, so it is safe in a public repository.
