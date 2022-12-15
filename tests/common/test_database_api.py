import unittest
from os.path import dirname, join

from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.json import read_json
from bugswarm.common.rest_api.database_api import DatabaseAPI

DATA_DIR = join(dirname(__file__), 'database-api')


def delete_underscore_keys(d):
    for k in list(d.keys()):
        if k.startswith('_'):
            del d[k]


class TestDatabaseReadonlyAPI(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = DatabaseAPI(DATABASE_PIPELINE_TOKEN)

    def test_find_artifact(self):
        image_tag = 'gwtbootstrap3-gwtbootstrap3-92837490'
        response = self.api.find_artifact(image_tag)
        self.assertEqual(response.status_code, 200)

        expected_json = read_json(join(DATA_DIR, f'artifact-{image_tag}.json'))
        actual_json = response.json()
        delete_underscore_keys(expected_json)
        delete_underscore_keys(actual_json)
        self.assertEqual(actual_json, expected_json)

    def test_find_nonexistent_artifact(self):
        response = self.api.find_artifact('nonexistent-artifact-12345678', False)
        self.assertEqual(response.status_code, 404)

    def test_filter_artifacts(self):
        flt = '{"reproduced": true, "lang": "Java", "classification.test": "Yes"}'
        response_json = self.api.filter_artifacts(flt)

        self.assertNotEqual(len(response_json), 0)
        for artifact in response_json:
            self.assertTrue(artifact['reproduced'])
            self.assertEqual(artifact['lang'], 'Java')
            self.assertEqual(artifact['classification']['test'], 'Yes')

    def test_get_build_log(self):
        job_id = '92837490'
        log_text = self.api.get_build_log(job_id)
        with open(join(DATA_DIR, f'job-log-{job_id}.log')) as f:
            expected_log = f.read()
        self.assertEqual(log_text, expected_log)

    def test_get_build_log_errors(self):
        self.assertRaises(Exception, self.api.get_build_log, '12345678', False)
