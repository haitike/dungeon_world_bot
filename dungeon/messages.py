from gettext import gettext as _

welcome = _("Welcome to Dungeon World Bot.")

no_exit = _("The bot is already stopped.")

states = [_("Stopped"),_("New Character"),_("Delete Character"),_("Master CLI"),_("Delente Adventure"),
          _("New Adventure"),_("Waiting for players"),_("Playing")]

help = list()
already_started = list()
exit = list()

for s in states:
    help.append(_("State: %s") % (s))
    already_started.append(_("The bot is already started and active. (State: %s)") % (s))
    exit.append(_("Exiting from: %s") % (s))