import warnings
from threading import Lock

from pfund_kit.utils import get_notebook_type


class SingletonMeta(type):
    _instances: dict[type, object] = {}
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        # In a notebook (e.g. marimo), re-running a cell is expected to rebuild
        # the singleton with the new arguments, so drop the cached instance first
        # and let the construction below create a fresh one.
        if get_notebook_type() is not None:
            cls._remove_singleton()
        # Double-checked locking pattern for thread-safe singleton
        # Check 1: Performance optimization - skip lock if instance already exists
        if cls not in cls._instances:
            with cls._lock:
                # Check 2: Correctness - another thread may have created instance while we waited
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
                    return cls._instances[cls]
        if args or kwargs:
            warnings.warn(
                f"{cls.__name__} already exists; ignoring the arguments passed to this call",
                stacklevel=2,
            )
        return cls._instances[cls]

    def _remove_singleton(cls):
        with cls._lock:
            cls._instances.pop(cls, None)
