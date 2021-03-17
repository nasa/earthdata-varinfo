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


class UrlAccessFailed(CustomError):
    """ This exception is raise when an HTTP request for a given URL has a non
        500 error, and is therefore not retried.

    """
    def __init__(self, url, status_code):
        super().__init__('UrlAccessFailed',
                         f'{status_code} error retrieving: {url}')


class UrlAccessFailedWithRetries(CustomError):
    """ This exception is raised when an HTTP request for a given URL has
        failed a specified number of times.

    """
    def __init__(self, url):
        super().__init__('UrlAccessFailedWithRetries',
                         f'URL: {url} was unsuccessfully requested the '
                         'maximum number of times.')
