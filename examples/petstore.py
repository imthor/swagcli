"""
Sample cli for swagger petstore
"""

from swagcli import Swagcli


def main():
    """
    Pet Store runner
    """

    def path_prehook(path):
        return path.replace("/pet/", "/")

    option = {
        "exclude_path_regex": ["/user/post"],
        #'include_path_regex': ['get'],
        "prehooks": {
            #'path': path_prehook
        },
    }

    swag = Swagcli("https://petstore.swagger.io/v2/swagger.json", **option)
    swag.run()


if __name__ == "__main__":
    main()
