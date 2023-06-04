

class Datastore:

    def __init__(self, store, branch) -> None:
        self.__store = store
        self.__branch = branch

    @property
    def store(self):
        return self.__store

    @property
    def branch(self):
        return self.__branch

    def open(self):
        pass

    def close(self, context):
        pass

    def create(self, **kwargs):
        pass

    def read(self, id, field_id, **kwargs):
        pass

    def read_all(self, **kwargs):
        pass

    def update(self, id, field_id, **kwargs):
        pass

    def delete(self, id, field_id, **kwargs):
        pass