# SwagCli
Make easy command line interfaces using swagger config

`SwagCli` helps wrap up a quick python cli program for your API using `click` based on the [swagger](https://swagger.io/) `json` configuration schema of your API.

## Getting Started

### Installation 

Clone the repo locally:

```bash
$ git clone https://github.com/imthor/swagcli
```

Instal using pip3 with the following command:

```
$ cd swagcli && pip3 install -u .
```

### Example Usage

Save the below python code in `/tmp/cli`
```Python3
from swagcli import Swagcli

swag = Swagcli("https://petstore.swagger.io/v2/swagger.json")
swag.run()
```

That's it! We should be all set with a basic cli, run the python code and try playing with a cli version of your API
```
$ python3 /tmp/cli
Usage: cli [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  pet
  store
  user
  
$ python3 /tmp/cli pet -h
Usage: cli pet [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  delete
  findByStatus
  findByTags
  get
  post
  put
  uploadImage
  
$ python3 /tmp/cli pet get -h
Usage: cli pet get [OPTIONS] COMMAND [ARGS]...

Options:
  --petId INTEGER  ID of pet to return  [required]
  -h, --help       Show this message and exit.
  
$ python3 /tmp/cli pet get --petId 100
Pet not found

$ python3 /tmp/cli pet get --petId 101
{'id': 101, 'category': {'id': 503, 'name': 'Omy2Q-47RxRzBXck'}, 'name': 'doggie', 'photoUrls': ['3eVNgEWYNynWNVhF'], 'tags': [{'id': 506, 'name': "KVzozAs3By9WJR9m' AND SLEEP(2)=0 LIMIT 1 -- "}], 'status': 'sold'}

```

### Caveats
- This is initial version of the tool which is still under development

### Known Issues
- It will not be able to handle paths if there are different paths with same name - `/user` and `/user/{username}`
