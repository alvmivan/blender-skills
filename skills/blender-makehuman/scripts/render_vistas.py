"""Renders rápidos de previsualización (Workbench, sin GPU) para comparar un personaje contra su referencia.

Como módulo (dentro de otro script):
    import render_vistas; render_vistas.render("salida/prev.png", vistas=("frente", "tres_cuartos", "cara"))
Desde la línea de comandos, sobre un .blend ya armado:
    blender -b personaje.blend --python render_vistas.py -- salida/prev.png [vista ...]

Las cámaras se encuadran solas con la altura del personaje (no hace falta que mida 1,80). Workbench no representa la
luz del motor del juego: sirve para forma, proporciones y texturas, no para evaluar materiales.
Vistas: frente, tres_cuartos, costado, espalda, cara, cara_costado, cara_espalda, torso, pies.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

VISTAS = {
    #  nombre:        (altura relativa del centro, fracción de la altura visible, ángulo alrededor en grados)
    "frente":       (0.50, 1.15, 0),
    "tres_cuartos": (0.50, 1.15, 40),
    "costado":      (0.50, 1.15, 90),
    "espalda":      (0.50, 1.15, 180),
    "cara":         (0.93, 0.17, 0),
    "cara_costado": (0.93, 0.20, 90),
    "cara_espalda": (0.93, 0.20, 180),
    "torso":        (0.70, 0.50, 0),
    "pies":         (0.10, 0.45, 20),
}


def _limites():
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.data.objects:
        if o.type == "MESH" and not o.hide_render:
            ev = o.evaluated_get(dg)
            pts += [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    if not pts:
        return Vector((0, 0, 0)), Vector((0, 0, 1.8))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def _centro_sobre(z0):
    """Centro (x, y) de los vértices por encima de z0 (para centrar las vistas de la cara en la cabeza)."""
    dg = bpy.context.evaluated_depsgraph_get()
    xs, ys = [], []
    for o in bpy.data.objects:
        if o.type == "MESH" and not o.hide_render:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            for v in me.vertices:
                p = ev.matrix_world @ v.co
                if p.z > z0:
                    xs.append(p.x)
                    ys.append(p.y)
            ev.to_mesh_clear()
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2) if xs else None


def render(ruta, vistas=("frente", "tres_cuartos", "cara"), res=(600, 900)):
    """Renderiza cada vista a `<ruta>_<vista>.png` (o a `ruta` si es una sola). Devuelve la lista de archivos."""
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    sc.display.shading.show_specular_highlight = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    if not sc.world:
        sc.world = bpy.data.worlds.new("Mundo")
    sc.world.color = (0.55, 0.57, 0.6)
    cam = bpy.data.objects.get("CamPrevia") or bpy.data.objects.new("CamPrevia", bpy.data.cameras.new("CamPrevia"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    sc.camera = cam
    lo, hi = _limites()
    alto = hi.z - lo.z
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    salidas = []
    for v in vistas:
        if v not in VISTAS:
            raise ValueError(f"Vista desconocida {v}. Hay: {', '.join(VISTAS)}")
        zrel, frac, ang = VISTAS[v]
        a = math.radians(ang)
        d = max(alto * 3, 5.0)
        # el personaje mira a -Y (convención de Blender/MPFB): la cámara de frente está en -Y
        px, py = cx, cy
        if frac < 0.3 and zrel > 0.8:
            px, py = _centro_sobre(lo.z + alto * 0.87) or (cx, cy)
        cam.location = (px + d * math.sin(a), py - d * math.cos(a), lo.z + alto * zrel)
        cam.rotation_euler = (math.radians(90), 0, a)
        # ortho_scale cubre el lado más largo de la imagen
        escala = alto * frac * max(1.0, res[0] / res[1])
        if frac >= 1.0:  # cuerpo entero: que entren los brazos abiertos de la pose en A
            ancho = max(hi.x - lo.x, hi.y - lo.y) * 1.08
            escala = max(escala, ancho * max(1.0, res[1] / res[0]))
        cam.data.ortho_scale = escala
        cam.data.clip_end = d * 3
        sc.render.filepath = ruta.replace(".png", f"_{v}.png") if len(vistas) > 1 else ruta
        bpy.ops.render.render(write_still=True)
        salidas.append(sc.render.filepath)
    return salidas


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    print("VISTAS", render(os.path.abspath(args[0]), vistas=tuple(args[1:]) or ("frente", "tres_cuartos", "cara")))
