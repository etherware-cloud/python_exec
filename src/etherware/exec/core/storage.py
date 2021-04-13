import sqlite3
from etherware.exec.logging import debug
from .typing import TypeVar, Generic


T = TypeVar('T')


class IncrementalStorage(Generic[T]):
    def __init__(self):
        pass

    def append(self, data: T):
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

    def __getitem__(self, key: int) -> T:
        raise NotImplementedError


class MemoryStorage(IncrementalStorage[T]):
    @debug
    def __init__(self):
        super().__init__()
        self._buffer = []

    @debug
    def append(self, data: T):
        self._buffer.append(data)

    @debug
    def __len__(self) -> int:
        return len(self._buffer)

    @debug
    def __getitem__(self, key: int) -> T:
        return self._buffer[key]

    def __str__(self) -> str:
        return f"<MemoryStorage[0x{id(self):x}] buffer=[{','.join(self._buffer)}]>"


class SqliteStorage(IncrementalStorage[T]):
    def __init__(self, url: str = None):
        super().__init__()
        self._conn = sqlite3.connect(url or ":memory:")
        cursor = self._conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS storage (timestamp INTEGER, data BLOB)"
        )

    def append(self, data: T):
        cursor = self._conn.cursor()
        cursor.execute("INSERT INTO storage VALUES (date('now'), ?)", (data,))
        self._conn.commit()

    def __len__(self) -> int:
        cursor = self._conn.cursor()
        cursor.execute("SELECT max(rowid) FROM storage")
        rowid = cursor.fetchone()[0]
        return rowid or 0

    def __getitem__(self, key: int) -> T:
        cursor = self._conn.cursor()
        cursor.execute("SELECT data FROM storage WHERE rowid=?", (key + 1,))
        row = cursor.fetchone()
        return row[0]

    def __str__(self) -> str:
        return f"<SqliteStorage[0x{id(self):x}]>"
