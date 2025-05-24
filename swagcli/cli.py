"""
This is where all the magic happens
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
import requests
import typer
from rich.console import Console
from rich.panel import Panel
from typer import Option

from .client import APIClient
from .commandstore import CommandStore
from .config import Config
from .models import APIResponse

app = typer.Typer()
console = Console()


class Swagcli:
    """
    Class with the actual logic to create equivalent click commands based on
    the swagger config
    """

    def __init__(self, url, **kwargs):
        self.auth = kwargs.get("auth", None)
        self.prehooks = kwargs.get("prehooks", None)
        self.exclude_path_regex = kwargs.get("exclude_path_regex", None)
        self.include_path_regex = kwargs.get("include_path_regex", None)
        self.default_headers = {}
        self.default_data = {}
        self.config_url = url
        self.config = {}
        self.command_store = CommandStore()

    def _get_config(self):
        if self.config:
            return self.config
        try:
            response = self.make_request("GET", self.config_url)
            self.config = response.json()
            return self.config
        except requests.exceptions.ConnectionError as err:
            raise ValueError(f"Invalid URL. Error details: {err}")

    def make_request(self, method, url, **kwargs):
        """
        Generic function to make web requests
        """

        method = method.upper()
        kwargs["data"] = kwargs.get("data", self.default_data)
        kwargs["headers"] = kwargs.get("headers", self.default_headers)

        auth = kwargs.get("auth", self.auth)
        if auth:
            kwargs["auth"] = auth

        req = requests.Request(method, url, **kwargs)
        session = requests.Session()
        response = session.send(session.prepare_request(req))
        return response

    @staticmethod
    def _verify_config(config, validator):
        """
        Checks if the required keys are all provided or not
        """
        for required_key, required_child in validator.items():
            if required_key not in config.keys():
                raise ValueError(f'Required key "{required_key}" not found.')
            if required_child:
                Swagcli._verify_config(config[required_key], required_child)

    def _should_process_path(self, path):
        """
        A function to decide if a specific path needs to be processed or not
        """
        if self.include_path_regex:
            if re.search("".join(self.include_path_regex), path) is None:
                # if it doesn't match ignore
                return False
        if self.exclude_path_regex:
            if re.search("".join(self.exclude_path_regex), path):
                # if there is a match ignore
                return False
        return True

    def _parse_paths(self):
        """
        Iterates over all the paths and updates its internal command store DS
        """
        validator = {"paths": "", "host": ""}
        Swagcli._verify_config(self._get_config(), validator)

        config = self._get_config()["paths"]
        host = self._get_config()["host"]
        basepath = self._get_config().get("basePath", "")

        # uses 'https' as default
        schemes = self._get_config().get("schemes", ["https"])

        baseurl = f"{schemes[0]}://{host}{basepath}"

        for path, conf in config.items():
            url = f"{baseurl}{path}"
            methods = conf.keys()

            path = self._handle_prehook("path", path)

            for method in methods:
                newpath = f"{path}/{method}"
                if not self._should_process_path(newpath):
                    continue
                if len(methods) == 1:
                    newpath = path
                self.command_store.add_path(newpath, url, method, conf[method])

    def print_paths(self):
        """
        Calls and prints the state of commands as a tree
        """
        self.command_store.print()

    @staticmethod
    def _process_url_args(payload, request_url):
        # pylint: disable=fixme
        # TODO: support the serialization
        # https://swagger.io/docs/specification/serialization/
        for key, value in payload.get("path", {}).items():
            regex = "{" + key.lower() + "}"
            request_url = re.sub(regex, str(value), request_url, flags=re.IGNORECASE)
        return request_url

    @staticmethod
    def _process_header_args():
        pass

    @staticmethod
    def _process_form_data_args():
        pass

    @staticmethod
    def _process_body_args():
        pass

    @staticmethod
    def _update_payload(payload, param):
        """
        the following config identified where the parameter value should be
        populated based on the value of 'in' parameter config

        Puts a parameter in payload dict consisting of the following keys
        [query, body, header, path ..]
        """
        data_in = param.get("in")
        if not payload.get(data_in, False):
            payload[data_in] = {}

        # passing a dummy value, this value has to be populated at runtime
        payload[data_in][param["name"]] = None
        return payload

    @staticmethod
    def _update_payload_value(payload, value_map):
        """
        Iterates over payload and assigns value from value_map if found
        """
        for p_type, arg_list in payload.items():
            for arg_name in arg_list.keys():
                arg_value = value_map.get(arg_name, None)
                if not arg_value:
                    # click has been known to return args in small case in
                    # kwargs
                    arg_value = value_map.get(arg_name.lower(), None)
                payload[p_type][arg_name] = arg_value
        return payload

    @staticmethod
    def _get_param_options(param):
        param_validator = {"name": ""}
        data_type_map = {"integer": int, "string": str}

        Swagcli._verify_config(param, param_validator)

        # Populate the click options for the command based on config
        option_kwargs = {"required": param.get("required", False)}

        option_map = {
            "type": "type",
            "enum": "enum",
            "help": "description",
            "default": "default",
        }

        def _prepare_args(tmp_options, option_map, local_param):
            for arg_name, param_name in option_map.items():
                value = local_param.get(param_name)
                if value:
                    tmp_options[arg_name] = value
            return tmp_options

        def _update_args(option_kwargs, tmp_options):
            """
            Updates the arguments to the option_kwargs
            """
            for arg_name, value in tmp_options.items():
                if arg_name == "enum":
                    continue
                if arg_name == "type":
                    value = data_type_map.get(tmp_options["type"], str)
                    if "enum" in tmp_options.keys():
                        value = click.Choice(tmp_options["enum"])
                option_kwargs[arg_name] = value
            return option_kwargs

        tmp_options = _prepare_args({}, option_map, param)
        if tmp_options.get("type") == "array":
            # for type arrays look into the datatype of items
            option_kwargs["multiple"] = True
            tmp_options = _prepare_args(tmp_options, option_map, param.get("items"))
            # Fix: ensure default is a list if multiple is True
            if "default" in tmp_options and not isinstance(
                tmp_options["default"], list
            ):
                tmp_options["default"] = [tmp_options["default"]]

        return _update_args(option_kwargs, tmp_options)

    @staticmethod
    def _preprocess_option_name(name):
        """
        PreProcess the option name to be compatible with click option names
        """
        return name.replace(".", "")

    @staticmethod
    def _create_root_function(node):
        @click.group(context_settings=dict(help_option_names=["-h", "--help"]))
        def main():
            pass

        # we are dealing with the root node, set the predefined main
        # function as the command function
        node.cmdfunc = main

    def _create_function(self, node):
        """
        We dynamically create the click command function here with the
        required parameters as fetched from the config and this will make
        a web request with the required parameters as specified by the
        config
        """
        # set name of the function to the name of the node
        name = node.name

        payload = {}

        # this will create another click group and associate it with its
        # parent, we don't create click-commands in literal sense as such,
        # but use click groups and set it to be invoked without a command
        # wherever its supposed to be command
        @node.parent.cmdfunc.group(name=name, invoke_without_command=node.is_command)
        def func(*_, **kwargs):
            # if it isn't a command, its most likely a placeholder command
            # group, in this case we need no do anything
            if node.is_command:
                request_args = Swagcli._update_payload_value(payload, kwargs)
                self._handle_command_run(node, request_args)

        # time to populate node specific params
        for param in node.parameters:
            option_kwargs = Swagcli._get_param_options(param)
            option_name = Swagcli._preprocess_option_name(param["name"])

            # Associate all the above options with our command function
            func = click.option(f"--{option_name}", **option_kwargs)(func)

            payload = Swagcli._update_payload(payload, param)

        if node.config:
            # add the summary as docstring of the function
            func.__doc__ = node.config.get("summary", "")

        func.__name__ = name
        node.cmdfunc = func

    def _handle_prehook(self, hook_name, value):
        if self.prehooks:
            prehook = self.prehooks.get(hook_name)
            if prehook:
                # user defined function to pre_process hook_name
                return prehook(value)
        return value

    def _handle_api_response(self, response, response_map):
        """
        Basic handler that prints response from the api call or the error
        """
        response_map["403"] = response_map.get(
            "403", {"description": "Access unauthorized"}
        )
        response_map["404"] = response_map.get(
            "404", {"description": "Resource not found"}
        )
        response_map["500"] = response_map.get(
            "500", {"description": "An Internal Server error occurred"}
        )

        output_response = response_map.get(str(response.status_code), {}).get(
            "description"
        )
        if not output_response or response.status_code == 200:
            output_response = self._handle_prehook("response", response.json())
        click.echo(output_response)

    def _handle_command_run(self, node, request_args):
        # replaces the in-url arguments with its value
        request_url = Swagcli._process_url_args(request_args, node.request_url)
        request_url = self._handle_prehook("url", request_url)

        request_options = {
            "params": request_args.get("query"),
            "data": request_args.get("formData") or request_args.get("body"),
        }
        try:
            response = self.make_request(
                node.request_method, request_url, **request_options
            )
            self._handle_api_response(response, node.responses)
        except requests.exceptions.ReadTimeout as err:
            click.echo(f"Request TIMED OUT: {err}")
        except requests.exceptions.HTTPError as err:
            click.echo(f"Unable to process your request: {err}")
        except requests.exceptions.ConnectionError as err:
            click.echo(f"Unable to connect to the server: {err}")
        return {"success": False}

    def _start(self):
        for node in self.command_store.iterate():
            if self.command_store.is_root(node):
                Swagcli._create_root_function(node)
            else:
                self._create_function(node)
        self.command_store.root.cmdfunc()  # pylint: disable=not-callable

    def run(self):
        """
        Start of the program, invokes the click commands
        """
        self._parse_paths()
        self._start()


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or environment."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            return Config.model_validate_json(f.read())
    return Config()


@app.command()
def request(
    method: str = Option(..., help="HTTP method (GET, POST, PUT, DELETE)"),
    path: str = Option(..., help="API endpoint path"),
    data: Optional[str] = Option(None, help="Request data (JSON string)"),
    params: Optional[str] = Option(None, help="Query parameters (JSON string)"),
    config_path: Optional[Path] = Option(None, help="Path to config file"),
    show_progress: bool = Option(False, help="Show progress bar"),
) -> None:
    """Make an API request."""
    config = load_config(config_path)
    client = APIClient(config)

    try:
        payload: Dict[str, Any] = {}
        if data:
            payload = json.loads(data)

        query_params: Optional[Dict[str, Any]] = None
        if params:
            query_params = json.loads(params)

        async def make_request() -> APIResponse:
            async with client:
                if method.upper() == "GET":
                    return await client.get(
                        path,
                        params=query_params,
                        show_progress=show_progress,
                    )
                elif method.upper() == "POST":
                    return await client.post(
                        path,
                        data=payload,
                        show_progress=show_progress,
                    )
                elif method.upper() == "PUT":
                    return await client.put(
                        path,
                        data=payload,
                        show_progress=show_progress,
                    )
                elif method.upper() == "DELETE":
                    return await client.delete(
                        path,
                        params=query_params,
                        show_progress=show_progress,
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

        response = typer.run_async(make_request())
        console.print(Panel(str(response.data), title="Response"))

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def validate(
    schema_path: Path = Option(..., help="Path to JSON schema file"),
    data_path: Path = Option(..., help="Path to data file to validate"),
) -> None:
    """Validate data against a JSON schema."""
    try:
        with open(schema_path) as f:
            schema = json.load(f)
        with open(data_path) as f:
            data = json.load(f)

        from jsonschema import validate

        validate(instance=data, schema=schema)
        console.print("[green]Validation successful![/green]")

    except Exception as e:
        console.print(f"[red]Validation failed:[/red] {str(e)}")
        raise typer.Exit(1)


def main() -> typer.Typer:
    """Main entry point for the CLI."""
    return app
