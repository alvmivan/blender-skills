# Blender AI Tools by Marcos Alvarez — https://www.caldengames.com · GPL-3.0-or-later (ver NOTICE y LICENSE)
"""Herramientas de calidad para personajes de MPFB pensados para juegos. Corre dentro de Blender.

- `limpiar_cuerpo()`: aplica los shape keys y borra la geometría auxiliar de MakeHuman (HelperGeometry, JointCubes).
- `decimar()`: baja la malla del cuerpo pero deja la cabeza entera (y el cuello y las manos a medias): decimar parejo
  aplasta la cara. Devuelve una copia completa y subdividida para hornear.
- `hornear()`: normal tangente y oclusión ambiental desde esa copia hacia los UV del cuerpo decimado (Cycles, CPU).
- `rasterizar()`: pinta atributos por vértice (máscaras de barba, labios, ojeras...) sobre el UV de la malla, con numpy.
- `piel_base()` + `mapas_piel()`: la piel arranca del difuso pintado del pack CC0 (poros, tono, labios) y sale con
  normal (geometría horneada + poros + barba) y máscara de suavidad.
- `publicar_texturas()`: junta las texturas en una carpeta y genera normal y máscara a las que solo tienen color.

Orientación de imágenes: todo lo que pasa por acá está en el orden de Blender (fila 0 = abajo), igual que `Image.pixels`.
"""
import os
import shutil
import sys

import bpy
import bmesh
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapas  # noqa: E402


# ---------- cuerpo ----------

def limpiar_cuerpo(h):
    """Aplica los shape keys y borra la geometría auxiliar de MakeHuman (HelperGeometry, JointCubes)."""
    bpy.context.view_layer.objects.active = h
    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    bm = bmesh.new()
    bm.from_mesh(h.data)
    lay = bm.verts.layers.deform.active
    gi = [h.vertex_groups[n].index for n in ("HelperGeometry", "JointCubes") if n in h.vertex_groups]
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if any(i in v[lay] for i in gi)], context="VERTS")
    bm.to_mesh(h.data)
    bm.free()


PROTEGER = {"head": 1.0, "neck_01": 0.7, "mano": 0.5}


def _tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def _tris_en(ob, nombre, umbral=0.5):
    """Triángulos cuyos vértices pesan más de `umbral` en el grupo `nombre` (para medir qué conservó la decimación)."""
    if nombre not in ob.vertex_groups:
        return 0
    gi = ob.vertex_groups[nombre].index
    w = np.zeros(len(ob.data.vertices))
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == gi:
                w[v.index] = g.weight
    return sum(len(p.vertices) - 2 for p in ob.data.polygons if all(w[i] > umbral for i in p.vertices))


