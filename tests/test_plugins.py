import pytest
from pathlib import Path
from swagcli.plugins import Plugin, PluginManager


@pytest.fixture
def plugin():
    return Plugin(
        name="test_plugin",
        description="Test plugin",
        version="1.0.0",
        author="Test Author",
    )


@pytest.fixture
def plugin_manager():
    return PluginManager()


def test_plugin_creation(plugin):
    assert plugin.name == "test_plugin"
    assert plugin.description == "Test plugin"
    assert plugin.version == "1.0.0"
    assert plugin.author == "Test Author"
    assert plugin.enabled is True


def test_plugin_manager_operations(plugin_manager, plugin):
    # Test adding and getting a plugin
    plugin_manager.plugins[plugin.name] = plugin
    assert plugin_manager.get_plugin(plugin.name) == plugin

    # Test enabling/disabling plugins
    assert plugin_manager.disable_plugin(plugin.name) is True
    assert plugin_manager.plugins[plugin.name].enabled is False
    assert plugin_manager.enable_plugin(plugin.name) is True
    assert plugin_manager.plugins[plugin.name].enabled is True

    # Test listing plugins
    plugins = plugin_manager.list_plugins()
    assert len(plugins) == 1
    assert plugins[0] == plugin


def test_plugin_hooks(plugin_manager, tmp_path):
    # Create a test plugin module
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()

    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text("""
from swagcli.plugins import Plugin

plugin = Plugin(
    name="test_plugin",
    description="Test plugin",
    version="1.0.0",
    author="Test Author"
)

def test_hook(*args, **kwargs):
    return "hook_result"
    """)

    # Test plugin discovery
    plugin_manager.discover_plugins(plugin_dir)
    assert "test_plugin" in plugin_manager.plugins

    # Test hook execution
    results = plugin_manager.execute_plugin_hook("test_hook")
    assert results == ["hook_result"]


def test_plugin_error_handling(plugin_manager, tmp_path):
    # Create a plugin that raises an error
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()

    plugin_file = plugin_dir / "error_plugin.py"
    plugin_file.write_text("""
from swagcli.plugins import Plugin

plugin = Plugin(
    name="error_plugin",
    description="Error plugin",
    version="1.0.0",
    author="Test Author"
)

def error_hook():
    raise Exception("Test error")
    """)

    # Test that errors in hooks don't crash the application
    plugin_manager.discover_plugins(plugin_dir)
    results = plugin_manager.execute_plugin_hook("error_hook")
    assert results == []  # Empty list because the hook raised an error
