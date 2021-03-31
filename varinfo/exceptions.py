""" This module contains custom exceptions specific to the `sds-varinfo` Python
    package. These exceptions are intended to allow for easier debugging of the
    expected errors that may occur during an invocation of the package, or any
    third party code that uses the package.

"""


class CustomError(Exception):
    """ Base class for exceptions in `sds-varinfo`. This base class allows for
        future work, such as assigning exit codes for specific failure modes.

    """
    def __init__(self, exception_type, message):
        self.exception_type = exception_type
        self.message = message
        super().__init__(self.message)


class DmrNamespaceError(CustomError):
    """ This exception is raised when the root element of a dmr XML document
        is not a fully qualified Dataset tag.

    """
    def __init__(self, tag):
        super().__init__('DmrNamespaceError', f'Unexpected root: {tag}')
