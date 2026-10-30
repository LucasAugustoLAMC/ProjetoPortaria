"""Regressões das máscaras: prefixos, colagem e valores completos."""
import unittest

from portaria.domain.input_masks import MASCARA_DATA, MASCARA_HORA, corresponde_mascara


class InputMasksTests(unittest.TestCase):
    def test_data_aceita_parciais_e_datas_reais(self):
        for valor in ('', '3', '30', '30/', '30/1', '30/10', '30/10/',
                      '30/10/2026', '29/02/2024', '01/01/0001'):
            with self.subTest(valor=valor):
                self.assertTrue(corresponde_mascara(valor, MASCARA_DATA))

    def test_data_rejeita_entradas_invalidas(self):
        for valor in ('texto', '😀', '3a', '3２', '44', '00', '32/01/2026',
                      '01-01-2026', '01/00/2026', '01/13/2026',
                      '31/04/2026', '29/02/2025', '00/01/2026',
                      '1/1/2026', '30/10/20261', '30/10/0000', '12//10'):
            with self.subTest(valor=valor):
                self.assertFalse(corresponde_mascara(valor, MASCARA_DATA))

    def test_hora_aceita_parciais_e_valores_validos(self):
        for valor in ('', '0', '09', '09:', '09:3', '09:30', '23:59', '00:00'):
            with self.subTest(valor=valor):
                self.assertTrue(corresponde_mascara(valor, MASCARA_HORA))

    def test_hora_rejeita_valores_invalidos(self):
        for valor in ('texto', '😀', '2a:30', '２3:20', '25', '24:00', '23:60',
                      '12/30', '12::30', '1:00', '12:300', '12:3x'):
            with self.subTest(valor=valor):
                self.assertFalse(corresponde_mascara(valor, MASCARA_HORA))


if __name__ == '__main__':
    unittest.main()
