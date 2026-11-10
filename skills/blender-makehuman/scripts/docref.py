# Blender AI Tools by Marcos Alvarez — https://www.caldengames.com · GPL-3.0-or-later (ver NOTICE y LICENSE)
"""Genera `docref/`: la referencia de la API del Blender y del MPFB que están INSTALADOS en esta máquina, en Markdown.

La idea es no depender de lo que el agente "se acuerda": las firmas y docstrings salen del propio Blender y del propio
MPFB, así que coinciden exactamente con la versión que se va a usar.

Uso:
    blender -b --python docref.py -- <carpeta_docref> [--forzar]

Genera:
    VERSIONES.md            versión de Blender y de MPFB con la que se generó (si coincide, no se regenera)
    ENLACES.md              documentación oficial online de esas versiones
    blender/cli.md          `blender --help` y `blender -c extension --help` (y sus subcomandos)
    blender/ops/<cat>.md    todos los operadores bpy.ops.<cat>.* con parámetros, tipos y valores por defecto
    blender/types/<T>.md    propiedades y funciones de los tipos que más se usan en un pipeline de personajes
    mpfb/<servicio>.md      todos los servicios de MPFB (HumanService, TargetService...) con firmas y docstrings
    mpfb/datos.md           qué assets, rigs y targets hay instalados
"""
import inspect
import os
import subprocess
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpfb_util  # noqa: E402

TIPOS = [
    "Object", "Mesh", "MeshVertex", "MeshPolygon", "MeshLoopTriangle", "MeshUVLoopLayer", "VertexGroup", "ShapeKey", "Key",
    "Armature", "Bone", "EditBone", "PoseBone", "Action", "Material", "ShaderNodeTree", "ShaderNodeTexImage",
    "ShaderNodeBsdfPrincipled", "ShaderNodeNormalMap", "Image", "Scene", "RenderSettings", "BakeSettings", "CyclesRenderSettings",
    "Camera", "World", "ViewLayer", "Collection", "BlendData", "Modifier", "ArmatureModifier", "DecimateModifier",
    "DataTransferModifier", "SolidifyModifier", "SubsurfModifier", "MaskModifier", "CorrectiveSmoothModifier",
]
OPS_PRIORIDAD = ["export_scene", "import_scene", "object", "mesh", "wm", "file", "render", "pose", "armature", "image", "extensions",
                 "preferences", "uv", "material", "outliner"]


def escribir(ruta, texto):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


def version_mpfb():
    try:
        return mpfb_util.version(), mpfb_util.raiz()
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def firma_versiones():
    vm, raiz = version_mpfb()
    return f"blender {bpy.app.version_string}\nmpfb {vm or 'no instalado'} ({raiz})\n"


# ---------- Blender ----------

def cli():
    exe = bpy.app.binary_path
    partes = ["# Línea de comandos de Blender\n", f"Generado con `{exe}`.\n"]
    comandos = [["--help"], ["-c", "extension", "--help"]]
    for sub in ("install", "install-file", "list", "sync", "update", "remove", "repo-list", "repo-add"):
        comandos.append(["-c", "extension", sub, "--help"])
    for c in comandos:
        try:
            r = subprocess.run([exe, "-b", "--factory-startup", *c], capture_output=True, text=True, timeout=60,
                               encoding="utf-8", errors="replace")
            salida = (r.stdout or "") + (r.stderr or "")
        except Exception as e:  # noqa: BLE001
            salida = f"(no se pudo correr: {e})"
        partes.append(f"\n## `blender {' '.join(c)}`\n\n```text\n{salida.strip()}\n```\n")
    return "".join(partes)


def describir_prop(p):
    tipo = p.type
    extra = []
    if tipo == "ENUM":
        items = [i.identifier for i in p.enum_items] if p.enum_items else []
        extra.append(("valores: " + ", ".join(f"`{i}`" for i in items[:40]) + (" …" if len(items) > 40 else ""))
                     if items else "valores dinámicos (dependen del contexto)")
        if getattr(p, "is_enum_flag", False):
            tipo = "ENUM (conjunto)"
    elif tipo in ("POINTER", "COLLECTION"):
        extra.append(f"de `{p.fixed_type.identifier}`" if p.fixed_type else "")
    if tipo in ("INT", "FLOAT") and getattr(p, "array_length", 0):
        tipo += f"[{p.array_length}]"
    try:
        if p.type == "ENUM" and not p.enum_items:
            raise ValueError("enum dinámico: sus opciones se calculan al usarlo, no tiene un default fijo")
        if p.type == "ENUM" and getattr(p, "is_enum_flag", False):
            d = set(p.default_flag)
        else:
            d = p.default_array[:] if getattr(p, "array_length", 0) else p.default
        extra.insert(0, f"por defecto `{d!r}`")
    except Exception:  # noqa: BLE001
        pass
    if getattr(p, "is_readonly", False):
        extra.append("solo lectura")
    desc = (p.description or "").replace("\n", " ")
    return f"- `{p.identifier}` ({tipo}) {desc} " + ("— " + "; ".join(x for x in extra if x) if any(extra) else "")


