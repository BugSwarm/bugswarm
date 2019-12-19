#!/usr/bin/env bash

ANSI_RED="\033[31;1m"
ANSI_GREEN="\033[32;1m"
ANSI_RESET="\033[0m"
ANSI_CLEAR="\033[0K"


# Prints `message` in green in compatible terminals.
#
# Usage: print_green <message>
print_green () {
    echo -e "\n${ANSI_GREEN}$1${ANSI_RESET}"
}


# Prints `message` in red in compatible terminals.
#
# Usage: print_red <message>
print_red () {
    echo -e "\n${ANSI_RED}$1${ANSI_RESET}"
}


# Prints `error-message` in context and then exits with 1 if the previous command exited with a non-zero code.
#
# Usage: exit_if_failed <error-message>
exit_if_failed () {
    if [ $? -ne 0 ]; then print_red "ERROR: $1 Exiting."; exit 1; fi
}


# Prints `done-message` in context. The text will appear green in compatible terminals.
# Use this function when a script completes successfully.
#
# Usage: print_done_message <done-message>
print_done_message () {
    print_green "Done! $1"
}


# Prints a message indicating that the current stage in a script has completed successfully. The text will appear green
# in compatible terminals.
# Use this function when a stage in a script completes successfully.
#
# Usage: print_stage_done <stage-name>
print_stage_done () {
    print_done_message "The $1 stage completed successfully."
}


# Checks if `project-directory` exists but does not determine whether it is actually a Git repository.
# Exits with 1 if `project-directory` does not exist.
#
# Usage: check_repo_exists <project-directory> <project-name>
check_repo_exists () {
    if [ ! -d $1 ]; then
        echo "$1 does not exist. Make sure you cloned $2 or specified a component directory."; exit 1;
    fi
}


# Prints a message that gives context for the current step of the current stage in a script.
#
# After sourcing the script that contains this function, `current_step` is 1. Each call to this function increments
# `current_step`. Thus, the script that contains this function must be sourced again when a new stage begins.
#
# Usage: print_step <stage-name> <total-steps> <step-name>
current_step=1
print_step () {
    print_green "$1 stage, step ${current_step} of $2: $3"; ((current_step++))
}
