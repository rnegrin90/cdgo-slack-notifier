import requests
import json
import configparser
from src.go_models import *


class GoCdProvider:
    def __init__(self, config=None):
        if config is None:
            config = configparser.ConfigParser()
            config.read('.\\app.cfg')
        self.base_url = config.get('ConnectionStrings', 'CdGoBaseUrl')
        self.auth = config.get('Credentials', 'CdGoCredentials')

    def tests_result(self, pipeline_name, stage_name, job_name, pipeline_counter, stage_counter):
        url = ['files', pipeline_name, pipeline_counter, stage_name, stage_counter, job_name, 'testoutput', 'result',
               'index.html']
        result = self.get(self.build_url(url, api=False))
        return result

    def job_details(self, pipeline_name, stage_name, job_name, pipeline_counter=None):
        url = ['jobs', pipeline_name, stage_name, job_name, 'history']
        result = json.loads(self.get(self.build_url(url)))
        job_result = Job()
        if pipeline_counter is None:
            i = 0
            while result['jobs'][i]['state'] != 'Completed':  # Get last completed stage
                i += 1
            job_result.parse_json(result['jobs'][i])
            return job_result
        else:
            for job in result['jobs']:
                if job['pipeline_counter'] == pipeline_counter:
                    job_result.parse_json(job)
                    return job_result
            return None

    def pipeline_counter(self, pipeline_name):
        url = ['pipelines', pipeline_name, 'history']
        result = json.loads(self.get(self.build_url(url)))
        return result['pagination']['total']

    def get(self, request_url):
        url = self.base_url + request_url

        headers = {
            'Authorization': self.auth
        }

        return requests.get(url, headers=headers).text

    @staticmethod
    def build_url(path, anchor=None, query=None, api=True):
        if api:
            path.insert(0, "api")
        str_list = []

        # Path
        for segment in path:
            str_list.append(str(segment))
            str_list.append('/')
        str_list.pop()  # Remove last '/'

        # Query string
        if query is not None:
            str_list.append('?')
            for key, value in query:
                if value is not None:
                    str_list.append(str(key))
                    str_list.append('=')
                    str_list.append(str(value))
                    str_list.append('&')
            str_list.pop()  # Remove last '&'

        # Anchor tag
        if anchor is not None:
            str_list.append('#')
            str_list.append(anchor)

        return ''.join(str_list)
