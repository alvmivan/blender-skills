# Blender AI Tools by Marcos Alvarez — https://www.caldengames.com · GPL-3.0-or-later (ver NOTICE y LICENSE)
"""Construye un humanoide de MPFB listo para un motor de juego, a partir de una ficha JSON.

Uso:
    blender -b --python humano.py -- <ficha.json> [<carpeta_salida>]

Qué hace, en orden (cada paso se puede apagar o ajustar en la ficha; ver ejemplos/ficha_ejemplo.json):
 1. Cuerpo con los macros (género, edad, músculo, peso, altura, proporciones, etnia) y los targets de detalle.
    Si la ficha pide `altura_m`, se mide el cuerpo y se reconstruye con la escala justa.
 2. Rig de MPFB (`game_engine` por defecto: 53 huesos, nombres tipo Unreal/Unity, sirve como Humanoid).
 3. Assets del pack (ojos, cejas, pestañas, pelo, dientes, ropa) con pesos interpolados del cuerpo.
 4. Limpieza: aplica los shape keys, borra la geometría auxiliar y (opcional) el cuerpo que queda bajo la ropa.
 5. Decimación con la cabeza protegida + horneado de normal y AO de la malla completa (opcional).
 6. Piel: el difuso del pack con un tinte, más normal y máscara de suavidad (o la piel GAMEENGINE de MPFB).
 7. Vistas de previsualización y export (.blend, .fbx para Unity, .glb).
Imprime al final una línea `RESUMEN {...}` con triángulos por malla, altura y archivos, para leer desde el agente.
"""
import json
import os
import sys

import bpy
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpfb_util  # noqa: E402
import calidad  # noqa: E402
import render_vistas  # noqa: E402
import exportar  # noqa: E402

