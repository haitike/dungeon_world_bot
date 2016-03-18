import pytz
from pytz import timezone
from telegram import Updater
from telegram.error import TelegramError

import dungeon
from dungeon import messages, const
from dungeon import db

class Bot(object):
    translations = {}
    bot = None

    def __init__(self):
        self.playing_state = dict()

        self.updater = Updater(token=dungeon.get_bot_conf("TOKEN"))
        self.dispatcher = self.updater.dispatcher
        self.add_handlers()

        try:
            self.tzinfo = timezone(dungeon.get_bot_conf("TIMEZONE"))
        except:
            self.tzinfo = pytz.utc

        # i18n BLOCK (see dungeon world commit 66 / haibot commits)

    def start_polling_loop(self):
        self.disable_webhook()
        self.update_queue = self.updater.start_polling()
        self.updater.idle()
        self.cleaning()

    def start_webhook_server(self):
        self.set_webhook()
        self.update_queue = self.updater.start_webhook(dungeon.get_env_conf("IP","127.0.0.1"),
                                                       int(dungeon.get_env_conf("PORT","8080")),
                                                       dungeon.get_bot_conf("TOKEN"))
        self.updater.idle()
        self.cleaning()

    def cleaning(self):
        dungeon.logger.info("Finished program.")

    def set_webhook(self):
        s = self.updater.bot.setWebhook(dungeon.get_bot_conf("WEBHOOK_URL") + "/" + dungeon.get_bot_conf("TOKEN"))
        if s:
            dungeon.logger.info("webhook setup worked")
        else:
            dungeon.logger.warning("webhook setup failed")
        return s

    def disable_webhook(self):
        s = self.updater.bot.setWebhook("")
        if s:
            dungeon.logger.info("webhook was disabled")
        else:
            dungeon.logger.warning("webhook couldn't be disabled")
        return s

    def add_handlers(self):
        self.dispatcher.addTelegramCommandHandler("start", self.command_start)
        self.dispatcher.addTelegramCommandHandler("help", self.command_help)
        self.dispatcher.addTelegramCommandHandler("exit", self.command_exit)
        self.dispatcher.addTelegramCommandHandler("pj", self.command_pj)
        self.dispatcher.addTelegramCommandHandler("master", self.command_master)
        self.dispatcher.addTelegramCommandHandler("play", self.command_play)

    def get_chat_info(self, update):
        self.last_chat = update.message.chat
        chad_id = update.message.chat.id

        sender = update.message.from_user
        text = update.message.text
        chat_data = db.chats.find_one({"_id" : chad_id})
        if not chat_data:
            chat_data = {"_id" : chad_id, "state" : const.STOPPED, "context": None}

        return chat_data, sender, text

    def command_start(self, bot, update):
        chat, sender, text = self.get_chat_info(update)
        if chat["state"] == const.STOPPED:
            chat["state"] = const.STOPPED
            self.send_message(messages.welcome)
            self.send_message(messages.help[chat["state"]])
        else:
            self.send_message(messages.already_started[chat["state"]])

    def command_help(self, bot, update):
        chat, sender, text = self.get_chat_info(update)
        self.send_message(messages.help[chat["state"]])

    def command_exit(self, bot, update):
        chat, sender, text = self.get_chat_info(update)
        if chat["state"] != const.STOPPED:
            self.send_message(messages.exit[chat["state"]])
            chat["state"] = const.STOPPED
            db.chats.replace_one({"_id":chat["_id"]}, chat, upsert=True )
            chat["context"] = None
        else:
            self.send_message(messages.no_exit)

    def command_pj(self, bot, update):
        chat, sender, text = self.get_chat_info(update)
        if chat["state"] == const.STOPPED:
            chat["state"] = const.NEWPJ
            db.chats.replace_one({"_id":chat["_id"]}, chat, upsert=True )
            self.send_message("guay")
        else:
            self.send_message("ya")

    def command_master(self, bot, update):
        pass

    def command_play(self, bot, update):
        pass

    def send_message(self, text):
        try:
            self.updater.bot.sendMessage(chat_id=self.last_chat.id, text=text)
            return True
        except TelegramError as e:
            if self.last_chat.type == "private":
                dungeon.logger.warning("Message sending error to %s [%d] [%s] (TelegramError: %s)" % (self.last_chat.first_name, self.last_chat.id, self.last_chat.type, e))
            else:
                dungeon.logger.warning("Message sending error to %s [%d] [%s] (TelegramError: %s)" % (self.last_chat.title, self.last_chat.id, self.last_chat.type, e))
            return False
        except:
            if self.last_chat.type == "private":
                dungeon.logger.warning("Message sending error to %s [%d] [%s]" % (self.last_chat.first_name, self.last_chat.id, self.last_chat.type))
            else:
                dungeon.logger.warning("Message sending error to %s [%d] [%s]" % (self.last_chat.title, self.last_chat.id, self.last_chat.type))
            return False