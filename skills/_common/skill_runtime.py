#!/usr/bin/env python3
import argparse
import base64
import datetime as dt
import json
import re
from pathlib import Path

RESULT_CONTRACT_VERSION = "2.0"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def _profile_for_run(run_id: str) -> str:
    m = re.search(r'(\d+)$', run_id or '')
    if m and int(m.group(1)) >= 2:
        return 'improved'
    return 'baseline'


def run_python_skill(spec: dict):
    parser = argparse.ArgumentParser(description=f"Run {spec['name']}")
    parser.add_argument('--input', default='module-run-input.json')
    parser.add_argument('--artifacts-root', default='artifacts')
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    module = payload.get('moduleName', 'UnknownModule')
    run_id = payload.get('runId', 'run-001')
    profile_key = _profile_for_run(run_id)
    profile = spec['profiles'].get(profile_key, spec['profiles']['baseline'])

    out_dir = Path(args.artifacts_root) / module / run_id / spec['name']
    out_dir.mkdir(parents=True, exist_ok=True)

    started = _now_iso()
    artifacts = []

    for rel, content in profile.get('extra', {}).items():
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if content == '__PNG__':
            raw = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AApMBgU8R4X0AAAAASUVORK5CYII=')
            target.write_bytes(raw)
        elif isinstance(content, str):
            target.write_text(content, encoding='utf-8')
        else:
            target.write_text(json.dumps(content, indent=2), encoding='utf-8')
        artifacts.append(target.as_posix())

    ended = _now_iso()
    result_path = out_dir / 'result.json'

    result = {
        'skillName': spec['name'],
        'stage': spec['stage'],
        'moduleName': module,
        'runId': run_id,
        'status': profile['status'],
        'startedAt': started,
        'endedAt': ended,
        'summary': profile['summary'],
        'metrics': profile.get('metrics', {}),
        'artifacts': [result_path.as_posix(), *artifacts],
        'findings': profile.get('findings', []),
        'recommendations': profile.get('recommendations', []),
        'resultContractVersion': RESULT_CONTRACT_VERSION
    }

    result_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(result_path.as_posix())
