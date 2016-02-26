import gettext
import os, sys
import logging
import pytz
from .database import Database
from telegram import Updater, Bot
from telegram.error import *
from pytz import timezone
from .terraria import *

DEFAULT_LANGUAGE = "en_EN"
logger = logging.getLogger("bot_log")

def translation_install(translation): # Comnpability with both python 2 / 3
    kwargs = {}
    if sys.version < '3':
        kwargs['unicode'] = True
    translation.install(**kwargs)

class TelegramBot(object):
    translations = {}
    bot = None

    def __init__(self, config):
        self.db = Database(config["MONGO_URL"], config["DB_NAME"])
        self.config = config
        self.terraria = Terraria(self.db)

        #LANGUAGE STUFF
        self.language_list = os.listdir(self.config["LOCALE_DIR"])
        for l in self.language_list:
            self.translations[l] = gettext.translation("telegrambot", self.config["LOCALE_DIR"], languages=[l], fallback=True)
        try:
            if self.config["LANGUAGE"] in self.language_list:
                translation_install(self.translations[self.config["LANGUAGE"]])
            else:
                translation_install(self.translations[DEFAULT_LANGUAGE])
        except:
            translation_install(self.translations[DEFAULT_LANGUAGE])

        # bot INICIALIZATION
        self.updater = Updater(token=self.config["TOKEN"])
        self.dispatcher = self.updater.dispatcher
        self.add_handlers()

        # Timezone Stuff
        try:
            self.tzinfo = timezone(self.config["TIMEZONE"])
        except:
            self.tzinfo = pytz.utc

    def start_polling_loop(self):
        self.disable_webhook()
        self.update_queue = self.updater.start_polling()
        self.updater.idle()

    def start_webhook_server(self):
        # url/token/server_on |  url/token/server_off | url/token/server_on?hostname |  url/token/server_off?hostname
        from telegram.utils.webhookhandler import WebhookHandler
        from .terraria_server_urls import do_GET
        WebhookHandler.do_GET = do_GET

        self.set_webhook()
        self.update_queue = self.updater.start_webhook(self.config["IP"], self.config["PORT"], self.config["TOKEN"])
        self.updater.idle()

    def set_webhook(self):
        bot = Bot(token=self.config["TOKEN"])  #try
        s = bot.setWebhook(self.config["WEBHOOK_URL"] + "/" + self.config["TOKEN"])
        if s:
            logger.info("webhook setup worked")
        else:
            logger.warning("webhook setup failed")
        return s

    def disable_webhook(self):
        bot = Bot(token=self.config["TOKEN"])  #try
        s = bot.setWebhook("")
        if s:
            logger.info("webhook was disabled")
        else:
            logger.warning("webhook couldn't be disabled")
        return s

    def add_handlers(self):
        self.dispatcher.addTelegramCommandHandler("start", self.command_start)
        self.dispatcher.addTelegramCommandHandler("help", self.command_help)
        self.dispatcher.addTelegramCommandHandler("terraria", self.command_terraria)
        self.dispatcher.addTelegramCommandHandler("list", self.command_list)
        self.dispatcher.addTelegramCommandHandler("search", self.command_search)
        self.dispatcher.addTelegramCommandHandler("settings",self.command_settings)
        self.dispatcher.addUnknownTelegramCommandHandler(self.command_unknown)
        #self.dispatcher.addErrorHandler(self.error_handle)

        self.dispatcher.addStringCommandHandler("terraria_on", self.terraria_on)
        self.dispatcher.addStringCommandHandler("terraria_off", self.terraria_off)
        self.dispatcher.addStringCommandHandler("notify", self.notify)


    def command_start(self, bot, update):
        self.send_message(bot, update.message.chat_id, _("Bot was initiated. Use /help for commands."))

    def command_help(self, bot, update):
        self.send_message(bot, update.message.chat_id, _(
            """Available Commands:
            /start - Iniciciate or Restart the bot
            /help - Show the command list.
            /terraria status/log/autonot/ip - Terraria options
            /list option item - Manage your lists.
            /search engine word - Search using a engine.
            /settings - Change bot options (language, etc.)"""))

    def command_terraria(self, bot, update, args):
        sender = update.message.from_user
        help_text = _(
            """Use one of the following commands:
            /terraria status - Server status (s)
            /terraria log <number> - Show Server history (l)
            /terraria autonot <on/off> - Toogle Autonotifications to user (a)
            /terraria ip - Display server IP (i)
            /terraria milestone - Add a milestone to server (m)
            /terraria on/off manually change server status""")
        if len(args) < 1:
            self.send_message(bot,update.message.chat_id, help_text)
        else:
            if args[0] == "status" or args[0] == "s":
                self.send_message(bot, update.message.chat_id, self.terraria.get_status())

            elif args[0] == "log" or args[0] == "l":
                if len(args) > 1:
                    try:
                        log_text = self.terraria.get_log(int(args[1]), tzinfo=self.tzinfo)
                    except:
                        if args[1] == "m":
                            log_text = self.terraria.get_log(5, only_milestone=True, tzinfo=self.tzinfo)
                        else:
                            log_text = _("/terraria log <number> - Number of log entries to show\n"
                                         "/terraria log m - Show only milestones")
                else:
                    log_text = self.terraria.get_log(5, tzinfo=self.tzinfo)
                self.send_message(bot, update.message.chat_id, log_text)

            elif args[0] == "autonot" or args[0] == "a":
                if len(args) > 1:
                    if args[1] == "on":
                        is_autonot = self.terraria.set_autonot_on(sender.id)
                    elif args[1] == "off":
                        is_autonot = self.terraria.set_autonot_off(sender.id)
                    else:
                        self.send_message(bot, update.message.chat_id, "/terraria autonot\n/terraria autonot on/off")
                else:
                    if self.terraria.get_autonot_status(sender.id):
                        is_autonot = self.terraria.set_autonot_off(sender.id)
                    else:
                        is_autonot = self.terraria.set_autonot_on(sender.id)
                if is_autonot:
                    self.send_message(bot, update.message.chat_id, sender.first_name+_(" was added to auto notifications."))
                else:
                    self.send_message(bot, update.message.chat_id, sender.first_name+_(" was removed from auto notifications."))

            elif args[0] == "ip" or args[0] == "i":
                self.send_message(bot, update.message.chat_id, self.terraria.get_ip())

            elif args[0] == "milestone" or args[0] == "m":
                if len(args) > 1:
                    milestone_text = self.terraria.add_milestone(sender.first_name, " ".join(args[2:]))
                    self.send_message(bot, update.message.chat_id, milestone_text)
                    self.autonotify(milestone_text)
                else:
                    self.send_message(bot, update.message.chat_id,_("Use /terraria milestone <TEXT>"))

            elif args[0] == "on":
                if len(args) > 1:
                    text = self.terraria.change_status(True, sender.first_name, args[1])
                else:
                    text = self.terraria.change_status(True, sender.first_name)
                    self.send_message(bot, update.message.chat_id,_("Note: You can set a IP with:\n/terraria on <your ip>" ))
                self.send_message(bot, update.message.chat_id, text)
                self.autonotify(text)

            elif args[0] == "off":
                text = self.terraria.change_status(False, sender.first_name)
                self.send_message(bot, update.message.chat_id, self.terraria.last_status_update.get_text())
                self.autonotify(text)

            else:
                self.send_message(bot, update.message.chat_id, help_text)

    def command_list(self, bot, update):
        self.send_message(bot, update.message.chat_id, _("/list option item"))

    def command_search(self, bot, update):
        self.send_message(bot, update.message.chat_id, _("/search engine word"))

    def command_settings(self, bot,update, args):
        languages_codes_text = _("Language codes:\n")
        for lang in self.language_list:
            languages_codes_text+= "<"+lang+"> "

        help_text = _("Use /settings language language_code\n\n" + languages_codes_text)

        if len(args) < 2:
            self.send_message(bot, update.message.chat_id, help_text)
        else:
            if args[0] == "language" or "l":
                if args[1] in self.language_list:
                    self.send_message(bot, update.message.chat_id, _("Language changed to %s") % (args[1]))
                    self.config["LANGUAGE"] =  args[1]
                    translation_install(self.translations[self.config["LANGUAGE"]])
                else:
                    self.send_message(bot, update.message.chat_id, _("Unknown language code\n\n" + languages_codes_text))
            else:
                self.send_message(bot, update.message.chat_id, help_text)

    def command_unknown(self, bot, update):
        self.send_message(bot, update.message.chat_id, _("%s is a unknown command. Use /help for available commands.") % (update.message.text))

    def autonotify(self, text):
        autonot_list = self.db.read_one( "data", query={'name':"autonot" } )
        if autonot_list:
            for tel_id in autonot_list["users"]:
                text_to_queue = str("/notify %s %s" % (tel_id, text))
                self.update_queue.put(text_to_queue)

    def terraria_on(self, bot, update, args):
        if len(args) > 1:
            text = self.terraria.change_status(True, args[0], args[1])
        else:
            text = self.terraria.change_status(True)
        self.autonotify(text)

    def terraria_off(self, bot, update, args):
        if len(args) > 0:
            text = self.terraria.change_status(False, args[0])
        else:
            text = self.terraria.change_status(False)
        self.autonotify(text)

    # Use ---> /notify ID text
    def notify(self, bot, update, args):
        self.send_message(bot, int(args[0]), " ".join(args[1:]))

    def send_message(self, bot, chat_id, text):
        try:
            bot.sendMessage(chat_id=chat_id, text=text)
        except TelegramError as e:
            logger.warning("Terraria Autonot to User [%d]: TelegramError: %s" % (chat_id,e))
        except:
            logger.warning("A Message could not be sent:\n%s " % (text))

