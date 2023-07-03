#!/usr/bin/env bash
# Untar cached dependency files
echo "Untarring dependencies (this may take a few seconds)"
sudo tar --directory / -xzf /home/github/home-m2-failed.tgz
sudo tar --directory / -xzf /home/github/home-gradle-failed.tgz
export GITHUB_WORKSPACE=/home/github/build/failed/consulo/consulo

set -o allexport
source /etc/environment
set +o allexport

export _GITHUB_JOB_STATUS=success

cd ${GITHUB_WORKSPACE}

echo "##[group]Operating System"
cat /etc/lsb-release | grep -oP '(?<=DISTRIB_ID=).*'
cat /etc/lsb-release | grep -oP '(?<=DISTRIB_RELEASE=).*'
echo "LTS"
echo "##[endgroup]"

mkdir -p /home/github/workflow/

cp /home/github/8409841338/event.json /home/github/workflow/event.json
echo -n > /home/github/workflow/envs.txt
echo -n > /home/github/workflow/paths.txt

CURRENT_ENV=()
update_current_env() {
  CURRENT_ENV=()
  unset CURRENT_ENV_MAP
  declare -gA CURRENT_ENV_MAP
  if [ -f /home/github/workflow/envs.txt ]; then
    local KEY=""
    local VALUE=""
    local DELIMITER=""
    local regex="(.*)<<(.*)"
    local regex2="(.*)=(.*)"

    while read line; do
      if [[ "$KEY" = "" && "$line" =~ $regex ]]; then
        KEY="${BASH_REMATCH[1]}"
        DELIMITER="${BASH_REMATCH[2]}"
      elif [[ "$KEY" != "" && "$line" = "$DELIMITER" ]]; then
        CURRENT_ENV_MAP["$KEY"]="$VALUE"
        KEY=""
        VALUE=""
        DELIMITER=""
      elif [[ "$KEY" != "" ]]; then
        if [[ $VALUE = "" ]]; then
          VALUE="$line"
        else
          VALUE="$VALUE
$line"
        fi
      elif [[ "$line" =~ $regex2 ]]; then
        CURRENT_ENV_MAP["${BASH_REMATCH[1]}"]="${BASH_REMATCH[2]}"
      fi
    done < /home/github/workflow/envs.txt

    for key in "${!CURRENT_ENV_MAP[@]}"; do
        val="${CURRENT_ENV_MAP["$key"]}"
        CURRENT_ENV+=("${key}=${val}")
    done
  else
    echo -n "" > /home/github/workflow/envs.txt
  fi
}

update_current_env
if [ -f /home/github/workflow/paths.txt ]; then
   while read NEW_PATH 
   do
      PATH="$(eval echo "$NEW_PATH"):$PATH"
   done <<< "$(cat /home/github/workflow/paths.txt)"
else
  echo -n '' > /home/github/workflow/paths.txt
fi

if [ ! -f /home/github/workflow/event.json ]; then
  echo -n '{}' > /home/github/workflow/event.json
fi

STEP_CONDITION=$(env CI=True GITHUB_TOKEN=DUMMY GITHUB_ACTION=1 GITHUB_ACTION_PATH='' GITHUB_ACTION_REPOSITORY=actions/setup-java GITHUB_ACTIONS=True GITHUB_ACTOR=VISTALL GITHUB_API_URL=https://api.github.com GITHUB_BASE_REF='' GITHUB_ENV=/home/github/workflow/envs.txt GITHUB_EVENT_NAME=push GITHUB_EVENT_PATH=/home/github/workflow/event.json GITHUB_GRAPHQL_URL=https://api.github.com/graphql GITHUB_HEAD_REF=valhalla GITHUB_JOB='' GITHUB_PATH=/home/github/workflow/paths.txt GITHUB_REF=refs/pull/513/merge GITHUB_REF_NAME=refs/pull/513/merge GITHUB_REF_TYPE=branch GITHUB_REPOSITORY=consulo/consulo GITHUB_REPOSITORY_OWNER=consulo GITHUB_RETENTION_DAYS=0 GITHUB_RUN_ATTEMPT=1 GITHUB_RUN_ID=1 GITHUB_RUN_NUMBER=1 GITHUB_SERVER_URL=https://github.com GITHUB_SHA=05318bff059d7024b7fb2e8a1e89eeea85cc503c GITHUB_STEP_SUMMARY='' GITHUB_WORKFLOW=jdk17 RUNNER_ARCH=X64 RUNNER_NAME='Bugswarm GitHub Actions Runner' RUNNER_OS=Linux RUNNER_TEMP=/tmp RUNNER_TOOL_CACHE=/opt/hostedtoolcache RUNNER_DEBUG=1 "${CURRENT_ENV[@]}" INPUT_JAVA-VERSION=17 INPUT_JAVA-PACKAGE=jdk INPUT_ARCHITECTURE=x64 INPUT_SERVER-ID=github INPUT_SERVER-USERNAME=GITHUB_ACTOR INPUT_SERVER-PASSWORD=GITHUB_TOKEN \
echo $(test "$_GITHUB_JOB_STATUS" = "success" && echo true || echo false))
if [[ "$STEP_CONDITION" = "true" ]]; then

