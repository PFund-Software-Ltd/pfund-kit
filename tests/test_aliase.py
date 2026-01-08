# VIBE-CODED
import pytest

from pfund_kit.aliase import AliasRegistry


class TestAliasRegistryBasics:
    """Test basic functionality of AliasRegistry."""

    def test_simple_alias_resolution(self):
        """Test basic alias → canonical resolution."""
        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'FMP': 'FINANCIAL_MODELING_PREP',
        })

        assert registry.resolve('YF') == 'YAHOO_FINANCE'
        assert registry.resolve('FMP') == 'FINANCIAL_MODELING_PREP'

    def test_canonical_passthrough(self):
        """Test that canonical names pass through unchanged."""
        registry = AliasRegistry({'YF': 'YAHOO_FINANCE'})

        # Canonical name should return itself
        assert registry.resolve('YAHOO_FINANCE') == 'YAHOO_FINANCE'

    def test_unknown_passthrough(self):
        """Test that unknown names pass through unchanged."""
        registry = AliasRegistry({'YF': 'YAHOO_FINANCE'})

        # Unknown name should return itself
        assert registry.resolve('UNKNOWN') == 'UNKNOWN'

    def test_reverse_lookup(self):
        """Test canonical → alias lookup."""
        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'FMP': 'FINANCIAL_MODELING_PREP',
        })

        assert registry.get_alias('YAHOO_FINANCE') == 'YF'
        assert registry.get_alias('FINANCIAL_MODELING_PREP') == 'FMP'
        assert registry.get_alias('UNKNOWN') is None

    def test_callable_interface(self):
        """Test __call__() for reverse lookups (canonical → alias)."""
        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'FMP': 'FINANCIAL_MODELING_PREP',
        })

        # __call__ should be same as get_alias
        assert registry('YAHOO_FINANCE') == 'YF'
        assert registry('YAHOO_FINANCE') == registry.get_alias('YAHOO_FINANCE')

        assert registry('FINANCIAL_MODELING_PREP') == 'FMP'
        assert registry('UNKNOWN') is None

    def test_contains_operator(self):
        """Test membership testing with 'in' operator."""
        registry = AliasRegistry({'YF': 'YAHOO_FINANCE'})

        # Both alias and canonical should be in registry
        assert 'YF' in registry
        assert 'YAHOO_FINANCE' in registry
        assert 'UNKNOWN' not in registry

    def test_dict_like_access(self):
        """Test dictionary-like access patterns."""
        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'FMP': 'FINANCIAL_MODELING_PREP',
        })

        # __getitem__
        assert registry['YF'] == 'YAHOO_FINANCE'

        # get with default
        assert registry.get('YF') == 'YAHOO_FINANCE'
        assert registry.get('UNKNOWN', 'DEFAULT') == 'DEFAULT'
        assert registry.get('UNKNOWN') is None

        # KeyError for missing alias
        with pytest.raises(KeyError):
            _ = registry['UNKNOWN']

    def test_iteration(self):
        """Test iteration over aliases."""
        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'FMP': 'FINANCIAL_MODELING_PREP',
        })

        # items()
        items = list(registry.items())
        assert len(items) == 2
        assert ('YF', 'YAHOO_FINANCE') in items
        assert ('FMP', 'FINANCIAL_MODELING_PREP') in items

        # aliases()
        aliases = list(registry.aliases())
        assert set(aliases) == {'YF', 'FMP'}

        # canonicals()
        canonicals = list(registry.canonicals())
        assert set(canonicals) == {'YAHOO_FINANCE', 'FINANCIAL_MODELING_PREP'}

    def test_export_to_dict(self):
        """Test exporting to plain dictionaries."""
        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'FMP': 'FINANCIAL_MODELING_PREP',
        })

        # to_dict() - alias → canonical
        forward = registry.to_dict()
        assert forward == {
            'YF': 'YAHOO_FINANCE',
            'FMP': 'FINANCIAL_MODELING_PREP',
        }

        # to_reverse_dict() - canonical → alias
        reverse = registry.to_reverse_dict()
        assert reverse == {
            'YAHOO_FINANCE': 'YF',
            'FINANCIAL_MODELING_PREP': 'FMP',
        }

    def test_len(self):
        """Test length/size of registry."""
        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'FMP': 'FINANCIAL_MODELING_PREP',
        })

        assert len(registry) == 2

    def test_repr_and_str(self):
        """Test string representations."""
        registry = AliasRegistry({'YF': 'YAHOO_FINANCE'})

        repr_str = repr(registry)
        assert 'AliasRegistry' in repr_str
        assert 'YF' in repr_str

        str_str = str(registry)
        assert 'AliasRegistry' in str_str
        assert '1 mappings' in str_str


