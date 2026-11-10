"""Instala el pack de assets del sistema de MakeHuman (CC0: ojos, cejas, pestañas, dientes, pelos, ropa, pieles) en MPFB.

Uso (MPFB ya instalado y habilitado):
    blender -b --python instalar_assets.py -- <makehuman_system_assets_cc0.zip>
    blender -b --python instalar_assets.py -- --descargar <carpeta_donde_guardar_el_zip>

`--descargar` baja el zip oficial (~281 MB) y después lo instala. El zip conviene guardarlo: la comunidad de MakeHuman
anunció el cierre de sus servicios en octubre de 2026 y el enlace podría dejar de responder.
La extracción la hace el propio MPFB (`AssetService.fix_and_extract_asset_pack_zip`), igual que el botón de su panel.
"""
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpfb_util  # noqa: E402

URL = "https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip"


def descargar(carpeta):
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, os.path.basename(URL))
    if os.path.exists(destino) and os.path.getsize(destino) > 100_000_000:
        print("ZIP ya descargado:", destino)
        return destino
    print("Descargando", URL)
    req = urllib.request.Request(URL, headers={"User-Agent": "blender-makehuman-skill"})
    with urllib.request.urlopen(req, timeout=60) as r, open(destino + ".parcial", "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        leido = 0
        while True:
            bloque = r.read(1 << 20)
            if not bloque:
                break
            f.write(bloque)
            leido += len(bloque)
            if total and leido % (20 << 20) < (1 << 20):
                print(f"  {leido >> 20} / {total >> 20} MB")
    os.replace(destino + ".parcial", destino)
    return destino


def main():
    args = mpfb_util.argumentos()
    if not args:
        raise SystemExit(__doc__)
    zip_ = descargar(args[1] if len(args) > 1 else ".") if args[0] == "--descargar" else os.path.abspath(args[0])
    AS = mpfb_util.servicio("assetservice").AssetService
    problema = AS.check_asset_pack_zip(zip_)
    if problema not in (None, "STRUCTURE", "MACOS"):
        raise SystemExit(f"El zip no parece un pack de MakeHuman: {problema}")
    destino = mpfb_util.datos()
    print("Extrayendo en", destino)
    error = AS.fix_and_extract_asset_pack_zip(zip_, destino)
    if error:
        raise SystemExit(f"Falló la extracción: {error}")
    AS.update_all_asset_lists()
    AS.rescan_pack_metadata()
    print("PACKS instalados:", AS.get_pack_names())
    print("OK sistema:", AS.system_assets_pack_is_installed())


main()
