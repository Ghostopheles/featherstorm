import json

from pathlib import Path


class DataCache:
    def __init__(self, path: Path, default_name: str | None = None):
        self._path = path
        self._path.mkdir(parents=True, exist_ok=True)

        self._default_name = default_name

    def read(self, as_json: bool = True):
        if self._default_name is None:
            return None

        if as_json:
            return self.read_json(self._default_name)
        else:
            return self.read_file(self._default_name)

    def write(self, data: str | dict, as_json: bool = True):
        if self._default_name is None:
            return False

        if as_json:
            return self.write_json(self._default_name, data)
        else:
            return self.write_file(self._default_name, data)

    def read_file(self, filename: str) -> str | None:
        full_path = self._path / filename
        if full_path.exists():
            return full_path.read_text()
        return None

    def read_json(self, filename: str, *args, **kwargs) -> dict | None:
        text = self.read_file(filename)
        if text:
            return json.loads(text, *args, **kwargs)
        return None

    def write_file(self, filename: str, text: str) -> bool:
        full_path = self._path / filename
        full_path.write_text(text)
        return True

    def write_json(self, filename: str, data: dict, *args, **kwargs):
        kwargs.setdefault("indent", 4)
        return self.write_file(filename, json.dumps(data, *args, **kwargs))

    def get_all_files(self) -> list[Path]:
        return [f for f in self._path.iterdir()]
