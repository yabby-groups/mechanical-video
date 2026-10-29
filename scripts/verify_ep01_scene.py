"""Inspect saved EP01 source objects for hidden objects and Boolean clipping."""
import json
import sys
from pathlib import Path

import bpy

scene_path = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(scene_path))
source = [o for o in bpy.context.scene.objects if o.get('part_id')]
hidden = [o.name for o in source if o.hide_render]
booleans = [(o.name, m.name) for o in source for m in o.modifiers
            if m.type == 'BOOLEAN' and m.show_render]
result = dict(source_parts=len(source), hidden=hidden, active_boolean_modifiers=booleans,
              passed=len(source) == 1428 and not hidden and not booleans)
report = scene_path.parent / (scene_path.stem + '-geometry-inspection.json')
report.write_text(json.dumps(result, indent=2))
print(json.dumps(result))
if not result['passed']:
    raise SystemExit(1)
