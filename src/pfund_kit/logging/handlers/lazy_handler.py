"""Lazy handler that defers file creation until first log message."""

import logging
import threading
from pathlib import Path
from typing import Any


class LazyHandler(logging.Handler):
    """
    A wrapper handler that defers the creation of the actual handler until the first log record is emitted.

    This prevents log files from being created for loggers that are never used.

    Usage in logging config:
        handlers:
          my_lazy_handler:
            class: 'pfund_kit.logging.handlers.LazyHandler'
            level: 'DEBUG'
            formatter: 'file'
            target_class: 'pfund_kit.logging.handlers.CompressedTimedRotatingFileHandler'
            target_kwargs: {'when': 'midnight', 'backupCount': 7, 'utc': True}
    """

    def __init__(
        self,
        filename: str | Path | None = None,
        target_class: str | None = None,
        target_kwargs: dict[str, Any] | None = None,
        level: int = logging.NOTSET,
        **kwargs
    ):
        """
        Initialize the lazy handler.

        Args:
            filename: Path to the log file (required for file-based handlers)
            target_class: Fully qualified class name of the actual handler to create (e.g., 'logging.FileHandler')
            target_kwargs: Keyword arguments to pass to the target handler constructor (filename will be prepended)
            level: Logging level
            **kwargs: Additional kwargs (captured but not used, for compatibility with dictConfig)
        """
        super().__init__(level=level)
        self._filename = filename
        self._target_class = target_class
        self._target_kwargs = target_kwargs or {}
        self._target_handler: logging.Handler | None = None
        self._init_lock = threading.Lock()  # Lock for thread-safe handler creation

    def _ensure_target_handler(self) -> logging.Handler:
        """
        Create the target handler if it doesn't exist yet.

        Thread-safe: Uses double-checked locking to ensure only one handler is created.
        """
        # Fast path: handler already exists (no lock needed)
        if self._target_handler is not None:
            return self._target_handler

        # Slow path: need to create handler (acquire lock)
        with self._init_lock:
            # Double-check: another thread might have created it while we waited for the lock
            if self._target_handler is not None:
                return self._target_handler

            # Validate target_class is provided
            if not self._target_class:
                raise ValueError("target_class must be specified for LazyHandler")

            try:
                # Import the target class
                module_name, class_name = self._target_class.rsplit('.', 1)
                module = __import__(module_name, fromlist=[class_name])
                handler_class = getattr(module, class_name)
            except (ValueError, ImportError, AttributeError) as e:
                raise ValueError(
                    f"Failed to import target handler class '{self._target_class}': {e}"
                ) from e

            try:
                # Create the target handler with filename as first argument (if provided)
                if self._filename is not None:
                    self._target_handler = handler_class(self._filename, **self._target_kwargs)
                else:
                    self._target_handler = handler_class(**self._target_kwargs)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to instantiate handler {self._target_class}: {e}"
                ) from e

            # Copy over our formatter, filters, level, and name to the target handler
            if self.formatter:
                self._target_handler.setFormatter(self.formatter)
            self._target_handler.setLevel(self.level)
            for filter_obj in self.filters:
                self._target_handler.addFilter(filter_obj)
            if hasattr(self, 'name') and self.name:
                self._target_handler.name = self.name

        return self._target_handler

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record.

        On the first call, this creates the actual target handler, then delegates to it.

        Note: This method is called by handle() after level and filter checks have passed.
        If called directly (bypassing handle()), it will create the handler unconditionally.
        """
        target = self._ensure_target_handler()
        target.emit(record)

    def setFormatter(self, fmt: logging.Formatter | None) -> None:
        """Set the formatter, applying it to target handler if it exists."""
        super().setFormatter(fmt)
        if self._target_handler:
            self._target_handler.setFormatter(fmt)

    def addFilter(self, filter: logging.Filter) -> None:
        """Add a filter, applying it to target handler if it exists."""
        super().addFilter(filter)
        if self._target_handler:
            self._target_handler.addFilter(filter)

    def removeFilter(self, filter: logging.Filter) -> None:
        """Remove a filter, removing it from target handler if it exists."""
        super().removeFilter(filter)
        if self._target_handler:
            self._target_handler.removeFilter(filter)

    def close(self) -> None:
        """Close the handler, and the target handler if it was created."""
        with self._init_lock:
            if self._target_handler:
                self._target_handler.close()
        super().close()

    def flush(self) -> None:
        """Flush the handler, and the target handler if it was created."""
        # Only flush if handler has been created
        if self._target_handler:
            self._target_handler.flush()
        super().flush()

    def handleError(self, record: logging.LogRecord) -> None:
        """
        Handle errors during emit.

        If the target handler exists, delegate to it. Otherwise, use default error handling.
        """
        if self._target_handler:
            self._target_handler.handleError(record)
        else:
            super().handleError(record)
