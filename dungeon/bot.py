import pytz
from telegram import Updater
from telegram.error import TelegramError
from pytz import timezone

import dungeon
from dungeon import messages

STOPPED, NEWPJ, DELPJ, MASTER, DELADV, NEWADV, JOINING, PLAYING = range(8)

class Bot(object):
    translations = {}
    bot = None

    def __init__(self):
        self.state = dict()
        self.playing_state = dict()
        self.context = dict()

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

    def get_chat_info(self, update):
        self.chat = update.message.chat
        self.user = update.message.from_user
        self.text = update.message.text
        self.chat_state = self.state.get(self.chat.id, STOPPED)
        self.chat_context = self.context.get(self.chat.id, None)

    def command_start(self, bot, update):
        self.get_chat_info(update)
        self.send_message(messages.welcome)
        self.send_message(messages.help[self.chat_state])

    def command_help(self, bot, update):
        self.get_chat_info(update)
        self.send_message(messages.help[self.chat_state])

    def command_exit(self, bot, update):
        self.get_chat_info(update)
        self.send_message(messages.exit[self.chat_state])
        self.state[self.chat.id] = STOPPED
        self.context[self.chat.id] = None

    def send_message(self, text):
        try:
            self.updater.bot.sendMessage(chat_id=self.chat.id, text=text)
            return True
        except TelegramError as e:
            dungeon.logger.warning("Message sending error to %s [%d] [%s] (TelegramError: %s)" % (self.chat.name, self.chat.id, self.chat.type, e))
            return False
        except:
            dungeon.logger.warning("Message sending error to %s [%d] [%s]" % (self.chat.name, self.chat.id, self.chat.type))
            return False