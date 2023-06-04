from yt15m.iface.datastore import Datastore

class Repository:

    def __init__(self, context: Datastore) -> None:
        self.__context = context

    @property
    def context(self) -> Datastore:
        return self.__context

    def add(self, model):
        pass

    def all(self):
        pass

    def find(self, id):
        pass

    def update(self, model):
        pass

    def remove(self, model):
        pass