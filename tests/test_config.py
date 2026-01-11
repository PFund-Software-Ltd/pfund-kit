# VIBE-CODED
"""
Tests for pfund_kit.config module.

Tests Configuration class functionality:
- Initialization (fresh start, existing config, corrupted config)
- Migration between versions
- Path management and properties
- File operations (save, load, to_dict)
- Default file initialization
- Edge cases
"""

from pathlib import Path

import pytest
import yaml

from pfund_kit.config import Configuration


@pytest.fixture
def mock_platformdirs(tmp_path, monkeypatch):
    """
    Mock platformdirs functions to return paths under tmp_path.
    This ensures tests are hermetic and don't pollute the real filesystem.
    """
    mock_log_dir = tmp_path / "logs"
    mock_data_dir = tmp_path / "data"
    mock_cache_dir = tmp_path / "cache"
    mock_config_dir = tmp_path / "config"

    # Patch the functions in the paths module (where they're imported)
    monkeypatch.setattr('pfund_kit.paths.user_log_dir', lambda: str(mock_log_dir))
    monkeypatch.setattr('pfund_kit.paths.user_data_dir', lambda: str(mock_data_dir))
    monkeypatch.setattr('pfund_kit.paths.user_cache_dir', lambda: str(mock_cache_dir))
    monkeypatch.setattr('pfund_kit.paths.user_config_dir', lambda: str(mock_config_dir))

    return {
        'log': mock_log_dir,
        'data': mock_data_dir,
        'cache': mock_cache_dir,
        'config': mock_config_dir,
    }


@pytest.fixture
def temp_package(tmp_path):
    """
    Create a temporary package directory with default files.
    This simulates the package directory (e.g., site-packages/pfund_kit).
    """
    package_dir = tmp_path / "src" / "test_pkg"
    package_dir.mkdir(parents=True)

    # Create default files that Configuration expects
    logging_yml = package_dir / "logging.yml"
    logging_yml.write_text("version: 1\nloggers:\n  root:\n    level: 'WARNING'\n")

    compose_yml = package_dir / "compose.yml"
    compose_yml.write_text("version: '3'\nservices: {}\n")

    # Create a dummy module file for ProjectPaths detection
    module_file = package_dir / "__init__.py"
    module_file.touch()

    return {
        'package_dir': package_dir,
        'module_file': module_file,
        'logging_yml': logging_yml,
        'compose_yml': compose_yml,
    }


@pytest.fixture
def mock_config_env(mock_platformdirs, temp_package):
    """
    Combined fixture providing a complete mock environment for Configuration testing.
    Returns project_name, source_file, and all mock paths.
    """
    return {
        'project_name': 'testproject',
        'source_file': str(temp_package['module_file']),
        'dirs': mock_platformdirs,
        'package': temp_package,
    }


