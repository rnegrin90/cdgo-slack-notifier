import schedule
import time
from src.go_api import *
from src.slack_integration import *
from src.test_result_processor import *
from src.notifications_handler import *


class IntegrationPipelineNotifier:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('./app.cfg')
        self.pipeline_name = config.get('AppConfig', 'PipelineName')
        self.stage_name = config.get('AppConfig', 'StageName')
        self.job_name = config.get('AppConfig', 'JobName')
        self.provider = GoCdProvider(config)
        self.notifier = NotificationsHandler(config)
        self.slack_handler = WebhookProvider(config)
        self.frequency = int(config.get('AppConfig', 'PollingFreq'))

    def run(self):
        print("Running @{0}".format(datetime.now()))

        try:
            job_details = self.provider.job_details(self.pipeline_name, self.stage_name, self.job_name)
            tests_result = self.provider.tests_result(self.pipeline_name, self.stage_name, self.job_name,
                                                    job_details.pipeline_counter, job_details.stage_counter)

            path = ['detail', self.pipeline_name, job_details.pipeline_counter,
                    self.stage_name, job_details.stage_counter, self.job_name]
            webhook_url = GoCdProvider.build_url(path, anchor='tab-failures', api=False)

            results_processor = TestResult()
            results_processor.parse(tests_result)

            self.notifier.load()
            self.notifier.refresh(results_processor)

            self.notifier.send_notification(self.slack_handler, webhook_url)

        except Exception as e:
            print(e)
            self.slack_handler.send({}, '', custom_message=str(e), channel_override='')
            # raise  # for debug
            return

notifier = IntegrationPipelineNotifier()

print('Setting notifier to run every {0} seconds'.format(notifier.frequency))
schedule.every(notifier.frequency).seconds.do(notifier.run)
notifier.run()

while True:
    schedule.run_pending()
    time.sleep(1)
