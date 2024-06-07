# How Matching Is Defined for Reproducibility

## Overview
The term **matching** describes whether the attributes extracted from the reproduced build log are equivalent to those extracted from the original build log.

## Compared Attributes
The following is a subset of attributes compared to decide matching.
1. Job status (one of failed, passed, or errored)
1. Total number of tests passed
1. Total number of tests failed
1. Total number of tests run
1. Total number of tests skipped
1. Function names of failed tests

If any of the compared attributes are not equivalent, the job is labeled mismatched.
