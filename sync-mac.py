#!/usr/bin/env python3
"""Sync routing rules between this Mac's Clash Verge Rev and the public repository.

Default direction (repository -> Mac): merge clash/rules.yaml with the local exceptions,
write the profile's rules override, validate with mihomo, and reload the running config.

`--export` reports the other direction (Mac -> repository) and `--export --write` rewrites
clash/rules.yaml from the Mac's rules override, excluding local exceptions and reversing
the AI-node remap so nothing device-private or device-specific reaches the public repo.

Requires macOS Ruby and Clash Verge Rev. Private state stays outside Git.

`--from-peer SSH_ALIAS` uses an existing trusted SSH connection to mirror the
source Mac's exact active rule list to this Mac.
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

REPO = Path(__file__).resolve().parent
STATE = Path.home() / 'Library/Application Support/io.github.clash-verge-rev.clash-verge-rev'
MIHOMO = '/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo'
FRAGMENT_HEADER = '# Profile Enhancement Rules Template for Clash Verge\n'
BUILTIN_POLICIES = {'DIRECT', 'REJECT', 'REJECT-DROP', 'PASS', 'COMPATIBLE'}
PEER_BLOCK = '  // Routing rules synced from the source Mac.'
PEER_SNAPSHOT = r"""
require 'yaml'
require 'json'
require 'net/http'

path = File.join(Dir.home, 'Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml')
text = File.read(path)
x = YAML.load(text)
address = x.fetch('external-controller')
abort unless address.match?(/\A(?:127\.0\.0\.1|localhost):\d+\z/)
host, port = address.split(':')
http = Net::HTTP.new(host, Integer(port), nil)
http.open_timeout = http.read_timeout = 5
request = Net::HTTP::Get.new('/rules')
request['Authorization'] = "Bearer #{x.fetch('secret')}"
response = http.request(request)
abort unless response.code == '200' && x['mode'] == 'rule' && File.read(path) == text
groups = x.fetch('proxy-groups', [])
names = groups.map { |group| group.fetch('name') } + ['DIRECT']
fallbacks = groups.select do |group|
  group['type'] == 'fallback' && !Array(group['proxies']).empty? &&
    Array(group['proxies']).all? { |name| names.include?(name) } && !group.key?('use')