def decimar(h, ratio=0.5, proteger=PROTEGER):
    """Decima el cuerpo dejando la cabeza con su malla original (y el cuello y las manos a medias).
    Devuelve `hi`: copia del cuerpo SIN decimar y con una subdivisión, para hornear normales y AO (borrarla después)."""
    hi = h.copy()
    hi.data = h.data.copy()
    hi.name = h.name + "_hi"
    bpy.context.collection.objects.link(hi)
    for m in list(hi.modifiers):
        hi.modifiers.remove(m)
    sub = hi.modifiers.new("sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1

    # peso por vértice: 1 = se decima, 0 = se conserva
    manos = [g.name for g in h.vertex_groups if g.name.startswith(("hand_", "index", "middle", "pinky", "ring", "thumb"))]
    grupos = {n: w for n, w in proteger.items() if n != "mano"}
    grupos.update({n: proteger.get("mano", 0.0) for n in manos})
    idx = {h.vertex_groups[n].index: w for n, w in grupos.items() if n in h.vertex_groups}
    vg = h.vertex_groups.new(name="decimar")
    for v in h.data.vertices:
        p = max((idx[g.group] * g.weight for g in v.groups if g.group in idx), default=0.0)
        vg.add([v.index], 1.0 - min(1.0, p), "REPLACE")

    antes, antes_cab = _tris(h), _tris_en(h, "head")
    dm = h.modifiers.new("dec", "DECIMATE")
    dm.ratio = ratio
    dm.vertex_group = "decimar"
    dm.vertex_group_factor = 1.0
    bpy.context.view_layer.objects.active = h
    bpy.ops.object.modifier_apply(modifier="dec")
    h.vertex_groups.remove(h.vertex_groups["decimar"])
    for m in list(h.modifiers):
        if m.type == "MASK":
            h.modifiers.remove(m)
    for p in h.data.polygons:
        p.use_smooth = True
    print(f"DECIMAR total {antes}->{_tris(h)} tris, cabeza {antes_cab}->{_tris_en(h, 'head')} tris")
    return hi


# ---------- horneado ----------

def hornear(h, hi, carpeta, prefijo, tam=2048, tam_ao=1024, muestras_ao=24, extrusion=0.006):
    """Hornea desde `hi` (malla completa, subdividida) sobre los UV de `h` (decimada): normal tangente y AO.
    Solo participan `h` y `hi` (lo demás se oculta al render mientras tanto). Deja `<prefijo>_normal.png` y
    `<prefijo>_ao.png` en `carpeta`, borra `hi` y devuelve {nombre: ruta}."""
    os.makedirs(carpeta, exist_ok=True)
    sc = bpy.context.scene
    motor = sc.render.engine
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    bk = sc.render.bake
    bk.use_selected_to_active = True
    bk.cage_extrusion = extrusion
    bk.max_ray_distance = extrusion * 4
    bk.margin = 16
    bk.use_pass_direct = False
    bk.use_pass_indirect = False

    ocultos = [o for o in bpy.data.objects if o not in (h, hi) and o.type == "MESH" and not o.hide_render]
    for o in ocultos:
        o.hide_render = True
    hi.hide_render = False
    hi.hide_viewport = False

    if not h.data.materials:
        m = bpy.data.materials.new("tmp_horneado")
        m.use_nodes = True
        h.data.materials.append(m)
    mat = h.data.materials[0]
    mat.use_nodes = True
    nodo = mat.node_tree.nodes.new("ShaderNodeTexImage")
    mat.node_tree.nodes.active = nodo

    salidas = {}
    for tipo, nombre, t, muestras in (("NORMAL", "normal", tam, 1), ("AO", "ao", tam_ao, muestras_ao)):
        img = bpy.data.images.new(f"{prefijo}_{nombre}", t, t)
        img.colorspace_settings.name = "Non-Color"
        nodo.image = img
        sc.cycles.samples = muestras
        for o in bpy.data.objects:
            o.select_set(False)
        hi.select_set(True)
        h.select_set(True)
        bpy.context.view_layer.objects.active = h
        kw = dict(type=tipo, use_selected_to_active=True, cage_extrusion=extrusion, max_ray_distance=extrusion * 4, margin=16)
        if tipo == "NORMAL":
            kw["normal_space"] = "TANGENT"
        bpy.ops.object.bake(**kw)
        ruta = os.path.join(carpeta, f"{prefijo}_{nombre}.png")
        img.filepath_raw = ruta
        img.file_format = "PNG"
        img.save()
        salidas[nombre] = ruta
        print("HORNEADO", tipo, ruta)

    mat.node_tree.nodes.remove(nodo)
    for o in ocultos:
        o.hide_render = False
    bpy.data.objects.remove(hi, do_unlink=True)
    sc.render.engine = motor
    return salidas


# ---------- imágenes (orden de Blender: fila 0 abajo) ----------

def leer_imagen(ruta, tam=None):
    """PNG → float32 (alto, ancho, 4) en [0, 1], reescalado a tam×tam si se pide."""
    img = bpy.data.images.load(ruta)
    if tam and tuple(img.size) != (tam, tam):
        img.scale(tam, tam)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def escribir_imagen(nombre, arr, ruta, no_color=False):
    """Guarda un arreglo (alto, ancho, 3|4) en [0, 1] como PNG y devuelve la imagen de Blender (queda empaquetada)."""
    h, w = arr.shape[:2]
    if arr.shape[-1] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), dtype=np.float32)], axis=-1)
    img = bpy.data.images.new(nombre, w, h, alpha=True)
    if no_color:
        img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.clip(arr, 0, 1).ravel().astype(np.float32))
    img.filepath_raw = ruta
    img.file_format = "PNG"
    img.save()
    img.pack()
    return img


