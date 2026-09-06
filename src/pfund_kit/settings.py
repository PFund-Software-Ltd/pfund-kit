from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, ClassVar, Self

import tomlkit
from pydantic import BaseModel, ConfigDict

from pfund_kit.migration import Migration, migrate
from pfund_kit.utils import toml


__all__ = ["Migration", "Settings"]


class Settings(BaseModel):
    """TOML settings with one version and migration chain for the whole file.

    Subclasses own their fields and migrations. Register each transition as
    ``migrations = {"0.1.0": ("0.1.1", upgrade_to_011)}``. Migration functions
    receive the whole file without ``__version__`` and return its updated data.
    Section-based models must override ``_validate_file`` to validate every
    section, including those not being loaded, before a migration is saved.
    """

    __version__: ClassVar[str] = "0.1.0"
    migrations: ClassVar[dict[str, tuple[str, Migration]]] = {}
    # Keys whose dict values are written as inline tables. None inlines every
    # dict nested deeper than one level.
    inline_keys: ClassVar[frozenset[str] | None] = None
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def _migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        return migrate(data, target=cls.__version__, migrations=cls.migrations, name="Settings")

    @staticmethod
    def _read(path: Path) -> tuple[bytes | None, dict[str, Any]]:
        original = path.read_bytes() if path.exists() else None
        document = tomlkit.parse(original.decode("utf-8")) if original is not None else {}
        # Match the shared TOML loader's conversion of the "None" sentinel.
        return original, toml._toml_to_python(document)

    @classmethod
    def _validate_file(cls, data: dict[str, Any]) -> None:
        """Validate all data without materializing defaults in the stored file."""
        cls.model_validate(data)

    @classmethod
    def load_file(cls, path: str | Path, *, section: str | None = None) -> Self:
        path = Path(path)
        original, stored = cls._read(path)
        data = cls._migrate(stored) if original is not None else {}
        cls._validate_file(data)
        settings = cls.model_validate(data.get(section, {}) if section is not None else data)
        migrated = original is not None and stored.get("__version__") != cls.__version__
        if original is None or migrated or (section is not None and section not in data):
            if section is None:
                data = settings.to_dict()
            else:
                data[section] = settings.to_dict()
            cls._validate_file(data)
            cls._write_file(path, data, original, backup=migrated)
        return settings

    def to_dict(self) -> dict[str, Any]:
        """Override when a project needs different default/null serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    def save_file(self, path: str | Path, *, section: str | None = None) -> None:
        path = Path(path)
        original, stored = self._read(path)
        # Refuse newer/unknown schemas even on explicit saves. Validate an older
        # file before replacing it, so a missing migration cannot erase values.
        data = self._migrate(stored) if original is not None else {}
        if original is not None:
            self._validate_file(data)
        fields = self.to_dict()
        type(self).model_validate(fields)
        if section is None:
            data = fields
        else:
            data[section] = fields
        self._validate_file(data)
        migrated = original is not None and stored.get("__version__") != self.__version__
        self._write_file(path, data, original, backup=migrated)

    @classmethod
    def _write_file(
        cls, path: Path, data: dict[str, Any], original: bytes | None, *, backup: bool
    ) -> None:
        payload = {"__version__": cls.__version__, **data}
        if cls.inline_keys is None:
            prepared = toml._prepare_for_toml(payload, auto_inline=True)
        else:
            prepared = toml._prepare_for_toml(payload, inline_keys=set(cls.inline_keys))
        document = tomlkit.parse(original.decode("utf-8")) if original is not None else tomlkit.document()
        for key in list(document):
            if key not in payload:
                del document[key]
        for key, value in prepared.items():
            # Preserve formatting and comments in unchanged sections.
            if key not in document or toml._toml_to_python(document[key]) != payload[key]:
                document[key] = value
        content = tomlkit.dumps(document).encode("utf-8")
        if content == original:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if (path.read_bytes() if path.exists() else None) != original:
                raise RuntimeError(f"Settings changed while saving {path}; reload before retrying")
            if original is not None:
                os.chmod(temporary, path.stat().st_mode & 0o777)
            if backup and original is not None:
                with tempfile.NamedTemporaryFile(
                    dir=path.parent, prefix=f"{path.name}.", suffix=".bak", delete=False
                ) as stream:
                    stream.write(original)
                    stream.flush()
                    os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
