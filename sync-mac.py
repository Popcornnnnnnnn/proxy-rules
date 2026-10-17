#!/usr/bin/env python3
"""Sync routing rules between this Mac's Clash Verge Rev and the public repository.

Default direction (repository -> Mac): merge clash/rules.yaml with the local exceptions,
write the profile's rules override, validate with mihomo, and reload the running config.

`--export` reports the other direction (Mac -> repository) and `--export --write` rewrites
clash/rules.yaml from the Mac's rules override, excluding local exceptions and reversing
the AI-node remap so nothing device-private or device-specific reaches the public repo.

Requires macOS Ruby and Clash Verge Rev. Private state stays outside Git.
"""
import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent
STATE = Path.home() / 'Library/Application Support/io.github.clash-verge-rev.clash-verge-rev'
MIHOMO = '/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo'
FRAGMENT_HEADER = '# Profile Enhancement Rules Template for Clash Verge\n'
BUILTIN_POLICIES = {'DIRECT', 'REJECT', 'REJECT-DROP', 'PASS', 'COMPATIBLE'}


def run(args, data=None):
    p = subprocess.run(args, input=data, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f'{Path(args[0]).name} failed; private output suppressed')
    return p.stdout


def read_yaml(path):
    return json.loads(run(['ruby', '-ryaml', '-rjson', '-e',
                          'puts JSON.generate(YAML.load_file(ARGV[0]))', str(path)]))


def yaml_text(obj):
    return run(['ruby', '-ryaml', '-rjson', '-e',
                'puts JSON.parse(STDIN.read).to_yaml'], json.dumps(obj))


def rule_key(rule):
    # Policy is the penultimate field when no-resolve is present.
    parts = rule.split(',')
    return ','.join(parts[:-2] if parts[-1] == 'no-resolve' else parts[:-1])


def policy_of(rule):
    parts = rule.split(',')
    return parts[-2] if parts[-1] == 'no-resolve' else parts[-1]


def normalize_local(rule):
    # Historical typos in the local rules; keep them repaired on import.
    return (rule.replace('DOMAIN-SUFFIX,https://z.ai/,', 'DOMAIN-SUFFIX,z.ai,')
                .replace('DOMAIN-KEYWORD,linuxdo,', 'DOMAIN-SUFFIX,linux.do,'))


def controller(config, path, body=None):
    addr = config.get('external-controller', '127.0.0.1:9097')
    if not __import__('re').fullmatch(r'(127\.0\.0\.1|localhost):\d+', addr):
        raise RuntimeError('Expected loopback Clash controller')
    req = Request('http://' + addr + path,
                  data=json.dumps(body).encode() if body is not None else None,
                  headers={'Authorization': 'Bearer ' + str(config.get('secret', '')),
                           'Content-Type': 'application/json'},
                  method='PUT' if body is not None else 'GET')
    with urlopen(req, timeout=15) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def fragment_text(rules):
    """Render the Clash Verge rules override in the same readable shape as the repo file."""
    body = '\n'.join(f"  - '{r.replace(chr(39), chr(39) * 2)}'" for r in rules)
    return f'{FRAGMENT_HEADER}\nprepend:\n{body}\n\nappend: []\n\ndelete: []\n'


def repo_entries(path):
    """Split clash/rules.yaml into (header, [(comments, rule)], tail, trailing comments)."""
    header, entries, tail = [], [], []
    comments, in_prepend, in_tail = [], False, False
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if in_tail:
            tail.append(line)
            continue
        if not in_prepend:
            header.append(line)
            if stripped == 'prepend:':
                in_prepend = True
            continue
        if stripped.startswith('- '):
            rule = stripped[2:].strip()
            if len(rule) > 1 and rule[0] == rule[-1] and rule[0] in "'\"":
                rule = rule[1:-1]
            entries.append((comments, rule))
            comments = []
        elif stripped.startswith('#') or not stripped:
            comments.append(line)
        else:
            in_prepend, in_tail = False, True
            tail.append(line)
    return header, entries, tail, comments


