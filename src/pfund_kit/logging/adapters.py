from typing import Any

from logging import Logger, LoggerAdapter


class PrefixLoggerAdapter(LoggerAdapter):
    """Tag every record from this logger with a static prefix, e.g. ``[REST]``.

    Wraps a logger per-instance, so when several components share one logger
    (e.g. a ``pfund.{venue}`` logger used by the venue, REST API and WS API),
    only what this adapter logs gets the prefix — the others stay untouched.

    Example:
        >>> logger = PrefixLoggerAdapter(logging.getLogger("pfund.bybit"), "[REST]")
        >>> logger.debug("get_balances raw response: ...")
        # -> "[REST] get_balances raw response: ..."
    """
    def __init__(self, logger: Logger, prefix: str):
        super().__init__(logger, {})
        self._prefix = prefix

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        return f"{self._prefix} {msg}", kwargs
