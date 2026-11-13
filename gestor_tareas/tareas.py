"""Modelo y operaciones de tareas independientes del almacenamiento."""

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Tarea:
    id: int
    titulo: str
    completada: bool = False


@dataclass
class Estado:
    tareas: list[Tarea] = field(default_factory=list)
    siguiente_id: int = 1


def agregar_tarea(estado: Estado, titulo: str) -> Tarea:
    if not isinstance(titulo, str) or not titulo.strip():
        raise ValueError("El título no puede estar vacío.")
    tarea = Tarea(estado.siguiente_id, titulo.strip())
    estado.tareas.append(tarea)
    estado.siguiente_id += 1
    return tarea


def listar_tareas(estado: Estado) -> list[Tarea]:
    return sorted(estado.tareas, key=lambda tarea: tarea.id)


def _indice(estado: Estado, tarea_id: int) -> int:
    if type(tarea_id) is not int or tarea_id <= 0:
        raise ValueError("El ID debe ser un entero positivo.")
    for indice, tarea in enumerate(estado.tareas):
        if tarea.id == tarea_id:
            return indice
    raise ValueError(f"No existe la tarea {tarea_id}.")


def completar_tarea(estado: Estado, tarea_id: int) -> Tarea:
    indice = _indice(estado, tarea_id)
    tarea = replace(estado.tareas[indice], completada=True)
    estado.tareas[indice] = tarea
    return tarea


def eliminar_tarea(estado: Estado, tarea_id: int) -> Tarea:
    return estado.tareas.pop(_indice(estado, tarea_id))
