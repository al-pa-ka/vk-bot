import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from random import randrange
import requests
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import os.path


class ChatBot(VkBotLongPoll):

    def __init__(self, vk_session: vk_api.VkApi, parser, database, wait=10, sended_out=False, group_id=213599387):
        super().__init__(vk_session, group_id=group_id, wait=wait)
        self.vk_session = vk_session
        self.vk = vk_session.get_api()
        self.parser = parser
        self.last_file = 'Schedules/{}'.format(parser.last_schedule.split('/')[-1])
        self.database = database
        self.sended_out = sended_out
        self.group_id = group_id

    @staticmethod
    def unexpected_error(func):

        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except Exception as err:
                print('This error has occurred in {}, \n {}'.format(func.__name__, err))
                return

        return wrapper

    @unexpected_error
    def error_handler(self):
        response = self.vk_session.method('groups.getLongPollServer', {'group_id': self.group_id})
        print(response)

        self.key = response['key']
        self.server = response['server']
        self.ts = response['ts']

        self.url = self.server

    @unexpected_error
    def listening(self):
        while True:
            try:
                events = self.check()
                if not events:
                    break
        # Ошибка самой библиотеки
            except TypeError as err:
                print("Error has occurred in listening - \n{}".format(err))
                self.error_handler()
                break

            for event in events:

                if event.type == VkBotEventType.MESSAGE_NEW:

                    if event.from_user:
                        self.get_user_choice(event.object)
                    elif event.from_chat:
                        print(event.message)
                        if event.message['text'].split(' ')[-1] == 'Добавить':
                            print('ok!')
                            self.add_chat(event.chat_id)

    def get_user_choice(self, message: VkBotEventType.MESSAGE_NEW):
        if message['message']['text'] in ["Подписаться", "Начать"]:
            self.add_user(message['message']['from_id'])

        elif message['message']['text'] == 'Отписаться':
            self.delete_user(message['message']['from_id'])

        elif message['message']['text'] == "!users":
            users_list = self.database.get_users_from_db()
            users_list = list(map(str, users_list))
            message_to_send = '\n'.join(users_list)
            self.send(user_id=message['message']['from_id'], message=message_to_send)

        else:
            result = self.database.get_one_user(message['message']['from_id'])
            if result is None:
                self.create_keyboard(message['message']['from_id'])

    def add_chat(self, chat_id):
        self.database.add_chat_to_db(chat_id)
        self.send(message='Беседа успешно добавлена в базу данных!', chat_id=chat_id)

    def add_user(self, user_id):
        users_list = self.database.get_users_from_db()
        print(users_list)
        if user_id in users_list:
            return
        self.database.add_user_to_db(user_id)
        self.send(user_id=user_id, message='Теперь вы подписаны на ежедневную рассылку расписания!')
        if os.path.exists(self.last_file):
            self.create_attachment(open(self.last_file, 'rb'), user_id=user_id)
        else:
            self.create_image()
            self.create_attachment(open(self.last_file, 'rb'), user_id=user_id)

    def delete_user(self, user_id):
        self.database.delete_user_from_db(user_id)

    def create_attachment(self, attachment, user_id=None, chat_id=None):
        url = self.vk_session.method("photos.getMessagesUploadServer")
        response = requests.post(url['upload_url'], files={'photo': attachment}).json()
        photo_uploaded = self.vk_session.method('photos.saveMessagesPhoto',
                                                {'photo': response['photo'],
                                                 'server': response['server'],
                                                 'hash': response['hash']})[0]
        print(photo_uploaded)
        attachments = 'photo{}_{}_{}'.format(photo_uploaded['owner_id'], photo_uploaded['id'],
                                             photo_uploaded['access_key'])
        print(attachments)
        self.send(user_id=user_id, chat_id=chat_id, attachment=attachments)

    def create_keyboard(self, user_id):
        keyboard = VkKeyboard(one_time=True)
        users = self.database.get_users_from_db()
        if user_id not in users:
            keyboard.add_button('Подписаться', color=VkKeyboardColor.POSITIVE)
        else:
            return None
        json_keyboard = keyboard.get_keyboard()
        self.send(user_id=user_id, keyboard=json_keyboard)

    def send(self, user_id=None, chat_id=None, message=None, attachment=None, keyboard=False):
        try:
            kwargs = {
                'user_id': user_id, 'chat_id': chat_id, 'random_id': randrange(-100, 100),
                'attachment': attachment, 'keyboard': keyboard, 'message': message
                 }
            self.vk_session.method('messages.send', kwargs)

        except Exception as err:
            print(err)
        except vk_api.exceptions.ApiError:
            return

    @unexpected_error
    def send_out(self):
        if self.sended_out:
            result = self.parser.parse()
            if result is None:
                return
        users = self.database.get_users_from_db()
        chats = self.database.get_chats_from_db()
        self.create_image()
        for chat in chats:
            try:
                self.create_attachment(open(self.last_file, 'rb'), chat_id=chat)
            except Exception as err:
                print(err)
                continue

        for user in users:
            try:
                self.create_attachment(open(self.last_file, 'rb'), user_id=user)
            except Exception as err:
                print(err)
                continue

        self.sended_out = True
        self.database.safe_current_status(self.parser.last_schedule, self.sended_out)

    def create_image(self):
        result = self.parser.parse()
        self.database.safe_current_status(self.parser.last_schedule, self.sended_out)
        print('Result of create_image is {}'.format(result))
        if result is not None:
            self.sended_out = False
        link = self.parser.last_schedule
        if link is None:
            return
        if not os.path.exists('Schedules/{}'.format(link.split('/')[-1])):
            with open('Schedules/{}'.format(link.split('/')[-1]), 'xb') as schedule:
                schedule.write(requests.get(link).content)
                self.last_file = 'Schedules/{}'.format(link.split('/')[-1])
