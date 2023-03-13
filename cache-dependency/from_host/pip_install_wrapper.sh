#!/bin/bash

# Run pip freeze before and after pip install command.
# If pip version is < 8, use pip freeze without --all option and then use pip list to get hidden dependencies
# Run diff to get the newly installed dependencies, then download the dependencies to $DEP_FOLDER
# if pip version is < 8, use pip install with --download option, otherwise, use pip download

DEP_FOLDER=$HOME/pypkg
DOWNLOAD_LOG=$HOME/dependencies.log

function get_current_deps () {
	# Find pip version
	PIP_MAJOR_VERSION=$(pip --disable-pip-version-check -V | cut -d' ' -f 2 | cut -d. -f 1)
	PIP_FREEZE="pip freeze --all --disable-pip-version-check"
	if [[ $PIP_MAJOR_VERSION -lt 8 ]]; then
		PIP_FREEZE="pip freeze --disable-pip-version-check"
	fi

	$PIP_FREEZE | grep "==" > ~/dependencies.txt

	if [[ $PIP_MAJOR_VERSION -lt 8 ]]; then
		pip --disable-pip-version-check list |
		while read -r line
		do
			regex="(\S+) \((\S+)\)"
			if [[ "$line" =~ $regex ]]; then
				if [[ ${BASH_REMATCH[1]} = "pip" || ${BASH_REMATCH[1]} = "setuptools" || ${BASH_REMATCH[1]} = "distribute" || ${BASH_REMATCH[1]} = "wheel" ]]; then
					if [[ -z $(grep "${BASH_REMATCH[1]}==" $DEP_LIST_FILE) ]]; then
						echo "${BASH_REMATCH[1]}==${BASH_REMATCH[2]}" >> ~/dependencies.txt
					fi
				fi
			fi
		done
	fi

	cat ~/dependencies.txt
}

function find_deps_diff_and_download () {
	# Find pip version
	PIP_MAJOR_VERSION=$(pip --disable-pip-version-check -V | cut -d' ' -f 2 | cut -d. -f 1)
	PIP_DOWNLOAD="pip download --disable-pip-version-check -d $DEP_FOLDER"
	if [[ $PIP_MAJOR_VERSION -lt 8 ]]; then
		PIP_DOWNLOAD="pip install --disable-pip-version-check --download=$DEP_FOLDER"
	fi

	diff <(echo "$original") <(echo "$final") |
	while read -r line
	do
		regex="> (\S+)"
		if [[ "$line" =~ $regex ]]; then
			echo "Downloading: ${BASH_REMATCH[1]}"
			$PIP_DOWNLOAD ${BASH_REMATCH[1]}
		fi
	done
}

echo "Caching pip dependencies..." >> $DOWNLOAD_LOG
mkdir -p $DEP_FOLDER
original=$(get_current_deps)
$@
final=$(get_current_deps)
find_deps_diff_and_download $original $final >> $DOWNLOAD_LOG 2>&1
