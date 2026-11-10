# Blender AI Tools by Marcos Alvarez — https://www.caldengames.com · GPL-3.0-or-later (ver NOTICE y LICENSE)
"""Exporta un personaje riggeado para un motor de juego.

Como módulo:   import exportar; exportar.exportar("salida/Pj.fbx", motor="unity")
Por consola:   blender -b personaje.blend --python exportar.py -- salida/Pj.fbx [unity|gltf]

Presets:
- `unity` (.fbx): probado en Unity 6 / URP con humanoides de MPFB (rig `game_engine`). Ejes -Z adelante / Y arriba,
  sin huesos hoja, solo huesos que deforman, texturas embebidas. En Unity: Rig > Humanoid.
- `gltf` (.glb): para Godot y motores que leen glTF. Texturas dentro del .glb. No se probó en un motor con esta skill.
Unreal no tiene preset porque no se probó: usar el FBX y verificar la escala y los ejes allá.
"""
import os
import sys

import bpy


def _seleccionar():
    for o in bpy.data.objects:
        o.select_set(o.type in ("MESH", "ARMATURE") and not o.hide_render)


def _sin_subdivision():
    """MPFB agrega Subdivision a ojos/pelo/ropa: en un juego no va (y el FBX lo aplicaría)."""
    for o in bpy.data.objects:
        for m in list(o.modifiers):
            if m.type == "SUBSURF":
                o.modifiers.remove(m)


def exportar(ruta, motor="unity", guardar_blend=None):
    """Exporta lo visible (mallas + armaduras). `guardar_blend`: ruta opcional de un .blend con todo empaquetado."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    _sin_subdivision()
    _seleccionar()
    if motor == "unity":
        bpy.ops.export_scene.fbx(
            filepath=ruta, use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
            path_mode="COPY", embed_textures=True, bake_anim=False, use_armature_deform_only=True,
            mesh_smooth_type="FACE", axis_forward="-Z", axis_up="Y")
    elif motor == "gltf":
        bpy.ops.export_scene.gltf(filepath=ruta, export_format="GLB", use_selection=True, export_skins=True,
                                  export_animations=False, export_yup=True)
    else:
        raise ValueError(f"Motor desconocido: {motor} (hay: unity, gltf)")
    if guardar_blend:
        try:
            bpy.ops.file.pack_all()
        except RuntimeError as e:
            print("AVISO no se pudo empaquetar todo:", e)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(guardar_blend), copy=True)
    print("EXPORTADO", ruta, os.path.getsize(ruta), "bytes")
    return ruta


if __name__ == "__main__" and "--" in sys.argv:
    a = sys.argv[sys.argv.index("--") + 1:]
    exportar(os.path.abspath(a[0]), motor=a[1] if len(a) > 1 else ("gltf" if a[0].lower().endswith((".glb", ".gltf")) else "unity"))
