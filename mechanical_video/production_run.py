"""Guard new custom production commands; never bypass a failed v4 gate."""
import argparse
import json
from pathlib import Path
import subprocess
from .production_gate import evaluate, sha, STAGES


def run(record_path, stage, command):
    record_path = Path(record_path).resolve()
    try:
        before = sha(record_path)
        record = json.loads(record_path.read_text())
        checks = record['production_checks']
        authorization = checks.get('execution', {}).get(stage)
        reviewed_execution = checks.get('content_review', {}).get('execution', {})
        if (not command or not isinstance(command, list) or authorization != command
                or reviewed_execution.get(stage) != command):
            return {'status': 'BLOCKED', 'reasons': ['command not bound to reviewed stage']}, 1
        report = evaluate(record, record_path.parent, stage, require_version=4)
        if report['status'] == 'BLOCKED':
            return report, 1
        if before != sha(record_path):
            return {'status': 'BLOCKED', 'reasons': ['record changed during preflight']}, 1
        # Recheck referenced assets immediately before process launch. This is a
        # local guard, not an OS sandbox or a guarantee against concurrent writes.
        report = evaluate(record, record_path.parent, stage, require_version=4)
        if report['status'] == 'BLOCKED' or before != sha(record_path):
            return {'status': 'BLOCKED', 'reasons': ['inputs changed during preflight']}, 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {'status': 'BLOCKED', 'reasons': ['invalid/unreadable execution record']}, 1
    result = subprocess.run(command, check=False)
    return {'status': 'COMMAND_COMPLETED', 'returncode': result.returncode,
            'record_sha256': before, 'stage': stage,
            'formal_acceptance': False}, result.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--stage', choices=STAGES, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    report, code = run(args.record, args.stage, command)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
