from pymongo import MongoClient
import logging
import configparser
import os

def get_bot_conf(value):
    return config["bot"][value]

def get_env_conf(value, default_value=None):
    if default_value:
        return os.environ.get(config["env"][value], default_value)
    else:
        return os.environ.get(config["env"][value])

CONFIGFILE_PATH = "data/config.cfg"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot_log")

config = configparser.ConfigParser()
config.read( CONFIGFILE_PATH )

client = MongoClient(get_env_conf("MONGO_URL", None))
db = client[get_bot_conf("DB_NAME")]

