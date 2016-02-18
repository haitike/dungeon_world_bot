from telegrambot.telegrambot import TelegramBot
from telegrambot.flask_config_class import Config
from pymongo import MongoClient
import logging

CONFIGFILE_PATH = "data/config.py"
config = Config(".")
config.from_pyfile(CONFIGFILE_PATH) #try

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot_log")

mclient = MongoClient()
db = mclient[config["DB_NAME"]]

if __name__ == '__main__':
    bot = TelegramBot(config, db)
    bot.start_polling_loop()
    mclient.close()
    logger.info("Finished program.")
