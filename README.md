# My routing rules (public repository, no node information)

The public editing entry point for multi-device rules. Each device configures its own
node subscription; this repository holds only rules and credential-free generation
scripts — no nodes, subscription URLs, or keys. Each device's rule files are maintained
separately and are currently not identical rule by rule.

## Layout

| Directory | Purpose | Clients |
| --- | --- | --- |
| `clash/` | The only Clash routing rules file to edit, `rules.yaml` | Clash Verge, Clash for Windows, Android generator |
| `shadowrocket/` | Shadowrocket configuration fragment | Shadowrocket on iPhone / iPad |
| `build-android.py` | Builds a complete configuration including nodes; the subscription URL is read from a private local file | Clash Meta for Android |

## How to make changes

Edit only on this one MacBook Pro, then push:

```sh
cd /path/to/proxy-rules
# Clash routing rules are edited only in clash/rules.yaml; the iPhone configuration is still maintained separately
git add -A && git commit -m "Update rules: xxx" && git push
```

Windows and iPhone can fetch the public rule files from the URL below; after an update
the configuration must still be re-applied in the client. The other Mac uses a local
override file, and the Redmi uses a complete configuration generated on this machine and
transferred manually; neither takes effect automatically from a GitHub push.

```
https://cdn.jsdelivr.net/gh/Popcornnnnnnnn/proxy-rules@main/<file path>
```

## Local Mac sync (manual)

```sh
cd /path/to/proxy-rules
git pull --ff-only
python3 sync-mac.py --check  # validate only
python3 sync-mac.py          # merge, back up, validate, and reload
```

The script writes the merged rules into the Clash Verge Rev rules override referenced by
the current profile (`profiles.yaml` → that profile's `rules` item). `Script.js` is left
alone and keeps DNS fixes only. Public rules take precedence; local exceptions live in
Clash's `profiles/codex-local-rules.json` and are not uploaded to GitHub. On the first run
that file does not exist yet, so the local exception list is seeded from whatever the rules
override currently prepends, and the AI-node remap list starts empty.

Before writing, it validates the merged rules with `mihomo -t`, refuses when a rule
references a policy the running configuration does not define, backs up to Clash's
`backups-codex`, and restores the previous files if the reload fails. This command does not
create a scheduled task, and other devices still need to be updated individually.

## Current per-device differences

The comparison below is of repository files; it does not establish that any device has
updated or is using these rules:

| Traffic | Clash `rules.yaml` | iPhone Shadowrocket `.conf` |
| --- | --- | --- |
| Steam API / checkout hosts | `DIRECT` | `DIRECT` |
| Some other Steam domains | forced `PROXY` | several domains are `DIRECT` |
| `featureassets.org` | `DIRECT` | `🤖AI美国节点` |

The public repository only guarantees that each device can fetch the corresponding rule
files; for a rule to actually take effect on a device, the configuration must be
re-applied and verified in the client.

## How to connect each device

See the README in each subdirectory.
