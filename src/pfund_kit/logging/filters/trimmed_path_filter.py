import os
from logging import Filter


class TrimmedPathFilter(Filter):
    """Adds 'trimmedpath' attribute by removing common path prefixes.

    Trims:
    - site-packages/ for installed packages (cross-platform)
    - Project root for application code (shows relative path from cwd)
    """

    def filter(self, record):
        pathname = record.pathname

        # Handle site-packages for both Unix and Windows
        # e.g., /usr/lib/python3.11/site-packages/requests/api.py -> requests/api.py
        if 'site-packages' + os.sep in pathname or 'site-packages/' in pathname:
            # Try both separators for cross-platform compatibility
            for sep in [f'site-packages{os.sep}', 'site-packages/']:
                if sep in pathname:
                    record.trimmedpath = pathname.split(sep)[-1]
                    return True
        # Handle local development: trim current working directory
        # e.g., /Users/stephenyau/pfund.ai/pfeed/some_file.py -> pfeed/some_file.py
        else:
            cwd = os.getcwd()
            if pathname.startswith(cwd + os.sep):
                # Get relative path from cwd
                record.trimmedpath = os.path.relpath(pathname, cwd)
            else:
                # Fallback: use full pathname
                record.trimmedpath = pathname

        return True