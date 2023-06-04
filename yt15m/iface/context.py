
class Context:

    def __init__(self, context) -> None:
        self.__context = context

    @property
    def context(self):
        return self.__context