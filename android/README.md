# How to connect the Redmi (Clash Meta for Android)

## Bottom line: it cannot use a "rules override"

Clash Meta for Android does have an override in its settings, but it **only covers global
options** (port, DNS, ipv6, mode, and so on). Checking its source, `ConfigurationOverride`
has **no `rules` field at all**, so a "rules override" does not exist for it.

The only way it takes rules is a **complete configuration file** (which must contain
`proxies` + `proxy-groups` + `rules`).

## How

Generate a complete configuration (subscription + custom rules merged) on this machine
with `build-android.py`:

For first-time use, put your own subscription URL in `android/subscription-url.txt` on a
single line, and make it readable only by you
(`chmod 600 android/subscription-url.txt`). That file is Git-ignored; do not put the URL in
a script or commit it to the public repository.

```sh
cd /path/to/proxy-rules
python3 build-android.py
# writes android/config.yaml, with the custom rules inserted at the front of rules
```

The generated `config.yaml` **contains node information**, is excluded by `.gitignore`,
and must not be committed. The script sets its permissions to `600`. The generator merges
the `prepend` section of `clash/rules.yaml`; before importing, check whether the process
names in it have matching package names on Android.

Then transfer that complete configuration to the Redmi and import and select it in
Clash Meta for Android. Every future change to rules or the subscription requires
regenerating, transferring, and applying it again.