def rasterizar(me, ATT, W):
    """Rasteriza atributos por vértice (N canales) a una imagen W×W sobre el UV activo de la malla; rellena 4 px de borde.
    Devuelve (W, W, N) en orden de Blender (fila 0 = v 0)."""
    N = ATT.shape[1]
    img = np.zeros((W, W, N))
    cov = np.zeros((W, W), bool)
    me.calc_loop_triangles()
    uvd = me.uv_layers.active.data
    for t in me.loop_triangles:
        uvs_ = np.array([uvd[l].uv[:] for l in t.loops]) * W
        vi = list(t.vertices)
        x0, y0 = np.floor(uvs_.min(axis=0)).astype(int) - 1
        x1, y1 = np.ceil(uvs_.max(axis=0)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, W - 1), min(y1, W - 1)
        if x1 <= x0 or y1 <= y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a, b, c = uvs_
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
        val = w0[..., None] * ATT[vi[0]] + w1[..., None] * ATT[vi[1]] + w2[..., None] * ATT[vi[2]]
        sub = img[y0:y1 + 1, x0:x1 + 1]
        sub[m] = val[m]
        cov[y0:y1 + 1, x0:x1 + 1] |= m
    for _ in range(4):
        for ax in (0, 1):
            for sh in (1, -1):
                r = np.roll(cov, sh, ax)
                fill = r & ~cov
                img[fill] = np.roll(img, sh, ax)[fill]
                cov |= fill
    return img


# ---------- piel ----------

def piel_base(ruta_pack, W, tono=(1.0, 1.0, 1.0)):
    """Color base de la piel: el difuso pintado del pack (poros, tono, labios, cejas) multiplicado por un tinte."""
    return leer_imagen(ruta_pack, W)[..., :3] * np.array(tono, dtype=np.float32)


def mapas_piel(carpeta, prefijo, ruta_normal_horneado, base_rgb, barba, labios, suavidad_base=0.32, poros=0.9, semilla=5):
    """Normal final de la piel (geometría horneada + poros del difuso + barba) y máscara de suavidad.
    `barba` y `labios` son mapas (W, W) en [0, 1] ya rasterizados. Escribe `<prefijo>_normal.png` (pisa el horneado) y
    `<prefijo>_mascara.png`."""
    W = base_rgb.shape[0]
    rng = np.random.default_rng(semilla)
    geo = leer_imagen(ruta_normal_horneado, W)[..., :3]
    altura = mapas.altura_desde_color(base_rgb, sigma_baja=6.0) - 0.5        # poros y vello, sin la forma general
    altura = altura * (1.0 - 0.5 * barba) + (rng.random((W, W)) - 0.5) * 0.9 * barba   # pelo corto: grano fino
    micro = mapas.normal_desde_altura(altura * poros, 2.0)
    normal = mapas.combinar_normales(geo, micro)
    escribir_imagen(f"{prefijo}_normal", normal, os.path.join(carpeta, f"{prefijo}_normal.png"), no_color=True)
    suav = suavidad_base + 0.22 * labios - 0.14 * barba + (mapas.luminancia(base_rgb) - 0.5) * 0.10
    masc = mapas.mascara(np.clip(suav, 0.05, 0.7))
    escribir_imagen(f"{prefijo}_mascara", masc, os.path.join(carpeta, f"{prefijo}_mascara.png"), no_color=True)


# ---------- publicación de texturas ----------

def publicar_texturas(origen, destino, albedos, extra=()):
    """Copia los PNG de `origen` a `destino` y, para cada albedo de la lista que no tenga `_normal`/`_mascara`, se los
    genera desde el color (relieve débil, suavidad baja). `extra`: (nombre, suavidad, metal) para ajustar alguno."""
    os.makedirs(destino, exist_ok=True)
    for f in os.listdir(origen):
        if f.endswith(".png"):
            shutil.copy(os.path.join(origen, f), os.path.join(destino, f))
    ajustes = {n: (s, m) for n, s, m in extra}
    for n in albedos:
        base = os.path.join(destino, n)
        if not os.path.exists(base + ".png") or os.path.exists(base + "_normal.png"):
            continue
        rgb = leer_imagen(base + ".png")[..., :3]
        s, m = ajustes.get(n, (0.12, 0.0))
        normal, masc = mapas.mapas_desde_color(rgb, fuerza=1.5, suavidad=s, metal=m)
        escribir_imagen(n + "_normal", normal, base + "_normal.png", no_color=True)
        escribir_imagen(n + "_mascara", masc, base + "_mascara.png", no_color=True)
        print("MAPAS desde color:", n)
