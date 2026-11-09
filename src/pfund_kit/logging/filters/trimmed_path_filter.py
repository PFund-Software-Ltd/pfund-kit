import os
from logging import Filter
from pathlib import Path
from typing import ClassVar

from pfund_kit.paths import _detect_project_layout


class TrimmedPathFilter(Filter):
    """Adds 'trimmedpath' attribute by removing common path prefixes.

    Trims:
    - site-packages/ for installed packages (cross-platform)
    - Project root for application code (finds pyproject.toml to determine root)
    """

    # Cache: maps resolved file path -> project root (or None if not found)
    _project_root_cache: ClassVar[dict[str, Path | None]] = {}

    @staticmethod
    def trim_path(pathname: str | Path) -> str:
        """
        Trim a file path by removing common prefixes.

        Args:
            pathname: File path to trim

        Returns:
            Trimmed path as string

        Examples:
            >>> TrimmedPathFilter.trim_path('/usr/lib/python3.11/site-packages/requests/api.py')
            'requests/api.py'
            >>> TrimmedPathFilter.trim_path('/Users/user/pfund.ai/pfeed/pfeed/dataflow/file.py')
            'pfeed/dataflow/file.py'
        """
        pathname = str(pathname)

        # Handle site-packages for both Unix and Windows
        # e.g., /usr/lib/python3.11/site-packages/requests/api.py -> requests/api.py
        if "site-packages" + os.sep in pathname or "site-packages/" in pathname:
            for sep in [f"site-packages{os.sep}", "site-packages/"]:
                if sep in pathname:
                    return pathname.split(sep)[-1]

        # Handle local development: find project root via pyproject.toml
        # e.g., /Users/user/pfund.ai/pfeed/pfeed/dataflow/file.py -> pfeed/dataflow/file.py
        file_path = Path(pathname)
        cache_key = str(file_path)

        if cache_key not in TrimmedPathFilter._project_root_cache:
            _, _, project_root = _detect_project_layout(file_path)
            TrimmedPathFilter._project_root_cache[cache_key] = project_root

        project_root = TrimmedPathFilter._project_root_cache[cache_key]

        if project_root is not None:
            try:
                return str(file_path.resolve().relative_to(project_root))
            except ValueError:
                pass  # Not relative to project root, fall through

        # Fallback: use full pathname
        return pathname

    def filter(self, record):
        record.trimmedpath = self.trim_path(record.pathname)
        return True
