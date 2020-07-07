# Cache Dependency

## Overview
![The Overview](./resources/figures/process.png)
CacheDependency is a automated tool for caching BugSwarm artifacts'
dependencies. In following this README, we will run the tool to generate
results and then evaluate those results.  
This evaluation

## Usage
`python3 CacheMaven.py <image-tag-file>`

image_tags_file: Path to a file containing a newline-separated list of image tags to process.

    
## Output
The output file `result.csv` is in the same directory which contains result for each artifact:

`image-tag, orginal-size, failed/succeed, increased-size, approach`

`approach` currently have `offline` and `build`:
1. offline: using mvn dependency:offline to resolve depenendency
2. build: actually build the target
