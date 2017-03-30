import re


class TestResult:
    def __init__(self):
        self.total_failed_test_count = 0
        self.service_count = {}
        self.service_list = {}

    def parse(self, tests_result):
        lines = tests_result.split('\n')
        for line in lines:
            if re.match('^<td class="section-data">Failure</td>', line):
                m = re.search('([a-zA-Z]+)\.([a-zA-Z]+\.)+([a-zA-Z_]+)', line) # For this to work, you need to have your tests named as ServiceName.What.Ever.In.The.Middle.TestName, you can always change this to adapt to your structure
                if m is not None:
                    self.total_failed_test_count += 1
                    self.add_if_exists(m.group(1), 1)
                    self.append_if_exists(m.group(1), m.group(3))

    def add_if_exists(self, key, value):
        if key in self.service_count:
            self.service_count[key] += value
        else:
            self.service_count[key] = value

    def append_if_exists(self, key, value):
        if key in self.service_list:
            self.service_list[key].append(value)
        else:
            self.service_list[key] = [value]
