# Common Library
Library of modules used throughout the BugSwarm toolset.


## REST API Usage:

### Import the DatabaseAPI and create an instance of it.
```
>>> from bugswarm.common.rest_api.database_api import DatabaseAPI
>>> bugswarmapi = DatabaseAPI(token='AN_OPTIONAL_TOKEN')
>>> unauthenticated_api = DatabaseAPI()  # Rate limited
```

### Using the API to filter artifacts such that artifacts that are returned are: Java and flaky.
```
>>> api_filter = '{"reproduce_successes":{"$gt":0, "$lt":5}, "lang":"Java"}'
>>> bugswarmapi.filter_artifacts(api_filter)
```

### Using the API to retrieve metadata for one artifact.
```
>>> bugswarmapi.find_artifact('Abjad-abjad-289716771')
```
### Using the API to retrieve metadata for all artifacts that are Java or Python and have at least one reproduce success.
```
>>> bugswarmapi.list_artifacts()
```
