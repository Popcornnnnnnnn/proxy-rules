# How to connect Mac / Windows / Android (Clash family)

Applies to: Clash Verge (the other Mac), Clash for Windows (two Windows machines),
Clash Meta (the Redmi Android phone).

The approach is exactly the same as what runs on this MacBook Pro: **keep the
subscription as is and attach this repository's rules as an override.**

## Connecting each client

**Clash Verge (the other Mac)** — use 「规则覆写」 (Rules override), but it **only accepts pasted content, not a URL**:

1. Right-click the subscription card → **编辑规则** (Edit Rules)
2. Paste the entire **contents** of this repository's `clash/rules.yaml` into the text box → save
3. Click the subscription card (or restart the app) so it re-applies once; only then do the rules take effect

If you previously enabled an **extension script** containing routing rules for this
subscription, disable the rules in it too, otherwise the script may override the order in
`rules.yaml`. On this machine the old script's rules have been migrated into the YAML.

> ⚠️ Clash Verge's override **only reads local files and has no "remote / URL" option**, so
> don't go looking for an address to fill in. Verified against the 2.5.6 source: the
> right-click menu has only 「编辑规则/编辑节点/编辑代理组/扩展覆写配置/扩展脚本」, all of which
> open local text boxes; the backend `enhance/chain.rs` reads from disk by "profiles
> directory + file name" only, skips missing files, and makes no network requests at all.
> So after the repository changes you **must paste it again** (a subscription update will
> not pull it automatically).

**Clash for Windows** — use "Merge / override":

1. On the Profiles page, right-click the subscription card → **Merge** next to **Edit File** (or Parsers)
2. Choose **Remote** and enter the URL of `clash/rules.yaml`
3. After saving, click the subscription card to regenerate the configuration

**Clash Meta (Redmi)** — **cannot use "override"**:

Its Override setting only covers global options (port, DNS, ipv6, mode, and so on); the
`ConfigurationOverride` in its source **has no `rules` field**, so rules cannot be attached
as an override. The only way it takes rules is a **complete configuration file**, generated
on this machine with `build-android.py`:

```sh
python3 build-android.py      # writes android/config.yaml
```

The generated configuration **contains node information**, is excluded by `.gitignore`,
and must not be committed. See `android/README.md` for details.

## Updating after rule changes

**Two cases — don't mix them up:**

- **Clients that take a URL (Clash for Windows, Shadowrocket)** — the configuration still
  has to be updated and re-applied in the client; a GitHub push by itself does not prove
  that the running rules changed.
- **Clash Verge on the two Macs (which takes pasted content)** — **does not update
  automatically.** After the repository changes, paste it again, or run the sync on this
  machine:

  ```sh
  cd /path/to/proxy-rules
  git pull --ff-only
  python3 sync-mac.py --check
  python3 sync-mac.py
  ```

  This script writes the merged rules into the rules override referenced by the current
  profile and reloads the running configuration; `Script.js` stays DNS-only. Other Macs
  should not copy the file name blindly. If you paste manually instead, you still need to
  click the subscription card to re-apply. To take changes made on the Mac back into the
  repository, run `python3 sync-mac.py --export` (report) or `--export --write` (rewrite
  `clash/rules.yaml`); local exceptions are excluded.

## Things to watch

- The override in this repository **contains rules only**, no nodes. So every device still
  has to fill in its own `ckip.uk` subscription URL.
- `rules.yaml` uses `prepend`, so the rules are inserted before the subscription's own
  rules and a subscription update will not wipe them.
- Routing rules are maintained only in `rules.yaml`; its `PROCESS-NAME` entries may match
  package names on Android, so check the actual names per device.
- The override references `GEOSITE,apple` and the policy group name `PROXY`, so the
  subscription must contain a group named `PROXY` — your current `ckip.uk` subscription
  satisfies this.
