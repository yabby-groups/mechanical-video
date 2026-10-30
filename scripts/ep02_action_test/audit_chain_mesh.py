"""Measure source-chain neighbour proximity during the illustrative motion."""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_path

source, manifest, output = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=source)
parts = {p['id']: p for p in json.loads(Path(manifest).read_text())['parts']}
objects = []
for obj in bpy.context.scene.objects:
    if '/X_Axis/X_Cable_Chain/' not in obj.get('source_path', ''):
        continue
    if '10x11_Chain_Link' not in obj.get('source_path', ''):
        continue
    matrix = Matrix(parts[obj['part_id']]['matrix_mm'])
    matrix.translation *= .001
    obj.matrix_world = matrix
    objects.append(obj)
if len(objects) != 21:
    raise RuntimeError(f'Expected 21 chain links, got {len(objects)}')
args = (.245, .1224, .035, .0949, .1411)
total = chain_path.length(*args)
samples = [total * i / 5000 for i in range(5001)]
reference = [chain_path.point(s, *args) for s in samples]
links = []
for obj in objects:
    matrix = obj.matrix_world.copy()
    pivot = sum((matrix @ Vector(c) for c in obj.bound_box), Vector()) / 8
    index = min(range(len(samples)), key=lambda i: (reference[i][0][0]-pivot.x)**2 + (reference[i][0][1]-pivot.z)**2)
    links.append((samples[index], obj, matrix, pivot, reference[index][1]))
links.sort(key=lambda item: item[0])
fixed = []
for obj in bpy.context.scene.objects:
    p = obj.get('source_path', '')
    if obj.type != 'MESH' or obj.get('part_id') not in parts or '/X_Axis/X_Cable_Chain/' in p or '/X_Axis/X_Carriage/' in p:
        continue
    matrix = Matrix(parts[obj['part_id']]['matrix_mm'])
    matrix.translation *= .001
    corners = [matrix @ Vector(c) for c in obj.bound_box]
    low = [min(v[i] for v in corners) for i in range(3)]
    high = [max(v[i] for v in corners) for i in range(3)]
    if high[0] < -.05 or low[0] > .31 or high[1] < .15 or low[1] > .22 or high[2] < .07 or low[2] > .17:
        continue
    vertices = [matrix @ v.co for v in obj.data.vertices]
    faces = [tuple(p.vertices) for p in obj.data.polygons]
    if faces:
        fixed.append((obj.name, BVHTree.FromPolygons(vertices, faces)))

def transformed(link, displacement):
    s, obj, matrix, pivot, tangent0 = link
    (x, z), tangent = chain_path.point(s, *args, displacement)
    (x0, z0), _ = chain_path.point(s, *args)
    angle = -(math.atan2(tangent[1], tangent[0]) - math.atan2(tangent0[1], tangent0[0]))
    transform = Matrix.Translation(pivot + Vector((x-x0, 0, z-z0))) @ Matrix.Rotation(angle, 4, 'Y') @ Matrix.Translation(-pivot) @ matrix
    vertices = [transform @ v.co for v in obj.data.vertices]
    faces = [tuple(p.vertices) for p in obj.data.polygons]
    return vertices, faces

def distance(a, b):
    tree = KDTree(len(b))
    for i, vertex in enumerate(b):
        tree.insert(vertex, i)
    tree.balance()
    return min(tree.find(vertex)[2] for vertex in a)

result = {'scope': 'nearest mesh vertices and sampled BVH surface intersections; not hinge or solid collision proof', 'fixed_candidates': len(fixed), 'poses': []}
for displacement in (i * .002 for i in range(-20, 21)):
    meshes = [transformed(link, displacement) for link in links]
    pairs = []
    for i, (left, right) in enumerate(zip(meshes, meshes[1:])):
        a, fa = left
        b, fb = right
        overlaps = BVHTree.FromPolygons(a, fa).overlap(BVHTree.FromPolygons(b, fb))
        pairs.append({'left': links[i][1].name, 'right': links[i+1][1].name,
                      'nearest_vertex_mm': distance(a, b)*1000, 'triangle_overlaps': len(overlaps)})
    nonadjacent = []
    trees = [BVHTree.FromPolygons(vertices, faces) for vertices, faces in meshes]
    for i in range(len(trees)):
        for j in range(i+2, len(trees)):
            overlaps = trees[i].overlap(trees[j])
            if overlaps:
                nonadjacent.append({'left': links[i][1].name, 'right': links[j][1].name,
                                    'triangle_overlaps': len(overlaps)})
    fixed_overlaps = []
    for i, tree in enumerate(trees):
        for name, fixed_tree in fixed:
            overlap = tree.overlap(fixed_tree)
            if overlap:
                fixed_overlaps.append({'link': links[i][1].name, 'object': name,
                                       'triangle_overlaps': len(overlap)})
    result['poses'].append({'displacement_mm': displacement*1000, 'pairs': pairs,
                            'nonadjacent_overlaps': nonadjacent, 'fixed_overlaps': fixed_overlaps})
Path(output).write_text(json.dumps(result, indent=2))
