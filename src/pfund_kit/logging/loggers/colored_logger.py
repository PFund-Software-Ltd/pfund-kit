# VIBE-CODED
"""Custom logger that supports a style parameter for colored output."""

import logging
from typing import Any


class ColoredLogger(logging.Logger):
    """Logger that accepts a style parameter for colored console output.

    The style parameter accepts Rich-compatible style strings that get
    converted to ANSI escape codes by ColoredFormatter.

    Usage:
        import logging
        from pfund_kit.logging.loggers import ColoredLogger
        from pfund_kit.style import TextStyle, RichColor

        # Set as default logger class (do this once, early in your app)
        logging.setLoggerClass(ColoredLogger)

        logger = logging.getLogger(__name__)

        # Use with style parameter
        logger.info("Success!", style="bold green")
        logger.debug("Details", style=TextStyle.ITALIC + RichColor.CYAN)
        logger.error("Failed", style="bold bright_red")

        # Still works without style (uses default level coloring)
        logger.warning("This uses default yellow coloring")
    """

    def _log(
        self,
        level: int,
        msg: object,
        args: tuple[Any, ...],
        exc_info: Any = None,
        extra: dict[str, Any] | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        style: str | None = None,
    ) -> None:
        """Log with optional style parameter.

        Args:
            level: The logging level.
            msg: The log message.
            args: Arguments to merge into msg.
            exc_info: Exception info to log.
            extra: Extra data to add to the LogRecord.
            stack_info: Whether to include stack info.
            stacklevel: Stack level for finding caller info.
            style: Rich-compatible style string (e.g., "bold red", "italic cyan").
        """
        if style is not None:
            if extra is None:
                extra = {}
            extra['style'] = style

        # Increment stacklevel by 1 to account for this wrapper frame,
        # so the correct caller location is reported instead of colored_logger.py
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel + 1)

    # Public log methods are re-declared only so the `style` kwarg is part of
    # their type signature (the stdlib stubs don't allow it). At runtime these
    # just delegate to the stdlib implementations, which forward **kwargs to
    # the overridden _log above.
    def debug(self, msg: object, *args: Any, style: str | None = None, **kwargs: Any) -> None:
        super().debug(msg, *args, style=style, **kwargs)

    def info(self, msg: object, *args: Any, style: str | None = None, **kwargs: Any) -> None:
        super().info(msg, *args, style=style, **kwargs)

    def warning(self, msg: object, *args: Any, style: str | None = None, **kwargs: Any) -> None:
        super().warning(msg, *args, style=style, **kwargs)

    def error(self, msg: object, *args: Any, style: str | None = None, **kwargs: Any) -> None:
        super().error(msg, *args, style=style, **kwargs)

    def critical(self, msg: object, *args: Any, style: str | None = None, **kwargs: Any) -> None:
        super().critical(msg, *args, style=style, **kwargs)

    def exception(self, msg: object, *args: Any, style: str | None = None, **kwargs: Any) -> None:
        super().exception(msg, *args, style=style, **kwargs)

    def log(self, level: int, msg: object, *args: Any, style: str | None = None, **kwargs: Any) -> None:
        super().log(level, msg, *args, style=style, **kwargs)
