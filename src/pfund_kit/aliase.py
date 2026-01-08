# VIBE-CODED
from __future__ import annotations

from typing import Iterator


class AliasRegistry:
    """
    Thread-safe bidirectional alias registry for mapping short aliases to canonical names.

    Features:
    - Bidirectional lookup (alias ↔ canonical)
    - Case-sensitive or case-insensitive matching
    - Conflict detection during initialization
    - Immutable after initialization
    - Dict-like interface for easy integration

    Examples:
        >>> registry = AliasRegistry({
        ...     'YF': 'YAHOO_FINANCE',
        ...     'FMP': 'FINANCIAL_MODELING_PREP',
        ... })
        >>> # Forward: alias → canonical
        >>> registry.resolve('YF')
        'YAHOO_FINANCE'
        >>> registry.resolve('YAHOO_FINANCE')  # passthrough
        'YAHOO_FINANCE'
        >>>
        >>> # Reverse: canonical → alias (two ways)
        >>> registry('YAHOO_FINANCE')  # callable interface
        'YF'
        >>> registry.get_alias('YAHOO_FINANCE')  # explicit method
        'YF'
        >>>
        >>> # Membership testing
        >>> 'YF' in registry
        True
    """

    def __init__(
        self,
        aliases: dict[str, str],
        *,
        case_sensitive: bool = True,
        allow_conflicts: bool = False,
    ):
        """
        Initialize the alias registry.

        Args:
            aliases: Dictionary mapping alias → canonical name
            case_sensitive: If False, all lookups are case-insensitive
            allow_conflicts: If False, raises ValueError when an alias conflicts
                           with an existing canonical name

        Raises:
            ValueError: If conflicts detected and allow_conflicts=False
        """
        self._case_sensitive = case_sensitive
        self._aliases: dict[str, str] = {}
        self._reverse: dict[str, str] = {}

        # Normalize keys if case-insensitive
        self._normalize = (lambda x: x) if case_sensitive else (lambda x: x.lower())

        # Validate and populate
        for alias, canonical in aliases.items():
            self._add_mapping(alias, canonical, allow_conflicts=allow_conflicts)

    def _add_mapping(self, alias: str, canonical: str, allow_conflicts: bool = False) -> None:
        """Add a single alias → canonical mapping with conflict detection."""
        norm_alias = self._normalize(alias)
        norm_canonical = self._normalize(canonical)

        # Check for conflicts: alias colliding with another canonical name
        if not allow_conflicts and norm_alias in self._reverse:
            raise ValueError(
                f"Conflict: alias '{alias}' collides with existing canonical name"
            )

        # Store normalized or original based on case sensitivity
        key_alias = norm_alias if not self._case_sensitive else alias
        key_canonical = norm_canonical if not self._case_sensitive else canonical

        self._aliases[key_alias] = key_canonical
        self._reverse[key_canonical] = key_alias

    def resolve(self, name: str) -> str:
        """
        Resolve a name to its canonical form.

        If the name is an alias, returns the canonical name.
        If the name is already canonical (or unknown), returns it unchanged.

        Args:
            name: Alias or canonical name

        Returns:
            Canonical name

        Examples:
            >>> registry.resolve('YF')  # alias
            'YAHOO_FINANCE'
            >>> registry.resolve('YAHOO_FINANCE')  # already canonical
            'YAHOO_FINANCE'
            >>> registry.resolve('UNKNOWN')  # unknown, passthrough
            'UNKNOWN'
        """
        norm_name = self._normalize(name)
        return self._aliases.get(norm_name, name)

    def get_alias(self, canonical: str) -> str | None:
        """
        Get the alias for a canonical name.

        Args:
            canonical: Canonical name

        Returns:
            Alias if exists, None otherwise

        Examples:
            >>> registry.get_alias('YAHOO_FINANCE')
            'YF'
            >>> registry.get_alias('UNKNOWN')
            None
        """
        norm_canonical = self._normalize(canonical)
        return self._reverse.get(norm_canonical)

    def __call__(self, canonical: str) -> str | None:
        """
        Get the alias for a canonical name (callable interface).

        This is a convenience method that calls get_alias() under the hood.
        Provides a more intuitive API for reverse lookups.

        Args:
            canonical: Canonical name

        Returns:
            Alias if exists, None otherwise

        Examples:
            >>> registry = AliasRegistry({'YF': 'YAHOO_FINANCE'})
            >>> registry('YAHOO_FINANCE')
            'YF'
            >>> registry('price')  # if no alias exists
            None

        Note:
            For forward lookups (alias → canonical), use resolve() instead.
        """
        return self.get_alias(canonical)

    def is_alias(self, name: str) -> bool:
        """
        Check if a name is an alias (not a canonical name).

        Args:
            name: Name to check

        Returns:
            True if name is an alias, False otherwise
        """
        norm_name = self._normalize(name)
        return norm_name in self._aliases

    def is_canonical(self, name: str) -> bool:
        """
        Check if a name is a canonical name.

        Args:
            name: Name to check

        Returns:
            True if name is a canonical name, False otherwise
        """
        norm_name = self._normalize(name)
        return norm_name in self._reverse

    def __contains__(self, name: str) -> bool:
        """
        Check if a name exists as either alias or canonical name.

        Examples:
            >>> 'YF' in registry
            True
            >>> 'YAHOO_FINANCE' in registry
            True
        """
        norm_name = self._normalize(name)
        return norm_name in self._aliases or norm_name in self._reverse

    def __getitem__(self, alias: str) -> str:
        """
        Get canonical name for an alias (raises KeyError if not found).

        Examples:
            >>> registry['YF']
            'YAHOO_FINANCE'

        Raises:
            KeyError: If alias not found
        """
        norm_alias = self._normalize(alias)
        return self._aliases[norm_alias]

    def get(self, alias: str, default: str | None = None) -> str | None:
        """
        Get canonical name for an alias with a default fallback.

        Args:
            alias: Alias to look up
            default: Default value if alias not found

        Returns:
            Canonical name or default
        """
        norm_alias = self._normalize(alias)
        return self._aliases.get(norm_alias, default)

    def items(self) -> Iterator[tuple[str, str]]:
        """
        Iterate over (alias, canonical) pairs.

        Examples:
            >>> for alias, canonical in registry.items():
            ...     print(f"{alias} -> {canonical}")
        """
        return iter(self._aliases.items())

    def aliases(self) -> Iterator[str]:
        """
        Get all aliases.

        Returns:
            Iterator of alias names
        """
        return iter(self._aliases.keys())

    def canonicals(self) -> Iterator[str]:
        """
        Get all canonical names.

        Returns:
            Iterator of canonical names
        """
        return iter(self._reverse.keys())

    def to_dict(self) -> dict[str, str]:
        """
        Export as a plain dictionary (alias → canonical).

        Returns:
            Dictionary mapping aliases to canonical names
        """
        return dict(self._aliases)

    def to_reverse_dict(self) -> dict[str, str]:
        """
        Export as a reverse dictionary (canonical → alias).

        Returns:
            Dictionary mapping canonical names to aliases
        """
        return dict(self._reverse)

    def __len__(self) -> int:
        """Return number of alias mappings."""
        return len(self._aliases)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"AliasRegistry({self._aliases!r})"

    def __str__(self) -> str:
        """Return human-readable string."""
        items = [f"  {a!r} -> {c!r}" for a, c in self._aliases.items()]
        return f"AliasRegistry({len(self)} mappings):\n" + "\n".join(items)


__all__ = ['AliasRegistry']