echo "##[group]"Run actions/setup-java@v1
echo "##[endgroup]"
echo node /home/github/8409841338/actions/actions-setup-java@v1/dist/setup/index.js > /home/github/8409841338/steps/bugswarm_cmd.sh
chmod u+x /home/github/8409841338/steps/bugswarm_cmd.sh


EXIT_CODE=0
env CI=True GITHUB_TOKEN=DUMMY GITHUB_ACTION=1 GITHUB_ACTION_PATH='' GITHUB_ACTION_REPOSITORY=actions/setup-java GITHUB_ACTIONS=True GITHUB_ACTOR=VISTALL GITHUB_API_URL=https://api.github.com GITHUB_BASE_REF='' GITHUB_ENV=/home/github/workflow/envs.txt GITHUB_EVENT_NAME=push GITHUB_EVENT_PATH=/home/github/workflow/event.json GITHUB_GRAPHQL_URL=https://api.github.com/graphql GITHUB_HEAD_REF=valhalla GITHUB_JOB='' GITHUB_PATH=/home/github/workflow/paths.txt GITHUB_REF=refs/pull/513/merge GITHUB_REF_NAME=refs/pull/513/merge GITHUB_REF_TYPE=branch GITHUB_REPOSITORY=consulo/consulo GITHUB_REPOSITORY_OWNER=consulo GITHUB_RETENTION_DAYS=0 GITHUB_RUN_ATTEMPT=1 GITHUB_RUN_ID=1 GITHUB_RUN_NUMBER=1 GITHUB_SERVER_URL=https://github.com GITHUB_SHA=05318bff059d7024b7fb2e8a1e89eeea85cc503c GITHUB_STEP_SUMMARY='' GITHUB_WORKFLOW=jdk17 RUNNER_ARCH=X64 RUNNER_NAME='Bugswarm GitHub Actions Runner' RUNNER_OS=Linux RUNNER_TEMP=/tmp RUNNER_TOOL_CACHE=/opt/hostedtoolcache RUNNER_DEBUG=1 "${CURRENT_ENV[@]}" INPUT_JAVA-VERSION=17 INPUT_JAVA-PACKAGE=jdk INPUT_ARCHITECTURE=x64 INPUT_SERVER-ID=github INPUT_SERVER-USERNAME=GITHUB_ACTOR INPUT_SERVER-PASSWORD=GITHUB_TOKEN \
bash -e /home/github/8409841338/steps/bugswarm_cmd.sh
EXIT_CODE=$?


