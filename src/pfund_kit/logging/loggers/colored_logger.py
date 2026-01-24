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
        logger.debug("Details", style=str(TextStyle.ITALIC + RichColor.CYAN))
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

        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