end
live = JSON.parse(response.body).fetch('rules')
abort if live.any? { |r| (r['extra'] || {})['disabled'] }
puts JSON.generate({
  rules: x.fetch('rules'),
  live: live.map { |r| r.values_at('type', 'payload', 'proxy') },
  fallbacks: fallbacks.map { |g| g.slice('name', 'type', 'proxies', 'interval', 'timeout', 'lazy', 'hidden') },
  inventory: (x.fetch('rule-providers', {}) || {}).keys,
})
"""


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
    with build_opener(ProxyHandler({})).open(req, timeout=15) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def live_rule_identities(config):
    return [[r['type'], r['payload'], r['proxy']]
            for r in controller(config, '/rules')['rules'] if not r.get('extra', {}).get('disabled')]


def peer_snapshot(peer):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@-]*', peer):
        raise RuntimeError('Use an existing SSH hostname or alias')
    args = ['/usr/bin/ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=6', '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
            peer, '/usr/bin/ruby']
    response = subprocess.run(args, input=PEER_SNAPSHOT, text=True, capture_output=True, timeout=25)
    if response.returncode:
        raise RuntimeError('Source Mac could not provide its live Clash rules')
    snapshot = json.loads(response.stdout)
    if not snapshot['rules'] or [policy_of(rule) for rule in snapshot['rules']] != [
            rule[2] for rule in snapshot['live']]:
        raise RuntimeError('Source Mac live rules differ from its generated config')
    return snapshot


def peer_script(text, rules, aliases):
    # This target already replaces the subscription rules in its Global Extend Script.
    # Replace only that assignment and the fallback groups owned by this workflow.
    assignment = r'^  config\.rules = \[\n.*?^ {0,2}\];$'
    marker = re.escape(PEER_BLOCK)
    pattern = re.compile(rf'(?:^{marker}\n.*?)?{assignment}', re.MULTILINE | re.DOTALL)
    fallback_code = ''
    if aliases:
        fallback_code = (
            f'  for (const group of {json.dumps(aliases, ensure_ascii=False)}) {{\n'
            '    if (!config["proxy-groups"].some(existing => existing.name === group.name)) {\n'
            '      config["proxy-groups"].push(group);\n'
            '    }\n'
            '  }\n'
        )
    rule_lines = ',\n'.join(f'    {json.dumps(rule, ensure_ascii=False)}' for rule in rules)
    replacement = f'{PEER_BLOCK}\n{fallback_code}  config.rules = [\n{rule_lines}\n  ];'
    updated, replaced = pattern.subn(lambda _: replacement, text)
    if replaced != 1:
        raise RuntimeError('Expected one routing assignment in the target Global Extend Script')
    return updated


def atomic_write(path, contents):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as pending:
        temporary = Path(pending.name)
        try:
            pending.write(contents)
            pending.flush()
            os.fsync(pending.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def sync_from_peer(peer, check):
    snapshot = peer_snapshot(peer)
    script_path = STATE / 'profiles/Script.js'
    runtime_path = STATE / 'clash-verge.yaml'
    registry_path = STATE / 'profiles.yaml'
    check_path = STATE / 'clash-verge-check.yaml'
    paths = [script_path, runtime_path, registry_path]
    if check_path.is_file():
        paths.append(check_path)
    originals = {path: path.read_bytes() for path in paths}
    runtime = read_yaml(runtime_path)
    if runtime['mode'] != 'rule' or snapshot['inventory'] or runtime.get('rule-providers'):
        raise RuntimeError('Peer sync requires rule mode with inline rules on both Macs')
    required_policies = {policy_of(rule) for rule in snapshot['rules']}
    # A previously cloned fallback is regenerated from the source on each sync.
    script = originals[script_path].decode()
    previous_fallbacks = re.search(
        rf'^{re.escape(PEER_BLOCK)}\n  for \(const group of (\[.*\])\) \{{$',
        script, re.MULTILINE)
    managed_names = ({group['name'] for group in json.loads(previous_fallbacks[1])}
                     if previous_fallbacks else set())
    own_groups = [group for group in runtime['proxy-groups']
                  if group['name'] not in managed_names]
    known = {group['name'] for group in own_groups} | BUILTIN_POLICIES
    aliases = [dict(group, url='https://www.gstatic.com/generate_204') for group in snapshot['fallbacks']
               if group['name'] in required_policies - known and set(group['proxies']) <= known]
    if required_policies - known - {group['name'] for group in aliases}:
        raise RuntimeError('The target lacks policies required by the source rules')
    updated_script = peer_script(script, snapshot['rules'], aliases)
    if (not check and updated_script == script and runtime['rules'] == snapshot['rules']
            and runtime['proxy-groups'] == own_groups + aliases
            and live_rule_identities(runtime) == snapshot['live']):
        return

    candidate = dict(runtime, rules=snapshot['rules'])
    candidate['proxy-groups'] = own_groups + aliases
    config = yaml_text(candidate)
    with tempfile.TemporaryDirectory(prefix='clash-peer-') as temporary:
        test_dir = Path(temporary)
        js = test_dir / 'Script.js'
        yaml = test_dir / 'clash.yaml'
        js.write_text(updated_script)
        yaml.write_text(config)
        run(['node', '--check', str(js)])
        run([MIHOMO, '-t', '-d', str(STATE), '-f', str(yaml)])
    if check:
        print(f'Validated {len(snapshot["rules"])} source rules on the target')
        return

    # Do not overwrite a subscription refresh that happened during validation.
    if any(path.read_bytes() != saved for path, saved in originals.items()):
        raise RuntimeError('Clash files changed during validation; try again')
    backup = Path(tempfile.mkdtemp(prefix=f'{datetime.now():%Y%m%d-%H%M%S}-clash-peer-',
                                  dir=STATE / 'backups-codex'))
    writes = {script_path: updated_script.encode(), runtime_path: config.encode()}
    if check_path in originals:
        writes[check_path] = config.encode()
    for path in writes:
        (backup / path.name).write_bytes(originals[path])
    applied = []
    reload_attempted = False
    try:
        for path, contents in writes.items():
            if path.read_bytes() != originals[path]:
                raise RuntimeError('Clash files changed during installation; try again')
            atomic_write(path, contents)
            applied.append(path)
        reload_attempted = True
        controller(runtime, '/configs?force=true', {'payload': config})
        if (live_rule_identities(runtime) != snapshot['live'] or
                any(path.read_bytes() != contents for path, contents in writes.items())):
            raise RuntimeError('Target and source live rule order or policy differ')
    except (Exception, KeyboardInterrupt):
        for path in reversed(applied):
            if path.read_bytes() == writes[path]:
                atomic_write(path, originals[path])
        if reload_attempted and runtime_path.read_bytes() == originals[runtime_path]:
            controller(runtime, '/configs?force=true', {'payload': originals[runtime_path].decode()})
        raise
    print(f'Synced and verified {len(snapshot["rules"])} ordered rules; backup: {backup}')


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
    parser.add_argument('--from-peer', metavar='SSH_ALIAS',
                        help='Mirror the live rules from a trusted Mac to this Mac over SSH')
    args = parser.parse_args()
    os.umask(0o077)

    if args.from_peer:
        if args.export or args.write:
            parser.error('--from-peer can only be combined with --check')
        with (STATE / 'peer-rule-sync.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                sync_from_peer(args.from_peer, args.check)
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                raise SystemExit(str(error))
        return

    global_script = STATE / 'profiles/Script.js'
    if global_script.is_file() and PEER_BLOCK in global_script.read_text():
        parser.error('This Mac mirrors a peer. Run --from-peer instead.')

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
