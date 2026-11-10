# Blender AI Tools by Marcos Alvarez — https://www.caldengames.com · GPL-3.0-or-later (ver NOTICE y LICENSE)
"""Chequeo rápido del entorno: Blender, MPFB, carpeta de datos, pack de assets y rigs. Sale con código 1 si falta algo.

Uso: blender -b --python verificar.py
Imprime líneas `OK ...` / `FALTA ...` y, al final, `ENTORNO {json}` para que lo lea el agente.
"""
import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpfb_util  # noqa: E402

estado = {"blender": bpy.app.version_string, "blender_exe": bpy.app.binary_path}
faltas = []
try:
    estado["mpfb"] = mpfb_util.version()
    estado["mpfb_modulo"] = mpfb_util.raiz()
    print("OK MPFB", estado["mpfb"], "en", estado["mpfb_modulo"])
except ImportError as e:
    faltas.append("mpfb")
    print("FALTA MPFB:", e)

if "mpfb" not in faltas:
    d = mpfb_util.datos()
    estado["datos"] = d
    AS = mpfb_util.servicio("assetservice").AssetService
    sistema = AS.system_assets_pack_is_installed()
    estado["pack_sistema"] = sistema
    estado["packs"] = AS.get_pack_names()
    estado["assets"] = {s: len(os.listdir(os.path.join(d, s))) for s in
                        ("eyes", "eyebrows", "eyelashes", "hair", "teeth", "clothes", "skins") if os.path.isdir(os.path.join(d, s))}
    if sistema:
        print("OK pack de assets del sistema en", d, estado["assets"])
    else:
        faltas.append("pack_sistema")
        print("FALTA el pack makehuman_system_assets (instalar_assets.py) en", d)
    import importlib
    rigs = os.path.join(os.path.dirname(importlib.import_module(mpfb_util.raiz()).__file__), "data", "rigs", "standard")
    estado["rigs"] = sorted(f[4:-5] for f in os.listdir(rigs) if f.startswith("rig.") and f.endswith(".json")) if os.path.isdir(rigs) else []
    print("OK rigs:", ", ".join(estado["rigs"]))
    estado["faceunits01"] = mpfb_util.servicio("targetservice").TargetService.target_full_path("cheekPuff") is not None
    print(("OK" if estado["faceunits01"] else "INFO sin") + " pack faceunits01 (expresiones ARKit)")

estado["faltan"] = faltas
print("ENTORNO", json.dumps(estado, ensure_ascii=False))
sys.exit(1 if faltas else 0)
