"""Interfaz de comandos; solo anuncia éxito después de persistir."""

import argparse
import sys

from .almacenamiento import (
    RUTA_DATOS, ErrorAlmacenamiento, cargar_estado, guardar_estado,
)
from .tareas import (
    agregar_tarea, completar_tarea, eliminar_tarea, listar_tareas,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gestor local de tareas")
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("agregar", help="Agregar una tarea").add_argument("titulo")
    comandos.add_parser("listar", help="Listar todas las tareas")
    for nombre in ("completar", "eliminar"):
        comandos.add_parser(nombre, help=f"{nombre.capitalize()} una tarea").add_argument(
            "id", type=int
        )
    argumentos = parser.parse_args(argv)
    try:
        estado = cargar_estado(RUTA_DATOS)
        if argumentos.comando == "listar":
            tareas = listar_tareas(estado)
            if not tareas:
                print("No hay tareas")
            for tarea in tareas:
                marca = "x" if tarea.completada else " "
                print(f"{tarea.id}. [{marca}] {tarea.titulo}")
            return 0
        if argumentos.comando == "agregar":
            tarea = agregar_tarea(estado, argumentos.titulo)
            mensaje = f"Tarea {tarea.id} agregada."
        elif argumentos.comando == "completar":
            tarea = completar_tarea(estado, argumentos.id)
            mensaje = f"Tarea {tarea.id} completada."
        else:
            tarea = eliminar_tarea(estado, argumentos.id)
            mensaje = f"Tarea {tarea.id} eliminada."
        guardar_estado(RUTA_DATOS, estado)
        print(mensaje)
        return 0
    except (ValueError, ErrorAlmacenamiento) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
