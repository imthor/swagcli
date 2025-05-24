import importlib
import inspect
import os
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import Plugin


class PluginManager:
    def __init__(self) -> None:
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[Plugin]] = {
            "on_request": [],
            "on_response": [],
        }

    def load_plugins(self, plugin_dir: Optional[Path] = None) -> None:
        """Load plugins from a directory."""
        if plugin_dir is None:
            plugin_dir = Path.home() / ".swagcli" / "plugins"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Add plugin directory to Python path
        if str(plugin_dir) not in os.environ.get("PYTHONPATH", "").split(os.pathsep):
            os.environ["PYTHONPATH"] = os.pathsep.join(
                [str(plugin_dir), os.environ.get("PYTHONPATH", "")]
            )

        # Load plugins
        for _, name, is_pkg in pkgutil.iter_modules([str(plugin_dir)]):
            if is_pkg:
                try:
                    module = importlib.import_module(name)
                    for item_name, item in inspect.getmembers(module):
                        if (
                            inspect.isclass(item)
                            and issubclass(item, Plugin)
                            and item != Plugin
                        ):
                            plugin = item()
                            self.register_plugin(plugin)
                except Exception as e:
                    print(f"Failed to load plugin {name}: {e}")

    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin."""
        self.plugins[plugin.name] = plugin
        for hook in self.hooks:
            if hasattr(plugin, hook):
                self.hooks[hook].append(plugin)

    def execute_plugin_hook(
        self, hook: str, *args: Any, **kwargs: Any
    ) -> List[Optional[Dict[str, Any]]]:
        """Execute a hook on all registered plugins."""
        results = []
        for plugin in self.hooks.get(hook, []):
            try:
                result = getattr(plugin, hook)(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Error executing hook {hook} on plugin {plugin.name}: {e}")
                results.append(None)
        return results


# Create a global plugin manager instance
plugin_manager = PluginManager()
