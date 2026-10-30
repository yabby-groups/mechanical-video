"""Build a separate display cache from source-verified occurrence corrections.

Never edits the accepted/legacy master or its geometry inventory.
"""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base = ROOT / 'series/3d-printer/master_assembly'
    evidence = ROOT / 'series/3d-printer-v2/revisions/EP02/connection-research-20261030/correction-assets.json'
    report = json.loads(evidence.read_text())
    original = base / 'assembly.json'
    data = json.loads(original.read_text())
    if report['source_sha256'] != data['source_sha256']:
        raise ValueError('Corrections do not belong to this source STEP')
    key = digest(evidence)[:16]
    target = ROOT / 'series/3d-printer-v2/models' / ('source-repair-' + key)
    manifest = target / 'assembly.json'
    if manifest.exists():
        print(manifest)
        return
    (target / 'parts').mkdir(parents=True, exist_ok=True)
    corrections = {c['id']: c for c in report['corrections']}
    for part in data['parts']:
        correction = corrections.get(part['id'])
        if correction:
            if part['path'] != correction['path'] or part['matrix_mm'] != correction['matrix_mm']:
                raise ValueError('Source occurrence placement/path mismatch: ' + part['id'])
            if not correction['reread_valid'] or correction['reread_volume'] <= 0:
                raise ValueError('Invalid source correction: ' + part['id'])
            for field in ('step', 'mesh'):
                source = Path(correction[field])
                if digest(source) != correction[field + '_sha256']:
                    raise ValueError('Correction bytes changed: ' + str(source))
                relative = 'parts/' + source.name
                shutil.copy2(source, target / relative)
                part[field] = relative
            part.update(volume_mm3=correction['volume'], solids=correction['solids'],
                        valid=True, topology_repair=None, display_approximation=[],
                        geometry_correction='Independent source STEP occurrence export; original placement retained')
        else:
            for field in ('step', 'mesh'):
                destination = target / part[field]
                if not destination.exists():
                    shutil.copy2(base / part[field], destination)
    data.update(version=data['version'] + '-source-repair-' + key,
                geometry_version=3,
                parent_model_sha256=digest(original),
                correction_evidence_sha256=digest(evidence),
                corrected_occurrences=sorted(corrections),
                geometry_identity_policy='Eight confirmed wrong mappings replaced from original STEP; legacy assets preserved',
                audit_limitations=['Six remaining shared-asset groups matched source volumes; topology equivalence not established.',
                                   'Correct geometry and source placement do not certify loads, contact or physical simulation.'])
    files = {p[field] for p in data['parts'] for field in ('step', 'mesh')}
    inventory = {name: digest(target / name) for name in sorted(files)}
    (target / 'geometry-assets.json').write_text(json.dumps(inventory, indent=2))
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    shutil.copy2(evidence, target / 'correction-evidence.json')
    shutil.copy2(Path(__file__), target / 'build-source-repair.py')
    print(manifest)


if __name__ == '__main__':
    main()
