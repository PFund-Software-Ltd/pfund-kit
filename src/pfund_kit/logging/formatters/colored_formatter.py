# VIBE-CODED
import logging

from pfund_kit.logging.formatters.ansi_styles import style_to_ansi, RESET


class ColoredFormatter(logging.Formatter):
    """Formatter that applies ANSI color codes to log messages.

    Supports:
    1. Default level-based coloring (WARNING/ERROR/CRITICAL)
    2. Custom styling via record.style attribute (set by ColoredLogger)

    Usage:
        # Default coloring
        logger.warning("This will be yellow")

        # Custom styling (requires ColoredLogger)
        logger.info("Success", style="bold green")
    """

    DEFAULT_LEVEL_COLORS = {
        'WARNING': '\033[1;93m',   # Bold Yellow
        'ERROR': '\033[1;91m',     # Bold Red
        'CRITICAL': '\033[1;95m',  # Bold Magenta
    }

    def format(self, record):
        log_message = super().format(record)

        # Check if record has custom style (set by ColoredLogger)
        if hasattr(record, 'style') and record.style:
            color_code = style_to_ansi(record.style)
            end_code = RESET if color_code else ''
        else:
            # Fall back to default level-based coloring
            color_code = self.DEFAULT_LEVEL_COLORS.get(record.levelname, '')
            end_code = RESET if color_code else ''

        return f"{color_code}{log_message}{end_code}"