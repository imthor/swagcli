import click
import json
import re
from requests import Request, Session

from anytree import NodeMixin, RenderTree, PreOrderIter


class NodeBase():
    pass

class Node(NodeBase, NodeMixin):
    """
    Node corresponding to each path in the config
    """
    def __init__(self, name, fullpath, is_command=False, config=None, parent=None, children=None):
        super(Node, self).__init__()
        self.name = name
        self.fullpath = fullpath
        self.is_command = is_command
        self.config = config
        self.parent = parent
        self.cmdfunc = None
        self.request_method = None
        self.request_url = None
        self.arguments = []
        self.parameters = []
        if children:
            self.children = children


class CommandStore():
    """
    Stores the paths as a Tree
    """
    def __init__(self):
        self.root = Node('/', '/')

    def _get_path_list(self, path):
        """
        Returns a list, with all names in the path
        """
        return path.split('/')[1:]

    def _get_node_by_path(self, fullpath, **kwargs):
        for node in PreOrderIter(self.root, **kwargs):
            if node.fullpath == fullpath:
                return node

    def is_root(self, node):
        if self.root.fullpath == node.fullpath:
            return True
        return False

    def add_path(self, path, request_url, request_method, path_config):
        """
        Function to correctly add a new path to the command store
        """

        def pre_process_fullpath(fullpath):
            """
            Strip of the in-path variable name from the fullpath
            """
            return re.sub("/{.*}", '', fullpath)

        path_list = self._get_path_list(path)
        if not path_list:
            return False

        # We set root as the parent, iterate over all the keywords in the path
        # and we create a corresponding Tree
        parent = self.root
        # create only till the second last item
        for index in range(0, len(path_list)-1):
            path_item = path_list[index]
            if re.search("{(.*)}", path_item):
                # If the path_item is of the form {.*}, then it is an argument
                # Do not create a node for this
                continue
            current_path = self.root.name + "/".join(path_list[:index+1])
            # Remove argument strings from our path
            current_path = pre_process_fullpath(current_path)

            # Check if another node with same path exist
            node = self._get_node_by_path(current_path)
            if node:
                # We need not create a node and st this guy as the parent
                parent = node
                continue

            parent = Node(path_item, current_path, parent=parent)

        path_name = path_list[-1]
        node = self._get_node_by_path(pre_process_fullpath(path))
        if node:
            node.config = path_config
        else:
            node = Node(path_name, pre_process_fullpath(path), is_command=True, config=path_config, parent=parent)

        node.arguments = [re.sub('{|}', '', path_name) for path_name in path_list if re.search("{(.*)}", path_name)]
        node.parameters = path_config.get('parameters', [])
        node.request_method = request_method
        node.request_url = request_url

    def iterate(self, **kwargs):
        for node in PreOrderIter(self.root, **kwargs):
            yield node

    def print(self):
        for pre, fill, node in RenderTree(self.root):
            treestr = u"%s%s" % (pre, node.name)
            print(treestr.ljust(8), " -- ", node.fullpath, node.arguments, node.is_command, node.request_method, node.request_url)

class Swagcli():

    def __init__(self, url):
        self.default_headers = {}
        self.default_data = {}
        self.config_url = url
        self.config = {}
        self.command_store = CommandStore()
        pass

    def _get_config(self):
        if self.config:
            return self.config
        response = self.make_request('GET', self.config_url)
        self.config = response.json()
        return self.config

    def make_request(self, method, url, data={}, headers={}):

        # clean inputs
        data = data or self.default_data
        headers = headers or self.default_headers
        method = method.upper()

        req = Request(method, url, data=data, headers=headers)
        session = Session()
        response = session.send(session.prepare_request(req))
        return response

    def _verify_config(self, config, validator):
        """
        Checks if the required keys are all provided or not
        """
        for required_key, required_child in validator.items():
            if required_key not in config.keys():
                raise ValueError(f'Required key "{required_key}" not found.')
            if required_child:
                self._verify_config(config[required_key], required_child)

    def _parse_paths(self):
        """
        Iterates over all the paths and updates its internal command store DS
        """
        validator = {
            'paths': '',
            'host': '',
            'basePath': '',
        }
        self._verify_config(self._get_config(), validator)

        config = self._get_config()['paths']
        host = self._get_config()['host']
        basepath = self._get_config()['basePath']

        # uses 'https' as default
        schemes = self._get_config().get('schemes', ['https'])

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
                    self.command_store.add_path(newpath, url, method, conf[method])

    def print_paths(self):
        self.command_store.print()

    def iterate_commands(self, **kwargs):
        for node in self.command_store.iterate(**kwargs):
            print(node.request_url)

    def _handle_path(self, path_name, path_config):
        pass

    def _start(self):
        import click

        @click.group(context_settings=dict(help_option_names=['-h', '--help']))
        def main():
            pass

        param_validator = {
            'name': ''
        }

        data_type_map = {
            'integer': int,
            'string': str,
        }

        def create_function(node):
            if self.command_store.is_root(node):
                node.cmdfunc = main
                return

            name = node.fullpath.replace('/', '_')[1:]
            payload = {}
            #@click.argument("test")
            def func(*args, **kwargs):

                def process_url_args(request_url, passed_values):
                    for key in payload.get('path', {}):
                        regex = '{' + key.lower() + '}'
                        request_url = re.sub(regex, str(passed_values.get(key.lower())), request_url, flags=re.IGNORECASE)
                    return request_url

                request_url = node.request_url
                request_url = process_url_args(request_url, kwargs)

                print(node.parent.name)
                print("I will make", node.request_method, 'request to', request_url, "with --", kwargs)
                #print("I am the '{}' command {}".format(name, kwargs))
                #print(node.arguments, node.parameters)

            func.__name__ = name

            # time to populate node specific params
            for param in node.parameters:
                self._verify_config(param, param_validator)

                # Populate the click options for the command based on the
                # config we have
                option_kwargs = {
                    'required': param.get('required', False),
                }

                option_type = param.get('type')
                option_enum = param.get('enum')
                option_help = param.get('description')
                option_default = param.get('default')

                # for arrays look into the datatype of items
                if option_type == 'array':
                    option_type = param.get('items').get('type')
                    option_enum = param.get('items').get('enum')
                    option_help = param.get('items').get('description')
                    option_default = param.get('items').get('default')
                    option_kwargs['multiple'] = True

                option_kwargs['type'] = data_type_map.get(option_type, str)
                if option_enum:
                    option_kwargs['type'] = click.Choice(option_enum)

                if option_help:
                    option_kwargs['help'] = option_help

                if option_default:
                    option_kwargs['default'] = option_default

                # Associate all the above options with our command function
                func = click.option(
                    f"--{param['name']}",
                    **option_kwargs
                )(func)

                # the following config states where the parameter value should
                # go to - [query, body, header, path ..]
                data_in = param.get('in')
                if not payload.get(data_in, False):
                    payload[data_in] = {}
                # passing a dummy value, this value has to be populated at runtime
                payload[data_in][param['name']] = ''

            if node.config:
                # add the summary as docstring of the function
                func.__doc__ = node.config.get('summary', '')


            node.cmdfunc = func
            #node.parent.cmdfunc.
            main.command(name=name)(func)

        for node in self.command_store.iterate():
            create_function(node)

        main()

    def run(self):
        self._parse_paths()
        self._start()


s = Swagcli("https://petstore.swagger.io/v2/swagger.json")
#s.print_paths()
#s.iterate_commands()
s.run()
