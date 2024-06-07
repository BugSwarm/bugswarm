# What Happens When a Job Is Reproduced

Below is a high-level overview of what happens when a job is reproduced. The code for these steps are located in `{travis,github}-reproducer/pipeline/`. Read the source comments in that directory for details that are not described here, including checking for skipping, storing temporary files for reuse, etc.

### Step 1 - Generate Files
1. **Copy and reset the repository**: The repository is copied to a temporary directory and reset to the commit hash of the job to be reproduced.
2. **Generate the build script**: Based on the job's configuration, a shell script is generated that will be used to build the project.
3. **Generate the Dockerfile**: A Dockerfile is generated that will be used to build the Docker image. The base image is determined by the job's configuration.

### Step 2 - Build the Docker Image and Spawn the Docker Container

The Docker image is built using the generated Dockerfile.

### Step 3 - Examine the Reproducibility

The reproduced log is analyzed by Analyzer and compared with the original log. 

