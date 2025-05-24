"""
Implements the CommandStore, a tree data structure to store the commands
"""

import re
from anytree import NodeMixin, RenderTree, PreOrderIter


class NodeBase:
    """
    Dummy class as it is required by anytree
    """

    # pylint: disable=too-few-public-methods

    def __init__(self):
        pass


class Node(NodeBase, NodeMixin):
    """
    Node corresponding to each path in the config
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, name, fullpath, **kwargs):
        # pylint: disable=missing-function-docstring
        super().__init__()
        self.name = name
        self.fullpath = fullpath
        self.config = kwargs.get("config", None)
        self.parent = kwargs.get("parent", None)
        self.is_command = kwargs.get("is_command", None)
        self.cmdfunc = None
        self.request_method = None
        self.request_url = None
        self.responses = None
        self.arguments = []
        self.parameters = []
        if kwargs.get("children"):
            self.children = kwargs.get("children")


class CommandStore:
    """
    Stores the paths as a Tree
    """

    def __init__(self):
        self.root = Node("/", "/")

    @staticmethod
    def _get_path_list(path):
        """
        Returns a list, with all names in the path
        """
        return path.split("/")[1:]

    def _get_node_by_path(self, fullpath, **kwargs):
        for node in PreOrderIter(self.root, **kwargs):
            if node.fullpath == fullpath:
                return node
        return None

    def is_root(self, node):
        """
        Checks if the passed node is the root node
        """
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
            return re.sub("/{.*}", "", fullpath)

        path_list = CommandStore._get_path_list(path)
        if not path_list:
            return False

        # We set root as the parent, iterate over all the keywords in the path
        # and we create a corresponding Tree
        parent = self.root
        # create only till the second last item
        for index in range(0, len(path_list) - 1):
            path_item = path_list[index]
            if re.search("{(.*)}", path_item):
                # If the path_item is of the form {.*}, then it is an argument
                # Do not create a node for this
                continue
            current_path = self.root.name + "/".join(path_list[: index + 1])
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
            node = Node(
                path_name,
                pre_process_fullpath(path),
                is_command=True,
                config=path_config,
                parent=parent,
            )

        node.arguments = [
            re.sub("{|}", "", path_name)
            for path_name in path_list
            if re.search("{(.*)}", path_name)
        ]
        node.parameters = path_config.get("parameters", [])
        node.request_method = request_method
        node.request_url = request_url
        node.responses = path_config.get("responses", {})

    def iterate(self, **kwargs):
        """
        Provides an iterator over CommandStore in PreOrder
        """
        for node in PreOrderIter(self.root, **kwargs):
            yield node

    def print(self):
        """
        Prints the tree state in CommandStore in a pretty way
        """
        for pre, _, node in RenderTree(self.root):
            treestr = "%s%s" % (pre, node.name)
            print(
                treestr.ljust(8),
                " -- ",
                node.fullpath,
                node.is_command,
                node.request_method,
                node.request_url,
            )
