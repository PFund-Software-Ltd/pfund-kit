# VIBE-CODED
"""
YAML utilities for serializing custom Python types with round-trip support.

Registers custom representers and constructors so that Decimal, Path, and StrEnum
can be dumped and loaded using standard yaml.dump()/yaml.load() or yaml.safe_dump()/yaml.safe_load().

Uses YAML tags (!decimal, !path) to preserve type information for round-trips.
"""
from enum import StrEnum
from pathlib import Path
from decimal import Decimal
from typing import Any, Literal, TypeAlias, cast, overload

import yaml


# =============================================================================
# YAML Tags
# =============================================================================
DECIMAL_TAG = '!decimal'
PATH_TAG = '!path'

# YAML top-level documents can be mappings, sequences, or scalar values.
YAMLScalar: TypeAlias = str | int | float | bool | None | Decimal | Path
YAMLDocument: TypeAlias = YAMLScalar | dict[str, Any] | list[Any]


# =============================================================================
# Representers (Python -> YAML)
# =============================================================================
def _represent_decimal(dumper: yaml.Dumper, data: Decimal) -> yaml.ScalarNode:
    return dumper.represent_scalar(DECIMAL_TAG, str(data))  # pyright: ignore[reportUnknownMemberType]


def _represent_path(dumper: yaml.Dumper, data: Path) -> yaml.ScalarNode:
    return dumper.represent_scalar(PATH_TAG, str(data))  # pyright: ignore[reportUnknownMemberType]


# =============================================================================
# Constructors (YAML -> Python)
# =============================================================================
def _construct_decimal(loader: yaml.Loader, node: yaml.ScalarNode) -> Decimal:
    value = loader.construct_scalar(node)
    return Decimal(value)


def _construct_path(loader: yaml.Loader, node: yaml.ScalarNode) -> Path:
    value = loader.construct_scalar(node)
    return Path(value)


# =============================================================================
# Register for SafeDumper / SafeLoader (yaml.safe_dump / yaml.safe_load)
# =============================================================================
yaml.SafeDumper.add_multi_representer(StrEnum, yaml.representer.SafeRepresenter.represent_str)
yaml.SafeDumper.add_representer(Decimal, _represent_decimal)  # pyright: ignore[reportArgumentType]
yaml.SafeDumper.add_multi_representer(Path, _represent_path)  # pyright: ignore[reportArgumentType]

yaml.SafeLoader.add_constructor(DECIMAL_TAG, _construct_decimal)
yaml.SafeLoader.add_constructor(PATH_TAG, _construct_path)


# =============================================================================
# Register for Dumper / Loader (yaml.dump / yaml.load)
# =============================================================================
yaml.Dumper.add_multi_representer(StrEnum, yaml.representer.Representer.represent_str)
yaml.Dumper.add_representer(Decimal, _represent_decimal)
yaml.Dumper.add_multi_representer(Path, _represent_path)

yaml.Loader.add_constructor(DECIMAL_TAG, _construct_decimal)
yaml.Loader.add_constructor(PATH_TAG, _construct_path)


# =============================================================================
# Convenience Functions
# =============================================================================

@overload
def load(
    file_path: str | Path,
    *,
    safe: bool = True,
    multi_document: Literal[False] = False,
) -> YAMLDocument | None: ...


@overload
def load(
    file_path: str | Path,
    *,
    safe: bool = True,
    multi_document: Literal[True],
) -> list[YAMLDocument] | None: ...


def load(
    file_path: str | Path,
    *,
    safe: bool = True,
    multi_document: bool = False,
) -> YAMLDocument | list[YAMLDocument] | None:
    """
    Load YAML file with automatic custom type reconstruction.

    Args:
        file_path: Path to YAML file (str or Path)
        safe: If True, use SafeLoader (default). If False, use Loader (allows arbitrary Python objects)
        multi_document: If True, return list of documents from YAML with multiple documents separated by '---'

    Returns:
        - Single document: dict or list
        - Multiple documents (multi_document=True): list of documents
        - Non-existent file: None

    Examples:
        # Load from file path
        data = load("config.yaml")
        data = load(Path("config.yaml"))

        # Load multi-document YAML
        docs = load("config.yaml", multi_document=True)

        # Use unsafe loader (be careful!)
        data = load("config.yaml", safe=False)
    """
    # Convert to Path and check existence
    path = Path(file_path)
    if not path.exists():
        return None

    # Determine loader
    loader: type[yaml.SafeLoader] | type[yaml.Loader] = yaml.SafeLoader if safe else yaml.Loader

    # Load file
    with open(path, 'r', encoding='utf-8') as f:
        if multi_document:
            result = cast(list[YAMLDocument], list(yaml.load_all(f, Loader=loader)))
            return result or None
        else:
            return cast(YAMLDocument | None, yaml.load(f, Loader=loader))


def dump(
    data: object,
    file_path: str | Path,
    *,
    safe: bool = True,
    append: bool = False,
    **kwargs: Any,
) -> None:
    """
    Dump data to YAML file with automatic custom type serialization.

    Args:
        data: Python object to serialize
        file_path: Path to YAML file (str or Path)
        safe: If True, use SafeDumper (default). If False, use Dumper
        append: If True, append as new document (multi-document). If False, overwrite file (default)
        **kwargs: Additional arguments passed to yaml.dump() (e.g., default_flow_style, allow_unicode)

    Examples:
        # Dump to file path (overwrites)
        dump(data, "config.yaml")
        dump(data, Path("config.yaml"))

        # Append as multi-document
        dump(data1, "config.yaml")
        dump(data2, "config.yaml", append=True)  # Now contains 2 documents

        # Custom formatting
        dump(data, "config.yaml", default_flow_style=False, allow_unicode=True)
    """
    # Set defaults
    kwargs.setdefault('default_flow_style', False)
    kwargs.setdefault('allow_unicode', True)

    # Determine dumper
    dumper: type[yaml.SafeDumper] | type[yaml.Dumper] = yaml.SafeDumper if safe else yaml.Dumper

    # Convert to Path and create parent directories
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Append mode: add document separator and append
    if append and path.exists():
        with open(path, 'a', encoding='utf-8') as f:
            _ = f.write('\n---\n')
            yaml.dump(data, f, Dumper=dumper, **kwargs)
    else:
        # Overwrite mode
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, Dumper=dumper, **kwargs)