def export_rules(args):
    """Report (and optionally write) the Mac's rules back into the repository."""
    registry = read_yaml(STATE / 'profiles.yaml')
    current = next(x for x in registry['items'] if x['uid'] == registry['current'])
    rule_profile = next(x for x in registry['items'] if x['uid'] == current['option']['rules'])
    rule_path = STATE / 'profiles' / rule_profile['file']
    private_path = STATE / 'profiles/codex-local-rules.json'
    private = (json.loads(private_path.read_text()) if private_path.exists()
               else {'rules': [], 'ai_keys': []})
    private_keys = {rule_key(r) for r in private.get('rules', [])}
    ai_keys = set(private.get('ai_keys', []))

    override = read_yaml(rule_path).get('prepend', [])
    exported, skipped_private, remapped = [], 0, 0
    for rule in override:
        if rule_key(rule) in private_keys:
            skipped_private += 1
            continue
        if rule.endswith(',🤖AI美国节点') and rule_key(rule) in ai_keys:
            rule = rule[:-len('🤖AI美国节点')] + 'PROXY'
            remapped += 1
        exported.append(rule)

    repo_path = REPO / 'clash/rules.yaml'
    repo = read_yaml(repo_path)['prepend']
    repo_keys, exp_keys = [rule_key(r) for r in repo], [rule_key(r) for r in exported]
    repo_set, exp_set = set(repo_keys), set(exp_keys)
    only_mac = [r for r, k in zip(exported, exp_keys) if k not in repo_set]
    only_repo = [r for r, k in zip(repo, repo_keys) if k not in exp_set]
    order_differs = ([k for k in exp_keys if k in repo_set] != [k for k in repo_keys if k in exp_set])

    print(f'Mac override: {len(override)} rules -> exportable {len(exported)} '
          f'(excluded {skipped_private} local exceptions, reversed {remapped} AI-node remaps)')
    print(f'Repository:   {len(repo)} rules')
    print(f'Only on the Mac ({len(only_mac)}):')
    for rule in only_mac[:20]:
        print('   +', rule)
    print(f'Only in the repository ({len(only_repo)}):')
    for rule in only_repo[:20]:
        print('   -', rule)
    print(f'Order differs from the Mac: {order_differs}')
    if not args.write:
        print('Report only; re-run with --export --write to rewrite clash/rules.yaml.')
        return

    header, entries, tail, leftover = repo_entries(repo_path)
    by_key = {}
    for comments, rule in entries:
        by_key.setdefault(rule_key(rule), comments)
    dropped_comments = sum(len(c) for k, c in by_key.items() if k not in exp_set)
    out = list(header)
    for rule in exported:
        out.extend(by_key.get(rule_key(rule), []))
        out.append(f"  - '{rule.replace(chr(39), chr(39) * 2)}'")
    # Trailing comments survive only as blank separators; real ones are reported.
    dropped_comments += sum(1 for line in leftover if line.strip().startswith('#'))
    out.extend(line for line in leftover if not line.strip())
    out.extend(tail)
    repo_path.write_text('\n'.join(out) + '\n')
    print(f'Wrote {repo_path}: {len(exported)} rules; dropped {len(only_repo)} repo-only rules '
          f'and {dropped_comments} comment lines.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate without applying')
    parser.add_argument('--export', action='store_true', help='Report Mac -> repository')
    parser.add_argument('--write', action='store_true', help='With --export, rewrite the repo file')
    args = parser.parse_args()
    os.umask(0o077)

    if args.export:
        export_rules(args)
        return

    registry = read_yaml(STATE / 'profiles.yaml')
    current = next(x for x in registry['items'] if x['uid'] == registry['current'])
    uid = current['option']['rules']
    rule_profile = next(x for x in registry['items'] if x['uid'] == uid)
    rule_path = STATE / 'profiles' / rule_profile['file']
    private_path = STATE / 'profiles/codex-local-rules.json'
    runtime = read_yaml(STATE / 'clash-verge.yaml')

    public = read_yaml(REPO / 'clash/rules.yaml')['prepend']
    if not public or len(public) != len(set(public)):
        raise RuntimeError('Public rules empty or duplicated')

    # Local exceptions: prefer the private file; otherwise take whatever the rules
    # override currently prepends. Script.js no longer carries rules, so nothing is
    # inferred from it. Entries already covered by public rules are not exceptions.
    public_keys = {rule_key(r) for r in public}
    if private_path.exists():
        private = json.loads(private_path.read_text())
        stale = [r for r in private.get('rules', []) if rule_key(r) in public_keys]
        if stale:
            private['rules'] = [r for r in private['rules'] if rule_key(r) not in public_keys]
            print(f'Note: dropped {len(stale)} local exception(s) already covered by public rules')
    else:
        private = {'rules': [normalize_local(r) for r in read_yaml(rule_path).get('prepend', [])
                             if rule_key(r) not in public_keys],
                   'ai_keys': []}

    ai_keys = set(private.get('ai_keys', []))
    merged = [r[:-len('PROXY')] + '🤖AI美国节点'
              if r.endswith(',PROXY') and rule_key(r) in ai_keys else r for r in public]
    merged += [r for r in private['rules'] if rule_key(r) not in public_keys]
    merged = list(dict.fromkeys(merged))

    # Every referenced policy must exist in the running configuration.
    groups = {g['name'] for g in runtime.get('proxy-groups', [])} | BUILTIN_POLICIES
    unknown = sorted({policy_of(r) for r in merged} - groups)
    if unknown:
        raise RuntimeError(f'Unknown policy names in merged rules: {unknown}')

    fragment = fragment_text(merged)

    # Clash Verge renders the running config as [rules override prepend] + [subscription
    # rules]. Recover the subscription part so the reload keeps it, and refuse when the
    # running config does not match the current override (the profile needs re-applying).
    prev_prepend = read_yaml(rule_path).get('prepend', [])
    runtime_rules = runtime.get('rules', [])
    if runtime_rules[:len(prev_prepend)] != prev_prepend:
        raise RuntimeError('Running rules do not start with the current override; '
                           're-apply the profile in Clash Verge first')
    subscription_rules = runtime_rules[len(prev_prepend):]
    live_rules = merged + subscription_rules

    candidate_config = dict(runtime)
    candidate_config['rules'] = live_rules

    backup = STATE / 'backups-codex' / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-proxy-rules-merge')
    backup.mkdir(parents=True)
    (backup / 'candidate-rules.yaml').write_text(fragment)
    (backup / 'candidate.yaml').write_text(yaml_text(candidate_config))
    run([MIHOMO, '-t', '-d', str(STATE), '-f', str(backup / 'candidate.yaml')])
    print(f'Validated: {len(public)} public, {len(merged)} override, '
          f'{len(subscription_rules)} subscription, {len(live_rules)} live rules')
    if args.check:
        return

    writes = {rule_path: fragment,
              STATE / 'clash-verge.yaml': yaml_text(candidate_config),
              STATE / 'clash-verge-check.yaml': yaml_text(candidate_config),
              private_path: json.dumps(private, ensure_ascii=False, indent=2) + '\n'}
    originals = {}
    for path in writes:
        originals[path] = path.read_bytes() if path.exists() else None
        if path.exists():
            shutil.copy2(path, backup / path.name)
    original_runtime_text = (STATE / 'clash-verge.yaml').read_text()

    def reload(text):
        # mihomo runs under Clash Verge's privileged service, whose home is the service
        # directory, so {"path": ...} outside it is rejected. Send the config as payload.
        controller(runtime, '/configs?force=true', {'payload': text})

    try:
        for path, content in writes.items():
            path.write_text(content)
        reload(yaml_text(candidate_config))
        live = controller(runtime, '/rules')['rules']
        if len(live) != len(live_rules) or [r['proxy'] for r in live] != [policy_of(r) for r in live_rules]:
            raise RuntimeError('Live rules differ after reload')
        if read_yaml(rule_path).get('prepend') != merged:
            raise RuntimeError('Local rules override differs after write')
        print(f'Applied and reloaded: {len(live)} live rules; backup: {backup}')
    except Exception:
        for path, original in originals.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
        reload(original_runtime_text)
        raise


if __name__ == '__main__':
    main()
