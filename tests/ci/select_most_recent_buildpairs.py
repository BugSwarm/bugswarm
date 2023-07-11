import sys
import json


def main():
    data = None
    with open('test.json', 'r') as f:
        data = json.load(f)

    if not data:
        print('Cannot open test.json file.')
        return 1

    latest_push_build_pair = None
    latest_pull_build_pair = None

    with open('test.json', 'w') as f:
        for build_pair in data:
            failed_build_id = build_pair['failed_build']['build_id']
            if build_pair['branch'] == 'pull_request':
                if (latest_pull_build_pair is None or
                        failed_build_id > latest_pull_build_pair['failed_build']['build_id']):
                    latest_pull_build_pair = build_pair
            else:
                if (latest_push_build_pair is None or
                        failed_build_id > latest_push_build_pair['failed_build']['build_id']):
                    latest_push_build_pair = build_pair

        if latest_push_build_pair and latest_pull_build_pair:
            json.dump([latest_push_build_pair, latest_pull_build_pair], f)
            return 0

    print('Cannot find the most recent job pairs.')
    print(data)
    return 1


if __name__ == "__main__":
    sys.exit(main())
