#!/usr/bin/env python3
from pathlib import Path
import re, sys
root = Path(__file__).resolve().parents[1]
scan_roots = [
    root / 'showcase' / 'fundiora-public-demo',
]
paths = []
for scan_root in scan_roots:
    if scan_root.is_file():
        paths.append(scan_root)
    elif scan_root.exists():
        paths.extend(p for p in scan_root.rglob('*') if p.is_file() and p.suffix.lower() in {'.html', '.md', '.json', '.yml', '.yaml', '.txt', '.css', '.js'})
patterns = {
    'absolute-user-path': re.compile(r'/Users/[^\s\)\]"\']+'),
    'secret-assignment-like': re.compile(r'(?i)(api[_-]?key|secret|token|private[_-]?key|auth_token|ct0|seed phrase|mnemonic)\s*[:=]'),
    'positive-reward-claim': re.compile(r'(?i)\b(guaranteed rewards?|staking yield|financial return|token price|listing confirmed|official endorsement)\b'),
    'wallet-action': re.compile(r'(?i)\b(sign transaction|send transaction|fund wallet|seed phrase)\b'),
}
failures = []
for path in paths:
    text = path.read_text(errors='ignore')
    low = text.lower()
    for name, rx in patterns.items():
        for m in rx.finditer(text):
            window = low[max(0, m.start()-180):m.start()+220]
            if name in {'positive-reward-claim', 'wallet-action'} and any(s in window for s in ['blocked', 'does not claim', 'not claim', 'no claims', 'no guaranteed', 'approval required', 'excludes', 'must stay blocked']):
                continue
            line = text.count('\n', 0, m.start()) + 1
            snippet = text[m.start():m.start()+90].replace('\n', ' ')
            failures.append(f'{path.relative_to(root)}:{line}: {name}: {snippet}')
if failures:
    print('PUBLIC_SAFETY_SCAN=FAIL')
    print('\n'.join(failures[:120]))
    sys.exit(1)
print(f'PUBLIC_SAFETY_SCAN=PASS files={len(paths)}')
