"""Inspect source-model bounds for the EP02 X-axis motion study."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

source, manifest, output = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=source)
parts = {p['id']: p for p in json.loads(Path(manifest).read_text())['parts']}
for obj in bpy.context.scene.objects:
    if obj.get('part_id') in parts:
        matrix = Matrix(parts[obj['part_id']]['matrix_mm'])
        matrix.translation *= .001
        obj.matrix_world = matrix
bpy.context.view_layer.update()
groups = {
    'carriage': lambda p: '/X_Axis/X_Carriage/' in p,
    'rail': lambda p: '/X_Axis/HFSB5-20-330/MGN12_rail__1_/' in p and p.endswith('/SOLID'),
    'slider': lambda p: '/X_Axis/X_Carriage/MGN12H__1_/' in p,
    'x_chain': lambda p: '/X_Axis/X_Cable_Chain/' in p,
    'guide_tube': lambda p: '4x3mm_PTFE_Guide_Tube' in p,
}
result = {}
for label, match in groups.items():
    objects = [o for o in bpy.context.scene.objects if match(o.get('source_path', ''))]
    if not objects:
        raise RuntimeError(f'Missing group: {label}')
    items = []
    for obj in objects:
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        items.append({'path': obj['source_path'], 'name': obj.name,
                      'min': [min(p[i] for p in points) for i in range(3)],
                      'max': [max(p[i] for p in points) for i in range(3)]})
    result[label] = {'count': len(items), 'objects': items,
                     'min': [min(item['min'][i] for item in items) for i in range(3)],
                     'max': [max(item['max'][i] for item in items) for i in range(3)]}
Path(output).write_text(json.dumps(result, indent=2))