class TestAliasRegistryConflicts:
    """Test conflict detection."""

    def test_conflict_detection_default(self):
        """Test that conflicts raise ValueError by default."""
        with pytest.raises(ValueError, match="Conflict.*alias 'YAHOO_FINANCE' collides"):
            AliasRegistry({
                'YF': 'YAHOO_FINANCE',
                'YAHOO_FINANCE': 'SOMETHING_ELSE',  # Conflict!
            })

    def test_allow_conflicts(self):
        """Test that conflicts can be allowed if explicitly enabled."""
        # Should not raise when allow_conflicts=True
        registry = AliasRegistry(
            {
                'YF': 'YAHOO_FINANCE',
                'YAHOO_FINANCE': 'SOMETHING_ELSE',
            },
            allow_conflicts=True,
        )

        assert registry.resolve('YF') == 'YAHOO_FINANCE'
        assert registry.resolve('YAHOO_FINANCE') == 'SOMETHING_ELSE'


class TestAliasRegistryCaseInsensitive:
    """Test case-insensitive mode."""

    def test_case_insensitive_resolution(self):
        """Test case-insensitive alias resolution."""
        registry = AliasRegistry(
            {'yf': 'yahoo_finance'},
            case_sensitive=False,
        )

        # All variations should resolve to same canonical
        assert registry.resolve('yf') == 'yahoo_finance'
        assert registry.resolve('YF') == 'yahoo_finance'
        assert registry.resolve('Yf') == 'yahoo_finance'

    def test_case_insensitive_contains(self):
        """Test case-insensitive membership testing."""
        registry = AliasRegistry(
            {'yf': 'yahoo_finance'},
            case_sensitive=False,
        )

        assert 'yf' in registry
        assert 'YF' in registry
        assert 'YAHOO_FINANCE' in registry
        assert 'yahoo_finance' in registry

    def test_case_insensitive_reverse_lookup(self):
        """Test case-insensitive reverse lookup."""
        registry = AliasRegistry(
            {'yf': 'yahoo_finance'},
            case_sensitive=False,
        )

        assert registry.get_alias('yahoo_finance') == 'yf'
        assert registry.get_alias('YAHOO_FINANCE') == 'yf'
        assert registry.get_alias('Yahoo_Finance') == 'yf'


class TestAliasRegistryHelpers:
    """Test helper methods."""

    def test_is_alias(self):
        """Test checking if a name is an alias."""
        registry = AliasRegistry({'YF': 'YAHOO_FINANCE'})

        assert registry.is_alias('YF') is True
        assert registry.is_alias('YAHOO_FINANCE') is False
        assert registry.is_alias('UNKNOWN') is False

    def test_is_canonical(self):
        """Test checking if a name is canonical."""
        registry = AliasRegistry({'YF': 'YAHOO_FINANCE'})

        assert registry.is_canonical('YAHOO_FINANCE') is True
        assert registry.is_canonical('YF') is False
        assert registry.is_canonical('UNKNOWN') is False


