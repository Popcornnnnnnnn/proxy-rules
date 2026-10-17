#!/usr/bin/env python3
"""Merge public rules into this Mac's Clash Verge rules override and reload.
Requires macOS Ruby and Clash Verge Rev. Private state stays outside Git.

The Mac's Clash Verge Rev keeps Script.js for DNS fixes only; routing rules live in the
"rules" enhancement item referenced by the current profile. This script writes the merged
rules there, validates the result with mihomo, and reloads the running configuration.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate without applying')
    args = parser.parse_args()
    os.umask(0o077)

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
    # inferred from it.
    if private_path.exists():
        private = json.loads(private_path.read_text())
    else:
        private = {'rules': [normalize_local(r) for r in read_yaml(rule_path).get('prepend', [])],
                   'ai_keys': []}

    public_keys = {rule_key(r) for r in public}
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

    fragment = FRAGMENT_HEADER + '\n' + yaml_text({'prepend': merged, 'append': [], 'delete': []})

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
    try:
        for path, content in writes.items():
            path.write_text(content)
        controller(runtime, '/configs?force=true', {'path': str(STATE / 'clash-verge.yaml')})
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
        controller(runtime, '/configs?force=true', {'path': str(STATE / 'clash-verge.yaml')})
        raise


if __name__ == '__main__':
    main()
