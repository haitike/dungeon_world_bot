from __future__ import absolute_import
import gettext
import os, sys
import logging
import pytz
from telegram import Updater, Bot
from telegram.error import TelegramError
from pytz import timezone, utc
from haibot import Database
from haibot import Terraria

try:
    import configparser  # Python 3
except ImportError:
    import ConfigParser as configparser  # Python 2

CONFIGFILE_PATH = "data/config.cfg"
DEFAULT_LANGUAGE = "en_EN"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot_log")

def translation_install(translation): # Comnpability with both python 2 / 3
    kwargs = {}
    if sys.version < '3':
        kwargs['unicode'] = True
    translation.install(**kwargs)

class HaiBot(object):
    translations = {}
    bot = None

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read( CONFIGFILE_PATH )
        self.db = Database(self.config.get("haibot","MONGO_URL"), self.config.get("haibot","DB_NAME"))
        self.terraria = Terraria(self.db)

        #LANGUAGE STUFF
        self.language_list = os.listdir(self.config.get("haibot","LOCALE_DIR"))
        for l in self.language_list:
            self.translations[l] = gettext.translation("telegrambot", self.config.get("haibot","LOCALE_DIR"), languages=[l], fallback=True)
        try:
            if self.config.get("haibot","LANGUAGE") in self.language_list:
                translation_install(self.translations[self.config.get("haibot","LANGUAGE")])
            else:
                translation_install(self.translations[DEFAULT_LANGUAGE])
        except:
            translation_install(self.translations[DEFAULT_LANGUAGE])

        # bot INICIALIZATION
        self.updater = Updater(token=self.config.get("haibot","TOKEN"))
        self.dispatcher = self.updater.dispatcher
        self.add_handlers()

        # Timezone Stuff
        try:
            self.tzinfo = timezone(self.config.get("haibot","TIMEZONE"))
        except:
            self.tzinfo = pytz.utc

    def start_polling_loop(self):
        self.disable_webhook()
        self.update_queue = self.updater.start_polling()
        self.updater.idle()
        self.cleaning()

    def start_webhook_server(self):
        # url/token/server_on |  url/token/server_off | url/token/server_on?hostname |  url/token/server_off?hostname
        from telegram.utils.webhookhandler import WebhookHandler
        from .terraria_server_urls import do_GET
        WebhookHandler.do_GET = do_GET

        self.set_webhook()
        self.update_queue = self.updater.start_webhook(self.config.get("haibot","IP"),
                                                       self.config.getint("haibot","PORT"),
                                                       self.config.get("haibot","TOKEN"))
        self.updater.idle()
        self.cleaning()

    def cleaning(self):
        with open(CONFIGFILE_PATH, "w") as configfile:
            self.config.write(configfile)
            logger.info("Saving config file...")
        logger.info("Finished program.")

    def set_webhook(self):
        bot = Bot(token=self.config.get("haibot","TOKEN"))  #try
        s = bot.setWebhook(self.config.get("haibot","WEBHOOK_URL") + "/" + self.config.get("haibot","TOKEN"))
        if s:
            logger.info("webhook setup worked")
        else:
            logger.warning("webhook setup failed")
        return s

    def disable_webhook(self):
        bot = Bot(token=self.config.get("haibot","TOKEN"))  #try
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
        self.dispatcher.addTelegramCommandHandler("quote", self.command_quote)
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
            /quote - Quote special list
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
                    milestone_text = self.terraria.add_milestone(sender.first_name, " ".join(args[1:]))
                    is_confirmated = self.send_message(bot, update.message.chat_id, milestone_text)
                    self.autonotify(milestone_text, check_double=is_confirmated, previous_chat_id=update.message.chat_id)

                else:
                    self.send_message(bot, update.message.chat_id,_("Use /terraria milestone <TEXT>"))

            elif args[0] == "on":
                if len(args) > 1:
                    text = self.terraria.change_status(True, sender.first_name, args[1])
                else:
                    text = self.terraria.change_status(True, sender.first_name)
                    self.send_message(bot, update.message.chat_id,_("Note: You can set a IP with:\n/terraria on <your ip>" ))
                is_confirmated = self.send_message(bot, update.message.chat_id, text)
                self.autonotify(text, check_double=is_confirmated, previous_chat_id=update.message.chat_id)

            elif args[0] == "off":
                text = self.terraria.change_status(False, sender.first_name)
                is_confirmated = self.send_message(bot, update.message.chat_id, text)
                self.autonotify(text, check_double=is_confirmated, previous_chat_id=update.message.chat_id)

            else:
                self.send_message(bot, update.message.chat_id, help_text)

    def command_list(self, bot, update, args):
        help_text = _(
            """Use one of the following commands:
            /list show <all:done:notdone> - show entries in the current list (s)
            /list add - add a new entry to the current list (a)
            /list remove - remove an entry from the current list (r)
            /list lists <show:add:remove:clone> - manage lists (l)
            /list use - select a list (makes the list the current list) (u)
            /list writers <show:add:remove> - manage admins for the list (w)
            /list readers <show:add:remove> - manage readers for the list (if apply) (re)
            /list done - mark an entry as <done> (d)
            /list random - pick a random entry and show it (ra)
            /list search - show all entries matching a text (se)""")
        if len(args) < 1:
            self.send_message(bot, update.message.chat_id, help_text)
        else:
            if args[0] == "show" or args[0] == "s":
                pass
            elif args[0] == "add" or args[0] == "a":
                pass
            elif args[0] == "remove" or args[0] == "r":
                pass
            elif args[0] == "lists" or args[0] == "l":
                pass
            elif args[0] == "use" or args[0] == "u":
                pass
            elif args[0] == "writers" or args[0] == "w":
                pass
            elif args[0] == "readers" or args[0] == "re":
                pass
            elif args[0] == "done" or args[0] == "d":
                pass
            elif args[0] == "random" or args[0] == "ra":
                pass
            elif args[0] == "search" or args[0] == "se":
                pass
            else:
                self.send_message(bot, update.message.chat_id, help_text)

    def command_quote(self, bot, update):
        self.send_message(bot, update.message.chat_id, _("QUOTE"))

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
                    try:
                        self.config.set("haibot","LANGUAGE", args[1] )
                        translation_install(self.translations[self.config.get("haibot","LANGUAGE")])
                        self.send_message(bot, update.message.chat_id, _("Language changed to %s") % (args[1]))
                        logger.info("Language was changed to %s" % (args[1]))
                    except:
                        logger.info("A error happened changing language to %s" % (args[1]))

                else:
                    self.send_message(bot, update.message.chat_id, _("Unknown language code\n\n" + languages_codes_text))
            else:
                self.send_message(bot, update.message.chat_id, help_text)

    def command_unknown(self, bot, update):
        self.send_message(bot, update.message.chat_id, _("%s is a unknown command. Use /help for available commands.") % (update.message.text))

    def autonotify(self, text, check_double=False, previous_chat_id=None ):
        autonot_list = self.db.read_one( "data", query={'name':"autonot" } )
        if autonot_list:
            for tel_id in autonot_list["users"]:
                if check_double and tel_id==previous_chat_id:
                    break
                else:
                    text_to_queue = str("/notify %s %s" % (tel_id, text))
                    self.update_queue.put(text_to_queue)

    # /terraria_on IP user
    def terraria_on(self, bot, update, args):
        if len(args) > 1:
            text = self.terraria.change_status(True, " ".join(args[1:]), args[0])
        else:
            text = self.terraria.change_status(True)
        self.autonotify(text)

    # /terraria_of user
    def terraria_off(self, bot, update, args):
        if len(args) > 0:
            text = self.terraria.change_status(False, " ".join(args[0:]))
        else:
            text = self.terraria.change_status(False)
        self.autonotify(text)

    # /notify ID text
    def notify(self, bot, update, args):
        self.send_message(bot, int(args[0]), " ".join(args[1:]))

    def send_message(self, bot, chat_id, text):
        try:
            bot.sendMessage(chat_id=chat_id, text=text)
            return True
        except TelegramError as e:
            logger.warning("Terraria Autonot to User [%d]: TelegramError: %s" % (chat_id,e))
            return False
        except:
            logger.warning("A Message could not be sent:\n%s " % (text))
            return False