CARPETA_DE_TIPO = {"Eyes": "eyes", "Eyebrows": "eyebrows", "Eyelashes": "eyelashes", "Hair": "hair", "Teeth": "teeth",
                   "Tongue": "tongue", "Clothes": "clothes"}


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def altura_cuerpo(h):
    """Altura del cuerpo visible (el modificador Mask de MPFB oculta la geometría auxiliar; se mide lo evaluado)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = h.evaluated_get(dg)
    me = ev.to_mesh()
    zs = [(ev.matrix_world @ v.co).z for v in me.vertices]
    ev.to_mesh_clear()
    return max(zs) - min(zs)


def altura_total():
    """Altura de todo el personaje (cuerpo + pelo + ropa + zapatos), por si al cuerpo se le borró lo de bajo la ropa."""
    from mathutils import Vector
    zs = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects if o.type == "MESH" for c in o.bound_box]
    return max(zs) - min(zs) if zs else 0.0


def crear_cuerpo(ficha, TS, HS, escala):
    d = TS.get_default_macro_info_dict()
    macros = dict(ficha.get("macros", {}))
    raza = macros.pop("race", None)
    d.update(macros)
    if raza:
        d["race"] = raza
    h = HS.create_human(macro_detail_dict=d, scale=escala)
    faltan = []
    for nombre, peso in ficha.get("targets", {}).items():
        ruta = TS.target_full_path(nombre)
        if not ruta:
            faltan.append(nombre)
            continue
        TS.load_target(h, ruta, weight=float(peso))
    if faltan:
        print("AVISO targets que no existen (ver docref/mpfb/datos.md):", faltan)
    return h


def borrar_bajo_ropa(h, umbral=0.5):
    """Borra del cuerpo los vértices que la ropa marca para ocultar (grupos `Delete.<prenda>` de MPFB)."""
    grupos = [g.index for g in h.vertex_groups if g.name.startswith("Delete.")]
    if not grupos:
        return 0
    bm = bmesh.new()
    bm.from_mesh(h.data)
    lay = bm.verts.layers.deform.active
    borrar = [v for v in bm.verts if any(v[lay].get(i, 0.0) > umbral for i in grupos)]
    bmesh.ops.delete(bm, geom=borrar, context="VERTS")
    bm.to_mesh(h.data)
    bm.free()
    for m in list(h.modifiers):
        if m.type == "MASK" and m.name.startswith("Delete."):
            h.modifiers.remove(m)
    return len(borrar)


def material_piel(nombre, color, normal=None, rugosidad=0.6):
    """Principled con color y (si hay) mapa de normales conectado: así lo leen el exportador FBX y el de glTF."""
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexImage")
    tc.image = color
    nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rugosidad
    if normal:
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = normal
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def main():
    args = mpfb_util.argumentos()
    if not args:
        raise SystemExit("Uso: blender -b --python humano.py -- <ficha.json> [<carpeta_salida>]")
    ruta_ficha = os.path.abspath(args[0])
    with open(ruta_ficha, encoding="utf-8") as f:
        ficha = json.load(f)
    nombre = ficha.get("nombre", "Humano")
    sal = ficha.get("salida", {})
    carpeta = os.path.abspath(args[1] if len(args) > 1 else
                              os.path.join(os.path.dirname(ruta_ficha), sal.get("carpeta", nombre.lower())))
    tex = os.path.join(carpeta, "texturas")
    os.makedirs(tex, exist_ok=True)

    mpfb_util.limpiar_escena()
    TS, HS, _ = mpfb_util.servicios()
    print("MPFB", mpfb_util.version(), "desde", mpfb_util.raiz(), "| datos", mpfb_util.datos())

    # 1. cuerpo (con la altura pedida)
    escala = 0.1
    h = crear_cuerpo(ficha, TS, HS, escala)
    objetivo = ficha.get("altura_m")
    if objetivo:
        alto = altura_cuerpo(h)
        if abs(alto - objetivo) > 0.005:
            me = h.data
            bpy.data.objects.remove(h, do_unlink=True)
            bpy.data.meshes.remove(me)
            escala = 0.1 * objetivo / alto
            h = crear_cuerpo(ficha, TS, HS, escala)
    print("ALTURA", round(altura_cuerpo(h), 3), "m, escala", round(escala, 5))

    # 2. rig
    rig = ficha.get("rig", "game_engine")
    arm = HS.add_builtin_rig(h, rig, import_weights=True) if rig else None
    if rig and arm is None:
        raise SystemExit(f"El rig {rig} no existe (ver docref/mpfb/datos.md)")

    # 3. assets
    extras = []
    for a in ficha.get("assets", []):
        tipo = a["tipo"]
        ruta = mpfb_util.asset(a["archivo"]) if "archivo" in a else mpfb_util.mhclo(CARPETA_DE_TIPO[tipo], a["nombre"])
        o = HS.add_mhclo_asset(ruta, h, asset_type=tipo, material_type=a.get("material", "GAMEENGINE"))
        o.name = f"{nombre}_{a.get('objeto', a.get('nombre', tipo))}"
        extras.append(o)

    # 4. limpieza
    calidad.limpiar_cuerpo(h)
    if ficha.get("borrar_cuerpo_bajo_ropa", True):
        print("BAJO_ROPA vértices borrados:", borrar_bajo_ropa(h))
    h.name = f"{nombre}_Cuerpo"
    if arm:
        arm.name = f"{nombre}_Rig"

    # 5. decimar + hornear
    dec = ficha.get("decimar")
    hornear = ficha.get("hornear", False)
    hi = None
    if dec or hornear:
        dec = dec or {"ratio": 1.0}
        hi = calidad.decimar(h, ratio=float(dec.get("ratio", 0.5)), proteger=dec.get("proteger", calidad.PROTEGER))
    else:
        for m in list(h.modifiers):
            if m.type == "MASK":
                h.modifiers.remove(m)
    tam = int(ficha.get("tam_textura", 2048))
    horneado = {}
    if hornear:
        horneado = calidad.hornear(h, hi, tex, f"{nombre.lower()}_piel", tam=tam, tam_ao=max(512, tam // 2))
    elif hi:
        bpy.data.objects.remove(hi, do_unlink=True)

    # 6. piel
    piel = ficha.get("piel", {"pack": "young_caucasian_male"})
    if piel:
        if piel.get("modo") == "mpfb":
            mhmat = mpfb_util.asset(os.path.join("skins", piel["pack"], piel["pack"] + ".mhmat"))
            HS.set_character_skin(mhmat, h, skin_type="GAMEENGINE")
        else:
            base = calidad.piel_base(mpfb_util.difuso_de_piel(piel.get("pack", "young_caucasian_male")), tam,
                                     tono=tuple(piel.get("tono", (1.0, 1.0, 1.0))))
            pref = f"{nombre.lower()}_piel"
            img = calidad.escribir_imagen(pref, base, os.path.join(tex, pref + ".png"))
            normal = None
            if horneado:
                import numpy as np
                cero = np.zeros(base.shape[:2], dtype=np.float32)
                calidad.mapas_piel(tex, pref, horneado["normal"], base, cero, cero)
                normal = bpy.data.images.load(os.path.join(tex, pref + "_normal.png"))
                normal.colorspace_settings.name = "Non-Color"
                normal.pack()
            h.data.materials.clear()
            h.data.materials.append(material_piel(pref, img, normal))

    # dientes: el asset del pack es muy denso para un juego
    for o in extras:
        if o.name.lower().endswith(("teeth_base", "dientes", "teeth")) or "teeth" in o.name.lower():
            arm_mods = [m for m in o.modifiers if m.type == "ARMATURE"]
            for m in list(o.modifiers):
                if m.type == "SUBSURF":
                    o.modifiers.remove(m)
            dm = o.modifiers.new("dec", "DECIMATE")
            dm.ratio = float(ficha.get("decimar_dientes", 0.2))
            bpy.context.view_layer.objects.active = o
            # el Decimate tiene que ir antes que el Armature para poder aplicarlo
            while o.modifiers[0].name != "dec":
                bpy.ops.object.modifier_move_up(modifier="dec")
            bpy.ops.object.modifier_apply(modifier="dec")
            if not arm_mods and arm:
                o.modifiers.new("Armature", "ARMATURE").object = arm

    # 7. vistas y export
    previas = []
    vistas = ficha.get("vistas", ["frente", "tres_cuartos", "cara"])
    if vistas:
        previas = render_vistas.render(os.path.join(carpeta, "previas", f"{nombre.lower()}.png"), vistas=tuple(vistas))
    archivos = []
    formatos = sal.get("formatos", ["blend", "fbx"])
    for fmt in formatos:
        if fmt == "fbx":
            archivos.append(exportar.exportar(os.path.join(carpeta, f"{nombre}.fbx"), motor=sal.get("motor", "unity")))
        elif fmt in ("glb", "gltf"):
            archivos.append(exportar.exportar(os.path.join(carpeta, f"{nombre}.glb"), motor="gltf"))
    if "blend" in formatos:
        try:
            bpy.ops.file.pack_all()
        except RuntimeError as e:
            print("AVISO no se pudo empaquetar todo:", e)
        ruta_blend = os.path.join(carpeta, f"{nombre}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=ruta_blend)
        archivos.append(ruta_blend)

    resumen = {
        "nombre": nombre, "altura_m": round(altura_total(), 3), "rig": rig,
        "huesos": len(arm.data.bones) if arm else 0,
        "tris": {o.name: tris(o) for o in bpy.data.objects if o.type == "MESH"},
        "tris_total": sum(tris(o) for o in bpy.data.objects if o.type == "MESH"),
        "archivos": archivos, "previas": previas, "texturas": sorted(os.listdir(tex)),
    }
    print("RESUMEN", json.dumps(resumen, ensure_ascii=False))


main()
