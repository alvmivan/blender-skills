# Blender AI Tools by Marcos Alvarez — https://www.caldengames.com · GPL-3.0-or-later (ver NOTICE y LICENSE)
"""Mapas PBR con numpy puro (sirve tanto en el Python del sistema como en el de Blender, que no trae scipy).

Convenciones:
- normal: tangente, OpenGL (Y+ arriba: Unity, Blender, Godot; para Unreal/DirectX invertir el verde), RGB 0–255.
- máscara: RGBA con R = metálico y A = suavidad (0 = mate, 1 = espejo); así la lee URP/Lit de Unity.
Todo con bordes que envuelven, para no romper el tileo.
"""
import numpy as np


def desenfocar(a, sigma):
    """Desenfoque gaussiano con bordes que envuelven (por FFT; no necesita scipy)."""
    if sigma <= 0:
        return a
    f = np.fft.fftfreq(a.shape[0])[:, None] ** 2 + np.fft.fftfreq(a.shape[1])[None, :] ** 2
    k = np.exp(-2 * (np.pi ** 2) * (sigma ** 2) * f)
    if a.ndim == 3:
        return np.real(np.fft.ifft2(np.fft.fft2(a, axes=(0, 1)) * k[..., None], axes=(0, 1)))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * k))


def ruido(forma, sigma, rng):
    """Ruido suave en [0, 1] (gaussiano desenfocado y normalizado)."""
    n = desenfocar(rng.standard_normal(forma), sigma)
    return (n - n.min()) / max(n.max() - n.min(), 1e-6)


def luminancia(rgb):
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def normalizar(v, p=(1, 99)):
    lo, hi = np.percentile(v, p)
    return np.clip((v - lo) / max(hi - lo, 1e-6), 0, 1)


def altura_desde_color(rgb01, sigma_baja=24.0):
    """Relieve a partir de la luminancia, sin la luz de baja frecuencia (que no es relieve)."""
    lum = luminancia(rgb01)
    h = lum - desenfocar(lum, sigma_baja)
    return normalizar(desenfocar(h, 0.8))


def normal_desde_altura(h, fuerza):
    """h en [0, 1]. Devuelve el normal tangente (OpenGL) en [0, 1], listo para guardar."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5   # las filas crecen hacia abajo
    n = np.stack([-dx * fuerza, dy * fuerza, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def combinar_normales(a, b):
    """Suma dos normales (en [0, 1]) al estilo "whiteout": conserva el relieve de las dos."""
    na = a * 2 - 1
    nb = b * 2 - 1
    n = np.stack([na[..., 0] + nb[..., 0], na[..., 1] + nb[..., 1], na[..., 2] * nb[..., 2]], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def mascara(suavidad, metal=0.0):
    """RGBA: R metálico, A suavidad. Acepta escalares o mapas."""
    forma = np.shape(suavidad) if np.ndim(suavidad) else np.shape(metal)
    m = np.zeros((*forma, 4), dtype=np.float32)
    m[..., 0] = metal
    m[..., 3] = suavidad
    return m


def a_uint8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def guardar(a, ruta):
    """Guarda un arreglo en [0, 1] (gris, RGB o RGBA) como PNG. Usa PIL si está; si no, el escritor de Blender."""
    try:
        from PIL import Image
        Image.fromarray(a_uint8(a)).save(ruta)
        return
    except ImportError:
        pass
    import bpy
    h, w = a.shape[:2]
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, axis=-1)
    if a.shape[-1] == 3:
        a = np.concatenate([a, np.ones((h, w, 1), dtype=a.dtype)], axis=-1)
    img = bpy.data.images.new("tmp_guardar", w, h, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.clip(a[::-1], 0, 1).ravel().astype(np.float32))
    img.filepath_raw = ruta
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def cargar(ruta):
    """PNG → float32 [0, 1] (RGB o RGBA, según el archivo), orientación de imagen (fila 0 arriba)."""
    try:
        from PIL import Image
        return np.asarray(Image.open(ruta), dtype=np.float32) / 255.0
    except ImportError:
        pass
    import bpy
    img = bpy.data.images.load(ruta)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1]


def mapas_desde_color(rgb01, fuerza=2.0, suavidad=0.1, metal=0.0):
    """Para una textura de la que solo hay color: normal débil desde la luminancia y máscara constante."""
    n = normal_desde_altura(altura_desde_color(rgb01), fuerza)
    return n, mascara(np.full(rgb01.shape[:2], suavidad, dtype=np.float32), metal)
