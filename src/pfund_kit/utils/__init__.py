from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pathlib import Path

import os
import timeit
import datetime

from pfund_kit.enums.notebook_type import NotebookType


__all__ = [
    'load_env_file',
    'get_free_port',
    'get_last_modified_time',
    'print_all_loggers',
    'get_notebook_type',
    'deep_merge',
    'time_import',
]


def load_env_file(env: str = '', verbose: bool = False) -> str | None:
    """
    Load environment-specific .env file.
    
    Args:
        env: Environment name (e.g., 'live', 'backtest'). Empty string loads '.env'.
        verbose: If True, print load status.
    
    Returns:
        Path to loaded env file, or None if not found.
    """
    from dotenv import find_dotenv, load_dotenv
    
    filename = f'.env.{env.lower()}' if env else '.env'
    env_file_path = find_dotenv(filename=filename, usecwd=True, raise_error_if_not_found=False)
    
    if env_file_path:
        load_dotenv(env_file_path, override=True)
        if verbose:
            print(f'Loaded {filename} from {env_file_path}')
        return env_file_path
    else:
        if verbose:
            print(f'{filename} not found')
        return None
    

def get_free_port(host: str = '127.0.0.1') -> int:
    """
    Return an ephemeral TCP port chosen by the OS.

    NOTE: This does NOT reserve the port. Another process can claim it after
    this function returns.
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def get_last_modified_time(file_path: Path | str, tz=datetime.timezone.utc) -> datetime.datetime:
    '''
    Return the file's last modified time (mtime) as a timezone-aware datetime.

    This reads the filesystem's modification timestamp (seconds since the Unix epoch)
    and converts it into a `datetime` with the provided timezone.
    '''
    if not isinstance(tz, datetime.tzinfo):
        raise TypeError("tz must be a datetime.tzinfo instance")
    # Get the last modified time in seconds since epoch
    last_modified_time = os.path.getmtime(file_path)
    # Convert to datetime object
    return datetime.datetime.fromtimestamp(last_modified_time, tz=tz)


def get_notebook_type() -> NotebookType | None:
    import importlib.util
    
    marimo_spec = importlib.util.find_spec("marimo")
    if marimo_spec is not None:
        try:
            import marimo as mo
            if mo.running_in_notebook():
                return NotebookType.marimo
        except (ImportError, AttributeError):
            pass
        
    if any(key.startswith(('JUPYTER_', 'JPY_')) for key in os.environ):
        return NotebookType.jupyter
    
    # if 'VSCODE_PID' in os.environ:
    #     return NotebookType.vscode
    
    # None means not in a notebook environment
    return None


def deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge override into base. Returns a new dict (non-mutating).

    Args:
        base: The base dictionary to merge into.
        override: The dictionary whose values take precedence.

    Returns:
        A new merged dictionary.

    Raises:
        TypeError: If base or override is not a dict.

    Behavior:
        - Keys only in base: kept
        - Keys only in override: added
        - Keys in both:
            - Both are dicts: recursive deep merge
            - Both are lists: concatenate (base_list + override_list)
            - Otherwise: override value wins
        - None is treated as a normal value (not as a deletion signal)

    Example:
        >>> base = {"logging": {"level": "DEBUG", "handlers": ["console"]}}
        >>> override = {"logging": {"level": "INFO", "handlers": ["file"]}}
        >>> deep_merge(base, override)
        {"logging": {"level": "INFO", "handlers": ["console", "file"]}}
    """
    if not isinstance(base, dict):
        raise TypeError(f"base must be a dict, got {type(base).__name__}")
    if not isinstance(override, dict):
        raise TypeError(f"override must be a dict, got {type(override).__name__}")

    result = base.copy()

    for key, override_value in override.items():
        if key in result:
            base_value = result[key]
            if isinstance(base_value, dict) and isinstance(override_value, dict):
                result[key] = deep_merge(base_value, override_value)
            elif isinstance(base_value, list) and isinstance(override_value, list):
                result[key] = base_value + override_value
            else:
                result[key] = override_value
        else:
            result[key] = override_value

    return result


def time_import(package_name: str, repeat: int = 5, verbose: bool = True) -> dict:
    """
    Time how long it takes to import a package.
    
    Uses Python's `timeit` module internally. The package (and all its 
    submodules) are fully unloaded from `sys.modules` before each timing run
    to ensure accurate "cold import" measurement.
    
    Args:
        package_name: Name of the package to import (e.g., 'numpy', 'pandas').
        repeat: Number of timing runs (-r in timeit). Default is 5.
            More runs → better statistics.
        verbose: If True, print timing results to stdout.
    
    Returns:
        A dict containing:
            - 'best': Minimum time (seconds) - the most meaningful metric
            - 'worst': Maximum time (seconds)
            - 'mean': Mean time (seconds)
            - 'stdev': Standard deviation (seconds), None if repeat < 2
            - 'times': List of all measured times (seconds)
            - 'modules_loaded': List of modules loaded by this import
            - 'package': The package that was timed
            - 'repeat': Number of runs performed
    
    Example:
        >>> result = time_import('numpy', repeat=3)
        Timing 'numpy' (3 runs)...
          best:    89.23 ms
          worst:  102.45 ms
          mean:    94.67 ms ± 5.12 ms
          modules loaded: 42
    
    Note:
        The 'best' time is typically most meaningful - it represents the import
        with minimal system interference (same reasoning as timeit's min()).
    """
    import sys
    
    # Capture modules before import to calculate what was loaded
    modules_before = set(sys.modules.keys())
    
    # Setup code: fully unload the package and all submodules
    setup = f'''import sys
to_remove = [k for k in sys.modules if k == "{package_name}" or k.startswith("{package_name}.")]
for k in to_remove:
    del sys.modules[k]
'''
    stmt = f'__import__("{package_name}")'
    
    # timeit.repeat handles GC disabling and uses time.perf_counter()
    times = timeit.repeat(stmt, setup, repeat=repeat, number=1)
    
    # Calculate what modules were loaded
    modules_after = set(sys.modules.keys())
    modules_loaded = sorted(modules_after - modules_before)
    
    best = min(times)
    worst = max(times)
    mean = sum(times) / len(times)
    
    # Calculate standard deviation (sample stdev, n-1 denominator)
    if repeat >= 2:
        variance = sum((t - mean) ** 2 for t in times) / (repeat - 1)
        stdev = variance ** 0.5
    else:
        stdev = None
    
    result = {
        'best': best,
        'worst': worst,
        'mean': mean,
        'stdev': stdev,
        'times': times,
        'modules_loaded': modules_loaded,
        'package': package_name,
        'repeat': repeat,
    }
    
    if verbose:
        print(f"Timing '{package_name}' ({repeat} runs)...")
        print(f"  best:   {best * 1000:>8.2f} ms")
        print(f"  worst:  {worst * 1000:>8.2f} ms")
        if stdev is not None:
            print(f"  mean:   {mean * 1000:>8.2f} ms ± {stdev * 1000:.2f} ms")
        else:
            print(f"  mean:   {mean * 1000:>8.2f} ms")
        print(f"  modules loaded: {len(modules_loaded)}")
    
    return result