if [[ $EXIT_CODE != 0 ]]; then
  CONTINUE_ON_ERROR=$(env CI=True GITHUB_TOKEN=DUMMY GITHUB_ACTION=1 GITHUB_ACTION_PATH='' GITHUB_ACTION_REPOSITORY=actions/setup-java GITHUB_ACTIONS=True GITHUB_ACTOR=VISTALL GITHUB_API_URL=https://api.github.com GITHUB_BASE_REF='' GITHUB_ENV=/home/github/workflow/envs.txt GITHUB_EVENT_NAME=push GITHUB_EVENT_PATH=/home/github/workflow/event.json GITHUB_GRAPHQL_URL=https://api.github.com/graphql GITHUB_HEAD_REF=valhalla GITHUB_JOB='' GITHUB_PATH=/home/github/workflow/paths.txt GITHUB_REF=refs/pull/513/merge GITHUB_REF_NAME=refs/pull/513/merge GITHUB_REF_TYPE=branch GITHUB_REPOSITORY=consulo/consulo GITHUB_REPOSITORY_OWNER=consulo GITHUB_RETENTION_DAYS=0 GITHUB_RUN_ATTEMPT=1 GITHUB_RUN_ID=1 GITHUB_RUN_NUMBER=1 GITHUB_SERVER_URL=https://github.com GITHUB_SHA=05318bff059d7024b7fb2e8a1e89eeea85cc503c GITHUB_STEP_SUMMARY='' GITHUB_WORKFLOW=jdk17 RUNNER_ARCH=X64 RUNNER_NAME='Bugswarm GitHub Actions Runner' RUNNER_OS=Linux RUNNER_TEMP=/tmp RUNNER_TOOL_CACHE=/opt/hostedtoolcache RUNNER_DEBUG=1 "${CURRENT_ENV[@]}" INPUT_JAVA-VERSION=17 INPUT_JAVA-PACKAGE=jdk INPUT_ARCHITECTURE=x64 INPUT_SERVER-ID=github INPUT_SERVER-USERNAME=GITHUB_ACTOR INPUT_SERVER-PASSWORD=GITHUB_TOKEN \
echo false)
  if [[ "$CONTINUE_ON_ERROR" != "true" ]]; then 
    export _GITHUB_JOB_STATUS=failure
  fi
  echo "" && echo "##[error]Process completed with exit code $EXIT_CODE."

fi
fi

update_current_env
if [ -f /home/github/workflow/paths.txt ]; then
   while read NEW_PATH 
   do
      PATH="$(eval echo "$NEW_PATH"):$PATH"
   done <<< "$(cat /home/github/workflow/paths.txt)"
else
  echo -n '' > /home/github/workflow/paths.txt
fi

if [ ! -f /home/github/workflow/event.json ]; then
  echo -n '{}' > /home/github/workflow/event.json
fi

STEP_CONDITION=$(env CI=True GITHUB_TOKEN=DUMMY GITHUB_ACTION=2 GITHUB_ACTION_PATH='' GITHUB_ACTION_REPOSITORY='' GITHUB_ACTIONS=True GITHUB_ACTOR=VISTALL GITHUB_API_URL=https://api.github.com GITHUB_BASE_REF='' GITHUB_ENV=/home/github/workflow/envs.txt GITHUB_EVENT_NAME=push GITHUB_EVENT_PATH=/home/github/workflow/event.json GITHUB_GRAPHQL_URL=https://api.github.com/graphql GITHUB_HEAD_REF=valhalla GITHUB_JOB='' GITHUB_PATH=/home/github/workflow/paths.txt GITHUB_REF=refs/pull/513/merge GITHUB_REF_NAME=refs/pull/513/merge GITHUB_REF_TYPE=branch GITHUB_REPOSITORY=consulo/consulo GITHUB_REPOSITORY_OWNER=consulo GITHUB_RETENTION_DAYS=0 GITHUB_RUN_ATTEMPT=1 GITHUB_RUN_ID=1 GITHUB_RUN_NUMBER=1 GITHUB_SERVER_URL=https://github.com GITHUB_SHA=05318bff059d7024b7fb2e8a1e89eeea85cc503c GITHUB_STEP_SUMMARY='' GITHUB_WORKFLOW=jdk17 RUNNER_ARCH=X64 RUNNER_NAME='Bugswarm GitHub Actions Runner' RUNNER_OS=Linux RUNNER_TEMP=/tmp RUNNER_TOOL_CACHE=/opt/hostedtoolcache RUNNER_DEBUG=1 "${CURRENT_ENV[@]}" \
echo $(test "$_GITHUB_JOB_STATUS" = "success" && echo true || echo false))
if [[ "$STEP_CONDITION" = "true" ]]; then

