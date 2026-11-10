# Recetas de la API de MPFB que ya se probaron

Probado con MPFB 2.0.18 en Blender 5.0.1 y 5.1.2. Para firmas exactas y todo lo demás: `docref/mpfb/*.md`.
Documentación oficial: https://static.makehumancommunity.org/mpfb/docs.html y, por servicio,
https://github.com/makehumancommunity/mpfb2 (carpeta `docs/services`).

```python
import sys; sys.path.insert(0, "<skill>/scripts")
import mpfb_util
TargetService, HumanService, AssetService = mpfb_util.servicios()
```

## Cuerpo

```python
d = TargetService.get_default_macro_info_dict()          # gender, age, muscle, weight, proportions, height, cupsize, firmness, race{}
d.update(gender=1.0, age=0.5, muscle=0.45, weight=0.38, height=0.8,
         race={"asian": 0.1, "caucasian": 0.75, "african": 0.15})
h = HumanService.create_human(macro_detail_dict=d, scale=0.1)   # scale 0.1 = metros; los pies quedan en z=0
```
- `create_human` agrega un modificador **Mask** ("Hide helpers") que oculta la geometría auxiliar. Para medir la
  altura real, medí la malla **evaluada** (con el Mask), no `h.dimensions`.
- La altura es lineal con `scale`: medí, y si no es la pedida, recreá con `scale = 0.1 * objetivo / medida`.

## Targets de detalle

```python
ruta = TargetService.target_full_path("head-oval")      # nombre de archivo, SIN carpeta; None si no existe
TargetService.load_target(h, ruta, weight=0.2)
```
Hay ~1.400 en `data/targets/<categoría>/` (cara, ojos, nariz, boca, mentón, cuello, torso, panza, brazos, piernas...).
Los simétricos vienen de a pares `l-...`/`r-...`: cargar los dos.

## Rig

```python
arm = HumanService.add_builtin_rig(h, "game_engine", import_weights=True)   # None si el nombre no existe
```
Rigs incluidos: `game_engine` (53 huesos, nombres tipo UE: `pelvis`, `spine_01..03`, `upperarm_l`, `hand_r`...),
`game_engine_with_breast`, `mixamo`, `mixamo_unity`, `default`, `default_no_toes`, `cmu_mb`, `openpose`.
Los que empiezan con `rigify.` se tratan como Rigify. El rig se agrega **antes** de los assets: ellos heredan los pesos.

## Assets del pack (.mhclo)

```python
o = HumanService.add_mhclo_asset(mpfb_util.mhclo("hair", "short02"), h, asset_type="Hair", material_type="GAMEENGINE")
```
- `asset_type`: `Eyes`, `Eyebrows`, `Eyelashes`, `Hair`, `Teeth`, `Tongue`, `Clothes` (se normaliza con `capitalize`).
- `material_type="GAMEENGINE"`: material simple de Principled + texturas, el que mejor sobrevive al FBX/glTF.
  `MAKESKIN` arma el material completo de MakeHuman (bonito en Blender, no se exporta igual).
- Cada asset trae un modificador **Subdivision**: sacarlo antes de exportar (`exportar.py` lo hace).
- La ropa marca en el cuerpo un grupo `Delete.<prenda>` y le pone un Mask: lo de abajo de la ropa se puede borrar de
  verdad (`humano.borrar_bajo_ropa`).
- Ojos `low-poly` (172 tris) para juego; `high-poly` para primeros planos.

## Piel

```python
HumanService.set_character_skin(mhmat, h, skin_type="GAMEENGINE")   # mhmat = data/skins/<piel>/<piel>.mhmat
```
O, para más control (lo que hace `humano.py`): leer el difuso de `skins/<piel>/*diffuse*.png`, teñirlo con numpy y
armar un Principled propio con `calidad.piel_base()` + `calidad.mapas_piel()`.
Pieles del pack: `young|middleage|old` × `african|asian|caucasian` × `male|female`, más algunas especiales
(ver `docref/mpfb/datos.md`).

## Limpieza para juego

`calidad.limpiar_cuerpo(h)`: aplica los shape keys (`shape_key_remove(all=True, apply_mix=True)`) y borra los vértices
de los grupos `HelperGeometry` y `JointCubes`. Hacerlo **después** de agregar rig y assets.

## Expresiones de la cara (no probado con esta skill)

`FaceService` (`mpfb_util.servicio("faceservice").FaceService`) carga las 52 unidades ARKit y visemas como shape keys
(`load_targets`, `set_expression`), pero necesita el pack `faceunits01`. Con eso el personaje puede exportarse con blend
shapes de cara, que el rig `game_engine` no tiene. Leer `docref/mpfb/faceservice.md` antes de usarlo y verificar el
resultado: esta skill todavía no lo probó.

## Guardar y cargar humanos

`HumanService.serialize_to_json_file(h, ruta)` / `deserialize_from_json_file(ruta, settings)` y `deserialize_from_mhm`
(archivos de MakeHuman 1.x). Ver `docref/mpfb/humanservice.md`.
