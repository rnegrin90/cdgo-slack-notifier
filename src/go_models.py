class Dto:
    def parse_json(self, json_object):
        return self


# Not in use
class Pagination:
    def __init__(self):
        self.offset = 0,
        self.total = 0,
        self.page_size = 0


# Not in use
class History:
    def __init__(self):
        self.pipelines = []
        self.pagination = Pagination()


class Job(Dto):
    def __init__(self):
        self.agent_uuid = None
        self.name = None
        self.job_state_transitions = None
        self.scheduled_date = None
        self.original_job_id = None
        self.pipeline_counter = None
        self.rerun = None
        self.pipeline_name = None
        self.result = None
        self.state = None  # Completed, Scheduled, Building (?)
        self.id = None
        self.stage_counter = None
        self.stage_name = None

    def parse_json(self, json_object):
        self.agent_uuid = json_object['agent_uuid']
        self.name = json_object['name']
        self.job_state_transitions = json_object['job_state_transitions']
        self.scheduled_date = json_object['scheduled_date']
        self.original_job_id = json_object['original_job_id']
        self.pipeline_counter = json_object['pipeline_counter']
        self.rerun = json_object['rerun']
        self.pipeline_name = json_object['pipeline_name']
        self.result = json_object['result']
        self.state = json_object['state']
        self.id = json_object['id']
        self.stage_counter = json_object['stage_counter']
        self.stage_name = json_object['stage_name']
