class InvalidPathException(Exception):
    def __init__(self, message):
        self.message = message
        Exception.__init__(self)

class InvalidInputException(Exception):
    def __init__(self, message):
        self.message = message
        Exception.__init__(self)