# My routing rules (public repository, no node information)

The public editing entry point for multi-device rules. Each device configures its own
node subscription; this repository holds only rules and credential-free generation
scripts — no nodes, subscription URLs, or keys. Each device's rule files are maintained
separately and are currently not identical rule by rule.

**This MacBook Pro is the authoritative source.** Rules are edited on it, and this
repository mirrors them for the other devices. When the two disagree, the Mac is right and
the repository is stale. The agent workflow is in [AGENTS.md](AGENTS.md).

## Layout

| Directory | Purpose | Clients |
| --- | --- | --- |
| `clash/` | The only Clash routing rules file to edit, `rules.yaml` | Clash Verge, Clash for Windows, Android generator |
| `shadowrocket/` | Shadowrocket configuration fragment | Shadowrocket on iPhone / iPad |
| `build-android.py` | Builds a complete configuration including nodes; the subscription URL is read from a private local file | Clash Meta for Android |

## How to make changes

Rules are edited on this MacBook Pro (in Clash Verge's rules override), then published:

```sh
cd /path/to/proxy-rules
python3 sync-mac.py --export        # report the difference first
python3 sync-mac.py --export --write
# Clash routing rules are edited only in clash/rules.yaml; the iPhone configuration is still maintained separately
git add -A && git commit -m "Update rules: xxx" && git push
```

Editing `clash/rules.yaml` in the repository directly also works, but then this Mac has to
be updated from it (`sync-mac.py`, see below) — the Mac is the source of truth, so a
repository-only change is not yet in effect anywhere.

Windows and iPhone can fetch the public rule files from the URL below; after an update
the configuration must still be re-applied in the client. The other Mac uses a local
override file, and the Redmi uses a complete configuration generated on this machine and
transferred manually; neither takes effect automatically from a GitHub push.

```
https://cdn.jsdelivr.net/gh/Popcornnnnnnnn/proxy-rules@main/<file path>
```

## Applying repository edits to this Mac (secondary)

Only needed when `clash/rules.yaml` was edited in the repository instead of on the Mac:

```sh
cd /path/to/proxy-rules
git pull --ff-only
python3 sync-mac.py --check  # validate only
python3 sync-mac.py          # merge, back up, validate, and reload
```

The script writes the merged rules into the Clash Verge Rev rules override referenced by
the current profile (`profiles.yaml` → that profile's `rules` item). `Script.js` is left
alone and keeps DNS fixes only. Public rules take precedence; local exceptions live in
Clash's `profiles/codex-local-rules.json` and are not uploaded to GitHub.

## Publishing Mac changes to the repository (primary)

```sh
python3 sync-mac.py --export          # report the difference only
python3 sync-mac.py --export --write  # rewrite clash/rules.yaml from the Mac
```

`--export` reads the Mac's rules override, excludes the local exceptions listed in
`profiles/codex-local-rules.json`, reverses the AI-node remap, and compares the result with
the repository. With `--write` it rewrites `clash/rules.yaml` in the Mac's order and keeps
the comments attached to each rule; rules that exist only in the repository are dropped.
Local exceptions are never published. Review the diff, commit, and push; then update the
other devices.

Before writing, `sync-mac.py` validates the merged rules with `mihomo -t`, refuses when a
rule references a policy the running configuration does not define, backs up to Clash's
`backups-codex`, and restores the previous files if the reload fails. The reload goes
through the Clash controller as a configuration payload, because the privileged service
rejects file paths outside its own directory. This command does not create a scheduled
task, and other devices still need to be updated individually.

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
