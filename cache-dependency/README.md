# Cache Dependency

## Overview
![The Overview](./resources/figures/process.png)
CacheDependency is a automated tool for caching BugSwarm artifacts' dependencies.
In following this README, we will run the tool to generate results and then evaluate those results.

## Usage
```
python3 CacheMaven.py <image-tag-file> <task-name>
```

* `image_tags_file`: Path to a file containing a newline-separated list of image tags to process.
* `task-name`: Name of the current task. Results will be put in `output/<task-name>.csv`.

    
## Output
Output files are placed in the `output` directory.
The name of the output file depends on the current task's name; if `<task-name>` is "foo", then the output file will be named `foo.csv`.

Each line in the output file follows this format:
```
image-tag, orginal-size, failed/succeed, increased-size, approach
```

1. `image-tag`: The name of the image tag attempted to be cached.
2. `original-size`: The size of the original Docker image.
3. `succeed` if the artifact's dependencies were successfully cached using the given approach; `failed` otherwise.
    * If the script is unable to get the artifact data for a given image tag from the database, `API error` is written and the next two columns are blank.
    * If an error occurs while attempting to verfy and cache an artifact, `error` is written and the next two columns are blank.
4. `increased-size`: How much the artifact's Docker image increased in size after its dependencies were cached.
   If dependencies could not be cached, `-1`.
5. `approach`: The approach that was attempted for this run. Currently one of `offline` or `build`.

## Caching Approaches
### Approach 1: offline
Uses the `dependency:go-offline` Maven plugin to resolve all project dependencies.

### Approach 2: build
Runs the failed and passed jobs using `run_failed.sh` and `run_passed.sh`, caching the dependencies in the process.
