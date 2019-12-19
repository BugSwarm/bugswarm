# Common Library
Library of modules used throughout the BugSwarm toolset


## REST API Usage:
```
from bugswarm.common.rest_api.database_api import DatabaseAPI

bugswarmapi = DatabaseAPI(token='YOUR_TOKEN')
response = bugswarmapi.find_artifact("Abjad-abjad-289716771")
```
