import click
import json
import re
from requests import Request, Session

from anytree import NodeMixin, RenderTree


class Swagcli():

    def __init__(self, url):
        self.default_headers = {}
        self.default_data = {}
        self.config_url = url
        pass

    def _get_config(self):
        return self.make_request('GET', self.config_url)

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
            print(f' -- validating {required_key} in {config.keys()}')
            if required_key not in config.keys():
                raise ValueError(f'Required key "{required_key}" not found.')
            if required_child:
                self._verify_config(config[required_key], required_child)

    def _handle_path(self, path_name, path_config):
        pass


s = Swagcli("https://petstore.swagger.io/v2/swagger.json")
response = s._get_config()

config = response.json()['paths']

path_config = {
    "post": {
        "summary": "",
        "operationId": "",
        "parameters": "",
    }
}


class PathTreeBase():
    pass

class PathTree(PathTreeBase, NodeMixin):
    def __init__(self, name, fullpath, argument=None, config=None, parent=None, children=None):
        super(PathTree, self).__init__()
        self.name = name
        self.argument = argument
        self.fullpath = fullpath
        self.config = config
        self.parent = parent
        if children:
            self.children = children


class CommandStore():
    def __init__(self):
        self.root = PathTree('/', '/')

    def _get_path_list(self, path):
        return path.split('/')[1:]

    def _get_node_by_path(self, fullpath):
        for pre, fill, node in RenderTree(self.root):
            if node.fullpath == fullpath:
                return node


    def add_path(self, path, path_config):
        print("--", path)

        def pre_process_fullpath(fullpath):
            return re.sub("/{.*}", '', fullpath)

        path_list = self._get_path_list(path)
        if not path_list:
            return False
        parent = self.root
        # create only till the second last item
        for index in range(0, len(path_list)-1):
            path_item = path_list[index]
            print("  ", path_item)
            if re.search("{(.*)}", path_item):
                # If the path_item is of the form {.*}, then it is an argument
                # Do not create a node for this append to arguments associated
                # with our parent node
                parent.argument = re.search("{(.*)}", path_item).group(1)
                continue
            current_path = self.root.name + "/".join(path_list[:index+1])
            # Remove argument strings from our path
            current_path = pre_process_fullpath(current_path)

            print("current_path", current_path)

            # Check if another node with same path exist
            node = self._get_node_by_path(current_path)
            if node:
                # We need not create a node and st this guy as the parent
                parent = node
                continue

            parent = PathTree(path_item, current_path, parent=parent)

        path_name = path_list[-1]
        node = self._get_node_by_path(pre_process_fullpath(path))
        if node:
            node.config = path_config
        else:
            node = PathTree(path_name, pre_process_fullpath(path), config=path_config, parent=parent)

        if re.search("{(.*)}", path_name):
            node.argument = re.search("{(.*)}", path_name).group(1)

    def print(self):
        for pre, fill, node in RenderTree(self.root):
            treestr = u"%s%s" % (pre, node.name)
            print(treestr.ljust(8), " -- ", node.fullpath, node.argument)


command_store = CommandStore()
def add_to_command_store(path):
    command_store.add_path(path, None)
for path, conf in config.items():
    add_to_command_store(path)
    #for method, mconfig in conf.items():
    #    print(method, "--", mconfig.get("operationId"))
    #s._verify_config(conf, path_config)

command_store.print()
