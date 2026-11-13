import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gestor_tareas import cli
from gestor_tareas.almacenamiento import (
    PROYECTO, ErrorAlmacenamiento, cargar_estado,
)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory(dir=PROYECTO, prefix=".test-")
        self.addCleanup(self.directorio.cleanup)
        self.ruta = Path(self.directorio.name) / "tareas.json"

    def ejecutar(self, *argumentos):
        salida, errores = io.StringIO(), io.StringIO()
        with patch.object(cli, "RUTA_DATOS", self.ruta):
            with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
                codigo = cli.main(list(argumentos))
        return codigo, salida.getvalue(), errores.getvalue()

    def proceso(self, *argumentos):
        # Cambiar únicamente el destino de datos a un archivo aislado del proyecto.
        script = (
            "import sys; from pathlib import Path; from gestor_tareas import cli; "
            "cli.RUTA_DATOS = Path(sys.argv[1]); "
            "raise SystemExit(cli.main(sys.argv[2:]))"
        )
        return subprocess.run(
            [sys.executable, "-B", "-c", script, str(self.ruta), *argumentos],
            cwd=PROYECTO, capture_output=True, text=True, timeout=10,
        )

    def test_listar_vacio_no_crea_json(self):
        self.assertEqual(self.ejecutar("listar"), (0, "No hay tareas\n", ""))
        self.assertFalse(self.ruta.exists())

    def test_flujo_persistente_entre_procesos(self):
        pasos = [
            (("agregar", "Revisión ñ"), "Tarea 1 agregada."),
            (("agregar", "Otra"), "Tarea 2 agregada."),
            (("listar",), "1. [ ] Revisión ñ"),
            (("completar", "1"), "Tarea 1 completada."),
            (("completar", "1"), "Tarea 1 completada."),
            (("listar",), "1. [x] Revisión ñ"),
            (("eliminar", "2"), "Tarea 2 eliminada."),
            (("agregar", "Nueva"), "Tarea 3 agregada."),
        ]
        for argumentos, esperado in pasos:
            with self.subTest(argumentos=argumentos):
                resultado = self.proceso(*argumentos)
                self.assertEqual(resultado.returncode, 0, resultado.stderr)
                self.assertIn(esperado, resultado.stdout)
                self.assertEqual(resultado.stderr, "")
        estado = cargar_estado(self.ruta)
        self.assertEqual([t.id for t in estado.tareas], [1, 3])
        self.assertTrue(estado.tareas[0].completada)

    def test_errores_funcionales_no_crean_datos(self):
        for argumentos in (("agregar", " "), ("completar", "0"), ("eliminar", "99")):
            with self.subTest(argumentos=argumentos):
                codigo, salida, error = self.ejecutar(*argumentos)
                self.assertEqual(codigo, 1)
                self.assertEqual(salida, "")
                self.assertIn("Error:", error)
                self.assertFalse(self.ruta.exists())

    def test_argumentos_invalidos_y_ayuda(self):
        for argumentos in ((), ("desconocido",), ("agregar",), ("completar", "abc")):
            with self.subTest(argumentos=argumentos):
                resultado = self.proceso(*argumentos)
                self.assertEqual(resultado.returncode, 2)
                self.assertTrue(resultado.stderr)
        ayuda = subprocess.run(
            [sys.executable, "-B", "-m", "gestor_tareas", "--help"],
            cwd=PROYECTO, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(ayuda.returncode, 0, ayuda.stderr)
        self.assertIn("agregar", ayuda.stdout)
        self.assertFalse(self.ruta.exists())

    def test_json_corrupto_no_se_sobrescribe_por_comandos(self):
        self.ruta.write_text("{roto", encoding="utf-8")
        for argumentos in (("listar",), ("agregar", "A"), ("completar", "1"), ("eliminar", "1")):
            with self.subTest(argumentos=argumentos):
                self.assertEqual(self.ejecutar(*argumentos)[0], 1)
                self.assertEqual(self.ruta.read_text(encoding="utf-8"), "{roto")

    def test_fallo_guardado_no_anuncia_exito(self):
        with patch.object(cli, "guardar_estado", side_effect=ErrorAlmacenamiento("fallo")):
            self.assertEqual(self.ejecutar("agregar", "A"), (1, "", "Error: fallo\n"))

    def test_entrada_modulo_con_json_predeterminado_aislado(self):
        raiz = Path(self.directorio.name)
        shutil.copytree(PROYECTO / "gestor_tareas", raiz / "gestor_tareas")
        for argumentos in (("agregar", "A"), ("completar", "1"), ("listar",)):
            resultado = subprocess.run(
                [sys.executable, "-B", "-m", "gestor_tareas", *argumentos],
                cwd=raiz, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("1. [x] A", resultado.stdout)
        destino = raiz / "data" / "tareas.json"
        self.assertTrue(destino.exists())
        # Ejecutar el paquete desde otro cwd sin cambiar el destino de datos.
        script = (
            "import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); "
            "runpy.run_module('gestor_tareas', run_name='__main__')"
        )
        resultado = subprocess.run(
            [sys.executable, "-B", "-c", script, str(raiz), "eliminar", "1"],
            cwd=raiz / "data", capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(cargar_estado(destino).tareas, [])
        self.assertFalse((raiz / "data" / "data").exists())
