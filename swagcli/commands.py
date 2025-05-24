from typing import Any, Dict, List, Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from .models import SwaggerDefinition, SwaggerPath
from .client import APIClient

app = typer.Typer(help="Swagger-based CLI tool")
console = Console()


class CommandGenerator:
    def __init__(self, swagger_def: SwaggerDefinition, client: APIClient):
        self.swagger_def = swagger_def
        self.client = client
        self.commands: Dict[str, typer.Typer] = {}

    def _create_parameter_options(
        self, parameters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        options = {}
        for param in parameters:
            if param.get("in") == "query":
                param_type = self._get_typer_type(param.get("type"))
                options[param["name"]] = typer.Option(
                    None,
                    help=param.get("description", ""),
                    required=param.get("required", False),
                )
        return options

    def _get_typer_type(self, param_type: Optional[str]) -> Any:
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": List,
            "object": Dict,
        }
        return type_map.get(param_type, str)

    def _format_response(self, response: Any) -> None:
        if isinstance(response, (dict, list)):
            table = Table(show_header=True, header_style="bold magenta")
            if isinstance(response, dict):
                table.add_column("Key", style="dim")
                table.add_column("Value")
                for key, value in response.items():
                    table.add_row(str(key), str(value))
            else:
                if response and isinstance(response[0], dict):
                    for key in response[0].keys():
                        table.add_column(str(key))
                    for item in response:
                        table.add_row(*[str(v) for v in item.values()])
                else:
                    table.add_column("Value")
                    for item in response:
                        table.add_row(str(item))

            console.print(Panel(table, title="Response", border_style="blue"))
        else:
            console.print(Panel(str(response), title="Response", border_style="blue"))

    def generate_commands(self) -> None:
        for path, path_item in self.swagger_def.paths.items():
            path_parts = path.strip("/").split("/")
            current_group = app

            # Create nested command groups
            for part in path_parts[:-1]:
                if part not in self.commands:
                    self.commands[part] = typer.Typer(help=f"Commands for {part}")
                    current_group.add_typer(self.commands[part], name=part)
                current_group = self.commands[part]

            # Create endpoint commands
            for method, operation in path_item.dict().items():
                if method in ["get", "post", "put", "delete"] and operation:
                    operation_id = operation.get(
                        "operationId", f"{method}_{path_parts[-1]}"
                    )

                    @current_group.command(name=operation_id)
                    async def endpoint_command(
                        **kwargs: Any,
                    ) -> None:
                        try:
                            response = await getattr(self.client, method)(
                                path,
                                params=kwargs if method == "get" else None,
                                data=kwargs if method != "get" else None,
                                show_progress=True,
                            )
                            self._format_response(response.data)
                        except Exception as e:
                            console.print(f"[red]Error: {str(e)}[/red]")

                    # Add parameter options
                    parameters = operation.get("parameters", [])
                    options = self._create_parameter_options(parameters)
                    for name, option in options.items():
                        endpoint_command.__annotations__[name] = option


def create_cli(swagger_url: str) -> typer.Typer:
    """Create a CLI application from a Swagger definition."""

    async def init_client():
        async with APIClient(swagger_url) as client:
            response = await client.get("")
            swagger_def = SwaggerDefinition(**response.data)
            generator = CommandGenerator(swagger_def, client)
            generator.generate_commands()
            return app

    return typer.run_async(init_client())
