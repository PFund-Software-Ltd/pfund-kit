# VIBE-CODED
"""
TOML utilities for serializing custom Python types with round-trip support.

Provides simple read/write functions for TOML files with support for:
- Decimal (serialized as strings to preserve precision)
- Path (serialized as strings)
- StrEnum (serialized as strings)
"""
from enum import StrEnum
from pathlib import Path
from decimal import Decimal
from typing import Any, Literal

import tomlkit


# =============================================================================
# Type Conversion Helpers
# =============================================================================

def _prepare_for_toml(
    data: Any,
    inline_keys: set[str] | None = None,
    current_key: str | None = None,
    auto_inline: bool = False,
    _depth: int = 0,
) -> Any:
    """
    Recursively convert custom types to TOML-serializable values.

    Args:
        data: Python object to convert
        inline_keys: Set of key names whose dict values should be inline tables
        current_key: The key name of the current data (used for inline detection)
        auto_inline: If True, convert all nested dicts (depth > 1) to inline tables
        _depth: Internal depth tracker for auto_inline

    Returns:
        TOML-serializable version of the data
    """
    if isinstance(data, Decimal):
        return str(data)
    elif isinstance(data, Path):
        return str(data)
    elif isinstance(data, StrEnum):
        return str(data)
    elif isinstance(data, dict):
        # Check if this dict should be an inline table:
        # 1. Explicitly listed in inline_keys, OR
        # 2. auto_inline is True and we're past the first level (depth > 1)
        should_inline = (inline_keys and current_key in inline_keys) or (auto_inline and _depth > 1)

        if should_inline:
            inline = tomlkit.inline_table()
            inline.update({
                k: _prepare_for_toml(v, inline_keys, k, auto_inline, _depth + 1)
                for k, v in data.items()
            })
            return inline
        return {
            k: _prepare_for_toml(v, inline_keys, k, auto_inline, _depth + 1)
            for k, v in data.items()
        }
    elif isinstance(data, (list, tuple)):
        return [_prepare_for_toml(item, inline_keys, None, auto_inline, _depth) for item in data]
    else:
        return data


def _toml_to_python(data: Any) -> Any:
    """
    Recursively convert TOMLKit types to plain Python types.

    Args:
        data: TOMLKit object to convert

    Returns:
        Plain Python version of the data
    """
    if isinstance(data, dict):
        return {k: _toml_to_python(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_toml_to_python(item) for item in data]
    else:
        return data


# =============================================================================
# Convenience Functions
# =============================================================================

def load(file_path: str | Path, to_python: bool = True) -> dict | None:
    """
    Load TOML file.

    Args:
        file_path: Path to TOML file (str or Path)
        to_python: Convert TOMLDocument to plain Python dict (default: True)

    Returns:
        - dict: Loaded TOML data (plain Python dict if to_python=True)
        - None: If file doesn't exist

    Examples:
        # Load from file path (returns plain Python dict)
        data = load("config.toml")
        data = load(Path("config.toml"))
        print(type(data))  # <class 'dict'>

        # Access nested values
        model_name = data['models']['devstral_small_2_24b']['providers']['ollama']['model_name']

        # Keep as TOMLDocument (for advanced use cases)
        toml_doc = load("config.toml", to_python=False)
        print(type(toml_doc))  # <class 'tomlkit.toml_document.TOMLDocument'>
    """
    # Convert to Path and check existence
    path = Path(file_path)
    if not path.exists():
        return None

    # Load file
    with open(path, 'r') as f:
        data = tomlkit.load(f)

    # Convert to plain Python types if requested
    if to_python:
        return _toml_to_python(data)
    return data


def dump(
    data: Any,
    file_path: str | Path,
    *,
    mode: Literal["overwrite", "update", "merge"] = "overwrite",
    inline_keys: set[str] | list[str] | None = None,
    auto_inline: bool = False,
) -> None:
    """
    Dump data to TOML file with automatic custom type serialization.

    Args:
        data: Python dict to serialize (TOML only supports dicts at top level)
        file_path: Path to TOML file (str or Path)
        mode: How to handle existing file data:
            - "overwrite": Replace entire file with new data (default)
            - "update": Replace only sections present in new data, preserve other sections
            - "merge": Deep merge new data into existing (old keys within sections persist)
        inline_keys: Key names whose dict values should be rendered as inline tables.
            Example: inline_keys={'cancel_all_at'} turns nested dict into {start = false, stop = false}
        auto_inline: If True, automatically convert all nested dicts to inline tables.
            Only top-level sections remain as [section] headers; everything below is inlined.

    Examples:
        # Overwrite entire file (default)
        dump(data, "config.toml")
        dump(data, "config.toml", mode="overwrite")

        # Update specific sections, preserve others
        # If file has [SANDBOX] and [OTHER], this replaces [SANDBOX] but keeps [OTHER]
        dump({'SANDBOX': {'new_key': 1}}, "config.toml", mode="update")

        # Deep merge into existing data (old keys persist)
        # If [SANDBOX] has old_key=1, after merge it still has old_key=1 plus new keys
        dump({'SANDBOX': {'new_key': 2}}, "config.toml", mode="merge")

        # Dump with specific inline tables
        data = {
            'SANDBOX': {
                'df_min_rows': 1000,
                'cancel_all_at': {'start': False, 'stop': False},
            }
        }
        dump(data, "config.toml", inline_keys={'cancel_all_at'})
        # Result: cancel_all_at = {start = false, stop = false}

        # Dump with auto_inline (all nested dicts become inline)
        dump(data, "config.toml", auto_inline=True)
        # Result:
        # [SANDBOX]
        # df_min_rows = 1000
        # cancel_all_at = {start = false, stop = false}
    """
    # Convert to Path and create parent directories
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Normalize inline_keys to a set
    inline_set = set(inline_keys) if inline_keys else None

    # Determine final data based on mode
    if mode == "overwrite" or not path.exists():
        # Overwrite mode or file doesn't exist: use new data as-is
        final_data = data
    elif mode == "update":
        # Update mode: shallow merge at top level (replace sections, preserve others)
        existing_data = load(file_path, to_python=True) or {}
        final_data = {**existing_data, **data}
    elif mode == "merge":
        # Merge mode: deep merge (old keys within sections persist)
        from pfund_kit.utils import deep_merge
        existing_data = load(file_path, to_python=True) or {}
        final_data = deep_merge(existing_data, data)
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'overwrite', 'update', or 'merge'.")

    # Prepare and write
    prepared_data = _prepare_for_toml(final_data, inline_set, auto_inline=auto_inline)
    with open(path, 'w') as f:
        tomlkit.dump(prepared_data, f)
