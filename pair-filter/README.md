# Pair Filter
`pair-filter` detects and labels jobpairs that we are not interested in reproducing.

When `pair-filter` detects a pair that should not be reproduced, it modifies the JSON representation of the pair by
1. setting the `filtered_out_reason` key to a human-readable string explaining why the pair was filtered.
1. setting the `is_filtered_out` key to `true`.

Later in the pipeline, `pair-classifier` and `reproducer` will handle skipping the labeled pairs. 

## Usage
```
$ python3 pair-filter.py <repo> <dir_of_jsons>

    <repo>          The GitHub slug for the project whose pairs are being filtered. Used when updating the mined projects collection in the database.
    <dir_of_jsons>  Input directory containing JSON files of pairs. This directory could be within the
                    PairFinder output directory.
```
_Example:_
```
$ python3 pair-filter.py Flipkart/foxtrot ~/bugswarm/pair-filter/output-json/Flipkart-foxtrot.json
```

## Filters
`pair-filter` currently uses the following filters:
1. `filter_no_sha` detects pairs for which we are either missing the trigger or base commit.
1. `filter_same_commit`
    is a sanity check filter that detects when, very rarely, there are pairs where the failed and passed builds have the same trigger commit.
    > At this time, we are not entirely sure why this happens. In the past, we discussed the idea that an intra-branch build on a pull request could result in a single commit triggering two builds. However, we are not sure if all the pairs found by this filter are in face such intra-branch pairs. Nevertheless, if the failed and passed builds have the same trigger commit, we filter the pair.
1. `filter_unavailable` detects pairs that both non-resettable and not archived by GitHub. A pair is non-resettable if
    the trigger commit or base commit of either the failed build or passed build is not found in the project's git log.
    The attributes that indicates resettable and archived by GitHub are set by pair-finder.
1. `filter_non_quay_images` detects pairs that did not use Quay travis images. See [Why We Are Reproducing Only Quay Pairs](https://github.com/BugSwarm/reproducer/wiki/Why-We-Are-Reproducing-Only-QUAY-Pairs) for details.
