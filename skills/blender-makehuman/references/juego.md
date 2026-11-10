# Del Blender al juego

Lo que salió de llevar tres personajes de MPFB a un juego en Unity 6 / URP.

## Versión de trabajo y versión publicada

- Iterá sobre `<nombre>-wip.blend/.fbx`, **fuera** de la carpeta de assets del motor (el motor no lo importa).
- Publicá a la carpeta del motor solo cuando el usuario aprueba, con un script (`exportar.py`), nunca a mano.
- Los nombres de huesos y de objetos tienen que ser **estables** entre publicaciones: si cambian, se rompen las
  animaciones, los prefabs y las referencias.
- Guardá en una carpeta `anterior/` la versión publicada antes de pisarla.
- Blender deja `<archivo>.blend1` al guardar: que no quede dentro de la carpeta de assets del motor.
- Reconstruir no da un resultado idéntico bit a bit (la decimación varía unas decenas de triángulos): no cambia nada
  visible, pero no lo uses para detectar cambios.

## Presupuesto de triángulos (referencias)

| Parte | Tris | Nota |
|---|---|---|
| Cuerpo de MPFB recién creado | ~37k | con la geometría auxiliar |
| Cuerpo después de `limpiar_cuerpo` | ~26,8k | |
| Cuerpo sin lo de abajo de la ropa (ejemplo) | ~16,8k | |
| Ese cuerpo con `decimar(ratio=0.5)` y cabeza protegida | ~8,4k | la cabeza conserva ~7,8k |
| Pelo del pack | 2–4k | |
| Ropa del pack (un traje) | ~7k | |
| Dientes del pack | ~7k → 1,4k con `decimar_dientes=0.2` | |
| Ojos `low-poly` | 172 | |
| Personaje completo de ejemplo | ~24k | |

## Calidad (por qué los personajes "de plástico")

Las causas que encontramos eran del pipeline, no de MakeHuman:
1. **Decimación pareja** → la cara pierde los rasgos. Solución: `calidad.decimar()` con la cabeza protegida.
2. **Piel de color plano sin normal** → plástico. Solución: el difuso del pack + normal horneada de la malla completa
   + poros desde el difuso (`calidad.mapas_piel`).
3. **Suavidad pareja** → todo brilla igual. Solución: máscara de suavidad (labios más lisos, barba más mate).
4. Hornear **antes** de agregar ropa propia (si no, la ropa tapa el rayo del horneado).

## Texturas

- Orden de filas: `Image.pixels` de Blender tiene la fila 0 **abajo**. `calidad.leer_imagen/escribir_imagen` trabajan
  en ese orden; `mapas.cargar/guardar` (PIL) en orden de imagen (fila 0 arriba). No mezclar sin invertir.
- Normal: tangente, convención OpenGL (Y+): Unity, Godot y Blender. Para Unreal (DirectX) invertir el canal verde.
- Máscara: RGBA con R = metálico y A = suavidad (la que lee URP/Lit). Unreal/Godot usan rugosidad (= 1 − suavidad).
- Mapas de normales, máscaras y AO: guardarlos como **Non-Color** en Blender y sin sRGB en el motor.
- Pelo, cejas y pestañas tienen alfa: en el motor necesitan *Alpha Clipping* (recorte), no transparencia mezclada.

## Unity

- Importar **un solo** formato (el `.fbx`); si también está el `.blend` en Assets, Unity intenta importarlo.
- Rig > **Humanoid** con el rig `game_engine`: mapea solo.
- **Fijá la escala antes de generar el Avatar.** Si se genera el Avatar y después se cambia la escala, el Animator
  multiplica las posiciones (en un caso, por un millón) y el personaje desaparece de la escena.
- El FBX trae las texturas embebidas: extraerlas (*Materials > Extract Textures*) para armar materiales propios.
- Con luces de sombra dura, la cara puede sombrearse a sí misma en escalones (*shadow acne*): subir el *normal bias*
  de la luz o desplazar la lectura de sombra en el shader.

## Personajes que vienen de otras herramientas

Lo que aprendimos con modelos generados por IA (Tripo) riggeados en AccuRIG:
- AccuRIG no tiene línea de comandos: ese paso lo hace el usuario a mano. Exportar para Unity, *Character only*,
  textura original y embebida.
- Esos FBX traen una acción `0_T-Pose` que pisa cualquier pose que pongas por script: borrala o desasignala antes de
  posar.
- El esqueleto puede quedar girado 90° respecto de la malla (en reposo no se nota; se nota al rotar huesos por script).
- Con los brazos pegados al cuerpo, el auto-rig le da al brazo parte del costado del torso ("aletas" al levantar el
  brazo): hay que devolverle esos pesos al torso.
- MPFB sigue siendo útil al lado de esas herramientas: un esqueleto consistente, proporciones exactas, variantes por
  parámetros (extras, gente de fondo) y, con `faceunits01`, expresiones de cara que un modelo generado no trae.
