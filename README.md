# Gestor local de tareas

Aplicación CLI con Python estándar (3.10 o superior), sin instalaciones ni red.
Desde la raíz del proyecto:

```bash
python3 -B -m gestor_tareas agregar "Preparar informe"
python3 -B -m gestor_tareas listar
python3 -B -m gestor_tareas completar 1
python3 -B -m gestor_tareas eliminar 1
python3 -B -m gestor_tareas --help
```

Los títulos se recortan y no pueden quedar vacíos. Los IDs son enteros positivos
que no se reutilizan tras eliminar. Completar una tarea ya completada es
idempotente. Listar muestra todas las tareas por ID y `[x]` indica completada.
Salida: 0 en éxito, 1 en error de datos/operación/almacenamiento y 2 en argumentos
incorrectos. Los mensajes operativos están en español; argparse puede mostrar
sus mensajes estándar en el idioma del intérprete.

## Datos y límites

`data/tareas.json` está anclado a la ubicación del proyecto, no al directorio de
invocación. Se crea al guardar la primera tarea. Listar sin archivo no crea datos.
No se permiten destinos fuera del proyecto, incluidos enlaces que resuelvan fuera.

```json
{
  "version": 1,
  "siguiente_id": 2,
  "tareas": [{"id": 1, "titulo": "Preparar informe", "completada": false}]
}
```

La carga valida versión, campos, tipos, IDs únicos y contador. Un JSON vacío,
corrupto o incompatible provoca un error y no se sobrescribe desde la CLI.
La escritura valida el estado y usa un temporal en el mismo directorio, flush,
fsync y reemplazo atómico; no anuncia éxito antes de guardar.

Uso monousuario y **una ejecución a la vez**: no hay bloqueo entre procesos,
copias de seguridad automáticas ni garantía ante pérdida de alimentación.
El JSON no está cifrado. No almacenar secretos. Los cambios manuales al JSON
deben conservar el contador para evitar reutilizar IDs históricos.

## Arquitectura

- `tareas.py`: modelos `Estado`/`Tarea` y operaciones sin acceso a archivos.
- `almacenamiento.py`: validación y persistencia JSON versionada.
- `cli.py`: argumentos, mensajes y códigos de salida.
- `__main__.py`: entrada `python3 -m gestor_tareas`.

## Pruebas

```bash
python3 -B -m unittest discover -s tests -v
```

Las pruebas usan directorios `.test-*` temporales dentro del proyecto y los
limpian al finalizar. No tocan el JSON de uso normal. Cubren lógica, persistencia,
entradas inválidas, fallos de E/S simulados y CLI entre procesos independientes.
`-B` evita generar archivos de bytecode.
