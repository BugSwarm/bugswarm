import os
import datetime
import json
import pprint
import sys
import secrets
import requests
import requests.auth

from datetime import date
from typing import Dict
from typing import Generator
from typing import List
from urllib.parse import urljoin
from requests import Response

from ..decorators.classproperty import classproperty
from ..decorators.classproperty import classproperty_support
from .. import log
from bugswarm.common.credentials import COMMON_HOSTNAME

__all__ = ['Endpoint', 'DatabaseAPI']

Endpoint = str


@classproperty_support
class DatabaseAPI(object):
    """
    This class encapsulates programmatic access to the BugSwarm metadata database via the REST API.
    """
    # The base URL must include 'www'. Otherwise, the redirect performed by the backend will cause the requests library
    # to strip authorization headers, which are needed for authentication.
    # See https://github.com/requests/requests/issues/2949 for more information.
    _HOSTNAME = COMMON_HOSTNAME
    if not _HOSTNAME:
        print('[ERROR]: COMMON_HOSTNAME has not been found. Please set the environmental variable and reinstall '
              'common package')
        sys.exit(1)
    _API_VERSION = 'v1'
    _BASE_URL = 'http://{}/{}'.format(_HOSTNAME, _API_VERSION)
    _ARTIFACTS_RESOURCE = 'artifacts'
    _MINED_BUILD_PAIRS_RESOURCE = 'minedBuildPairs'
    _MINED_PROJECTS_RESOURCE = 'minedProjects'
    _EMAIL_SUBSCRIBERS_RESOURCE = 'emailSubscribers'
    _ACCOUNTS_RESOURCE = 'accounts'
    _LOGS_RESOURCE = 'logs'

    def __init__(self, token: str):
        """
        Provide a valid authentication token in order to use the endpoints accessible by the account that is associated
        with the token. If an invalid authentication token is provided, the initializer will raise an exception.

        :param token: An authentication token.
        :raises InvalidToken: When an invalid authentication token is provided.
        """
        if not isinstance(token, str):
            raise TypeError
        if not token:
            raise ValueError
        self.token = token
        self.auth = requests.auth.HTTPBasicAuth(username=self.token, password='')

    ###################################
    # Class properties
    ###################################

    @classproperty
    def base_url(cls) -> Endpoint:
        """
        Exposes the base URL of the API as a read-only class property.
        """
        return cls._BASE_URL

    @classproperty
    def hostname(cls) -> Endpoint:
        """
        Exposes the hostname of the API as a read-only class property.
        """
        return cls._HOSTNAME

    ###################################
    # Artifact REST methods
    ###################################

    def insert_artifact(self, artifact) -> Response:
        return self._insert(DatabaseAPI._artifacts_endpoint(), artifact, 'artifact')

    def patch_artifact(self, image_tag, updates) -> Response:
        if not image_tag:
            raise ValueError
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def find_artifact(self, image_tag: str, error_if_not_found: bool = True) -> Response:
        """
        Get artifact data based on image_tag.
        :param image_tag: The image tag identifying the artifact to find.
        :param error_if_not_found: return err if the image tag not found. default True.
        :return: The response object.
        e.g. find_artifact("Abjad-abjad-289716771")
        """
        log.debug('Trying to find artifact with image_tag {}.'.format(image_tag))
        return self._get(DatabaseAPI._artifact_image_tag_endpoint(image_tag), error_if_not_found)

    def list_artifacts(self) -> List:
        """
        Return a List of artifacts that has at least one reproduce_successes.
        """
        api_filter = '{"reproduce_successes":{"$gt":0}}'
        return self.filter_artifacts(api_filter)

    def filter_artifacts(self, api_filter: str) -> List:
        """
        Return a list of artifacts based on custom filter.
        :param api_filter: a string filter.
        e.g.: api_filter = '{"reproduce_successes":{"$gt":0},"lang":{"$in":["Java","Python"]}}'
        """
        return self._filter(DatabaseAPI._artifacts_endpoint(), api_filter)

    def count_artifacts(self) -> int:
        return self._count(DatabaseAPI._artifacts_endpoint())

    def set_artifact_metric(self, image_tag: str, metric_name: str, metric_value) -> Response:
        """
        Add a metric to an existing artifact.
        The value of the metric can be any valid database type.

        If the metric with name `metric_name` already exists, then its value will be overridden with `metric_value`.
        Otherwise, the metric will be created with value `metric_value`.

        :param image_tag: The image tag identifying the artifact to update.
        :param metric_name: The name of the metric to add or update.
        :param metric_value: The new value of the metric.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        if not isinstance(metric_name, str):
            raise TypeError
        if not metric_name:
            raise ValueError
        updates = {'metrics.{}'.format(metric_name): metric_value}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_failed_config(self, image_tag: str, config) -> Response:
        """
        Add the configuration of the job to an existing artifact's failed job metadata.

        :param image_tag: The image tag identifying the artifact to update.
        :param config: The configuration of the job.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        updates = {'failed_job.config': config}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_passed_config(self, image_tag: str, config) -> Response:
        """
        Add the configuration of the job to an existing artifact's passed job metadata.

        :param image_tag: The image tag identifying the artifact to update.
        :param config: The configuration of the job.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        updates = {'passed_job.config': config}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_classification_exceptions(self, image_tag: str, exceptions) -> Response:
        """
        Add the code exceptions to an existing artifact's classification metadata.

        :param image_tag: The image tag identifying the artifact to update.
        :param exceptions: The standard code exceptions for the artifact.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        updates = {'classification.exceptions': exceptions}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_classification_category(self, image_tag: str, category_type: str, category_confidence) -> Response:
        """
        Add a classification to an existing artifact.

        If the metric with name `category_type` already exists, then its value will be overridden with
        `category_confidence`. Otherwise, the metric will be created with value `category_confidence`.

        :param image_tag: The image tag identifying the artifact to update.
        :param category_type: The name of the category type to update.
        :param category_confidence: The new confidence value of the category.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        if not isinstance(category_type, str):
            raise TypeError
        if not category_type:
            raise ValueError
        updates = {'classification.{}'.format(category_type): category_confidence}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_failed_patch(self, image_tag: str, patch_name: str) -> Response:
        """
        Add the patch for the artifact to an existing artifact's failed job metadata.

        :param image_tag: The image tag identifying the artifact to update.
        :param patch_name: Name of patch that was applied
        :param patch: The patch that was added to the artifact.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        today = str(date.today())
        updates = {'failed_job.patches.{}'.format(patch_name): today}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_passed_patch(self, image_tag: str, patch_name: str) -> Response:
        """
        Add the patch for the artifact to an existing artifact's passed job metadata.

        :param image_tag: The image tag identifying the artifact to update.
        :param patch_name: Name of patch that was applied
        :param patch: The patch that was added to the artifact.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        today = str(date.today())
        updates = {'passed_job.patches.{}'.format(patch_name): today}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_reproduce_successes(self, image_tag: str, successes: int) -> Response:
        """
        Update the reproduce_successes of the job to an existing artifact's failed job metadata.

        :param image_tag: The image tag identifying the artifact to update.
        :param successes: The number of reproduce_successes of the job.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        updates = {'reproduce_successes': int(successes)}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_stability(self, image_tag: str, stability) -> Response:
        """
        Update the stability of the job to an existing artifact's failed job metadata.

        :param image_tag: The image tag identifying the artifact to update.
        :param stability: The reproduce_successes the job.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        updates = {'stability': stability}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def set_artifact_current_status(self, image_tag: str, status: str, date: str) -> Response:
        """
        Update the current status of an artifact.

        :param image_tag: The image tag identifying the artifact to update.
        :param status: Unreproducible/Reproducible/Broken/Flaky.
        :param date: the date (YYYY-MM-DD) of artifacts status changed
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        if status not in ['Unreproducible', 'Reproducible', 'Broken', 'Flaky']:
            raise ValueError("Incorrect status, should be Unreproducible/Reproducible/Broken/Flaky")
        try:
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DD")
        updates = {'current_status': {'status': status, 'time_stamp': date}}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    def update_artifact_repo_name(self, image_tag: str, new_repo: str) -> Response:
        """
        Update the repository name of an artifact.
        :param image_tag: The image tag identifying the artifact to update.
        :param new_repo: The updated repo name we are setting.
        :return: The response object.
        """
        if not isinstance(image_tag, str):
            raise TypeError
        if not isinstance(new_repo, str):
            raise TypeError
        updates = {'repo': new_repo}
        return self._patch(DatabaseAPI._artifact_image_tag_endpoint(image_tag), updates)

    ###################################
    # Logs REST methods
    ###################################
    def set_build_log(self, job_id: str, build_log_fp: str) -> Response:
        """
        Add the failed or passed build log for the artifact to the logs collection.
        :param job_id: The job id corresponding to the passed or failed build log.
        :param build_log_fp: The path for the build log to be loaded into the database.
        :return: The response object.
        """
        if not isinstance(job_id, str):
            raise TypeError
        if not job_id:
            raise ValueError
        if not isinstance(build_log_fp, str):
            raise TypeError
        if not build_log_fp:
            raise ValueError
        if not os.path.exists(build_log_fp):
            raise IOError
        with open(build_log_fp, 'r') as build_log:
            build_log_text = build_log.read()
        log_entry = {
            'job_id': job_id,
            'build_log': build_log_text,
        }
        return self._insert(DatabaseAPI._logs_endpoint(), log_entry, 'log')

    def get_build_log(self, job_id: str, error_if_not_found: bool = True) -> Response:
        """
        Get artifact failed or passed build log based on job id.
        :param job_id: The job id corresponding to the passed or failed build log.
        :param error_if_not_found: return err if the image tag not found. default True.
        :return: The build_log.
        """
        if not isinstance(job_id, str):
            raise TypeError
        if not job_id:
            raise ValueError
        log_object = self._get(DatabaseAPI._logs_job_id_endpoint(job_id), error_if_not_found).json()
        return log_object['build_log']

    ###################################
    # Mined Build Pair REST methods
    ###################################
    def patch_job_pairs(self, obj_id: str, job_pairs) -> Response:
        updates = {'jobpairs': job_pairs}
        return self._patch(DatabaseAPI._mined_build_pair_object_id_endpoint(obj_id), updates)

    def insert_mined_build_pair(self, mined_build_pair) -> Response:
        return self._insert(DatabaseAPI._mined_build_pairs_endpoint(), mined_build_pair, 'mined build pair')

    def bulk_insert_mined_build_pairs(self, mined_build_pairs) -> bool:
        return all(self._bulk_insert(DatabaseAPI._mined_build_pairs_endpoint(), mined_build_pairs, 'mined build pairs'))

    def find_mined_build_pair(self, object_id: str, error_if_not_found: bool = True) -> Response:
        log.debug('Trying to find mined build pairs for ObjectId {}.'.format(object_id))
        return self._get(DatabaseAPI._mined_build_pair_object_id_endpoint(object_id), error_if_not_found)

    def list_mined_build_pairs(self) -> List:
        return self._list(DatabaseAPI._mined_build_pairs_endpoint())

    def filter_mined_build_pairs(self, api_filter: str) -> List:
        return self._filter(DatabaseAPI._mined_build_pairs_endpoint(), api_filter)

    def count_mined_build_pairs(self) -> int:
        return self._count(DatabaseAPI._mined_build_pairs_endpoint())

    def filter_mined_build_pairs_for_repo(self, repo: str) -> List:
        """
        Returns a list of build pairs mined from `repo`. Returns an empty list if no build pairs for `repo` are found or
        if `repo` has not yet been mined.
        """
        return self._filter(DatabaseAPI._mined_build_pairs_endpoint(), '{{"repo": "{}"}}'.format(repo))

    def remove_mined_build_pairs_for_repo(self, repo: str) -> bool:
        """
        Non-atomically remove the existing mined build pairs for `repo`.

        If your goal is to replace mined build pairs for `repo`, you should use `replace_mined_build_pairs_for_repo`.
        """
        for bp in self.filter_mined_build_pairs_for_repo(repo):
            if not self._delete(DatabaseAPI._mined_build_pair_object_id_endpoint(bp['_id'])):
                log.error('Could not remove an existing mined build pair for {}.'.format(repo))
                return False
        return True

    def replace_mined_build_pairs_for_repo(self, repo: str, new_build_pairs: List[Dict]) -> bool:
        """
        Non-atomically remove the existing mined build pairs for `repo` and then non-atomically insert the newly mined
        build pairs for `repo` in `new_build_pairs`.
        """
        if not self.remove_mined_build_pairs_for_repo(repo):
            return False
        # Take advantage of bulk insertions.
        if not self.bulk_insert_mined_build_pairs(new_build_pairs):
            log.error('While replacing mined build pairs, a bulk insertion failed.')
            return False
        return True

    def update_mined_build_pairs_repo_name(self, obj_id: str, new_repo: str) -> Response:
        """
        Update the repository name of an artifact in the minedBuildPairs db.
        :param obj_id: The unique id of an object.
        :param new_repo: The updated repo name we are setting.
        :return: The response object.
        """
        if not isinstance(new_repo, str):
            raise TypeError
        updates = {'repo': new_repo}
        return self._patch(DatabaseAPI._mined_build_pair_object_id_endpoint(obj_id), updates)

    ###################################
    # Mined Project REST methods
    ###################################

    def insert_mined_project(self, mined_project) -> Response:
        return self._insert(DatabaseAPI._mined_projects_endpoint(), mined_project, 'mined project')

    def find_mined_project(self, repo: str, ci_service: str, error_if_not_found: bool = True) -> Response:
        log.debug('Trying to find mined project with repo {} and CI service {}.'.format(repo, ci_service))
        return self._get(DatabaseAPI._mined_project_repo_endpoint(repo, ci_service), error_if_not_found)

    def list_mined_projects(self) -> List:
        return self._list(DatabaseAPI._mined_projects_endpoint())

    def filter_mined_projects(self, api_filter: str) -> List:
        return self._filter(DatabaseAPI._mined_projects_endpoint(), api_filter)

    # TODO should this count repos, or repo-CI pairs?
    def count_mined_projects(self) -> int:
        return self._count(DatabaseAPI._mined_projects_endpoint())

    def upsert_mined_project(self, mined_project) -> Response:
        """
        Upsert a mined project. Can be used for initial mining or re-mining of a project.
        """
        repo = mined_project.get('repo')
        ci_service = mined_project.get('ci_service')
        assert repo
        assert ci_service
        return self._upsert(DatabaseAPI._mined_project_repo_endpoint(repo, ci_service), mined_project, 'mined project')

    def set_latest_build_info_metric(self, repo: str, ci_service: str, build_number: int, build_id: int):
        """
        Set the build information regarding the build number and build id of the latest build we've mined.

        :param repo: The repository slug for identifying the mined project to update.
        :param ci_service: The CI service for identifying the project to update.
        :param build_number: The latest build number associated to the last build we've mined
        :param build_id: The latest build id associated to the last build we've mined
        :return: The response object.
        """
        if not isinstance(repo, str):
            raise TypeError
        if not repo:
            raise ValueError
        if not isinstance(build_number, int):
            raise TypeError
        if not build_number:
            raise ValueError
        if not isinstance(build_id, int):
            raise TypeError
        if not build_id:
            raise ValueError
        updates = {
            'last_build_mined.build_number': build_number,
            'last_build_mined.build_id': build_id
        }
        return self._patch(DatabaseAPI._mined_project_repo_endpoint(repo, ci_service), updates)

    def set_mined_project_progression_metric(self, repo: str, ci_service: str,
                                             metric_name: str, metric_value) -> Response:
        """
        Add a mining progression metric to an existing mined project.
        The value of the metric can be any valid database type.

        If the metric with name `metric_name` already exists, then its value will be overridden with `metric_value`.
        Otherwise, the metric will be created with value `metric_value`.

        :param repo: The repository slug identifying the mined project to update.
        :param metric_name: The name of the metric to add or update.
        :param metric_value: The new value of the metric.
        :return: The response object.
        """
        if not isinstance(repo, str):
            raise TypeError
        if not repo:
            raise ValueError
        if not isinstance(metric_name, str):
            raise TypeError
        if not metric_name:
            raise ValueError
        updates = {'progression_metrics.{}'.format(metric_name): metric_value}
        return self._patch(DatabaseAPI._mined_project_repo_endpoint(repo, ci_service), updates)

    def update_mined_project_repo_name(self, repo: str, ci_service: str, new_repo: str):
        if not isinstance(repo, str):
            raise TypeError
        if not isinstance(repo, str):
            raise TypeError
        updates = {'repo': new_repo}
        return self._patch(DatabaseAPI._mined_project_repo_endpoint(repo, ci_service), updates)

    def soft_delete_mined_project(self, repo: str, ci_service: str) -> Response:
        if not isinstance(repo, str):
            raise TypeError
        if not repo:
            raise ValueError
        return self._delete(DatabaseAPI._mined_project_repo_endpoint(repo, ci_service))

    ###################################
    # Email Subscriber REST methods
    ###################################

    def insert_email_subscriber(self, email_subscriber) -> Response:
        return self._insert(DatabaseAPI._email_subscribers_endpoint(), email_subscriber, 'email subscriber')

    def find_email_subscriber(self, email: str, error_if_not_found: bool = True) -> Response:
        log.debug('Trying to find email subscriber with email {}.'.format(email))
        return self._get(DatabaseAPI._email_subscriber_email_endpoint(email), error_if_not_found)

    def list_email_subscribers(self) -> List:
        return self._list(DatabaseAPI._email_subscribers_endpoint())

    def filter_email_subscribers(self, api_filter: str) -> List:
        return self._filter(DatabaseAPI._email_subscribers_endpoint(), api_filter)

    def count_email_subscribers(self) -> int:
        return self._count(DatabaseAPI._email_subscribers_endpoint())

    def confirm_email_subscriber(self, email: str) -> Response:
        # Set confirmed to True and clear the confirmation token.
        updates = {'confirmed': True, 'confirm_token': ''}
        return self._patch(DatabaseAPI._email_subscriber_email_endpoint(email), updates)

    def unsubscribe_email_subscriber(self, email: str) -> Response:
        return self._delete(DatabaseAPI._email_subscriber_email_endpoint(email))

    ###################################
    # Account REST methods
    ###################################

    def create_account(self, email: str, role: list = None) -> Response:
        """
       Create an account with given email and role. Return token in Response if succeed.
       :param email: email address.
       :param role: default to ['user'].
       :return: The response object.
       """
        token = secrets.token_urlsafe()
        while self.filter_account_for_token(token):
            token = secrets.token_urlsafe()
        if role is None:
            role = ['user']
        account = {'email': email, 'roles': role, 'token': token, 'password': ''}
        response = self._insert(DatabaseAPI._accounts_endpoint(), account, 'account')
        if response.ok:
            response._content = json.dumps(account).encode('utf-8')
        return response

    def find_account(self, email: str, error_if_not_found: bool = True) -> Response:
        log.debug('Trying to find account with email {}.'.format(email))
        return self._get(DatabaseAPI._account_email_endpoint(email), error_if_not_found)

    def list_accounts(self) -> List:
        return self._list(DatabaseAPI._accounts_endpoint())

    def filter_account_for_token(self, token: str) -> List:
        return self._filter(DatabaseAPI._accounts_endpoint(), '{{"token":"{}"}}'.format(token))

    def filter_accounts(self, api_filter: str) -> List:
        return self._filter(DatabaseAPI._accounts_endpoint(), api_filter)

    def count_accounts(self) -> int:
        return self._count(DatabaseAPI._accounts_endpoint())

    ###################################
    # Convenience REST methods
    ###################################

    def _get(self, endpoint: Endpoint, error_if_not_found: bool = True) -> Response:
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        resp = requests.get(endpoint, auth=self.auth)
        # Do not print an error message if the entity was not expected to be found and we got a 404 status code.
        not_found = resp.status_code == 404
        if not_found and not error_if_not_found:
            return resp
        elif not resp.ok:
            log.error(resp.url)
            log.error(resp.content)
        return resp

    def _post(self, endpoint: Endpoint, data) -> Response:
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(endpoint, json.dumps(data), headers=headers, auth=self.auth)
        if not resp.ok:
            log.error(resp.url)
            log.error(resp.content)
        return resp

    def _patch(self, endpoint: Endpoint, updates) -> Response:
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        # First get the entity's etag.
        etag = self._get(endpoint).json()['_etag']
        # Now patch the entity.
        headers = {
            'Content-Type': 'application/json',
            'If-Match': etag,
        }
        resp = requests.patch(endpoint, json.dumps(updates), headers=headers, auth=self.auth)
        if not resp.ok:
            log.error(resp.url)
            log.error(resp.content)
        return resp

    def _put(self, endpoint: Endpoint, data, etag: str = None) -> Response:
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        headers = {'Content-Type': 'application/json'}
        if etag:
            headers['If-Match'] = etag
        # Now replace the entity.
        resp = requests.put(endpoint, json.dumps(data), headers=headers, auth=self.auth)
        if not resp.ok:
            log.error(resp.url)
            log.error(resp.content)
        return resp

    def _delete(self, endpoint: Endpoint) -> Response:
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        # First get the entity's etag.
        etag = self._get(endpoint).json()['_etag']
        headers = {'If-Match': etag}
        # Now delete the entity.
        resp = requests.delete(endpoint, headers=headers, auth=self.auth)
        if not resp.ok:
            log.error(resp.url)
            log.error(resp.content)
        return resp

    ###################################
    # Convenience methods
    ###################################

    def _insert(self, endpoint: Endpoint, entity, singular_entity_name: str = 'entity') -> Response:
        if entity is None:
            raise TypeError
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        if not isinstance(singular_entity_name, str):
            raise TypeError
        if not singular_entity_name:
            raise ValueError
        log.debug('Trying to insert {}.'.format(singular_entity_name))
        resp = self._post(endpoint, entity)
        if resp.status_code == 422:
            log.error('The', singular_entity_name, 'was not inserted because it failed validation.')
            log.error(pprint.pformat(entity))
            log.error(resp.content)
        return resp

    def _bulk_insert(self,
                     endpoint: Endpoint,
                     entities: List,
                     plural_entity_name: str = 'entities') -> Generator[Response, None, None]:
        if not isinstance(entities, list):
            raise TypeError('The {} to bulk insert must be provided as a list.'.format(plural_entity_name))
        if not all(e for e in entities):
            raise ValueError('All {} must be non-None.'.format(plural_entity_name))
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        if not isinstance(plural_entity_name, str):
            raise TypeError
        if not plural_entity_name:
            raise ValueError
        log.debug('Trying to bulk insert {} {}.'.format(len(entities), plural_entity_name))
        # Insert the entities in chunks to avoid a 413 Request Entity Too Large error.
        for chunk in DatabaseAPI._chunks(entities, 100):
            list_for_insertion = []
            list_of_build_ids = []
            for data in chunk:
                failed_build_id = data['failed_build']['build_id']
                list_of_build_ids.append(failed_build_id)

            api_filter = '{"failed_build.build_id":{"$in":' + '{}'.format(list_of_build_ids) + '}}'
            list_of_existing_build_pairs = self.filter_mined_build_pairs(api_filter)
            for data in chunk:
                bp_exists = False
                for bp in list_of_existing_build_pairs:
                    if data['failed_build']['build_id'] == bp['failed_build']['build_id']:
                        log.info('Failed Build ID: {} already exists in the database. Skipping insertion.'
                                 .format(data['failed_build']['build_id']))
                        bp_exists = True
                        break
                if bp_exists:
                    continue
                list_for_insertion.append(data)
            resp = self._post(endpoint, list_for_insertion)
            if resp.status_code == 422:
                log.error('The', plural_entity_name, 'were not inserted because they failed validation.')
                log.error(pprint.pformat(chunk))
                log.error(resp.content)
            elif resp.status_code == 400:
                log.error('Buildpairs were not inserted because the list is either empty, or all pairs already exist.')
            yield resp

    def _upsert(self, endpoint: Endpoint, entity, singular_entity_name: str = 'entity') -> Response:
        if entity is None:
            raise TypeError
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        if not isinstance(singular_entity_name, str):
            raise TypeError
        if not singular_entity_name:
            raise ValueError
        log.debug('Trying to upsert {}.'.format(singular_entity_name))
        # First, check if the entity exists. If it does, then pass its etag.
        get_resp = self._get(endpoint, error_if_not_found=False)
        etag = get_resp.json()['_etag'] if get_resp.ok else None
        resp = self._put(endpoint, entity, etag)
        if resp.status_code == 422:
            log.error('The', singular_entity_name, 'was not upserted because it failed validation.')
            log.error(pprint.pformat(entity))
            log.error(resp.content)
        return resp

    def _iter_pages(self, start_link: str) -> List:
        """
        Returns a list of all the results by following the next link chain starting with `start_link`.
        """
        if not isinstance(start_link, str):
            raise TypeError
        if not start_link:
            raise ValueError
        results = []
        next_link = start_link
        while next_link:
            next_resp = self._get(next_link)
            next_resp.raise_for_status()
            next_json = next_resp.json()
            try:
                if not next_json['_items']:
                    break
                results += next_json['_items']
            except KeyError:
                break
            try:
                next_link = urljoin(next_link, next_json['_links']['next']['href'])
            except KeyError:
                break
        return results

    def _list(self, endpoint: Endpoint) -> List:
        """
        Returns all results from the current page to the last page, inclusive.
        """
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        return self._iter_pages(endpoint)

    def _filter(self, endpoint: Endpoint, api_filter: str) -> List:
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        if not isinstance(api_filter, str):
            raise TypeError
        if not api_filter:
            raise ValueError
        # Append the filter as a url parameter.
        url = '{}?where={}'.format(endpoint, api_filter)
        return self._iter_pages(url)

    def _count(self, endpoint: Endpoint) -> int:
        if not isinstance(endpoint, Endpoint):
            raise TypeError
        if not endpoint:
            raise ValueError
        resp = self._get(endpoint)
        result = resp.json()
        try:
            total = result['_meta']['total']
            assert isinstance(total, int)
            return total
        except KeyError:
            return -1

    @staticmethod
    def _chunks(l: List, n: int) -> Generator[List, None, None]:
        """
        Yields successive `n`-sized chunks from `l`. `n` is clamped to the length of `l`.
        """
        if not isinstance(l, list):
            raise TypeError
        if not isinstance(n, int):
            raise TypeError
        if n == 0:
            raise ValueError('Chunk size must be greater than zero.')
        if not l:
            # Yield nothing if the list is empty.
            return
        # Even though clamping is implied when slicing, we explicitly clamp n to the length of the list.
        n = min(n, len(l))
        for i in range(0, len(l), n):
            yield l[i:i + n]

    @staticmethod
    def _endpoint(resource: str) -> Endpoint:
        if not isinstance(resource, str):
            raise TypeError
        if not resource:
            raise ValueError
        return '/'.join([DatabaseAPI.base_url, resource])

    @staticmethod
    def _artifacts_endpoint() -> Endpoint:
        return DatabaseAPI._endpoint(DatabaseAPI._ARTIFACTS_RESOURCE)

    @staticmethod
    def _artifact_image_tag_endpoint(image_tag: str) -> Endpoint:
        if not isinstance(image_tag, str):
            raise TypeError
        if not image_tag:
            raise ValueError
        return '/'.join([DatabaseAPI._artifacts_endpoint(), image_tag])

    @staticmethod
    def _mined_build_pairs_endpoint() -> Endpoint:
        return DatabaseAPI._endpoint(DatabaseAPI._MINED_BUILD_PAIRS_RESOURCE)

    @staticmethod
    def _mined_build_pair_object_id_endpoint(object_id: str) -> Endpoint:
        if not isinstance(object_id, str):
            raise TypeError
        if not object_id:
            raise ValueError
        return '/'.join([DatabaseAPI._mined_build_pairs_endpoint(), object_id])

    @staticmethod
    def _mined_projects_endpoint() -> Endpoint:
        return DatabaseAPI._endpoint(DatabaseAPI._MINED_PROJECTS_RESOURCE)

    @staticmethod
    def _mined_project_repo_endpoint(repo: str, ci_service) -> Endpoint:
        if not isinstance(repo, str):
            raise TypeError
        if not repo:
            raise ValueError
        if ci_service not in ['travis', 'github']:
            raise ValueError
        return '/'.join([DatabaseAPI._mined_projects_endpoint(), ci_service, repo])

    @staticmethod
    def _email_subscribers_endpoint() -> Endpoint:
        return DatabaseAPI._endpoint(DatabaseAPI._EMAIL_SUBSCRIBERS_RESOURCE)

    @staticmethod
    def _email_subscriber_email_endpoint(email: str) -> Endpoint:
        if not isinstance(email, str):
            raise TypeError
        if not email:
            raise ValueError
        return '/'.join([DatabaseAPI._email_subscribers_endpoint(), email])

    @staticmethod
    def _accounts_endpoint() -> Endpoint:
        return DatabaseAPI._endpoint(DatabaseAPI._ACCOUNTS_RESOURCE)

    @staticmethod
    def _account_email_endpoint(email: str) -> Endpoint:
        if not isinstance(email, str):
            raise TypeError
        if not email:
            raise ValueError
        return '/'.join([DatabaseAPI._accounts_endpoint(), email])

    @staticmethod
    def _logs_endpoint() -> Endpoint:
        return DatabaseAPI._endpoint(DatabaseAPI._LOGS_RESOURCE)

    @staticmethod
    def _logs_job_id_endpoint(job_id: str) -> Endpoint:
        if not isinstance(job_id, str):
            raise TypeError
        if not job_id:
            raise ValueError
        return '/'.join([DatabaseAPI._logs_endpoint(), job_id])
