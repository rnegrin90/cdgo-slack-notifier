import configparser
from datetime import datetime, timedelta
import os
from enum import Enum

from croniter import croniter


def serialize(failure_event, key):
    str_list = [key,
                failure_event.failing_test_name,
                failure_event.last_modification.isoformat(),
                failure_event.failure_count,
                failure_event.first_notification.isoformat(),
                failure_event.last_notification.isoformat(),
                failure_event.fail_triggered,
                failure_event.status]
    return ','.join(map(str, str_list))


class NotificationsHandler:
    def __init__(self, config=None):
        if config is None:
            config = configparser.ConfigParser()
            config.read('.\\app.cfg')
        self.failure_history = {}
        self.fixed_since_last_run = {}
        self.last_general_notification = datetime.min
        self.cron_schedule = config.get('AppConfig', 'CronSchedule', fallback=None)
        self.backoff_period = config.get('AppConfig', 'BackOffPeriod', fallback=1440)  # In minutes, used in case the schedule fails
        self.storage_file_name = config.get('AppConfig', 'StorageFileName')
        self.status_report_active = config.get('AppConfig', 'SendStatusReport', fallback=False)
        self.fixed_tests_expiry = config.get('AppConfig', 'FixedTestsExpiration', fallback=7)  # In days

    def refresh(self, tests_result):
        for _, test in self.failure_history.items():
            for t in test:
                t.fail_triggered = False
        for name in tests_result.service_count:
            if name not in self.failure_history:
                self.failure_history[name] = []
            for test in tests_result.service_list[name]:
                existing_event = list(filter(lambda x: x.failing_test_name == test, self.failure_history[name]))
                if any(existing_event):
                    if len(existing_event) > 1:
                        print("Multiple tests with the same name detected", existing_event)
                    existing_event[0].last_modification = datetime.utcnow()
                    existing_event[0].fail_triggered = True if existing_event[0].status == TestState.FIXED else False
                    existing_event[0].status = TestState.BROKEN
                    existing_event[0].failure_count += 1 if existing_event[0].status == TestState.FIXED else 0
                else:
                    ev = FailureEvent()
                    ev.failing_test_name = test
                    ev.last_modification = datetime.utcnow()
                    ev.fail_triggered = True
                    ev.failure_count = 1
                    self.failure_history[name].append(ev)

        for service, tests in self.failure_history.items():
            for broken_test in list(filter(lambda b: b.status == TestState.BROKEN, tests)):
                if service not in tests_result.service_list or broken_test.failing_test_name not in tests_result.service_list[name]:
                    broken_test.status = TestState.FIXED
        self.remove_expired()
        self.persist()

    def remove_expired(self):
        keys_to_delete = []
        for service, failure in self.failure_history.items():
            failing_tests = list(filter(lambda t: t.fail_triggered, failure))
            if not any(failing_tests):
                keys_to_delete.append(service)
            else:
                self.failure_history[service] = failing_tests
                if service in self.fixed_since_last_run:
                    self.fixed_since_last_run.pop(service)

            for fixed_test in list(filter(lambda t: t.status == TestState.FIXED, failure)):
                if datetime.utcnow() - fixed_test.last_modification > timedelta(days=self.fixed_tests_expiry):
                    failure.remove(fixed_test)
        for service in keys_to_delete:
            self.fixed_since_last_run[service] = None

    def send_notification(self, notification_engine, webhook_url):
        """
        Reminder logic
        """
        now = datetime.utcnow()
        if self.cron_schedule is not None:
            cronjob = croniter(self.cron_schedule, self.last_general_notification)
            next_run_time = cronjob.get_next(datetime)
            print('Next run time:' + str(next_run_time))
        else:
            next_run_time = self.last_general_notification + timedelta(minutes=self.backoff_period)
        reminder_active = next_run_time.second == 0 and now > next_run_time

        """
        New failure logic
        """
        new_fail_dict = {'attachments': {'broken': {}}}
        reminder_dict = {'attachments': {}}
        for service, tests in self.failure_history.items():
            service_total_count = 0
            for t in tests:
                if t.fail_triggered:
                    service_total_count += 1
                    t.last_notification = datetime.utcnow()
            if service_total_count > 0:
                new_fail_dict['attachments']['broken'][service] = service_total_count

            if reminder_active:
                for t in tests:
                    if t.status == TestState.BROKEN:
                        t.last_notification = datetime.utcnow()
                        delta = now - t.first_notification
                        """
                        Failures on the last day, #Yellow
                        """
                        if delta < timedelta(days=1):
                            if 'elevated' not in reminder_dict['attachments']:
                                reminder_dict['attachments']['elevated'] = {}
                            reminder_dict['attachments']['elevated'][service] = 1 if service not in reminder_dict['attachments']['elevated'] else reminder_dict['attachments']['elevated'][service] + 1

                        """
                        Failures in the last 3 days, #Orange
                        """
                        if timedelta(days=3) > delta > timedelta(days=1):
                            if 'high' not in reminder_dict['attachments']:
                                reminder_dict['attachments']['high'] = {}
                            reminder_dict['attachments']['high'][service] = 1 if service not in reminder_dict['attachments']['high'] else reminder_dict['attachments']['high'][service] + 1

                        """
                        Failures older than 3 days, #Red:
                        """
                        if delta > timedelta(days=3):
                            if 'severe' not in reminder_dict['attachments']:
                                reminder_dict['attachments']['severe'] = {}
                            reminder_dict['attachments']['severe'][service] = 1 if service not in reminder_dict['attachments']['severe'] else reminder_dict['attachments']['severe'][service] + 1

        if any(new_fail_dict['attachments']['broken']):
            if any(self.fixed_since_last_run):
                new_fail_dict['attachments']['fixed'] = self.fixed_since_last_run
                self.fixed_since_last_run = {}
            if self.status_report_active:
                notification_engine.send(new_fail_dict, webhook_url, channel_override='webhooktest')
            else:
                notification_engine.send(new_fail_dict, webhook_url)

        if any(reminder_dict['attachments']):
            count = 0
            for group in reminder_dict['attachments'].values():
                count += sum(int(i) for i in group.values())
            notification_engine.send(reminder_dict, webhook_url, last_run_date=self.last_general_notification, total_count=count)

        self.last_general_notification = datetime.utcnow()
        # TODO send 'All fixed' message
        # if not any(new_fail_dict['attachments']) and not any(reminder_dict):
        #     notification_engine.send()
        self.persist()

    def persist(self):
        f = open(self.storage_file_name, 'w')
        f.write(self.last_general_notification.isoformat() + '\n')
        for key, value in self.failure_history.items():
            f.write(''.join(list(map(lambda s: serialize(s, key) + '\n', value))))
        f.close()

    def load(self):
        if os.path.exists(self.storage_file_name):
            f = open(self.storage_file_name, 'r')
            content = f.readlines()
            last_run = content.pop(0).rstrip()
            self.last_general_notification = datetime.strptime(last_run, '%Y-%m-%dT%H:%M:%S.%f') \
                if '.' in last_run else datetime.strptime(last_run, '%Y-%m-%dT%H:%M:%S')
            self.failure_history = {}
            for line in content:
                elements = line.rstrip().split(',')
                existing_event = FailureEvent()
                existing_event.failing_test_name = elements[1]
                existing_event.last_modification = datetime.strptime(elements[2], '%Y-%m-%dT%H:%M:%S.%f') if '.' in elements[2] else datetime.strptime(elements[2], '%Y-%m-%dT%H:%M:%S')
                existing_event.failure_count = int(elements[3])
                existing_event.first_notification = datetime.strptime(elements[4], '%Y-%m-%dT%H:%M:%S.%f') if '.' in elements[4] else datetime.strptime(elements[4], '%Y-%m-%dT%H:%M:%S')
                existing_event.last_notification = datetime.strptime(elements[5], '%Y-%m-%dT%H:%M:%S.%f') if '.' in elements[5] else datetime.strptime(elements[5], '%Y-%m-%dT%H:%M:%S')
                existing_event.fail_triggered = elements[6] == 'True'
                existing_event.status = TestState(int(elements[7]))
                if elements[0] not in self.failure_history:
                    self.failure_history[elements[0]] = [existing_event]
                else:
                    self.failure_history[elements[0]].append(existing_event)
            f.close()


class FailureEvent:
    def __init__(self):
        self.failing_test_name = 0
        self.last_modification = datetime.utcnow()
        self.failure_count = 0
        self.first_notification = datetime.utcnow()
        self.last_notification = datetime.min
        self.fail_triggered = False
        self.status = TestState.BROKEN


class TestState(Enum):
    def __str__(self):
        return str(self.value)

    FIXED = 1
    BROKEN = 2
