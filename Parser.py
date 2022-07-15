import requests
import os


class Parser:

    def __init__(self, url, domain, last_schedule):
        self.url = url
        self.domain = domain
        self.last_schedule = last_schedule

    def parse(self):

        try:
            html_code = requests.get(self.url, timeout=5)
        except Exception as err:
            print(err)
            return None

        number = html_code.text.find('/vec_assistant/Расписание/')
        stroke = list(html_code.text[number:number + 100:1])
        link = '' + self.domain
        flag = False
        for literal in stroke:
            if literal == '/':
                flag = True
            if flag:
                link += literal
            if literal == 'g':
                break

        if self.last_schedule is not None:
            if link == self.last_schedule:
                return None

        self.last_schedule = link
        print('link is {}'.format(link))
        return link


class FileManager:

    def __init__(self, directory):
        self.directory = directory
        if not os.path.exists(self.directory):
            os.mkdir('Schedules')

    def clear(self, necessary_file: str):
        try:
            self.files = os.listdir(self.directory)
            for file in self.files:
                if file != necessary_file.split('/')[-1]:
                    os.remove('Schedules/{}'.format(file))
        except FileNotFoundError:
            os.mkdir('Schedules')
