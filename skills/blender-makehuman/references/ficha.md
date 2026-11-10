# La ficha JSON de `humano.py`

Ejemplo completo: `ejemplos/ficha_ejemplo.json`. Todos los campos son opcionales salvo `nombre`.

| Campo | Qué es | Por defecto |
|---|---|---|
| `nombre` | Prefijo de objetos (`<Nombre>_Cuerpo`, `<Nombre>_Rig`, `<Nombre>_Pelo`...) y nombre de archivos. **Mantenerlo estable**: el motor referencia esos nombres. | `Humano` |
| `altura_m` | Altura del cuerpo en metros. Se mide y se reconstruye con la escala justa (±5 mm). Sin esto, sale la que den los macros. | — |
| `macros` | `gender` (0 mujer, 1 hombre), `age` (0,5 ≈ 25 años; 1 ≈ 90), `muscle`, `weight`, `height`, `proportions`, `cupsize`, `firmness`, todos 0–1, y `race` `{african, asian, caucasian}` (se normaliza). | 0,5 todo |
| `targets` | `{nombre: peso}` de detalle (cara, cuello, panza...). Nombre = archivo sin carpeta ni `.target.gz`. Lista en `docref/mpfb/datos.md`. Los inexistentes se avisan con `AVISO`. | — |
| `rig` | Rig incluido de MPFB: `game_engine` (53 huesos, Humanoid de Unity), `mixamo`, `mixamo_unity`, `default`, `cmu_mb`, `openpose`... `null` = sin rig. | `game_engine` |
| `assets` | Lista de `{tipo, nombre}` o `{tipo, archivo}`. `tipo`: `Eyes`, `Eyebrows`, `Eyelashes`, `Hair`, `Teeth`, `Tongue`, `Clothes`. `nombre` = carpeta del asset (`short02`); `archivo` = ruta relativa a la carpeta data. `objeto`: sufijo del objeto. `material`: `GAMEENGINE` (por defecto) o `MAKESKIN`. | — |
| `borrar_cuerpo_bajo_ropa` | Borra del cuerpo lo que la ropa marca para ocultar (grupos `Delete.<prenda>`). Ahorra triángulos y evita que la piel atraviese la ropa al animar. | `true` |
| `piel` | `{pack, tono}`: difuso del pack (`skins/<pack>`) multiplicado por `tono` RGB. Con `"modo": "mpfb"` usa la piel GAMEENGINE de MPFB (`set_character_skin`). `null` = deja la de MPFB. | `young_caucasian_male` |
| `decimar` | `{ratio, proteger}`. `ratio` sobre lo no protegido; `proteger` = peso por grupo (`head`, `neck_01`, `mano` = todos los dedos). `null` = sin decimar. | — |
| `hornear` | Normal tangente + AO de la malla completa (subdividida) sobre la decimada. Cycles CPU, segundos. | `false` |
| `tam_textura` | Lado de las texturas de piel. | 2048 |
| `decimar_dientes` | Ratio de decimación de los dientes (el asset del pack es muy denso). | 0,2 |
| `vistas` | Vistas de previsualización (`frente`, `tres_cuartos`, `costado`, `espalda`, `cara`, `cara_costado`, `cara_espalda`, `torso`, `pies`). `[]` = ninguna. | frente, tres_cuartos, cara |
| `salida` | `{carpeta, formatos: [blend, fbx, glb], motor: unity}`. La carpeta es relativa a la ficha (o el 2.º argumento). | `blend`, `fbx` |

Números de referencia (ejemplo de la ficha, Blender 5.1.2 + MPFB 2.0.18): ~24k triángulos en total, cuerpo 8,4k con
la cabeza en 7,8k, 53 huesos, ~15 s de punta a punta en CPU.
