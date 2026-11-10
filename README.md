# Blender AI Tools by Marcos Alvarez

[caldengames.com](https://www.caldengames.com)

Una skill para Claude Code que le deja a Claude manejar **MakeHuman adentro de Blender**, todo por script, sin tocar la
interfaz. Le pedís un personaje y te lo arma: cuerpo, cara, rig, ojos, pelo, ropa, piel, y te lo exporta listo para
meterlo en el motor. 😃

Y no solo eso: **te setupea Blender**. Se fija qué tenés instalado, te instala el add-on de MakeHuman (MPFB), te baja
el pack de assets y te deja todo andando.

## ¿Qué hace?

- **Te prepara la máquina**: chequea Blender, instala MPFB desde la plataforma oficial de extensiones y el pack de
  assets CC0 (ojos, pelos, ropa, pieles...).
- **Arma personajes desde una ficha**: un JSON con altura, género, edad, músculo, rasgos de la cara, rig, pelo, ropa
  y piel. Corrés un comando y en unos 15 segundos tenés el `.blend`, el `.fbx` y el `.glb`.
- **Los deja listos para juego**: le saca la geometría que no se ve (lo de abajo de la ropa), decima el cuerpo
  **sin aplastarle la cara**, hornea normal y oclusión de la malla completa y le pone una piel con relieve en vez de
  ese color plano que queda de plástico.
- **Te muestra cómo quedó**: renders de frente, tres cuartos, costado y cara para comparar con tu referencia.
- **No "flashea"**: genera una carpeta `docref/` con la documentación de **tu** Blender y **tu** MPFB, sacada de lo que
  tenés instalado, más los enlaces a la documentación oficial. Claude consulta eso antes de inventar una función que
  no existe.

## ¿Por qué está bueno si hacés juegos con humanoides?

Porque hacer gente es carísimo. Modelar, riggear y pesar un personaje a mano son días de laburo, y si encima querés
diez NPCs distintos para un pueblo, olvidate.

Con esto:

- **Todos salen con el mismo esqueleto** (el `game_engine` de MPFB, 53 huesos): en Unity lo marcás como Humanoid y las
  mismas animaciones le sirven a todos.
- **Variás por parámetros**: más alto, más viejo, más gordo, otra cara. Ideal para extras y gente de fondo.
- **Es repetible**: el personaje es una ficha JSON, no un archivo que alguien tocó a mano y nadie sabe cómo. Lo
  reconstruís cuando quieras.
- **Los assets son CC0**, así que no tenés dramas de licencias con la ropa, el pelo o las pieles del pack.
- **Lo que aprendimos a los golpes ya está adentro**: las trampas de Blender sin interfaz, de MPFB y de la importación
  en Unity están documentadas en la skill, para que no te coman las mismas horas que a nosotros.

## Cuidado con el uncanny valley

Esto es importante, che. MakeHuman te da humanos bastante realistas, y ahí está la trampa: **un personaje casi real
pero no del todo da cosa**. Ojos un poco muertos, piel medio de cera, una cara que se mueve raro... y el jugador lo
siente aunque no sepa explicar por qué.

Si querés fotorealismo en los personajes, **andá a todo o nada**: o lo llevás hasta el final (buena piel, buenos ojos,
expresiones, animación de cara, buena luz), o te quedás del lado seguro del valle con algo más estilizado.

Lo que no conviene es quedarse a mitad de camino. Salvo que estés haciendo terror y ese "da cosa" sea justamente lo que
buscás. 😉

## Instalación

Necesitás [Claude Code](https://docs.claude.com/en/docs/claude-code) y [Blender](https://www.blender.org/download/)
4.2 o más nuevo (lo probamos con 5.0 y 5.1). MPFB y los assets te los instala la skill.

**Como plugin** (dentro de Claude Code):

```
/plugin marketplace add alvmivan/blender-skills
/plugin install blender-ai-tools@blender-ai-tools
```

**A mano**: copiá la carpeta `skills/blender-makehuman` a `~/.claude/skills/` (para todos tus proyectos) o a
`.claude/skills/` de tu proyecto.

## ¿Qué le puedo pedir?

- "Fijate si tengo todo para usar MakeHuman en Blender y si no, instalámelo."
- "Haceme un peón de campo de unos 50 años, 1,75, flaco, con barba corta y ropa de trabajo, para Unity."
- "Armame cinco extras distintos para el fondo de un pueblo, todos con el mismo rig."
- "Exportame este personaje a GLB para Godot."

## Qué hay adentro

```
skills/blender-makehuman/
  SKILL.md               lo que lee Claude: el flujo y las reglas
  scripts/
    verificar.py         chequea Blender, MPFB, assets y rigs
    instalar_assets.py   baja e instala el pack de assets CC0
    docref.py            genera docref/ con la doc de lo que tenés instalado
    humano.py            arma un personaje desde una ficha JSON
    render_vistas.py     renders de previsualización
    info_modelo.py       resumen de un .blend/.fbx/.glb (huesos, tris, texturas, altura)
    exportar.py          FBX para Unity, GLB para Godot
    calidad.py, mapas.py, mpfb_util.py   las herramientas de abajo
  references/            instalación, API de MPFB, del Blender al juego, trampas
  ejemplos/              una ficha de ejemplo
```

También lo podés usar sin Claude, a mano:

```
blender -b --python skills/blender-makehuman/scripts/humano.py -- skills/blender-makehuman/ejemplos/ficha_ejemplo.json
```

## Lo que todavía no está probado

- Unreal (el FBX debería andar, pero no lo probamos).
- Expresiones de cara con el pack `faceunits01`: MPFB las soporta, la skill todavía no.
- Instalar todo de cero en una máquina limpia. Lo armamos y probamos en Windows sobre un Blender que ya tenía MPFB;
  macOS y Linux, sin probar.

## Créditos

- [MakeHuman / MPFB](https://static.makehumancommunity.org/mpfb.html), de la comunidad de MakeHuman
  ([código](https://github.com/makehumancommunity/mpfb2)).
- [Blender](https://www.blender.org).

Hecho por Marcos Alvarez · [Calden Games](https://www.caldengames.com)
