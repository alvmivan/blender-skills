"""Acceso a MPFB (MakeHuman para Blender) desde scripts que corren dentro de Blender.

Lo importan los demás scripts de la skill. Resuelve lo que más falla al automatizar MPFB:

- El add-on vive en un módulo distinto según cómo se instaló: `bl_ext.blender_org.mpfb` (plataforma de extensiones de
  Blender, lo normal desde 4.2) o `bl_ext.user_default.mpfb` (instalado desde un zip). `servicio()` prueba los dos.
- La carpeta de assets del usuario (ojos, pelos, pieles, ropa) cambia con la versión de Blender y el sistema operativo.
  `datos()` se la pregunta al propio MPFB (`LocationService`); la variable `MPFB_DATA` manda si está definida.
- Si Blender se abrió con `--factory-startup`, el add-on no carga: el error lo dice explícitamente.
"""
import importlib
import os
import sys

REPOSITORIOS = ("bl_ext.blender_org.mpfb", "bl_ext.user_default.mpfb")
_RAIZ = None


def raiz():
    """Nombre del paquete de MPFB que carga en este Blender (p. ej. `bl_ext.blender_org.mpfb`)."""
    global _RAIZ
    if _RAIZ:
        return _RAIZ
    errores = []
    for mod in REPOSITORIOS:
        try:
            # importar un servicio, no solo el paquete: con --factory-startup el paquete se importa igual,
            # pero los servicios fallan (TypeError en logservice) porque el add-on no está registrado
            importlib.import_module(f"{mod}.services.locationservice")
            _RAIZ = mod
            return mod
        except Exception as e:  # noqa: BLE001 - se informa todo junto
            errores.append(f"{mod}: {type(e).__name__}: {e}")
    raise ImportError(
        "MPFB no carga. ¿Está instalado y habilitado? ¿Se abrió Blender con --factory-startup (no hay que usarlo)? "
        "Probá: blender -b -c extension install mpfb --sync --enable\n  " + "\n  ".join(errores))


def servicio(nombre):
    """Clase de servicio de MPFB por nombre de módulo: servicio("humanservice").HumanService, etc."""
    return importlib.import_module(f"{raiz()}.services.{nombre}")


def servicios():
    """(TargetService, HumanService, AssetService), los tres que se usan casi siempre."""
    return (servicio("targetservice").TargetService,
            servicio("humanservice").HumanService,
            servicio("assetservice").AssetService)


def version():
    m = importlib.import_module(raiz())
    v = getattr(m, "VERSION", None)
    if v:
        return ".".join(str(x) for x in v)
    try:
        import addon_utils
        return ".".join(str(x) for x in addon_utils.module_bl_info(m).get("version", ()))
    except Exception:  # noqa: BLE001
        return "?"


def datos(sub=None):
    """Carpeta `data` del usuario de MPFB (donde se descomprimen los packs de assets)."""
    base = os.environ.get("MPFB_DATA") or servicio("locationservice").LocationService.get_user_data()
    return os.path.join(base, sub) if sub else base


def asset(ruta_relativa):
    """Ruta absoluta de un asset del pack, p. ej. asset("hair/short02/short02.mhclo"). Falla con un mensaje útil."""
    p = os.path.join(datos(), ruta_relativa)
    if not os.path.exists(p):
        carpeta = os.path.dirname(p)
        hay = sorted(os.listdir(os.path.dirname(carpeta))) if os.path.isdir(os.path.dirname(carpeta)) else []
        raise FileNotFoundError(f"No existe {p}. ¿Está instalado el pack de assets? Disponibles ahí: {hay[:30]}")
    return p


def mhclo(tipo_carpeta, nombre):
    """Ruta del .mhclo de un asset por carpeta y nombre: mhclo("hair", "short02"), mhclo("eyes", "low-poly")."""
    carpeta = os.path.join(datos(), tipo_carpeta, nombre)
    if os.path.isdir(carpeta):
        for f in sorted(os.listdir(carpeta)):
            if f.endswith(".mhclo"):
                return os.path.join(carpeta, f)
    return asset(os.path.join(tipo_carpeta, nombre, nombre + ".mhclo"))


def difuso_de_piel(nombre="young_caucasian_male"):
    """PNG difuso de una piel del pack (`skins/<nombre>/*diffuse*.png`)."""
    carpeta = datos(os.path.join("skins", nombre))
    if not os.path.isdir(carpeta):
        disp = sorted(os.listdir(datos("skins"))) if os.path.isdir(datos("skins")) else []
        raise FileNotFoundError(f"No existe la piel {nombre}. Disponibles: {disp}")
    for f in sorted(os.listdir(carpeta)):
        if f.lower().endswith(".png") and "diffuse" in f.lower():
            return os.path.join(carpeta, f)
    raise FileNotFoundError(f"La piel {nombre} no tiene un PNG difuso en {carpeta}")


def argumentos():
    """Lo que viene después de `--` en la línea de comandos de Blender."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def limpiar_escena():
    """Borra todo lo de la escena (el cubo, la luz y la cámara de la escena de inicio, o lo que haya)."""
    import bpy
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
