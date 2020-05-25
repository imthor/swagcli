"""
This is where all the magic happens
"""

import re
import click
import requests
from .commandstore import CommandStore


class Swagcli:
    """
    Class with the actual logic to create equivalent click commands based on
    the swagger config
    """

    def __init__(self, url, auth=None):
        self.auth = auth
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

    def _parse_paths(self):
        """
        Iterates over all the paths and updates its internal command store DS
        """
        validator = {"paths": "", "host": "", "basePath": ""}
        Swagcli._verify_config(self._get_config(), validator)

        config = self._get_config()["paths"]
        host = self._get_config()["host"]
        basepath = self._get_config()["basePath"]

        # uses 'https' as default
        schemes = self._get_config().get("schemes", ["https"])

        baseurl = f"{schemes[0]}://{host}{basepath}"

        for path, conf in config.items():
            methods = conf.keys()
            url = f"{baseurl}{path}"
            if len(methods) == 1:
                method = list(methods)[-1]
                self.command_store.add_path(path, url, method, conf[method])
            else:
                for method in methods:
                    newpath = f"{path}/{method}"
                    self.command_store.add_path(
                        newpath, url, method, conf[method]
                    )

    def print_paths(self):
        """
        Calls and prints the state of commands as a tree
        """
        self.command_store.print()

    @staticmethod
    def _process_url_args(payload, request_url, passed_values):
        # pylint: disable=fixme
        # TODO: support the serialization
        # https://swagger.io/docs/specification/serialization/
        for key in payload.get("path", {}):
            regex = "{" + key.lower() + "}"
            request_url = re.sub(
                regex,
                str(passed_values.get(key.lower())),
                request_url,
                flags=re.IGNORECASE,
            )
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
                payload[p_type][arg_name] = value_map.get(arg_name, None)
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
            tmp_options = _prepare_args(
                tmp_options, option_map, param.get("items")
            )

        return _update_args(option_kwargs, tmp_options)

    @staticmethod
    def _create_root_function(node):
        @click.group(context_settings=dict(help_option_names=["-h", "--help"]))
        def main():
            pass

        # we are dealing with the root node, set the predefined main
        # function as the command function
        node.cmdfunc = main

    @staticmethod
    def _create_function(node):
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
        @node.parent.cmdfunc.group(
            name=name, invoke_without_command=node.is_command
        )
        def func(*_, **kwargs):
            # if it isn't a command, its most likely a placeholder command
            # group, in this case we need no do anything
            if node.is_command:

                # replaces the in-url arguments we have with the ones that
                # have been provided as click options

                request_url = Swagcli._process_url_args(
                    payload, node.request_url, kwargs
                )
                request_args = Swagcli._update_payload_value(payload, kwargs)

                print(
                    "I will make",
                    node.request_method,
                    "request to",
                    request_url,
                    "with --",
                    request_args,
                )

        # time to populate node specific params
        for param in node.parameters:

            option_kwargs = Swagcli._get_param_options(param)

            # Associate all the above options with our command function
            func = click.option(f"--{param['name']}", **option_kwargs)(func)

            payload = Swagcli._update_payload(payload, param)

        if node.config:
            # add the summary as docstring of the function
            func.__doc__ = node.config.get("summary", "")

        func.__name__ = name
        node.cmdfunc = func

    @staticmethod
    def _handle_command_run(node, payload):
        pass

    def _start(self):
        for node in self.command_store.iterate():
            if self.command_store.is_root(node):
                Swagcli._create_root_function(node)
            else:
                Swagcli._create_function(node)
        self.command_store.root.cmdfunc()  # pylint: disable=not-callable

    def run(self):
        """
        Start of the program, invokes the click commands
        """
        self._parse_paths()
        self._start()
