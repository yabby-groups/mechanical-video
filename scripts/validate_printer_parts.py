"""Sequential, low-memory independent STEP round-trip acceptance."""
import gc
import hashlib
import json
from pathlib import Path
import time

from build123d import import_step, import_brep
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--canonical",action="store_true")
args=parser.parse_args()

root=Path(__file__).resolve().parents[1]/'series/3d-printer/master_assembly'
model=json.loads((root/('cad_assembly.json' if args.canonical else 'assembly.json')).read_text())
unique={part['cad'] if args.canonical else part['step']:part for part in model['parts']}
results=[]; started=time.monotonic()
for index,(name,part) in enumerate(unique.items(),1):
    shape=(import_brep if name.endswith('.brep') else import_step)(root/name)
    solids=shape.solids()
    valid=bool(solids) and all(s.is_valid and s.volume>0 for s in solids)
    relative=abs(shape.volume-part['volume_mm3'])/part['volume_mm3']
    results.append(dict(step=name,sha256=hashlib.sha256((root/name).read_bytes()).hexdigest(),valid=valid,solids=len(solids),volume_mm3=shape.volume,
        relative_volume_roundtrip_difference=relative,
        passed=valid and len(solids)==part['solids'] and (args.canonical or relative<.001),
        volume_drift_warning=relative>=.001))
    del solids,shape
    if index%50==0:
        gc.collect(); print(index,'/',len(unique),flush=True)
    if not results[-1]['passed']: print('FAILED',results[-1],flush=True)
report=dict(passed=all(r['passed'] for r in results),unique_step_files=len(results),
    cad_manifest_sha256=hashlib.sha256((root/('cad_assembly.json' if args.canonical else 'assembly.json')).read_bytes()).hexdigest(),
    display_manifest_sha256=hashlib.sha256((root/'assembly.json').read_bytes()).hexdigest(),
    acceptance='Independent disk reimport: valid positive-volume solids and expected solid count. Volume differences are reported, not manufacturing accuracy checks.',
    total_occurrences=len(model['parts']),wall_seconds=time.monotonic()-started,results=results)
(root/('cad-roundtrip-validation.json' if args.canonical else 'roundtrip-validation.json')).write_text(json.dumps(report,indent=2))
print('ROUNDTRIP_COMPLETE',report['passed'],len(results),flush=True)
raise SystemExit(0 if report['passed'] else 1)
