# Preparar la máquina: Blender + MPFB + assets

Verificá primero con `blender -b --python scripts/verificar.py`; hacé solo los pasos que dicen `FALTA`.

## 1. Blender

- Versión ≥ 4.2 (por la plataforma de extensiones). Probado con 5.0.1 y 5.1.2.
- Ejecutable típico:
  - Windows: `C:\Program Files\Blender Foundation\Blender <X.Y>\blender.exe` (o `winget install BlenderFoundation.Blender`)
  - macOS: `/Applications/Blender.app/Contents/MacOS/Blender`
  - Linux: `blender` en el PATH, o `/snap/bin/blender`, o la carpeta del tar.xz descargado
- Si hay varias versiones instaladas, preguntale al usuario cuál usa: cada versión tiene su propia carpeta de usuario
  (add-ons y assets se instalan **por versión**).
- Descarga oficial: https://www.blender.org/download/

## 2. MPFB (el add-on de MakeHuman)

Forma recomendada, desde la plataforma oficial de extensiones (https://extensions.blender.org/add-ons/mpfb/):
```
blender -b -c extension install mpfb --sync --enable
```
Queda como `bl_ext.blender_org.mpfb`. Ayuda del comando: `docref/blender/cli.md` o
https://docs.blender.org/manual/en/latest/advanced/command_line/extension_arguments.html

Alternativa con un zip (por ejemplo un build nocturno de https://files2.makehumancommunity.org/plugins/):
```
blender -b -c extension install-file -r user_default --enable <mpfb2-AAAAMMDD.zip>
```
Queda como `bl_ext.user_default.mpfb`. El FAQ de MPFB (https://static.makehumancommunity.org/mpfb/faq/index.html)
recomienda el nocturno cuando la versión estable está vieja.

Comprobar: `blender -b --python scripts/verificar.py` → `OK MPFB <versión>`.

## 3. Pack de assets del sistema (CC0)

Ojos, cejas, pestañas, dientes, lengua, pelos, ropa, zapatos y pieles. Sin esto, MPFB solo arma el cuerpo.
Página oficial: https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html

```
blender -b --python scripts/instalar_assets.py -- --descargar <carpeta_para_el_zip>    # baja ~281 MB
blender -b --python scripts/instalar_assets.py -- <makehuman_system_assets_cc0.zip>    # si ya está el zip
```
- **Pedí permiso antes de descargar** (tamaño y origen).
- Recomendá guardar el zip fuera de la PC: la comunidad de MakeHuman anunció en octubre de 2026 que cerraba sus
  servicios y el enlace puede caerse.
- La carpeta de datos la decide MPFB (`LocationService.get_user_data()`), por ejemplo en Windows con Blender 5.1:
  `%APPDATA%\Blender Foundation\Blender\5.1\extensions\.user\blender_org\mpfb\data\`. Si el usuario la tiene en otro
  lado, `MPFB_DATA=<carpeta data>` la pisa para los scripts de esta skill.

Packs opcionales (no los instala esta skill): `faceunits01` trae las 52 expresiones ARKit para `FaceService`.
`verificar.py` avisa si está.

## 4. Referencia local

```
blender -b --python scripts/docref.py -- <proyecto>/docref
```
Regenerala cada vez que cambie la versión de Blender o de MPFB (el script no hace nada si ya está al día; `--forzar`
la rehace).

## Python del sistema (opcional)

Solo para usar `mapas.py` fuera de Blender: Python 3 con `numpy` (y `Pillow` para leer/escribir PNG). En Windows,
`python` no entiende rutas estilo Git Bash (`/c/Users/...`): usar `C:/Users/...`.
