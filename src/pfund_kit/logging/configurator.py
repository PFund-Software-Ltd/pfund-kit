from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from pathlib import Path

import copy
import logging
from logging.config import DictConfigurator
from logging.handlers import TimedRotatingFileHandler

from pfund_kit.logging.handlers import LazyHandler
from pfund_kit.logging.loggers import ColoredLogger


# override logging's DictConfigurator as it doesn't pass in logger names to file handlers to create filenames
class LoggingDictConfigurator(DictConfigurator):
    # class variables set via create() before instantiation
    log_path: Path | None = None
    logging_config: dict[str, Any] | None = None
    lazy: bool = False
    use_colored_logger: bool = True

    @classmethod
    def create(cls, log_path: Path, logging_config: dict[str, Any], lazy: bool = False, use_colored_logger: bool = True) -> LoggingDictConfigurator:
        """
        Factory method to create a configurator with proper class variable setup.

        Args:
            log_path: Base path for log files
            logging_config: Logging configuration dict
            lazy: If True, file handlers will be wrapped in LazyHandler to defer file creation
                  until the first log message is emitted
            use_colored_logger: If True, use ColoredLogger as the default logger class,
                  enabling the style parameter in log calls (e.g., logger.info("msg", style="bold green"))

        Returns:
            Configured LoggingDictConfigurator instance
        """
        cls.log_path = log_path
        cls.logging_config = logging_config
        cls.lazy = lazy
        cls.use_colored_logger = use_colored_logger

        # copy config to avoid modifying the original config
        config = copy.deepcopy(logging_config)

        # remove file handlers before passing to __init__
        # as they are configured in _configure_file_handler with correct filenames based on configured log_path
        handlers: list[str] = list(config.get('handlers', {}))
        for handler_name in handlers:
            if handler_name.endswith('file_handler'):
                del config['handlers'][handler_name]

        return cls(config)
    
    def add_handlers(self, logger: logging.Logger, handlers: list[str]):
        """Add handlers to a logger from a list of names."""
        for handler_name in handlers:
            try:
                if handler_name.endswith('file_handler'):
                    handler = self._configure_file_handler(logger.name, handler_name)
                    # Check if rollover is already overdue and perform it immediately.
                    if isinstance(handler, TimedRotatingFileHandler):
                        if handler.shouldRollover(None):
                            handler.doRollover()
                else:
                    # self.config was created in super().__init__, get handler from it
                    handler = self.config['handlers'][handler_name]
                logger.addHandler(handler)
            except Exception as e:
                raise ValueError('Unable to add handler %r' % handler_name) from e

    def _configure_file_handler(self, logger_name: str, handler_name: str) -> logging.FileHandler:
        logging_config: dict = self.logging_config
        # copy handler config so we can pop keys without modifying the original
        handler_config: dict = dict(logging_config['handlers'][handler_name])

        # configure filename
        # filename = time.strftime(f'{log_path}/{logger_name}.{filename_format}.log')
        filename = self.log_path / f'{logger_name}.log'

        # pop reserved keys (following Python's DictConfigurator.configure_handler pattern)
        handler_class = handler_config.pop('class')
        level = handler_config.pop('level', None)
        formatter_name = handler_config.pop('formatter', 'file')
        filter_names = handler_config.pop('filters', [])
        # remaining keys are constructor kwargs
        handler_kwargs = handler_config

        # NOTE: LazyHandler was VIBE-CODED and is considered as a nice-to-have feature
        # if it is buggy and cannot be fixed, just comment out the code under if self.lazy:
        # If lazy mode is enabled, wrap the handler in LazyHandler
        if self.lazy:
            # Create a lazy handler that will instantiate the actual handler on first use
            fh = LazyHandler(
                filename=filename,
                target_class=handler_class,
                target_kwargs=handler_kwargs,
            )
        else:
            # resolve handler class and instantiate immediately
            Handler = self.resolve(handler_class)
            fh = Handler(filename, **handler_kwargs)

        # for convention, since logging.config also gives the handlers names
        fh.name = handler_name

        # configure formatter
        formatter = self.configure_formatter(logging_config['formatters'][formatter_name])
        fh.setFormatter(formatter)

        # configure level
        if level is not None:
            fh.setLevel(logging._checkLevel(level))

        # Add filters if specified in config
        for filter_name in filter_names:
            # Make a copy because configure_filter mutates the dict
            filter_config = copy.copy(logging_config['filters'][filter_name])
            filter_obj = self.configure_filter(filter_config)
            fh.addFilter(filter_obj)

        return fh

    def configure(self):
        """Configure logging with optional ColoredLogger support."""
        if self.use_colored_logger:
            logging.setLoggerClass(ColoredLogger)
        super().configure()
