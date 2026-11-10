# Trampas conocidas

## Blender sin interfaz

- **`--factory-startup` apaga los add-ons**: MPFB se importa a medias y sus servicios fallan con
  `TypeError: 'NoneType' object is not subscriptable` en `logservice.py`. Usarlo solo para comandos que no tocan MPFB
  (por ejemplo `-c extension --help`).
- Los argumentos propios van después de `--`: `blender -b archivo.blend --python s.py -- a b`. El `.blend` va **antes**
  de `--python`.
- La escena de inicio trae cubo, luz y cámara: `mpfb_util.limpiar_escena()`.
- Muchos operadores dependen del objeto activo y la selección: fijarlos explícitamente antes de cada `bpy.ops`
  (`view_layer.objects.active = o`, `o.select_set(True)`).
- Aplicar un modificador que no es el primero de la pila (por ejemplo un Decimate debajo del Armature) da un resultado
  distinto del esperado (Blender avisa "not first"): moverlo arriba con `modifier_move_up` o aplicarlo antes de agregar
  el Armature.
- Blender termina con `Error: Not freed memory blocks` en algunas corridas: es ruido de salida, no un fallo.

## MPFB

- El módulo cambia según cómo se instaló: `bl_ext.blender_org.mpfb` (plataforma de extensiones) o
  `bl_ext.user_default.mpfb` (zip). Nunca escribirlo fijo: `mpfb_util.raiz()`.
- La carpeta de datos también cambia (por versión de Blender y por repositorio): preguntársela a
  `LocationService.get_user_data()` (`mpfb_util.datos()`), o `MPFB_DATA`.
- `target_full_path("head/head-oval")` devuelve `None`: el nombre va sin carpeta.
- Decimar **antes** de agregar assets rompe el ajuste de la ropa y el pelo: decimar al final.
- `h.dimensions` incluye la geometría auxiliar oculta por el Mask: medir la malla evaluada.
- Tras borrar el cuerpo de abajo de la ropa, medir la altura con todas las mallas, no con el cuerpo.
- Los assets traen Subdivision: en un juego se saca (o el FBX exporta la malla subdividida).
- El importador de glTF de Blender agrega una `Icosphere` en la colección `glTF_not_exported` (forma de los huesos):
  no es parte del modelo.

## Windows

- El Python de Windows no entiende rutas estilo Git Bash (`/c/Users/...`): usar `C:/Users/...`.
- Guardar los scripts en **UTF-8**: con acentos o ñ en otra codificación, Blender falla con
  `SyntaxError: (unicode error)`. Si un script edita otro, abrir con `encoding="utf-8"`.
- En PowerShell las variables de entorno se definen con `$env:NOMBRE = "valor"` antes del comando.

## Texturas

- `Image.pixels` es lento elemento a elemento: usar `foreach_get/foreach_set` con arreglos de numpy.
- Una imagen nueva de Blender es sRGB por defecto: los mapas de datos (normal, máscara, AO) van en **Non-Color**.
- Blender no trae scipy: `mapas.py` desenfoca por FFT con numpy puro.