def ops():
    salidas = {}
    for cat in sorted(dir(bpy.ops)):
        if cat.startswith("_"):
            continue
        modulo = getattr(bpy.ops, cat)
        lineas = [f"# bpy.ops.{cat}\n\nBlender {bpy.app.version_string}. Parámetros tal como los expone esta instalación.\n"]
        for nombre in sorted(dir(modulo)):
            if nombre.startswith("_"):
                continue
            try:
                op = getattr(modulo, nombre)
                rna = op.get_rna_type()
            except Exception:  # noqa: BLE001
                continue
            lineas.append(f"\n## `bpy.ops.{cat}.{nombre}()`\n\n{(rna.description or '').strip()}\n")
            props = [p for p in rna.properties if p.identifier != "rna_type"]
            if props:
                lineas.append("\n" + "\n".join(describir_prop(p) for p in props) + "\n")
        salidas[cat] = "".join(lineas)
    return salidas


def tipos():
    salidas = {}
    for t in TIPOS:
        cls = getattr(bpy.types, t, None)
        if cls is None:
            continue
        rna = cls.bl_rna
        base = rna.base.identifier if rna.base else None
        lineas = [f"# bpy.types.{t}\n\nBlender {bpy.app.version_string}." + (f" Hereda de `{base}`." if base else "") +
                  f"\n\n{(rna.description or '').strip()}\n\n## Propiedades\n\n"]
        lineas.append("\n".join(describir_prop(p) for p in rna.properties if p.identifier != "rna_type") + "\n")
        funcs = list(rna.functions)
        if funcs:
            lineas.append("\n## Funciones\n")
            for f in funcs:
                params = ", ".join(p.identifier for p in f.parameters if not p.is_output)
                lineas.append(f"\n### `{f.identifier}({params})`\n\n{(f.description or '').strip()}\n")
                for p in f.parameters:
                    lineas.append(describir_prop(p) + (" **(salida)**" if p.is_output else "") + "\n")
        salidas[t] = "".join(lineas)
    return salidas


# ---------- MPFB ----------

def mpfb_servicios():
    import importlib
    import pkgutil
    raiz = mpfb_util.raiz()
    paquete = importlib.import_module(f"{raiz}.services")
    salidas = {}
    for info in pkgutil.iter_modules(paquete.__path__):
        try:
            mod = importlib.import_module(f"{raiz}.services.{info.name}")
        except Exception as e:  # noqa: BLE001
            salidas[info.name] = f"# {info.name}\n\nNo se pudo importar: {e}\n"
            continue
        lineas = [f"# MPFB {mpfb_util.version()} · services/{info.name}.py\n\n"
                  f"Importar: `from {raiz}.services.{info.name} import ...` (o `mpfb_util.servicio(\"{info.name}\")`).\n"]
        if mod.__doc__:
            lineas.append(f"\n{inspect.cleandoc(mod.__doc__)}\n")
        for nombre, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ != mod.__name__:
                continue
            lineas.append(f"\n## class `{nombre}`\n")
            if cls.__doc__:
                lineas.append(f"\n{inspect.cleandoc(cls.__doc__)}\n")
            for mn, m in inspect.getmembers(cls):
                if mn.startswith("_"):
                    continue
                f = m.__func__ if isinstance(m, (staticmethod, classmethod)) else m
                if not callable(f):
                    continue
                try:
                    sig = str(inspect.signature(f))
                except (TypeError, ValueError):
                    sig = "(...)"
                lineas.append(f"\n### `{nombre}.{mn}{sig}`\n")
                doc = inspect.getdoc(f)
                if doc:
                    lineas.append(f"\n{doc}\n")
        # objetos sueltos del módulo (p. ej. LocationService = _LocationService())
        for nombre, obj in vars(mod).items():
            if not nombre.startswith("_") and not inspect.isclass(obj) and not inspect.ismodule(obj) and \
                    type(obj).__module__ == mod.__name__:
                lineas.append(f"\n## instancia `{nombre}` (de `{type(obj).__name__}`)\n")
        salidas[info.name] = "".join(lineas)
    return salidas


