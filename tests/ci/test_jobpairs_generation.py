import os
import sys
import time
import requests

repo = 'BugSwarm/actions-pipeline-testing'
token = os.getenv('token')

api_url = 'https://api.github.com/repos/{}/actions/runs?per_page=4'.format(repo)
authorization = 'Token {}'.format(token)

starting_time = time.time()
TIMEOUT = 600  # Default timeout after 10 minutes
WAIT_INTERVAL = 30  # Wait 30 seconds then pull again


def main():
    while time.time() < starting_time + TIMEOUT:
        result = requests.get(api_url, headers={'Authorization': authorization})
        conclusion = set()

        for run in result.json()['workflow_runs']:
            if run['event'] == 'pull_request':
                if run['status'] == 'completed':
                    if run['conclusion'] == 'success':
                        if 'pull_request:success' in conclusion:
                            print('Multiple PR passed run')
                            return 1
                        conclusion.add('pull_request:success')
                    elif run['conclusion'] == 'failure':
                        if 'pull_request:failure' in conclusion:
                            print('Multiple PR failed run')
                            return 1
                        conclusion.add('pull_request:failure')
            elif run['event'] == 'push':
                if run['status'] == 'completed':
                    if run['conclusion'] == 'success':
                        if 'push:success' in conclusion:
                            print('Multiple non-PR passed run')
                            return 1
                        conclusion.add('push:success')
                    elif run['conclusion'] == 'failure':
                        if 'push:failure' in conclusion:
                            print('Multiple none-PR failed run')
                            return 1
                        conclusion.add('push:failure')

        if len(conclusion) == 4:
            print('Got 4 job pairs!')
            return 0

        time.sleep(WAIT_INTERVAL)

    print('Timeout: Cannot find valid job pairs within {} seconds'.format(TIMEOUT))
    return 1


if __name__ == '__main__':
    sys.exit(main())
