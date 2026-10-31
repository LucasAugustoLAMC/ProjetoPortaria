"""Ponto de entrada: python cadastro_portaria.py [--data-dir PASTA]"""
import argparse
import logging
import os
from pathlib import Path
from tkinter import messagebox

from portaria.config import DATA_DIR
from portaria.infrastructure.instance_lock import InstanceLock
from portaria.infrastructure.storage import StorageError
from portaria.presentation_v2.app import PortariaApp


def main(argv=None):
    parser = argparse.ArgumentParser(description='Portaria • Controle local de acessos')
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('PORTARIA_DATA_DIR', DATA_DIR)),
                        help='pasta do cofre local (padrão: pasta do projeto)')
    args = parser.parse_args(argv)
    path = args.data_dir.expanduser().resolve()
    try:
        path.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=path / 'portaria.log', level=logging.ERROR,
                            format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
        with InstanceLock(path / 'dados_portaria.lock'):
            return PortariaApp(data_dir=path).run()
    except (StorageError, OSError) as exc:
        try:
            messagebox.showerror('Não foi possível abrir a Portaria', str(exc))
        except Exception:
            print(str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