def mpfb_datos():
    lineas = [f"# Assets, rigs y targets instalados (MPFB {mpfb_util.version()})\n"]
    try:
        d = mpfb_util.datos()
    except Exception as e:  # noqa: BLE001
        return lineas[0] + f"\nNo se encontró la carpeta de datos: {e}\n"
    lineas.append(f"\nCarpeta de datos del usuario: `{d}`\n")
    for sub in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        p = os.path.join(d, sub)
        if os.path.isdir(p):
            hijos = sorted(x for x in os.listdir(p) if not x.startswith("."))
            lineas.append(f"\n## {sub} ({len(hijos)})\n\n" + ", ".join(f"`{x}`" for x in hijos) + "\n")
    sistema = os.path.join(os.path.dirname(importlib_file(mpfb_util.raiz())), "data")
    rigs = os.path.join(sistema, "rigs", "standard")
    if os.path.isdir(rigs):
        nombres = sorted(f[4:-5] for f in os.listdir(rigs) if f.startswith("rig.") and f.endswith(".json"))
        lineas.append("\n## Rigs incluidos (`HumanService.add_builtin_rig(h, <nombre>)`)\n\n" + ", ".join(f"`{n}`" for n in nombres) + "\n")
    tg = os.path.join(sistema, "targets")
    if os.path.isdir(tg):
        lineas.append("\n## Targets incluidos (nombre = archivo sin carpeta ni `.target.gz`)\n")
        for cat in sorted(os.listdir(tg)):
            pc = os.path.join(tg, cat)
            if os.path.isdir(pc) and not cat.startswith("_"):
                ns = sorted(f.split(".target")[0] for f in os.listdir(pc) if ".target" in f)
                lineas.append(f"\n### {cat} ({len(ns)})\n\n" + ", ".join(f"`{n}`" for n in ns) + "\n")
    return "".join(lineas)


def importlib_file(mod):
    import importlib
    return importlib.import_module(mod).__file__


def enlaces():
    v = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
    vm, _ = version_mpfb()
    return f"""# Documentación oficial online

Versión instalada: Blender {bpy.app.version_string}, MPFB {vm or 'no instalado'}. Si algo de acá contradice a `docref/`,
manda `docref/` (es lo que está instalado).

## Blender {v}

- API de Python: https://docs.blender.org/api/{v}/
- Manual: https://docs.blender.org/manual/en/{v}/
- Argumentos de línea de comandos: https://docs.blender.org/manual/en/{v}/advanced/command_line/arguments.html
- Extensiones por línea de comandos: https://docs.blender.org/manual/en/{v}/advanced/command_line/extension_arguments.html
- Trucos de la API (correr sin interfaz, contexto): https://docs.blender.org/api/{v}/info_tips_and_tricks.html

## MPFB (MakeHuman para Blender)

- Documentación: https://static.makehumancommunity.org/mpfb/docs.html
- Primeros pasos: https://static.makehumancommunity.org/mpfb/docs/getting_started.html
- Preguntas frecuentes: https://static.makehumancommunity.org/mpfb/faq/index.html
- Código fuente y documentación de cada servicio: https://github.com/makehumancommunity/mpfb2 (carpeta `docs/services`)
- En la plataforma de extensiones de Blender: https://extensions.blender.org/add-ons/mpfb/
- Pack de assets del sistema (CC0): https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html
- Descarga directa de packs: https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/

> La comunidad de MakeHuman anunció en octubre de 2026 que cerraba sus servicios. Si los sitios de
> makehumancommunity.org no responden, el código y la documentación siguen en GitHub, y la referencia local de `docref/`
> no depende de ellos.
"""


def main():
    args = mpfb_util.argumentos()
    salida = os.path.abspath(next((a for a in args if not a.startswith("--")), "docref"))
    forzar = "--forzar" in args
    firma = firma_versiones()
    marca = os.path.join(salida, "VERSIONES.md")
    if not forzar and os.path.exists(marca) and firma in open(marca, encoding="utf-8").read():
        print("DOCREF al día:", salida)
        return
    escribir(os.path.join(salida, "ENLACES.md"), enlaces())
    escribir(os.path.join(salida, "blender", "cli.md"), cli())
    o = ops()
    for cat, txt in o.items():
        escribir(os.path.join(salida, "blender", "ops", f"{cat}.md"), txt)
    t = tipos()
    for nombre, txt in t.items():
        escribir(os.path.join(salida, "blender", "types", f"{nombre}.md"), txt)
    s = {}
    try:
        s = mpfb_servicios()
        for nombre, txt in s.items():
            escribir(os.path.join(salida, "mpfb", f"{nombre}.md"), txt)
        escribir(os.path.join(salida, "mpfb", "datos.md"), mpfb_datos())
    except ImportError as e:
        escribir(os.path.join(salida, "mpfb", "NO_INSTALADO.md"), f"# MPFB no está instalado\n\n{e}\n")
    indice = [f"# docref\n\nReferencia generada de lo instalado en esta máquina. No editar a mano: se regenera con\n"
              f"`blender -b --python docref.py -- <esta carpeta> --forzar`.\n\n```text\n{firma}```\n",
              "\n- `ENLACES.md`: documentación oficial online de estas versiones",
              "\n- `blender/cli.md`: línea de comandos y extensiones",
              f"\n- `blender/ops/`: {len(o)} categorías de operadores (prioridad: " + ", ".join(c for c in OPS_PRIORIDAD if c in o) + ")",
              f"\n- `blender/types/`: {len(t)} tipos",
              f"\n- `mpfb/`: {len(s)} servicios + `datos.md` (assets, rigs, targets instalados)\n"]
    escribir(marca, "".join(indice))
    print("DOCREF generado en", salida, "| ops", len(o), "| tipos", len(t), "| servicios MPFB", len(s))


main()
