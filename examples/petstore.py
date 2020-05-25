"""
Sample cli for swagger petstore
"""

import json
from swagcli import Swagcli


def main():
    """
    Pet Store runner
    """

    def path_prehook(path):
        return path.replace("/pet/", "/")

    def url_prehook(url):
        return url.replace(":8000", "")

    option = {
        "exclude_path_regex": ["/user/post"],
        #'include_path_regex': ['get'],
        "prehooks": {
            # "path": path_prehook,
            "url": url_prehook,
            "response": json.dumps,
        },
    }

    swag = Swagcli("https://petstore.swagger.io/v2/swagger.json", **option)
    swag.run()


if __name__ == "__main__":
    main()