class TestAliasRegistryRealWorld:
    """Test with real-world use cases from pfeed and pfund."""

    def test_pfeed_data_sources(self):
        """Test pfeed data source aliases."""
        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'FRD': 'FIRSTRATE_DATA',
            'DBT': 'DATABENTO',
            'FMP': 'FINANCIAL_MODELING_PREP',
        })

        # CLI usage: user types alias
        assert registry.resolve('YF') == 'YAHOO_FINANCE'
        assert registry.resolve('DBT') == 'DATABENTO'

        # Internal usage: already have canonical name
        assert registry.resolve('YAHOO_FINANCE') == 'YAHOO_FINANCE'

        # Get short form for display
        assert registry.get_alias('DATABENTO') == 'DBT'

    def test_pfund_trading_aliases(self):
        """Test pfund trading domain aliases."""
        registry = AliasRegistry({
            'px': 'price',
            'qty': 'quantity',
            'bkr': 'broker',
            'exch': 'exchange',
            'SPOT': 'cryptocurrency',
            'PERP': 'perpetual_contract',
            'FUT': 'futures_contract',
        })

        # Normalize user input
        assert registry.resolve('px') == 'price'
        assert registry.resolve('PERP') == 'perpetual_contract'

        # Already normalized
        assert registry.resolve('price') == 'price'
        assert registry.resolve('cryptocurrency') == 'cryptocurrency'

    def test_mixed_case_domains(self):
        """Test handling mixed uppercase/lowercase domains."""
        registry = AliasRegistry({
            'px': 'price',  # lowercase
            'SPOT': 'cryptocurrency',  # uppercase
            'IB': 'interactive brokers',  # mixed
        })

        assert registry.resolve('px') == 'price'
        assert registry.resolve('SPOT') == 'cryptocurrency'
        assert registry.resolve('IB') == 'interactive brokers'

    def test_cli_choice_expansion(self):
        """Test expanding CLI choices with aliases (like pfeed download command)."""
        # Simulate: SUPPORTED_DATA_SOURCES_ALIASES_INCLUDED
        CANONICAL_SOURCES = ['YAHOO_FINANCE', 'DATABENTO', 'FIRSTRATE_DATA']

        registry = AliasRegistry({
            'YF': 'YAHOO_FINANCE',
            'DBT': 'DATABENTO',
            'FRD': 'FIRSTRATE_DATA',
        })

        # Get all aliases for these canonical sources
        aliases = [
            registry.get_alias(source)
            for source in CANONICAL_SOURCES
            if registry.get_alias(source)
        ]

        # CLI accepts both canonical and aliases
        cli_choices = CANONICAL_SOURCES + aliases

        assert 'YAHOO_FINANCE' in cli_choices
        assert 'YF' in cli_choices
        assert 'DBT' in cli_choices

        # User input normalization
        user_input = 'YF'
        normalized = registry.resolve(user_input)
        assert normalized == 'YAHOO_FINANCE'


class TestAliasRegistryEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_registry(self):
        """Test empty registry."""
        registry = AliasRegistry({})

        assert len(registry) == 0
        assert registry.resolve('ANYTHING') == 'ANYTHING'  # passthrough
        assert list(registry.items()) == []

    def test_self_referential_alias(self):
        """Test alias that points to itself."""
        registry = AliasRegistry({'SELF': 'SELF'})

        assert registry.resolve('SELF') == 'SELF'
        assert registry.is_alias('SELF') is True
        assert registry.is_canonical('SELF') is True

    def test_whitespace_in_names(self):
        """Test handling of whitespace in names."""
        registry = AliasRegistry({
            'IB': 'interactive brokers',  # space in canonical
        })

        assert registry.resolve('IB') == 'interactive brokers'
        assert registry.get_alias('interactive brokers') == 'IB'

    def test_special_characters(self):
        """Test handling of special characters."""
        registry = AliasRegistry({
            'btc_usdt': 'BTC/USDT',
            'eth-usd': 'ETH-USD',
        })

        assert registry.resolve('btc_usdt') == 'BTC/USDT'
        assert registry.resolve('eth-usd') == 'ETH-USD'