echo "##[group]"Run 'mvn install -T 1C -Dmaven.javadoc.skip=true -B -V'
echo "##[endgroup]"
echo 'mvn install -T 1C -Dmaven.javadoc.skip=true -B -V' > /home/github/8409841338/steps/bugswarm_2.sh
chmod u+x /home/github/8409841338/steps/bugswarm_2.sh


EXIT_CODE=0
env CI=True GITHUB_TOKEN=DUMMY GITHUB_ACTION=2 GITHUB_ACTION_PATH='' GITHUB_ACTION_REPOSITORY='' GITHUB_ACTIONS=True GITHUB_ACTOR=VISTALL GITHUB_API_URL=https://api.github.com GITHUB_BASE_REF='' GITHUB_ENV=/home/github/workflow/envs.txt GITHUB_EVENT_NAME=push GITHUB_EVENT_PATH=/home/github/workflow/event.json GITHUB_GRAPHQL_URL=https://api.github.com/graphql GITHUB_HEAD_REF=valhalla GITHUB_JOB='' GITHUB_PATH=/home/github/workflow/paths.txt GITHUB_REF=refs/pull/513/merge GITHUB_REF_NAME=refs/pull/513/merge GITHUB_REF_TYPE=branch GITHUB_REPOSITORY=consulo/consulo GITHUB_REPOSITORY_OWNER=consulo GITHUB_RETENTION_DAYS=0 GITHUB_RUN_ATTEMPT=1 GITHUB_RUN_ID=1 GITHUB_RUN_NUMBER=1 GITHUB_SERVER_URL=https://github.com GITHUB_SHA=05318bff059d7024b7fb2e8a1e89eeea85cc503c GITHUB_STEP_SUMMARY='' GITHUB_WORKFLOW=jdk17 RUNNER_ARCH=X64 RUNNER_NAME='Bugswarm GitHub Actions Runner' RUNNER_OS=Linux RUNNER_TEMP=/tmp RUNNER_TOOL_CACHE=/opt/hostedtoolcache RUNNER_DEBUG=1 "${CURRENT_ENV[@]}" \
bash -e /home/github/8409841338/steps/bugswarm_2.sh
EXIT_CODE=$?


if [[ $EXIT_CODE != 0 ]]; then
  CONTINUE_ON_ERROR=$(env CI=True GITHUB_TOKEN=DUMMY GITHUB_ACTION=2 GITHUB_ACTION_PATH='' GITHUB_ACTION_REPOSITORY='' GITHUB_ACTIONS=True GITHUB_ACTOR=VISTALL GITHUB_API_URL=https://api.github.com GITHUB_BASE_REF='' GITHUB_ENV=/home/github/workflow/envs.txt GITHUB_EVENT_NAME=push GITHUB_EVENT_PATH=/home/github/workflow/event.json GITHUB_GRAPHQL_URL=https://api.github.com/graphql GITHUB_HEAD_REF=valhalla GITHUB_JOB='' GITHUB_PATH=/home/github/workflow/paths.txt GITHUB_REF=refs/pull/513/merge GITHUB_REF_NAME=refs/pull/513/merge GITHUB_REF_TYPE=branch GITHUB_REPOSITORY=consulo/consulo GITHUB_REPOSITORY_OWNER=consulo GITHUB_RETENTION_DAYS=0 GITHUB_RUN_ATTEMPT=1 GITHUB_RUN_ID=1 GITHUB_RUN_NUMBER=1 GITHUB_SERVER_URL=https://github.com GITHUB_SHA=05318bff059d7024b7fb2e8a1e89eeea85cc503c GITHUB_STEP_SUMMARY='' GITHUB_WORKFLOW=jdk17 RUNNER_ARCH=X64 RUNNER_NAME='Bugswarm GitHub Actions Runner' RUNNER_OS=Linux RUNNER_TEMP=/tmp RUNNER_TOOL_CACHE=/opt/hostedtoolcache RUNNER_DEBUG=1 "${CURRENT_ENV[@]}" \
echo false)
  if [[ "$CONTINUE_ON_ERROR" != "true" ]]; then 
    export _GITHUB_JOB_STATUS=failure
  fi
  echo "" && echo "##[error]Process completed with exit code $EXIT_CODE."

fi
fi

if [[ $_GITHUB_JOB_STATUS != "success" ]]; then
   exit 1
fi
