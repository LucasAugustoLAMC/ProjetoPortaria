"""Ponto de entrada. Execute: python cadastro_portaria.py"""
import logging
from pathlib import Path
from portaria.presentation.app import PortariaApp


def main():
    logging.basicConfig(filename=Path(__file__).resolve().parent / 'portaria.log',
                        level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(message)s',
                        encoding='utf-8')
    return PortariaApp().run()


if __name__ == '__main__':
    main()
