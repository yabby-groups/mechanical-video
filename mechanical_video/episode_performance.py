"""Record creative estimates and imported platform observations separately."""
import argparse
import json
import math
from pathlib import Path
import sqlite3
import statistics


METRICS = {'plays', 'retention_3s', 'retention_30s', 'average_watch_seconds',
           'completion_rate', 'likes', 'comments', 'saves', 'shares'}
RATES = {'retention_3s', 'retention_30s', 'completion_rate'}
COUNTS = {'plays', 'likes', 'comments', 'saves', 'shares'}


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS performance_snapshots (
        id INTEGER PRIMARY KEY, episode_id TEXT NOT NULL, video_version TEXT NOT NULL,
        platform TEXT NOT NULL, duration_seconds REAL NOT NULL, title TEXT NOT NULL,
        cover_version TEXT NOT NULL, prediction_json TEXT, actual_json TEXT)''')
    return db


def validate(record):
    for key in ('episode_id', 'video_version', 'platform', 'title', 'cover_version'):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f'{key} must be a nonempty string')
    duration = record.get('duration_seconds')
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('duration_seconds must be positive and finite')
    prediction = record.get('subjective_prediction')
    if prediction is not None:
        if not isinstance(prediction, dict) or not isinstance(prediction.get('basis'), str) or not prediction['basis'].strip():
            raise ValueError('subjective_prediction requires a written basis')
        score = prediction.get('audience_score')
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError('subjective audience_score must be between 0 and 100')
    actual = record.get('actual')
    if actual is not None:
        if not isinstance(actual, dict):
            raise ValueError('actual must be an object')
        for key in ('source', 'observed_at', 'measurement_window'):
            if not isinstance(actual.get(key), str) or not actual[key].strip():
                raise ValueError(f'actual.{key} must be a nonempty string')
        metrics = actual.get('metrics')
        if not isinstance(metrics, dict) or not metrics or set(metrics) - METRICS:
            raise ValueError('actual.metrics must contain supported metric names')
        for key, value in metrics.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'actual.metrics.{key} must be nonnegative and finite')
            if key in RATES and value > 1:
                raise ValueError(f'{key} must be a fraction from 0 to 1')
            if key in COUNTS and (not isinstance(value, int)):
                raise ValueError(f'{key} must be an integer count')
    if prediction is None and actual is None:
        raise ValueError('a subjective prediction or actual observation is required')


def record_snapshot(db, record):
    validate(record)
    with db:
        cursor = db.execute('''INSERT INTO performance_snapshots
            (episode_id, video_version, platform, duration_seconds, title, cover_version, prediction_json, actual_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (record['episode_id'], record['video_version'], record['platform'], record['duration_seconds'],
             record['title'], record['cover_version'],
             json.dumps(record['subjective_prediction'], ensure_ascii=False) if record.get('subjective_prediction') is not None else None,
             json.dumps(record['actual'], ensure_ascii=False) if record.get('actual') is not None else None))
    return cursor.lastrowid


def compare(db, snapshot_id, metric):
    if metric not in METRICS:
        raise ValueError('unsupported metric')
    target = db.execute('SELECT * FROM performance_snapshots WHERE id = ?', (snapshot_id,)).fetchone()
    if target is None:
        raise ValueError('snapshot not found')
    actual = json.loads(target['actual_json']) if target['actual_json'] else None
    if not actual or metric not in actual['metrics']:
        return {'status': 'NO_ACTUAL_DATA', 'metric': metric, 'peer_count': 0}
    window = actual['measurement_window']
    rows = db.execute('''SELECT * FROM performance_snapshots WHERE platform = ? AND actual_json IS NOT NULL
        AND duration_seconds BETWEEN ? AND ? AND NOT (episode_id = ? AND video_version = ?) ORDER BY id DESC''',
        (target['platform'], target['duration_seconds'] * .9, target['duration_seconds'] * 1.1,
         target['episode_id'], target['video_version'])).fetchall()
    peers = {}
    seen = set()
    for row in rows:
        key = (row['episode_id'], row['video_version'])
        if key in seen:
            continue
        seen.add(key)
        observation = json.loads(row['actual_json'])
        if observation['measurement_window'] == window and metric in observation['metrics']:
            peers[key] = observation['metrics'][metric]
    values = list(peers.values())
    if not values:
        return {'status': 'NO_COMPARABLE_PEERS', 'metric': metric,
                'target': actual['metrics'][metric], 'peer_count': 0}
    median = statistics.median(values)
    value = actual['metrics'][metric]
    return {'status': 'COMPARISON', 'metric': metric, 'target': value, 'peer_count': len(values),
            'peer_median': median, 'difference_from_median': value - median,
            'scope': 'same platform, same measurement window, duration within 10%; descriptive only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('import')
    add.add_argument('json_file', type=Path)
    comparison = sub.add_parser('compare')
    comparison.add_argument('snapshot_id', type=int)
    comparison.add_argument('metric', choices=sorted(METRICS))
    args = parser.parse_args()
    db = connect(args.db)
    try:
        if args.command == 'import':
            result = {'snapshot_id': record_snapshot(db, json.loads(args.json_file.read_text()))}
        else:
            result = compare(db, args.snapshot_id, args.metric)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == '__main__':
    main()
