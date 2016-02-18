import gettext
import os, sys
import logging
from telegram import Updater, Dispatcher, Update, Bot
from .terraria_update import *

DEFAULT_LANGUAGE = "en_EN"
logger = logging.getLogger("bot_log")

ASCENDING = 1
DESCENDING = -1

def translation_install(translation): # Comnpability with both python 2 / 3
    kwargs = {}
    if sys.version < '3':
        kwargs['unicode'] = True
    translation.install(**kwargs)

class TelegramBot(object):
    translations = {}
    api = None

    def __init__(self, config, db, use_webhook=False):
        self.config = config
        self.db = db
        self.db_collections()

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

        # API INICIALIZATION
        self.api = Bot(token=self.config["TOKEN"])  #try
        if use_webhook:
            self.set_webhook()
            self.dispatcher = Dispatcher(self.api,None)
        else:
            self.disable_webhook()
            self.updater = Updater(token=self.config["TOKEN"])
            self.dispatcher = self.updater.dispatcher

        self.add_handlers()

    def db_collections(self):
        self.col_terraria = self.db.terraria
        self.col_list = self.db.list
        self.col_data = self.db.data
        self.col_test = self.db.test

    def set_webhook(self):
        s = self.api.setWebhook(self.config["WEBHOOK_URL"] + "/" + self.config["TOKEN"])
        if s:
            logger.info("webhook setup worked")
        else:
            logger.warning("webhook setup failed")
        return s

    def disable_webhook(self):
        s = self.api.setWebhook("")
        if s:
            logger.info("webhook was disabled")
        else:
            logger.warning("webhook couldn't be disabled")
        return s

    def webhook_handler(self, request):
        update = Update.de_json(request)
        self.dispatcher.processUpdate(update)

    def start_polling_loop(self):
        self.update_queue = self.updater.start_polling()
        self.updater.idle()

    def add_handlers(self):
        self.dispatcher.addTelegramCommandHandler("start", self.command_start)
        self.dispatcher.addTelegramCommandHandler("help", self.command_help)
        self.dispatcher.addTelegramCommandHandler("terraria", self.command_terraria)
        self.dispatcher.addTelegramCommandHandler("list", self.command_list)
        self.dispatcher.addTelegramCommandHandler("search", self.command_search)
        self.dispatcher.addTelegramCommandHandler("settings",self.command_settings)
        self.dispatcher.addUnknownTelegramCommandHandler(self.command_unknown)
        #self.dispatcher.addErrorHandler(self.error_handle)

        self.dispatcher.addTelegramCommandHandler("dbtest",self.command_dbtest)

    def command_start(self, bot, update):
        bot.sendMessage(chat_id=update.message.chat_id, text=_("Bot was initiated. Use /help for commands."))

    def command_help(self, bot, update):
        bot.sendMessage(chat_id=update.message.chat_id, text=_(
            """Available Commands:
            /start - Iniciciate or Restart the bot
            /help - Show the command list.
            /terraria status/log/autonot/ip - Terraria options
            /list <option> <item> - Manage your lists.
            /search <engine> <word> - Search using a engine.
            /settings - Change bot options (language, etc.)"""))

    def command_terraria(self, bot, update):
        user = update.message.from_user.first_name
        help_text = _(
            """Use one of the following commands:
            /terraria status - Server status (s)
            /terraria log <number> - Show Server history (l)
            /terraria autonot - Toogle Autonotifications to user (a)
            /terraria ip - Display server IP (i)
            /terraria milestone - Add a milestone to server (m)
            /terraria on/off manually change server status""")
        command_args = update.message.text.split()
        if len(command_args) < 2:
            bot.sendMessage(chat_id=update.message.chat_id, text=help_text)
        else:
            if command_args[1] == "status" or command_args[1] == "s":
                last_update = self.get_col_lastest(self.col_terraria)
                if last_update["status"]:
                    bot.sendMessage(chat_id=update.message.chat_id, text=_("Terraria server is On (IP:%s) (Host:%s)") %
                                                                (last_update["ip"], last_update["user"]))
                else:
                    bot.sendMessage(chat_id=update.message.chat_id, text=_("Terraria server is Off"))
            elif command_args[1] == "log" or command_args[1] == "l":
                if len(command_args) > 2:
                    try:
                        limit = int(command_args[2])
                    except:
                        if command_args[2] == "m":
                            bot.sendMessage(chat_id=update.message.chat_id, text=_("Log milestone placeholder."))
                        else:
                            bot.sendMessage(chat_id=update.message.chat_id, text=_(
                                "/terraria log <number> - Number of log entries to show\n"
                                "/terraria log m - Show only milestones"))
                else:
                    limit = 5
                for i in self.get_col_lastdocs(self.col_terraria, limit):
                    string_date = i["date"].strftime("%d/%m/%y %H:%M")
                    if i["status"]:
                        status = _("On")
                    else:
                        status = _("Off")
                    text = _("[%s] (%s) Server is %s (%s) ") % ( string_date,i["user"],status,i["ip"])
                    bot.sendMessage(chat_id=update.message.chat_id, text=text)
            elif command_args[1] == "autonot" or command_args[1] == "a":
                bot.sendMessage(chat_id=update.message.chat_id, text=_("placeholder autonot text"))
            elif command_args[1] == "ip" or command_args[1] == "i":
                last_ip = self.get_col_lastest(self.col_terraria)["ip"]
                ip_text = last_ip if last_ip else _("There is no IP")
                bot.sendMessage(chat_id=update.message.chat_id, text=ip_text)
            elif command_args[1] == "milestone" or command_args[1] == "m":
                bot.sendMessage(chat_id=update.message.chat_id, text=_("placeholder milestone text"))
            elif command_args[1] == "on":
                if len(command_args) > 2:
                    self.terraria_change_status(True, user, command_args[2])
                    bot.sendMessage(chat_id=update.message.chat_id, text=_("Server was set On by %s (IP:%s)") %
                                                                          (user, command_args[2]))
                else:
                    self.terraria_change_status(True, user)
                    bot.sendMessage(chat_id=update.message.chat_id, text=_("Server was set On by %s\n*You can set a IP with:"
                                                                           " /server on <your ip>" % (user)))
            elif command_args[1] == "off":
                self.terraria_change_status(False, user)
                bot.sendMessage(chat_id=update.message.chat_id, text=_("Terraria Server Status changed to Off"))
            else:
                bot.sendMessage(chat_id=update.message.chat_id, text=help_text)

    def command_list(self, bot, update):
        bot.sendMessage(chat_id=update.message.chat_id, text=_("/list <option> <item>"))

    def command_search(self, bot, update):
        bot.sendMessage(chat_id=update.message.chat_id, text=_("/search <engine> <word>"))

    def command_settings(self, bot,update):
        languages_codes_text = _("Language codes:\n")
        for lang in self.language_list:
            languages_codes_text+= "<"+lang+"> "

        help_text = _("Use /settings language language_code\n\n" + languages_codes_text)

        command_args = update.message.text.split()
        if len(command_args) < 3:
            bot.sendMessage(chat_id=update.message.chat_id, text=help_text)
        else:
            if command_args[1] == "language" or "l":
                if command_args[2] in self.language_list:
                    bot.sendMessage(chat_id=update.message.chat_id, text=_("Language changed to %s") % (command_args[2]))
                    self.config["LANGUAGE"] =  command_args[2]
                    translation_install(self.translations[self.config["LANGUAGE"]])
                else:
                    bot.sendMessage(chat_id=update.message.chat_id, text=_("Unknown language code\n\n" + languages_codes_text))
            else:
                bot.sendMessage(chat_id=update.message.chat_id, text=help_text)

    def command_unknown(self, bot, update):
        bot.sendMessage(chat_id=update.message.chat_id, text=_("%s is a unknown command. Use /help for available commands.") % (update.message.text))

    def command_dbtest(self, bot, update):
        cursor = self.col_test.find()
        for i in cursor:
            bot.sendMessage(chat_id=update.message.chat_id, text="%s  -  <%s>" % (i["name"],i["text"]))

    def terraria_change_status(self, status, user=None, ip=None ):
        t_update = TerrariaStatusUpdate(user, status, ip)
        self.col_terraria.insert(t_update.toDBCollection())

    def get_col_lastest(self, col):
        cursor = col.find().sort("$natural",DESCENDING).limit(1)
        return cursor[0]

    def get_col_lastdocs(self, col, amount):
        return col.find().sort("$natural",DESCENDING).limit(amount)
