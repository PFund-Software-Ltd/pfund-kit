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
from typing import Any

import tomlkit


# =============================================================================
# Type Conversion Helpers
# =============================================================================

def _prepare_for_toml(data: Any) -> Any:
    """
    Recursively convert custom types to TOML-serializable values.

    Args:
        data: Python object to convert

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
        return {k: _prepare_for_toml(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [_prepare_for_toml(item) for item in data]
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
) -> None:
    """
    Dump data to TOML file with automatic custom type serialization.

    Args:
        data: Python dict to serialize (TOML only supports dicts at top level)
        file_path: Path to TOML file (str or Path)

    Examples:
        # Dump to file path (overwrites)
        data = {
            'models': {
                'devstral_small_2_24b': {
                    'routing': ['ollama'],
                    'providers': {
                        'ollama': {
                            'type': 'openai',
                            'api_base': 'http://host.docker.internal:11434/v1',
                            'model_name': 'devstral-small-2:24b',
                            'api_key_location': 'none',
                        }
                    }
                }
            }
        }
        dump(data, "config.toml")
        dump(data, Path("config.toml"))

        # Dump with custom types
        data = {
            'paths': {
                'data_dir': Path('/path/to/data'),
                'output_dir': Path('/path/to/output'),
            },
            'settings': {
                'threshold': Decimal('0.01'),
                'max_value': Decimal('100.50'),
            }
        }
        dump(data, "config.toml")
    """
    # Convert to Path and create parent directories
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare data for TOML serialization
    prepared_data = _prepare_for_toml(data)

    # Write to file
    with open(path, 'w') as f:
        tomlkit.dump(prepared_data, f)
