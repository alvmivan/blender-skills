---
name: blender-makehuman
description: Crear y exportar humanoides para juegos con MakeHuman (add-on MPFB 2) dentro de Blender, todo por script y sin interfaz. Instala y verifica Blender + MPFB + el pack de assets CC0, arma personajes desde una ficha JSON (cuerpo, targets de cara, rig game_engine/mixamo, ojos, pelo, ropa, piel), decima protegiendo la cara, hornea normal y AO, y exporta FBX para Unity o GLB para Godot. Usar siempre que el pedido mencione MakeHuman, MPFB, "humano/humanoide/personaje/NPC 3D en Blender", crear personajes para un juego con Blender, riggear un humano para Unity/Godot, o automatizar Blender por línea de comandos (blender -b --python) para personajes, aunque no se nombre la skill. Also for English requests - MakeHuman, MPFB, Blender character pipeline, game-ready humanoid.
---

# Blender + MakeHuman (MPFB) para juegos

Todo corre con **Blender sin interfaz** (`blender -b --python script.py -- args`). Las rutas de los scripts son
relativas a la carpeta de esta skill (`scripts/`, `references/`, `ejemplos/`).

## Regla 1: no adivinar la API, consultar `docref/`

Las firmas de Blender y de MPFB cambian entre versiones. Antes de escribir código `bpy` o de MPFB que no esté en estos
scripts:

1. Buscá `docref/VERSIONES.md` en la raíz del proyecto del usuario. Si no existe, o la versión que dice no coincide con
   la de `scripts/verificar.py`, regenerala (tarda unos 20 s, pesa unos 2 MB):
   ```
   blender -b --python scripts/docref.py -- <proyecto>/docref
   ```
   `docref/` sale del Blender y del MPFB **instalados** (firmas y docstrings reales). Sugerí agregarla al `.gitignore`
   del proyecto: depende de cada máquina.
2. Buscá ahí con grep: `docref/mpfb/humanservice.md`, `docref/mpfb/targetservice.md`, `docref/mpfb/datos.md` (qué
   assets, rigs y targets hay de verdad), `docref/blender/ops/export_scene.md`, `docref/blender/types/BakeSettings.md`, etc.
3. Para lo conceptual, la documentación oficial está en `docref/ENLACES.md` (con la versión justa del usuario):
   - MPFB: https://static.makehumancommunity.org/mpfb/docs.html · código y docs por servicio: https://github.com/makehumancommunity/mpfb2
   - Blender: `https://docs.blender.org/api/<versión>/` y `https://docs.blender.org/manual/en/<versión>/`

Si algo de esta skill contradice a `docref/`, gana `docref/`. Si no lo encontrás en ninguno de los dos, decilo en vez
de inventarlo.

## Flujo

### 1. Entorno (una vez por máquina)

```
blender -b --python scripts/verificar.py
```
Imprime `OK`/`FALTA` y una línea `ENTORNO {json}`. Si falta algo, seguí `references/setup.md`. En resumen:
- **Blender** ≥ 4.2 (probado en 5.0 y 5.1). Encontrar el ejecutable (`references/setup.md` tiene las rutas típicas).
- **MPFB**: `blender -b -c extension install mpfb --sync --enable` (desde la plataforma oficial de extensiones).
- **Assets** (~281 MB, CC0): `blender -b --python scripts/instalar_assets.py -- --descargar <carpeta>`.
  **Pedile permiso al usuario antes de descargar** y recomendale guardar el zip: la comunidad de MakeHuman anunció en
  octubre de 2026 que cerraba sus servicios.

### 2. Personaje desde una ficha

Copiá `ejemplos/ficha_ejemplo.json`, ajustala y corré:
```
blender -b --python scripts/humano.py -- <ficha.json> [<carpeta_salida>]
```
Tarda ~15 s. Deja `<Nombre>.blend/.fbx/.glb`, `texturas/` y `previas/*.png`, e imprime `RESUMEN {json}` (altura,
huesos, triángulos por malla, archivos). Los campos de la ficha están en `references/ficha.md`.

**Mirá siempre las previas** (`previas/<nombre>_frente.png`, `_tres_cuartos`, `_cara`) antes de decir que quedó bien, y
comparalas con la referencia si el usuario dio una. Para más vistas sobre un `.blend` ya armado:
```
blender -b <pj>.blend --python scripts/render_vistas.py -- <salida.png> frente costado espalda cara cara_costado pies
```

### 3. Verificar y exportar

```
blender -b <pj>.blend --python scripts/info_modelo.py           # o: -- <pj>.fbx / <pj>.glb
blender -b <pj>.blend --python scripts/exportar.py -- <pj>.fbx unity
```
Qué mirar: 1 armadura con los huesos esperados (`game_engine` = 53), ninguna malla sin Armature, 0 shape keys (o los
que se pidieron), texturas empaquetadas, altura correcta.

### 4. Ir más allá de la ficha

Para lo que la ficha no cubre (ropa propia, retoques de pelo, máscaras de barba pintadas, etc.), escribí un script
propio que importe los módulos de `scripts/`:
- `mpfb_util`: `servicios()`, `datos()`, `asset()`, `mhclo()`, `difuso_de_piel()`, `argumentos()`, `limpiar_escena()`.
- `calidad`: `limpiar_cuerpo()`, `decimar()`, `hornear()`, `rasterizar()`, `piel_base()`, `mapas_piel()`,
  `leer_imagen()`, `escribir_imagen()`, `publicar_texturas()`.
- `mapas` (numpy puro, sirve fuera de Blender): normal desde altura, combinar normales, máscara metal/suavidad.
- `render_vistas.render()`, `exportar.exportar()`.

Recetas de la API de MPFB que ya se probaron: `references/mpfb-api.md`. Cómo llevar el personaje a un juego (nombres
estables, versión de trabajo y publicada, presupuesto de triángulos, Unity): `references/juego.md`.

## Trampas que ya costaron horas

Lista completa en `references/trampas.md`. Las cinco que más muerden:
- **Nunca** `--factory-startup` en los scripts que usan MPFB: el add-on no se registra y los servicios fallan con
  `TypeError` en `logservice`.
- El módulo es `bl_ext.blender_org.mpfb` (plataforma de extensiones) o `bl_ext.user_default.mpfb` (instalado desde
  zip). `mpfb_util` prueba los dos; no escribas uno fijo.
- Los targets se cargan por **nombre de archivo sin carpeta**: `head-oval`, no `head/head-oval`.
- Decimar el cuerpo parejo aplasta la cara: decimá con `calidad.decimar()`, que protege la cabeza, y **después** del rig
  y los assets (ellos se ajustan a la malla completa).
- En Unity, generá el Avatar **después** de fijar la escala del modelo: si no, el Animator multiplica las posiciones y
  el personaje desaparece.

## Al terminar

Contale al usuario qué se generó (archivos, triángulos, altura), mostrá las previas, qué quedó sin verificar (por
ejemplo, la importación en el motor) y qué decisiones de diseño tomaste vos y conviene que revise.