class TestConfigurationInit:
    """Test Configuration initialization scenarios."""

    def test_fresh_start_creates_config(self, mock_config_env):
        """Test that Configuration creates config file from scratch when none exists."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Verify config file doesn't exist yet
        config_path = dirs['config'] / 'testproject' / 'config'
        config_file = config_path / 'testproject.yml'
        assert not config_file.exists()

        # Create Configuration
        config = Configuration(project_name, source_file)

        # Assert config file was created
        assert config.file_path.exists()

        # Assert file contains correct data
        with open(config.file_path) as f:
            data = yaml.safe_load(f)

        assert data['__version__'] == Configuration.__version__
        assert '__version__' in data

    def test_fresh_start_uses_default_paths(self, mock_config_env):
        """Test that fresh Configuration uses default paths from ProjectPaths."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        config = Configuration(project_name, source_file)

        # Paths should match ProjectPaths defaults
        assert config.data_path == dirs['data'] / 'testproject'
        assert config.log_path == dirs['log'] / 'testproject'
        assert config.cache_path == dirs['cache'] / 'testproject'

    def test_fresh_start_creates_directories(self, mock_config_env):
        """Test that Configuration creates all required directories."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        # All directories should exist
        assert config.config_path.exists()
        assert config.data_path.exists()
        assert config.log_path.exists()
        assert config.cache_path.exists()

    def test_fresh_start_copies_default_files(self, mock_config_env):
        """Test that Configuration copies default files to config directory."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        # Default files should be copied
        assert config.logging_config_file_path.exists()
        assert config.docker_compose_file_path.exists()

        # Verify content was copied correctly
        assert 'version: 1' in config.logging_config_file_path.read_text()

    def test_loads_existing_config(self, mock_config_env):
        """Test that Configuration loads existing config with custom paths."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create existing config with custom paths
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        custom_data_path = dirs['data'] / 'custom_data'
        custom_log_path = dirs['log'] / 'custom_logs'

        existing_config = {
            '__version__': Configuration.__version__,
            'data_path': str(custom_data_path),
            'log_path': str(custom_log_path),
            'cache_path': str(dirs['cache'] / 'testproject'),
        }
        with open(config_file, 'w') as f:
            yaml.dump(existing_config, f)

        # Create Configuration - should load existing
        config = Configuration(project_name, source_file)

        # Should use custom paths from file
        assert config.data_path == custom_data_path
        assert config.log_path == custom_log_path

    def test_corrupted_config_missing_version_resets(self, mock_config_env, capsys):
        """Test that missing __version__ triggers reset to defaults."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create corrupted config (missing __version__)
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        # Use valid paths under tmp_path (not absolute paths outside test env)
        corrupted_config = {
            'data_path': str(dirs['data'] / 'corrupted_data'),
            'log_path': str(dirs['log'] / 'corrupted_log'),
        }
        with open(config_file, 'w') as f:
            yaml.dump(corrupted_config, f)

        # Create Configuration - should detect corruption and reset
        config = Configuration(project_name, source_file)

        # Should print warning
        captured = capsys.readouterr()
        assert 'corrupted or missing' in captured.out

        # Config file should now have __version__
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert '__version__' in data

    def test_config_filename_format(self, mock_config_env):
        """Test that config filename follows {project_name}.yml format."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        assert config.config_filename == 'testproject.yml'
        assert config.file_path.name == 'testproject.yml'


class TestConfigurationMigration:
    """Test configuration migration between versions."""

    def test_migration_triggers_on_version_mismatch(self, mock_config_env, capsys):
        """Test that version mismatch triggers migration."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with old version
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        old_config = {
            '__version__': '0.0',  # Older than current
            'data_path': str(dirs['data'] / 'testproject'),
            'log_path': str(dirs['log'] / 'testproject'),
            'cache_path': str(dirs['cache'] / 'testproject'),
        }
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)

        # Create Configuration - should trigger migration
        config = Configuration(project_name, source_file)

        # Should print migration message
        captured = capsys.readouterr()
        assert 'Migrating config from version 0.0' in captured.out

        # Config should now have new version
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert data['__version__'] == Configuration.__version__

    def test_migration_preserves_user_paths(self, mock_config_env):
        """Test that migration preserves user's custom paths."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with old version and custom paths
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        custom_data_path = dirs['data'] / 'my_custom_data'
        custom_log_path = dirs['log'] / 'my_custom_logs'

        old_config = {
            '__version__': '0.0',
            'data_path': str(custom_data_path),
            'log_path': str(custom_log_path),
            'cache_path': str(dirs['cache'] / 'testproject'),
        }
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)

        # Create Configuration - should migrate but preserve paths
        config = Configuration(project_name, source_file)

        # Custom paths should be preserved
        assert config.data_path == custom_data_path
        assert config.log_path == custom_log_path

        # Saved config should also have custom paths
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        # Note: paths are saved with !path tag, need to check the actual value
        assert str(custom_data_path) in str(data['data_path'])

    def test_migration_identifies_new_fields(self, mock_config_env, capsys):
        """Test that migration identifies newly added fields."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with old version missing a field
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        # Simulate old config missing cache_path
        old_config = {
            '__version__': '0.0',
            'data_path': str(dirs['data'] / 'testproject'),
            'log_path': str(dirs['log'] / 'testproject'),
            # cache_path intentionally missing
        }
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)

        # Create Configuration
        Configuration(project_name, source_file)

        # Should report new field
        captured = capsys.readouterr()
        assert 'Adding new fields' in captured.out
        assert 'cache_path' in captured.out

    def test_migration_identifies_removed_fields(self, mock_config_env, capsys):
        """Test that migration identifies removed/obsolete fields."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with old version and extra field
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        old_config = {
            '__version__': '0.0',
            'data_path': str(dirs['data'] / 'testproject'),
            'log_path': str(dirs['log'] / 'testproject'),
            'cache_path': str(dirs['cache'] / 'testproject'),
            'obsolete_field': 'should be removed',  # Extra field
        }
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)

        # Create Configuration
        Configuration(project_name, source_file)

        # Should report removed field
        captured = capsys.readouterr()
        assert 'Removing obsolete fields' in captured.out
        assert 'obsolete_field' in captured.out

    def test_migration_prevents_downgrade(self, mock_config_env):
        """Test that migration prevents downgrade (future version > current)."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with future version
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        future_config = {
            '__version__': '99.0',  # Future version
            'data_path': str(dirs['data'] / 'testproject'),
            'log_path': str(dirs['log'] / 'testproject'),
            'cache_path': str(dirs['cache'] / 'testproject'),
        }
        with open(config_file, 'w') as f:
            yaml.dump(future_config, f)

        # Should raise AssertionError
        with pytest.raises(AssertionError, match="Cannot migrate from version"):
            Configuration(project_name, source_file)

    def test_no_migration_when_version_matches(self, mock_config_env, capsys):
        """Test that no migration occurs when versions match."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with current version
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        current_config = {
            '__version__': Configuration.__version__,
            'data_path': str(dirs['data'] / 'testproject'),
            'log_path': str(dirs['log'] / 'testproject'),
            'cache_path': str(dirs['cache'] / 'testproject'),
        }
        with open(config_file, 'w') as f:
            yaml.dump(current_config, f)

        # Create Configuration
        Configuration(project_name, source_file)

        # Should NOT print migration message
        captured = capsys.readouterr()
        assert 'Migrating' not in captured.out


class TestConfigurationPaths:
    """Test path management and properties."""

    def test_config_path_is_fixed(self, mock_config_env):
        """Test that config_path comes from ProjectPaths and cannot be overridden."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        config = Configuration(project_name, source_file)

        # config_path should match expected path
        assert config.config_path == dirs['config'] / 'testproject' / 'config'

    def test_path_property_returns_config_path(self, mock_config_env):
        """Test that path property is alias for config_path."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        assert config.path == config.config_path

    def test_file_path_property(self, mock_config_env):
        """Test file_path property returns correct path."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        assert config.file_path == config.config_path / 'testproject.yml'

    def test_filename_property(self, mock_config_env):
        """Test filename property returns config filename."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        assert config.filename == 'testproject.yml'

    def test_logging_config_file_path_property(self, mock_config_env):
        """Test logging_config_file_path property."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        assert config.logging_config_file_path == config.config_path / 'logging.yml'

    def test_docker_compose_file_path_property(self, mock_config_env):
        """Test docker_compose_file_path property."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        assert config.docker_compose_file_path == config.config_path / 'compose.yml'

    def test_ensure_dirs_creates_all_directories(self, mock_config_env):
        """Test ensure_dirs() creates all directories when called with no args."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        # Create config (which calls ensure_dirs internally)
        config = Configuration(project_name, source_file)

        # All directories should exist
        assert config.config_path.exists()
        assert config.data_path.exists()
        assert config.log_path.exists()
        assert config.cache_path.exists()

    def test_ensure_dirs_creates_specific_directories(self, mock_config_env):
        """Test ensure_dirs() creates only specified directories when passed args."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        config = Configuration(project_name, source_file)

        # Create a new path that doesn't exist
        new_path = dirs['data'] / 'new_subdir'
        assert not new_path.exists()

        # ensure_dirs with specific path
        config.ensure_dirs(new_path)

        assert new_path.exists()

    def test_ensure_dirs_validates_path_type(self, mock_config_env):
        """Test ensure_dirs() raises TypeError for non-Path objects."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)

        # Should raise TypeError for string
        with pytest.raises(TypeError, match="not a Path object"):
            config.ensure_dirs("/some/string/path")


