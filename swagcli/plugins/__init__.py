import importlib
import importlib.util
import pkgutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel


class Plugin(BaseModel):
    name: str
    description: str
    version: str
    author: str
    enabled: bool = True


class PluginManager:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_modules: Dict[str, Any] = {}

    def discover_plugins(self, plugins_dir: Optional[Path] = None):
        """Discover and load plugins from a directory."""
        if plugins_dir is None:
            plugins_dir = Path(__file__).parent
            # First try to load package-based plugins
            for _, name, is_pkg in pkgutil.iter_modules([str(plugins_dir)]):
                if is_pkg:
                    continue
                module_name = f"swagcli.plugins.{name}"
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, "plugin"):
                        plugin = getattr(module, "plugin")
                        self.plugins[plugin.name] = plugin
                        self.plugin_modules[plugin.name] = module
                except Exception as e:
                    print(f"Failed to load plugin {name}: {e}")
        else:
            # Then try to load standalone plugins
            if not plugins_dir.exists():
                return

            # Add plugin directory to Python path if not already there
            plugin_dir_str = str(plugins_dir.absolute())
            if plugin_dir_str not in sys.path:
                sys.path.insert(0, plugin_dir_str)

            for file in plugins_dir.glob("*.py"):
                if file.name.startswith("_"):
                    continue

                module_name = file.stem
                try:
                    # Import the module using importlib
                    spec = importlib.util.spec_from_file_location(module_name, file)
                    if spec is None:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module  # Add to sys.modules
                    spec.loader.exec_module(module)

                    # Look for plugin instance
                    if hasattr(module, "plugin"):
                        plugin = getattr(module, "plugin")
                        if isinstance(plugin, Plugin):
                            self.plugins[plugin.name] = plugin
                            self.plugin_modules[plugin.name] = module
                            print(f"Loaded plugin: {plugin.name}")
                except Exception as e:
                    print(f"Failed to load plugin {module_name}: {str(e)}")
                    import traceback

                    traceback.print_exc()

    def enable_plugin(self, name: str) -> bool:
        if name in self.plugins:
            self.plugins[name].enabled = True
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        if name in self.plugins:
            self.plugins[name].enabled = False
            return True
        return False

    def list_plugins(self) -> List[Plugin]:
        return list(self.plugins.values())

    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self.plugins.get(name)

    def execute_plugin_hook(self, hook: str, *args, **kwargs):
        results = []
        for plugin in self.plugins.values():
            if plugin.enabled:
                module = self.plugin_modules.get(plugin.name)
                if module and hasattr(module, hook):
                    try:
                        results.append(getattr(module, hook)(*args, **kwargs))
                    except Exception as e:
                        print(f"Plugin {plugin.name} hook {hook} failed: {e}")
        return results


plugin_manager = PluginManager()
