from datetime import datetime
import inspect
class BaseModel(object):
    def __init__(self, id):
        self.id = id

    def to_json(self):
        return self.__dict__  #Equivalent to vars(object)

    @classmethod
    def from_json(cls, json_data):
        if json_data is not None:
            build_list = []
            par_list = inspect.getargspec(cls.__init__).args[1:] #Get parameters names removing self
            try:
                for i in par_list:
                    build_list.append(json_data[i])
                return cls(*build_list)
            except KeyError as e:
                raise Exception("Key not found in json_data: %s" % (repr(e)))
        else:
            raise Exception("No data to create Project from!")

class TemporalExample(BaseModel):
    def __init__(self, user, status, date=datetime.utcnow(), is_admin = False):
        self.user = user
        self.status = status
        self.date = date
        self.is_admin = is_admin

    def __str__(self):
        fdate = self.date.strftime("%d/%m/%y %H:%M")
        if self.status:
            return _("[%s] %s is On") % (fdate , self.user)
        else:
            return _("[%s] %s is Off") % (fdate , self.user)