class TestConfigurationFileOps:
    """Test file operations (save, load, to_dict)."""

    def test_to_dict_returns_correct_schema(self, mock_config_env):
        """Test to_dict() returns dictionary with correct keys."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)
        data = config.to_dict()

        # Should have all expected keys
        assert '__version__' in data
        assert 'data_path' in data
        assert 'log_path' in data
        assert 'cache_path' in data

        # Should have exactly these keys (no more, no less)
        assert set(data.keys()) == {'__version__', 'data_path', 'log_path', 'cache_path'}

    def test_to_dict_returns_path_objects(self, mock_config_env):
        """Test to_dict() returns Path objects for paths."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)
        data = config.to_dict()

        assert isinstance(data['data_path'], Path)
        assert isinstance(data['log_path'], Path)
        assert isinstance(data['cache_path'], Path)

    def test_save_writes_to_file(self, mock_config_env):
        """Test save() writes config to YAML file."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        config = Configuration(project_name, source_file)

        # Modify a path
        new_data_path = dirs['data'] / 'modified_data'
        config.data_path = new_data_path

        # Save
        config.save()

        # Verify file was updated
        with open(config.file_path) as f:
            data = yaml.safe_load(f)

        # The path should be saved (as !path tagged string)
        assert str(new_data_path) in str(data['data_path'])

    def test_save_load_roundtrip(self, mock_config_env):
        """Test that config survives save/load roundtrip."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with custom paths
        config1 = Configuration(project_name, source_file)
        custom_data_path = dirs['data'] / 'roundtrip_test'
        config1.data_path = custom_data_path
        config1.save()

        # Create new Configuration instance (should load from file)
        config2 = Configuration(project_name, source_file)

        # Should have same custom path
        assert config2.data_path == custom_data_path

    def test_to_dict_version_matches_class_version(self, mock_config_env):
        """Test to_dict() __version__ matches class __version__."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        config = Configuration(project_name, source_file)
        data = config.to_dict()

        assert data['__version__'] == Configuration.__version__


class TestConfigurationDefaultFiles:
    """Test default file initialization."""

    def test_copies_logging_yml(self, mock_config_env):
        """Test that logging.yml is copied from package to config directory."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        package = mock_config_env['package']

        config = Configuration(project_name, source_file)

        # File should exist
        assert config.logging_config_file_path.exists()

        # Content should match source
        source_content = package['logging_yml'].read_text()
        dest_content = config.logging_config_file_path.read_text()
        assert source_content == dest_content

    def test_copies_compose_yml(self, mock_config_env):
        """Test that compose.yml is copied from package to config directory."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        package = mock_config_env['package']

        config = Configuration(project_name, source_file)

        # File should exist
        assert config.docker_compose_file_path.exists()

        # Content should match source
        source_content = package['compose_yml'].read_text()
        dest_content = config.docker_compose_file_path.read_text()
        assert source_content == dest_content

    def test_skips_existing_default_files(self, mock_config_env, capsys):
        """Test that existing default files are not overwritten."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Pre-create config directory and logging.yml with custom content
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)

        existing_logging = config_path / 'logging.yml'
        custom_content = "# My custom logging config\nversion: 99\n"
        existing_logging.write_text(custom_content)

        # Create Configuration
        Configuration(project_name, source_file)

        # Custom content should be preserved
        assert existing_logging.read_text() == custom_content

        # Should NOT print "Copied logging.yml"
        captured = capsys.readouterr()
        assert 'Copied logging.yml' not in captured.out

    def test_raises_error_for_missing_source_file(self, mock_config_env):
        """Test that missing source file raises FileNotFoundError."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        package = mock_config_env['package']

        # Delete source logging.yml
        package['logging_yml'].unlink()

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="logging.yml not found"):
            Configuration(project_name, source_file)


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""

    def test_path_string_converted_to_path(self, mock_config_env):
        """Test that string paths from YAML are converted to Path objects."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with string paths (simulating YAML without !path tags)
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        # Write config with plain strings (no !path tags)
        config_content = f"""
__version__: "{Configuration.__version__}"
data_path: "{dirs['data'] / 'string_path'}"
log_path: "{dirs['log'] / 'string_path'}"
cache_path: "{dirs['cache'] / 'string_path'}"
"""
        config_file.write_text(config_content)

        # Create Configuration
        config = Configuration(project_name, source_file)

        # Paths should be Path objects, not strings
        assert isinstance(config.data_path, Path)
        assert isinstance(config.log_path, Path)
        assert isinstance(config.cache_path, Path)

    def test_multiple_instances_share_config(self, mock_config_env):
        """Test that multiple Configuration instances see same config file."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # First instance
        config1 = Configuration(project_name, source_file)
        custom_path = dirs['data'] / 'shared_test'
        config1.data_path = custom_path
        config1.save()

        # Second instance
        config2 = Configuration(project_name, source_file)

        # Should see the change from first instance
        assert config2.data_path == custom_path

    def test_empty_config_file_treated_as_missing(self, mock_config_env, capsys):
        """Test that empty config file is treated as corrupted/missing."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create empty config file
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'
        config_file.write_text("")

        # Create Configuration - should treat as missing
        config = Configuration(project_name, source_file)

        # Should print warning about corrupted/missing
        captured = capsys.readouterr()
        assert 'corrupted or missing' in captured.out

        # Should have valid config now
        assert config.file_path.exists()
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert '__version__' in data

    def test_config_with_only_version(self, mock_config_env):
        """Test config file with only __version__ uses defaults for paths."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        dirs = mock_config_env['dirs']

        # Create config with only __version__
        config_path = dirs['config'] / 'testproject' / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / 'testproject.yml'

        minimal_config = {'__version__': Configuration.__version__}
        with open(config_file, 'w') as f:
            yaml.dump(minimal_config, f)

        # Create Configuration
        config = Configuration(project_name, source_file)

        # Should use default paths
        assert config.data_path == dirs['data'] / 'testproject'
        assert config.log_path == dirs['log'] / 'testproject'
        assert config.cache_path == dirs['cache'] / 'testproject'


class TestConfigurationSubclassing:
    """Test that Configuration can be properly subclassed."""

    def test_subclass_can_override_default_files(self, mock_config_env):
        """Test subclass can customize DEFAULT_FILES."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']
        package = mock_config_env['package']

        # Remove compose.yml from package (simulating project that doesn't need it)
        package['compose_yml'].unlink()

        # Create subclass with only logging.yml
        class MinimalConfiguration(Configuration):
            DEFAULT_FILES = [Configuration.LOGGING_CONFIG_FILENAME]

        # Should work without compose.yml
        config = MinimalConfiguration(project_name, source_file)

        assert config.logging_config_file_path.exists()
        assert not config.docker_compose_file_path.exists()

    def test_subclass_can_override_version(self, mock_config_env):
        """Test subclass can have its own version."""
        project_name = mock_config_env['project_name']
        source_file = mock_config_env['source_file']

        # Create subclass with different version
        class CustomConfiguration(Configuration):
            __version__ = "1.0"

        # Create config
        config = CustomConfiguration(project_name, source_file)

        # Should use subclass version
        assert config.to_dict()['__version__'] == "1.0"

        # File should have subclass version
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert data['__version__'] == "1.0"
