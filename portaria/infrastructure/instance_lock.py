"""Bloqueia duas instâncias locais escrevendo no mesmo cofre.

Bloqueio do SO: a existência de um arquivo .lock não é tratada como bloqueio
(arquivos residuais não impedem a inicialização). Disponível Windows/POSIX.
"""
import os
from pathlib import Path
from .storage import StorageError


class InstanceLock:
    def __init__(self, path):
        self.path = Path(path)
        self._stream = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                stream.seek(0)
                stream.write(b'0')
                stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            stream.close()
            raise StorageError('A base já está em uso por outra instância. Feche o outro aplicativo.') from exc
        self._stream = stream
        return self

    def release(self):
        if not self._stream:
            return
        stream, self._stream = self._stream, None
        try:
            if os.name == 'nt':
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()
