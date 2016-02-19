import datetime # TODO i18n multiple files

class TerrariaUpdate(object):
    def __init__(self, user):
        self.user = user
        self.date = datetime.datetime.utcnow()
        self.is_milestone = False

    def toDBCollection(self):
        return vars(self)


class TerrariaStatusUpdate(TerrariaUpdate):
    def __init__(self, user, status, ip):
        super(TerrariaStatusUpdate, self).__init__(user)
        self.status = status
        self.ip = ip

    def __str__(self):
        if self.status:
            return _("(%s) Terraria server is On (IP:%s)") % (self.user , self.ip)
        else:
            return _("(%s) Terraria server is Off (IP:%s)")  % (self.user , self.ip)

class TerrariaMilestoneUpdate(TerrariaUpdate):
    def __init__(self, user, text):
        super(TerrariaMilestoneUpdate, self).__init__(user)
        self.milestone_text = text
        self.is_milestone = True

    def __str__(self):
        return "(%s) Milestone: %s" % (self.user , self.milestone_text)