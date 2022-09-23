import json
from .github_builder import GitHubBuilder


class EventBuilder:

    def __init__(self, github_builder: GitHubBuilder):
        self.github_builder = github_builder
        self.event = {}
        self.generate_event()

    def generate_json(self, output_path):
        with open(output_path, 'w') as f:
            json.dump(self.event, f, indent=4)

    def generate_event(self):
        self.event = {
            'after': '',
            'base_ref': self.github_builder.GITHUB_BASE_REF if len(self.github_builder.GITHUB_BASE_REF) > 0 else None,
            'before': '',
            'commits': [
                # Limitation: only show the latest commit. (Head commit)
                {
                    'author': {
                        'email': self.github_builder.HEAD_COMMIT.get('author', {}).get('email', ''),
                        'name': self.github_builder.HEAD_COMMIT.get('author', {}).get('name', ''),
                        'username': self.github_builder.TRIGGERING_ACTOR

                    },
                    'committer': {
                        'email': 'noreply@github.com',
                        'name': 'GitHub',
                        'username': 'web-flow'
                    },
                    'distinct': True,
                    'id': self.github_builder.job.sha,
                    'message': self.github_builder.HEAD_COMMIT.get('message', ''),
                    'timestamp': self.github_builder.HEAD_COMMIT.get('timestamp', ''),
                    'tree_id': self.github_builder.HEAD_COMMIT.get('tree_id', ''),
                    'url': ''
                }
            ],
            'compare': '',
            'created': False,
            'deleted': False,
            'forced': False,
            'head_commit': {
                'author': {
                    'email': self.github_builder.HEAD_COMMIT.get('author', {}).get('email', ''),
                    'name': self.github_builder.HEAD_COMMIT.get('author', {}).get('name', ''),
                    'username': self.github_builder.TRIGGERING_ACTOR

                },
                'committer': {
                    'email': 'noreply@github.com',
                    'name': 'GitHub',
                    'username': 'web-flow'
                },
                'distinct': True,
                'id': self.github_builder.job.sha,
                'message': self.github_builder.HEAD_COMMIT.get('message', ''),
                'timestamp': self.github_builder.HEAD_COMMIT.get('timestamp', ''),
                'tree_id': self.github_builder.HEAD_COMMIT.get('tree_id', ''),
                'url': ''
            },
            'pusher': {
                'email': self.github_builder.HEAD_COMMIT.get('author', {}).get('email', ''),
                'name': self.github_builder.TRIGGERING_ACTOR
            },
            'ref': self.github_builder.GITHUB_REF,
            'repository': {
                'allow_forking': True,
                'archive_url': self.github_builder.REPOSITORY.get('archive_url', ''),
                'archived': False,
                'assignees_url': self.github_builder.REPOSITORY.get('assignees_url', ''),
                'blobs_url': self.github_builder.REPOSITORY.get('blobs_url', ''),
                'branches_url': self.github_builder.REPOSITORY.get('branches_url', ''),
                'clone_url': 'https://github.com/{}.git'.format(self.github_builder.job.repo),
                'collaborators_url': self.github_builder.REPOSITORY.get('collaborators_url', ''),
                'comments_url': self.github_builder.REPOSITORY.get('comments_url', ''),
                'commits_url': self.github_builder.REPOSITORY.get('commits_url', ''),
                'compare_url': self.github_builder.REPOSITORY.get('compare_url', ''),
                'contents_url': self.github_builder.REPOSITORY.get('contents_url', ''),
                'contributors_url': self.github_builder.REPOSITORY.get('contributors_url', ''),
                'created_at': 0,
                'default_branch': 'master',
                'deployments_url': self.github_builder.REPOSITORY.get('deployments_url', ''),
                'description': self.github_builder.REPOSITORY.get('description', ''),
                'disabled': False,
                'downloads_url': self.github_builder.REPOSITORY.get('downloads_url', ''),
                'events_url': self.github_builder.REPOSITORY.get('events_url', ''),
                'fork': self.github_builder.REPOSITORY.get('fork', ''),
                'forks': 0,
                'forks_count': 0,
                'forks_url': self.github_builder.REPOSITORY.get('forks_url', ''),
                'full_name': self.github_builder.REPOSITORY.get('full_name', ''),
                'git_commits_url': self.github_builder.REPOSITORY.get('git_commits_url', ''),
                'git_refs_url': self.github_builder.REPOSITORY.get('git_refs_url', ''),
                'git_tags_url': self.github_builder.REPOSITORY.get('git_tags_url', ''),
                'git_url': 'git://github.com/{}.git'.format(self.github_builder.job.repo),
                'has_downloads': True,
                'has_issues': True,
                'has_pages': True,
                'has_projects': True,
                'has_wiki': True,
                'homepage': None,
                'hooks_url': self.github_builder.REPOSITORY.get('hooks_url', ''),
                'html_url': self.github_builder.REPOSITORY.get('html_url', ''),
                'id': self.github_builder.REPOSITORY.get('id', 0),
                'is_template': False,
                'issue_comment_url': self.github_builder.REPOSITORY.get('issue_comment_url', ''),
                'issue_events_url': self.github_builder.REPOSITORY.get('issue_events_url', ''),
                'issues_url': self.github_builder.REPOSITORY.get('issues_url', ''),
                'keys_url': self.github_builder.REPOSITORY.get('keys_url', ''),
                'labels_url': self.github_builder.REPOSITORY.get('labels_url', ''),
                'language': '',
                'languages_url': self.github_builder.REPOSITORY.get('languages_url', ''),
                'license': None,
                'master_branch': 'master',
                'merges_url': self.github_builder.REPOSITORY.get('merges_url', ''),
                'milestones_url': self.github_builder.REPOSITORY.get('milestones_url', ''),
                'mirror_url': None,
                'name': self.github_builder.REPOSITORY.get('name', ''),
                'node_id': self.github_builder.REPOSITORY.get('node_id', ''),
                'notifications_url': self.github_builder.REPOSITORY.get('notifications_url', ''),
                'open_issues': 0,
                'open_issues_count': 0,
                'owner': {
                    'avatar_url': self.github_builder.REPOSITORY.get('owner', {}).get('avatar_url', ''),
                    'email': '',
                    'events_url': self.github_builder.REPOSITORY.get('owner', {}).get('events_url', ''),
                    'followers_url': self.github_builder.REPOSITORY.get('owner', {}).get('followers_url', ''),
                    'following_url': self.github_builder.REPOSITORY.get('owner', {}).get('following_url', ''),
                    'gists_url': self.github_builder.REPOSITORY.get('owner', {}).get('gists_url', ''),
                    'gravatar_id': '',
                    'html_url': self.github_builder.REPOSITORY.get('owner', {}).get('html_url', ''),
                    'id': self.github_builder.REPOSITORY.get('owner', {}).get('id', 0),
                    'login': self.github_builder.REPOSITORY.get('owner', {}).get('login', ''),
                    'name': self.github_builder.REPOSITORY.get('owner', {}).get('login', ''),
                    'node_id': self.github_builder.REPOSITORY.get('owner', {}).get('node_id', ''),
                    'organizations_url': self.github_builder.REPOSITORY.get('owner', {}).get('organizations_url', ''),
                    'received_events_url': self.github_builder.REPOSITORY.get('owner', {}).get('received_events_url', ''),
                    'repos_url': self.github_builder.REPOSITORY.get('owner', {}).get('repos_url', ''),
                    'site_admin': self.github_builder.REPOSITORY.get('owner', {}).get('site_admin', False),
                    'starred_url': self.github_builder.REPOSITORY.get('owner', {}).get('starred_url', ''),
                    'subscriptions_url': self.github_builder.REPOSITORY.get('owner', {}).get('subscriptions_url', ''),
                    'type': self.github_builder.REPOSITORY.get('owner', {}).get('type', ''),
                    'url': self.github_builder.REPOSITORY.get('owner', {}).get('url', ''),
                },
                'private': self.github_builder.REPOSITORY.get('private', False),
                'pulls_url': self.github_builder.REPOSITORY.get('pulls_url', ''),
                'pushed_at': 0,
                'releases_url': self.github_builder.REPOSITORY.get('releases_url', ''),
                'size': 4253,
                'ssh_url': 'git@github.com:{}.git'.format(self.github_builder.job.repo),
                'stargazers': 0,
                'stargazers_count': 0,
                'stargazers_url': self.github_builder.REPOSITORY.get('stargazers_url', ''),
                'statuses_url': self.github_builder.REPOSITORY.get('statuses_url', ''),
                'subscribers_url': self.github_builder.REPOSITORY.get('subscribers_url', ''),
                'subscription_url': self.github_builder.REPOSITORY.get('subscription_url', ''),
                'svn_url': 'https://github.com/{}'.format(self.github_builder.job.repo),
                'tags_url': self.github_builder.REPOSITORY.get('tags_url', ''),
                'teams_url': self.github_builder.REPOSITORY.get('teams_url', ''),
                'topics': [],
                'trees_url': self.github_builder.REPOSITORY.get('trees_url', ''),
                'updated_at': self.github_builder.HEAD_COMMIT.get('timestamp', ''),
                'url': self.github_builder.REPOSITORY.get('url', ''),
                'visibility': 'public',
                'watchers': 0,
                'watchers_count': 0,
                'web_commit_signoff_required': False
            },
            'sender': {
                # Limitation: assume owner is the sender
                'avatar_url': self.github_builder.REPOSITORY.get('owner', {}).get('avatar_url', ''),
                'email': '',
                'events_url': self.github_builder.REPOSITORY.get('owner', {}).get('events_url', ''),
                'followers_url': self.github_builder.REPOSITORY.get('owner', {}).get('followers_url', ''),
                'following_url': self.github_builder.REPOSITORY.get('owner', {}).get('following_url', ''),
                'gists_url': self.github_builder.REPOSITORY.get('owner', {}).get('gists_url', ''),
                'gravatar_id': '',
                'html_url': self.github_builder.REPOSITORY.get('owner', {}).get('html_url', ''),
                'id': self.github_builder.REPOSITORY.get('owner', {}).get('id', 0),
                'login': self.github_builder.REPOSITORY.get('owner', {}).get('login', ''),
                'name': self.github_builder.REPOSITORY.get('owner', {}).get('login', ''),
                'node_id': self.github_builder.REPOSITORY.get('owner', {}).get('node_id', ''),
                'organizations_url': self.github_builder.REPOSITORY.get('owner', {}).get('organizations_url', ''),
                'received_events_url': self.github_builder.REPOSITORY.get('owner', {}).get('received_events_url', ''),
                'repos_url': self.github_builder.REPOSITORY.get('owner', {}).get('repos_url', ''),
                'site_admin': self.github_builder.REPOSITORY.get('owner', {}).get('site_admin', False),
                'starred_url': self.github_builder.REPOSITORY.get('owner', {}).get('starred_url', ''),
                'subscriptions_url': self.github_builder.REPOSITORY.get('owner', {}).get('subscriptions_url', ''),
                'type': self.github_builder.REPOSITORY.get('owner', {}).get('type', ''),
                'url': self.github_builder.REPOSITORY.get('owner', {}).get('url', ''),
            }
        }
