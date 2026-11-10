# Blender AI Tools by Marcos Alvarez — https://www.caldengames.com · GPL-3.0-or-later (ver NOTICE y LICENSE)
"""Resumen de un modelo para verificar antes de pasarlo al motor: armaduras, mallas, triángulos, materiales, texturas.

Uso: blender -b <modelo>.blend --python info_modelo.py
     blender -b --python info_modelo.py -- <modelo>.fbx|.glb      (importa y resume)
"""
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if args:
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    ext = os.path.splitext(args[0])[1].lower()
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=args[0])
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=args[0])
    else:
        raise SystemExit(f"Formato no soportado: {ext}")

for a in (o for o in bpy.data.objects if o.type == "ARMATURE"):
    huesos = a.data.bones
    deform = [b for b in huesos if b.use_deform]
    print(f"INFO armadura {a.name}: {len(huesos)} huesos ({len(deform)} deforman). Raíz: "
          f"{[b.name for b in huesos if not b.parent]}")
total = 0
zmin, zmax = float("inf"), float("-inf")
def _es_auxiliar(o):
    # el importador de glTF agrega una Icosphere (forma de los huesos) en la colección "glTF_not_exported"
    return any(c.name == "glTF_not_exported" for c in o.users_collection)


for o in sorted((o for o in bpy.data.objects if o.type == "MESH" and not _es_auxiliar(o)), key=lambda o: o.name):
    t = sum(len(p.vertices) - 2 for p in o.data.polygons)
    total += t
    for c in o.bound_box:
        z = (o.matrix_world @ __import__("mathutils").Vector(c)).z
        zmin, zmax = min(zmin, z), max(zmax, z)
    imgs = []
    for m in o.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    imgs.append(f"{n.image.name}({n.image.size[0]}x{n.image.size[1]},"
                                f"{'empaquetada' if n.image.packed_file else 'externa'})")
    sk = o.data.shape_keys
    print(f"INFO malla {o.name}: {t} tris, {len(o.data.vertices)} verts, materiales {[m.name for m in o.data.materials if m]}, "
          f"texturas {imgs}, shape keys {len(sk.key_blocks) if sk else 0}, "
          f"armature {any(m.type == 'ARMATURE' for m in o.modifiers)}, grupos {len(o.vertex_groups)}")
print("INFO total triángulos", total)
if total:
    print("INFO altura (m)", round(zmax - zmin, 3))
