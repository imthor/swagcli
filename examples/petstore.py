"""
Sample cli for swagger petstore
"""

from swagcli import Swagcli


def main():
    """
    Pet Store runner
    """
    swag = Swagcli("https://petstore.swagger.io/v2/swagger.json")
    swag.run()


if __name__ == "__main__":
    main()
