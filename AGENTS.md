# Working notes for agents

## Authority

**This MacBook Pro's live Clash Verge rules are the authoritative source.** The repository
mirrors them so the other devices (another Mac, two Windows machines, two iPhones, the
Redmi) can fetch the same rules. Treat the repository as a copy, not as the origin: when
the two disagree, the Mac is right and the repository is stale.

Local exceptions (company, intranet, and similar) are deliberately **not** part of the
mirror. They live in Clash's `profiles/codex-local-rules.json`, outside Git.

## When rules change on this Mac

1. Check whether the Mac and the repository already agree:

   ```sh
   cd /path/to/proxy-rules
   python3 sync-mac.py --export     # report only, never writes
   ```

2. Publish the Mac's rules into the repository:

   ```sh
   python3 sync-mac.py --export --write
   ```

   This rewrites `clash/rules.yaml` from the Mac's rules override, keeps the comments
   attached to each rule, excludes local exceptions, and reverses the AI-node remap so no
   device-private or device-specific value reaches the public repository.

3. Review the diff, then commit and push. Commit messages are English, with the agent
   attribution trailer as the final paragraph:

   ```
   Agent: <harness>/<model>
   ```

4. Tell the user which devices still need action, and never claim a device is updated
   without checking it: Windows fetches `clash/rules.yaml` through Merge/Parsers;
   iPhone updates and re-selects the Shadowrocket configuration; the Redmi needs a
   regenerated complete configuration (`build-android.py`) imported again; the other Mac
   needs the same paste or sync step. A GitHub push does not update any device by itself.

## When the repository is edited instead

Apply it to this Mac:

```sh
python3 sync-mac.py --check   # validate only
python3 sync-mac.py           # merge, back up, validate, reload, read back
```

It validates the merged rules with `mihomo -t`, refuses rules whose policy the running
configuration does not define, refuses to act when the running rules do not start with the
current override (the profile needs re-applying), backs up to Clash's `backups-codex`, and
restores the previous files if the reload fails.

## Never

- Never commit node information, subscription URLs, UUIDs, or keys: this repository is
  public. `build-android.py` output and `android/subscription-url.txt` stay Git-ignored.
- Never publish local exceptions.
- Never describe a rule change as effective on a device you did not verify.

## Mechanism (may change; the script is the source of truth)

Clash Verge Rev on this Mac keeps `Script.js` for DNS fixes only; routing rules live in the
"rules" enhancement item referenced by the current profile in `profiles.yaml`. The running
configuration renders as `[rules override prepend] + [subscription rules]`. mihomo runs
under Clash Verge's privileged service, whose home directory is the service directory, so a
reload must send the configuration as a controller payload rather than a file path. Earlier
versions of this workflow copied a file into `profiles/` or injected `config.rules` into
`Script.js`; both are obsolete, and a profile-layout rebuild silently resets the override,
so always verify with `--export` before trusting either side.
