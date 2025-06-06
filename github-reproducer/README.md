# Reproducer
Reproduce jobs that originally ran on GitHub Actions by providing the same or a similar build environment. The goal is for the log generated by the reproduced job to match that of the job originally run on GitHub Actions.

## Learn More
To learn more about `reproducer`, see the following [docs](/docs/) articles:
- [What Happens When a Job Is Reproduced](/docs/What-Happens-When-a-Job-Is-Reproduced.md)
- [Reproducer Folder Structure Explained](/docs/Reproducer-Folder-Structure-Explained.md)
- [How Matching Is Defined for Reproducibility](/docs/How-Matching-Is-Defined-for-Reproducibility.md)

## Automatic Usage

Normally, you can use `run_reproduce_pair.sh` in the repo root to reproduce a set of job pairs.
(Pass the `--skip-cacher` argument if you don't want to run the [cacher](/github-cacher) after the reproducer.)
Note that the job pairs must have already been mined.

## Manual Usage

### 1. Pair Chooser

This step takes a list of job pairs and extracts their corresponding JSON from the `minedBuildPairs` database.
To use it, run:

```sh
python3 pair_chooser.py -o <output-file> [-r <repo>] [-f <failed-job-id>] [-p <passed-job-id>]
```

Or, if you have a CSV file containing a list of (repo, failed ID, passed ID) triplets, run:

```sh
python3 pair_chooser.py -o <output-file> [--pair-file <input-csv>]
```

### 2. Reproducer

This step runs a set of job pairs, capturing their logs and other information for use later in the pipeline.

```
python3 entry.py -i <pair-json> -o <task-name>_run<n> [options]
```

Required arguments:

- `-i`, `--input-file <file>`: The output file of the previous step; a JSON file containing the job pairs to reproduce.
- `-o`, `--task-name <task-name>_run<n>`: The name of this reproducer task; the name of the folder in `output/tasks` to put results into.
  **For this step only, it must end in "\_run`<n>`", where `<n>` is a number greater than 0.**
  If you want to reproduce the same set of job pairs multiple times (e.g. to account for flakiness), increment this number by 1 for each run.

Extra options:

- `-t`, `--threads <n>`: The number of worker processes (not threads) to use for reproducing.
  Defaults to 1.
- `-k`, `--keep`: Skip deletion of temporary files and temporary Docker images.
- `-s`, `--skip-disk-check`: Do not check whether there's enough free disk space when reproducing.
  The amount of free disk space required is set in [./reproducer/config.py](reproducer/config.py).

### 3. Results Analyzer

This step takes the output of 1 or more reproducer runs and checks whether the job pair is reproducible.

It puts its output in `output/results_json/<task-name>.json`.

```
python3 reproduced_results_analyzer.py -i <pair-json> -n <num-reproducer-runs> --task-name <task-name>
```

Required arguments:

- `-i`, `--input-file <file>`: The same input file as the last step; a JSON file containing the job pairs to reproduce.
- `-n`, `--runs <n>`: The number of times you ran the previous step.
- `--task-name`: The name of the reproducer task you used in the previous step (minus the "\_run<n>" part).

### 4. Image Packager

This step takes the reproducible job pairs (as determined in step 3), packages each into its own Docker image, and pushes them to the DockerHub repo specified in `bugswarm/common/credentials.py`.

```
python3 entry.py --package -i output/results_json/<task-name>.json -o <task-name>_pkg
```

Required arguments:

- `--package`: Tells the script to package job pairs into artifacts instead of trying to reproduce them.
- `-i`, `--input-file <file>`: The output file of the previous step; this should be `output/results_json/<task-name>.json`.
- `-o`, `--task-name <task-name>`: The name of this task; the name of the folder in `output/tasks` to put results into.

Extra options:

- `--no-push`: Build the images, but don't push them to DockerHub.
- `--cleanup-images`: Remove the images after pushing them to DockerHub.
