# Run this test script inside a VM
GH_TOKEN=$1
TOKEN_USERNAME=$2
REPOSITORY=$3
BRANCH=$4

exit_if_failed () {
	if [ $? -ne 0 ]; then echo "::error::$1"; exit 1; fi
}


echo "::group::Step 0: Add GitHub credential for miner."
git config --global credential.helper store
echo "https://$TOKEN_USERNAME:$GH_TOKEN@github.com" > ~/.git-credentials
echo "::endgroup::"


echo "::group::Step 1: Clone repository to repo directory"
git clone -b "$BRANCH" "https://github.com/$REPOSITORY.git" repo
exit_if_failed "Failed to clone $REPOSITORY at branch $BRANCH"
echo "::endgroup::"


echo "::group::Step 2: Download latest bugswarm-db image from Docker Hub and run it."
docker pull bugswarm/containers:bugswarm-db
docker tag bugswarm/containers:bugswarm-db test-bugswarm-db
docker run -itd -p 127.0.0.1:27017:27017 -p 127.0.0.1:5000:5000 test-bugswarm-db
echo "::endgroup::"


echo "::group::Step 3: Install dependencies"
pushd repo
pip install -e .
exit_if_failed 'Failed to install dependencies.'
popd
echo "::endgroup::"


echo "::group::Step 4: Setup credentials.py"
pushd repo/bugswarm/common
cp credentials.sample.py credentials.py
sed -i "s/DATABASE_PIPELINE_TOKEN = .*/DATABASE_PIPELINE_TOKEN = 'testDBPassword'/g" credentials.py
sed -i "s/COMMON_HOSTNAME = .*/COMMON_HOSTNAME = '127.0.0.1:5000'/g" credentials.py
sed -i "s/GITHUB_TOKENS = .*/GITHUB_TOKENS = ['$GH_TOKEN']/g" credentials.py
sed -i "s/TRAVIS_TOKENS = .*/TRAVIS_TOKENS = ['<dummy travis token>']/g" credentials.py
sed -i "s/''/'#'/g" credentials.py
popd
echo "::endgroup::"


echo "::group::Step 5: Mine jobpairs"
pushd repo
sed -i "s/.*python3 pair_finder\.py.*/python3 pair_finder.py --repo \${repo} --threads \${threads} --cutoff-days 1/g" run_mine_project.sh
./run_mine_project.sh --ci github -r BugSwarm/actions-pipeline-testing
exit_if_failed 'Failed to mine project.'
popd


echo "::group::Step 6: Test reproducer"
pushd repo/github-reproducer
python3 pair_chooser.py -o test.json -r BugSwarm/actions-pipeline-testing
exit_if_failed 'Failed to get build pairs from database.'

python3 ~/repo/tests/ci/select_most_recent_buildpairs.py
exit_if_failed 'Failed to select the most recent build pairs.'

python3 entry.py -i test.json -t 8 -s -o test
exit_if_failed 'Failed to run reproducer.'

python3 ~/repo/tests/ci/check_reproducer.py
exit_if_failed 'Reproducer test failed.'
popd
echo "::endgroup::"


echo "::group::Step 7: Test cacher"
pushd repo/github-cacher/tests
python3 -m unittest integration_test_cache_maven.py
exit_if_failed 'Cacher test failed.'
popd
echo "::endgroup::"
