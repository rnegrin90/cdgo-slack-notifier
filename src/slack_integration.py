import re
import requests
import json
import configparser


def get_color(status):
    default_color = '#000000'
    if status not in ('fixed', 'broken', 'warning', 'high', 'severe', 'elevated') and re.match('#[0-9A-Fa-f]{0,6}', status):
        if re.match('#[0-9A-Fa-f]{0,6}', status):
            return status
        return default_color
    if status == 'fixed':
        return 'good'
    if status == 'broken' or status == 'severe':
        return 'danger'
    if status == 'elevated':
        return '#ffff00'
    if status == 'warning' or status == 'high':
        return 'warning'
    return default_color


def get_title(status):
    default_title = 'Tests:'
    if status == 'fixed':
        return 'Fixed services::tada:'
    if status == 'broken':
        return 'Broken tests::boom:'
    if status == 'warning':
        return 'Failing for a long time!:'
    if status == 'elevated':
        return 'Failed in the last day::question:'
    if status == 'high':
        return 'Failed between 1 and 3 days ago::exclamation:'
    if status == 'severe':
        return 'Failed more than 3 days ago::bangbang:'

    return default_title


def get_formatted_services(services_dict):
    services = ''
    for key, value in services_dict.items():
        if value is not None:
            services += key + ' : ' + str(value)  # TODO remove []
        else:
            services += key
        services += '\n'

    return services


class WebhookProvider:
    def __init__(self, config=None):
        if config is None:
            config = configparser.ConfigParser()
            config.read('.\\app.cfg')
        self.base_url = config.get('ConnectionStrings', 'CdGoWebhookUrl')
        self.bot_name = 'Cd-Go'
        self.icon_url = 'https://raw.githubusercontent.com/grundic/yagocd/master/img/gocd_logo.png'
        self.channel = config.get('AppConfig', 'SlackChannel', fallback=None)
        self.new_fail_message = '*Integration test failed in last build!*\n'
        self.reminder_message = '*Test summary*\n{1} integration test{2} failing:'
        self.footer = 'Please fix me!\n<http://your-cd-go-server/go/tab/build/{0}|Click here> for more details'

    def get_text(self, args, custom_message=None):
        if custom_message:
            return custom_message.format(*args)

        if any(args):
            return self.reminder_message.format(*args)
        else:
            return self.new_fail_message

    def post_message(self, message, channel_override):
        message['username'] = self.bot_name
        message['icon_url'] = self.icon_url

        if channel_override is not None:
            message['channel'] = channel_override
        else:
            if self.channel is not None:
                message['channel'] = self.channel

        print('Posting message to slack')
        requests.post(self.base_url, data=json.dumps(message, ensure_ascii=False))

    def send(self, dict, link, custom_message=None, last_run_date=None, total_count=None, channel_override=None):
        """
        :param channel_override: Target channel for the message published
        :param dict: dictionary containing the following structure:
            {
                'message': 'Base message to show'
                'attachments': {
                        'fixed': { 'test_name': count }
                        'broken': { 'test_name': count }
                        'warning': { test_name': count }
                        '#hex_colour': { test_name': count }
                    }
                'footer': 'footer text'
            }
        :param link: URL pointing to the tests screen
        :param custom_message: Provide if you want to send your own message
        :param last_run_date: If the notification is a reminder, this value needs to be specified
        :param total_count: Total amount of failing tests
        :return:
        """
        args = () if last_run_date is None else (last_run_date.strftime('%Y-%m-%d %H:%M:%S'), total_count, 's are' if total_count > 1 else ' is')

        req = {
            'text': self.get_text(args, custom_message),
            'attachments': []
        }

        if 'attachments' in dict:
            for status, services in dict['attachments'].items():
                attch = {
                    'color': get_color(status),
                    'title': get_title(status),
                    'text': get_formatted_services(services)
                }
                req['attachments'].append(attch)

            if 'footer' in dict:
                req['attachments'].append({'pretext': dict['footer'].format(link)})
            else:
                req['attachments'].append({'pretext': self.footer.format(link)})

            self.post_message(req, channel_override)
        else:
            print('Attachments not specified')
