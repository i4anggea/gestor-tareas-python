import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gestor_tareas.almacenamiento import (
    PROYECTO, ErrorAlmacenamiento, cargar_estado, guardar_estado,
)
from gestor_tareas.tareas import Estado, Tarea


class AlmacenamientoTests(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory(dir=PROYECTO, prefix=".test-")
        self.addCleanup(self.directorio.cleanup)
        self.ruta = Path(self.directorio.name) / "data" / "tareas.json"

    def test_ausente_no_crea_archivo_ni_directorio(self):
        self.assertEqual(cargar_estado(self.ruta), Estado())
        self.assertFalse(self.ruta.parent.exists())

    def test_guardar_y_recargar_unicode_y_contador(self):
        estado = Estado([Tarea(3, "Revisión 📝", True)], 7)
        guardar_estado(self.ruta, estado)
        self.assertEqual(cargar_estado(self.ruta), estado)
        self.assertIn("Revisión 📝", self.ruta.read_text(encoding="utf-8"))

    def test_json_corrupto_no_se_modifica(self):
        self.ruta.parent.mkdir()
        for contenido in (b"", b"{roto", b"\xff"):
            with self.subTest(contenido=contenido):
                self.ruta.write_bytes(contenido)
                with self.assertRaises(ErrorAlmacenamiento):
                    cargar_estado(self.ruta)
                self.assertEqual(self.ruta.read_bytes(), contenido)

    def test_esquemas_invalidos(self):
        base = {"version": 1, "siguiente_id": 2, "tareas": [
            {"id": 1, "titulo": "A", "completada": False}
        ]}
        casos = [[], {}, {**base, "version": 2}, {**base, "version": True},
                 {**base, "siguiente_id": 1}, {**base, "siguiente_id": True},
                 {**base, "tareas": {}},
                 {**base, "tareas": base["tareas"] * 2}]
        for campo, valor in (("id", True), ("id", -1), ("titulo", " "),
                             ("titulo", 9), ("completada", 1)):
            casos.append({**base, "tareas": [{**base["tareas"][0], campo: valor}]})
        self.ruta.parent.mkdir()
        for datos in casos:
            with self.subTest(datos=datos):
                self.ruta.write_text(json.dumps(datos), encoding="utf-8")
                with self.assertRaises(ErrorAlmacenamiento):
                    cargar_estado(self.ruta)

    def test_estado_invalido_no_sobrescribe(self):
        guardar_estado(self.ruta, Estado())
        original = self.ruta.read_bytes()
        with self.assertRaises(ErrorAlmacenamiento):
            guardar_estado(self.ruta, Estado([Tarea(1, "A")], 1))
        self.assertEqual(self.ruta.read_bytes(), original)

    def test_fallo_reemplazo_conserva_archivo_y_limpia_temporal(self):
        guardar_estado(self.ruta, Estado())
        original = self.ruta.read_bytes()
        with patch("gestor_tareas.almacenamiento.os.replace", side_effect=OSError("fallo")):
            with self.assertRaises(ErrorAlmacenamiento):
                guardar_estado(self.ruta, Estado([Tarea(1, "A")], 2))
        self.assertEqual(self.ruta.read_bytes(), original)
        self.assertEqual(list(self.ruta.parent.iterdir()), [self.ruta])

    def test_fallo_lectura_controlado(self):
        with patch.object(Path, "read_text", side_effect=PermissionError("sin acceso")):
            with self.assertRaises(ErrorAlmacenamiento):
                cargar_estado(self.ruta)

    def test_fallo_escritura_controlado(self):
        with patch("gestor_tareas.almacenamiento.os.fsync", side_effect=OSError("fallo")):
            with self.assertRaises(ErrorAlmacenamiento):
                guardar_estado(self.ruta, Estado())
        self.assertFalse(self.ruta.exists())
        self.assertEqual(list(self.ruta.parent.iterdir()), [])

    def test_ruta_externa_rechazada_sin_acceso(self):
        ruta = PROYECTO.parent / "no-crear-tareas.json"
        with patch.object(Path, "read_text") as lectura:
            with self.assertRaises(ErrorAlmacenamiento):
                cargar_estado(ruta)
            lectura.assert_not_called()
        with patch.object(Path, "mkdir") as escritura:
            with self.assertRaises(ErrorAlmacenamiento):
                guardar_estado(ruta, Estado())
            escritura.assert_not_called()

    def test_fallo_limpieza_temporal_es_controlado(self):
        with patch("gestor_tareas.almacenamiento.os.fsync", side_effect=OSError("fallo")):
            with patch.object(Path, "unlink", side_effect=PermissionError("sin acceso")):
                with self.assertRaisesRegex(ErrorAlmacenamiento, "archivo temporal"):
                    guardar_estado(self.ruta, Estado())
        self.assertFalse(self.ruta.exists())
