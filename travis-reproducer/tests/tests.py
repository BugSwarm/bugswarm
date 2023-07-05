import sys
import unittest
import json
from unittest import mock

sys.path.append('../')
from pair_chooser import is_jp_unique, should_include_jobpair  # noqa: E402


class Test(unittest.TestCase):

    def _mock_response(self, status=200, content="CONTENT", json_data=None, raise_for_status=None):
        mock_resp = mock.Mock()
        # mock raise_for_status call w/ optional error
        mock_resp.raise_for_status = mock.Mock()
        if raise_for_status:
            mock_resp.raise_for_status.side_effect = raise_for_status
        mock_resp.status = status
        mock_resp.content = content
        if json_data:
            mock_resp.json = mock.Mock(
                return_value=json_data
            )
        return mock_resp

    def _mock_json_data(self, filename):
        with open('pair_chooser_files/' + filename, 'r') as f:
            return json.loads(f.read())

    def test_pair_uniqueness_1(self):
        scout_filename = 'Scout24-minedBuildPairs-data'
        scout_mock_resp = self._mock_response(
            json_data=self._mock_json_data(scout_filename)
        )

        immobilien_filename = 'ImmobilienScout24-minedBuildPairs-data'
        immobilien_mock_resp = self._mock_response(
            json_data=self._mock_json_data(immobilien_filename)
        )

        artifact_filename = '131735009-artifact-data'
        artifact_mock_resp = self._mock_response(
            json_data=self._mock_json_data(artifact_filename)
        )

        # simulates repo: Scout24/deadcode4j's failed job ID: 131735009 and passed job ID: 131741120
        # to be included for reproducing, but will be filtered out due to already being associated with
        # Artifact: ImmobilienScout24-deadcode4j-131735009
        false_count = 0
        include_jobpair_count = 0
        for jp in scout_mock_resp.json.return_value['jobpairs']:
            include_jobpair = should_include_jobpair(jp, 131735009, 131741120)
            if include_jobpair:
                include_jobpair_count += 1
            is_unique = is_jp_unique('Scout24/deadcode4j', jp, artifact_mock_resp.json.return_value)
            if not is_unique:
                scout_failed_job_id = jp['failed_job']['job_id']
                false_count += 1

        self.assertEqual(include_jobpair_count, 1)
        self.assertEqual(false_count, 1)
        self.assertEqual(scout_failed_job_id,
                         artifact_mock_resp.json.return_value[str(scout_failed_job_id)]['failed_job']['job_id'])

        # simulates repo: ImmobilienScout24/deadcode4j's failed job ID: 131735009 and passed job ID: 131741120
        # to be included for reproducing and will not be filtered out due to it's association with it's
        # Artifact: ImmobilienScout24-deadcode4j-131735009
        true_count = 0
        include_jobpair_count = 0
        include_projects_jobpair_count = 0
        for jp in immobilien_mock_resp.json.return_value['jobpairs']:
            # simulates total # of jobpairs for project for reproducing
            include_jobpair = should_include_jobpair(jp, None, None)
            if include_jobpair:
                include_projects_jobpair_count += 1

            # simulates the jobpair for reproducing
            include_jobpair = should_include_jobpair(jp, 131735009, 131741120)
            if include_jobpair:
                include_jobpair_count += 1

            is_unique = is_jp_unique('ImmobilienScout24/deadcode4j', jp, artifact_mock_resp.json.return_value)
            if is_unique:
                true_count += 1

        self.assertEqual(include_projects_jobpair_count, 15)
        self.assertEqual(include_jobpair_count, 1)
        self.assertEqual(true_count, len(scout_mock_resp.json.return_value['jobpairs']))
