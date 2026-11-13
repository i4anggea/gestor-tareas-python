import unittest

from gestor_tareas.tareas import (
    Estado, Tarea, agregar_tarea, completar_tarea, eliminar_tarea, listar_tareas,
)


class TareasTests(unittest.TestCase):
    def test_agregar_recorta_y_preserva_unicode(self):
        estado = Estado()
        tarea = agregar_tarea(estado, "  Revisar documentación ñ 📝  ")
        self.assertEqual(tarea, Tarea(1, "Revisar documentación ñ 📝"))
        self.assertEqual(estado.siguiente_id, 2)

    def test_titulo_invalido_no_muta_estado(self):
        for titulo in ("", " \t\n", None, 12):
            with self.subTest(titulo=titulo):
                estado = Estado()
                with self.assertRaises(ValueError):
                    agregar_tarea(estado, titulo)
                self.assertEqual(estado, Estado())

    def test_listar_ordena_sin_exponer_la_lista_interna(self):
        estado = Estado([Tarea(2, "B"), Tarea(1, "A")], 3)
        resultado = listar_tareas(estado)
        self.assertEqual([t.id for t in resultado], [1, 2])
        resultado.clear()
        self.assertEqual(len(estado.tareas), 2)

    def test_completar_es_idempotente(self):
        estado = Estado()
        agregar_tarea(estado, "A")
        completar_tarea(estado, 1)
        self.assertEqual(completar_tarea(estado, 1), Tarea(1, "A", True))
        self.assertEqual(len(estado.tareas), 1)

    def test_eliminar_solo_objetivo_y_no_reutilizar_ids(self):
        estado = Estado()
        agregar_tarea(estado, "A")
        agregar_tarea(estado, "B")
        self.assertEqual(eliminar_tarea(estado, 2).titulo, "B")
        self.assertEqual(agregar_tarea(estado, "C").id, 3)
        self.assertEqual([t.id for t in estado.tareas], [1, 3])

    def test_ids_invalidos_o_inexistentes_no_mutan(self):
        for operacion in (completar_tarea, eliminar_tarea):
            for tarea_id in (0, -1, True, "1", 1.5, 99):
                with self.subTest(operacion=operacion.__name__, id=tarea_id):
                    estado = Estado([Tarea(1, "A")], 2)
                    with self.assertRaises(ValueError):
                        operacion(estado, tarea_id)
                    self.assertEqual(estado, Estado([Tarea(1, "A")], 2))
