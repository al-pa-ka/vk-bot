from auth import *
from ChatBot import *
from Parser import FileManager, Parser
from Database import *

vk_session = vk_api.VkApi(token=api_key)
vk = vk_session.get_api()

url = "https://www.energocollege.ru/schedule/"
domain = "https://www.energocollege.ru"
file_manager = FileManager("Schedules")
database = PostgressDatabase()
link, sended_out = database.get_last_status()
parser = Parser(url, domain, link)
bot = ChatBot(vk_session, parser, database, wait=50, sended_out=sended_out)

while True:
    bot.listening()
    bot.send_out()
    file_manager.clear(bot.last_file)
