"""JSON versionado con validación estricta y reemplazo atómico."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from .tareas import Estado, Tarea

PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DATOS = PROYECTO / "data" / "tareas.json"


class ErrorAlmacenamiento(Exception):
    """Datos inválidos o fallo de acceso al archivo local."""


def _ruta_local(ruta: Path) -> Path:
    destino = Path(ruta).resolve()
    if not destino.is_relative_to(PROYECTO):
        raise ErrorAlmacenamiento("El archivo debe estar dentro del proyecto.")
    return destino


def _validar(datos: object) -> Estado:
    if not isinstance(datos, dict) or set(datos) != {
        "version", "siguiente_id", "tareas"
    }:
        raise ValueError("Estructura JSON inválida.")
    if type(datos["version"]) is not int or datos["version"] != 1:
        raise ValueError("Versión JSON incompatible.")
    siguiente = datos["siguiente_id"]
    if type(siguiente) is not int or siguiente <= 0:
        raise ValueError("Contador de IDs inválido.")
    if not isinstance(datos["tareas"], list):
        raise ValueError("La colección de tareas debe ser una lista.")
    tareas = []
    ids = set()
    for fila in datos["tareas"]:
        if not isinstance(fila, dict) or set(fila) != {
            "id", "titulo", "completada"
        }:
            raise ValueError("Estructura de tarea inválida.")
        tarea_id = fila["id"]
        titulo = fila["titulo"]
        if type(tarea_id) is not int or tarea_id <= 0 or tarea_id in ids:
            raise ValueError("IDs inválidos o duplicados.")
        if not isinstance(titulo, str) or not titulo.strip():
            raise ValueError("Título inválido.")
        if type(fila["completada"]) is not bool:
            raise ValueError("Estado de tarea inválido.")
        ids.add(tarea_id)
        tareas.append(Tarea(**fila))
    if siguiente <= max(ids, default=0):
        raise ValueError("El siguiente ID debe superar los IDs existentes.")
    return Estado(tareas, siguiente)


def cargar_estado(ruta: Path = RUTA_DATOS) -> Estado:
    """Un archivo ausente representa un estado vacío; no se crea al leer."""
    try:
        destino = _ruta_local(ruta)
        try:
            contenido = destino.read_text(encoding="utf-8")
        except FileNotFoundError:
            return Estado()
        return _validar(json.loads(contenido))
    except (OSError, ValueError, RuntimeError) as error:
        raise ErrorAlmacenamiento(f"No se pudieron cargar las tareas: {error}") from error


def guardar_estado(ruta: Path, estado: Estado) -> None:
    """Valida antes de escribir y conserva el destino si falla el reemplazo.

    No proporciona bloqueo entre procesos ni garantiza recuperación ante una
    pérdida de alimentación; el uso concurrente no está soportado.
    """
    temporal = None
    try:
        destino = _ruta_local(ruta)
        datos = {"version": 1, "siguiente_id": estado.siguiente_id,
                 "tareas": [asdict(tarea) for tarea in estado.tareas]}
        _validar(datos)
        contenido = json.dumps(datos, ensure_ascii=False, indent=2) + "\n"
        destino.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destino.parent,
            prefix=".tareas-", suffix=".tmp", delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, destino)
    except (OSError, ValueError, RuntimeError) as error:
        raise ErrorAlmacenamiento(f"No se pudieron guardar las tareas: {error}") from error
    finally:
        if temporal is not None:
            try:
                temporal.unlink(missing_ok=True)
            except OSError as error:
                raise ErrorAlmacenamiento(
                    f"No se pudo limpiar el archivo temporal: {error}"
                ) from error
