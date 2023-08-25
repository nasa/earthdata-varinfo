""" This module contains custom exceptions specific to the `earthdata-varinfo`
    Python package. These exceptions are intended to allow for easier debugging
    of the expected errors that may occur during an invocation of the package,
    or any third party code that uses the package.

"""


class CustomError(Exception):
    """ Base class for exceptions in `earthdata-varinfo`. This base class
        allows for future work, such as assigning exit codes for specific
        failure modes.

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


class InvalidConfigFileFormatError(CustomError):
    """ This exception is raised when a configuration file is specified when
        creating an instance of a VarInfo or CFConfig class with a non ".json"
        extension.

    """

    def __init__(self, file_path):
        super().__init__('InvalidConfigFileFormatError',
                         f'"{file_path}" must be a JSON file.')


class InvalidExportDirectory(CustomError):
    """ This exception is raised when an output directory is specified for
        variable record export, and a file exists at that location instead.

    """

    def __init__(self, directory_path):
        super().__init__('InvalidExportDirectory',
                         f'"{directory_path}" cannot be an existing file.')


class MissingConfigurationFileError(CustomError):
    """ This exception is raised when a configuration file path is supplied to
        either a VarInfo class or the CFConfig class, but there is no file at
        the specified location.

    """

    def __init__(self, file_path):
        super().__init__('MissingConfigurationFileError',
                         f'No file in specified location: {file_path}')


class CMRQueryException(CustomError):
    ''' This exception is raised when a query to CMR fails.
    '''

    def __init__(self, cmr_exception_message):
        super().__init__('CMRQueryException',
                         'CMR query failed with the following error: '
                         f'{cmr_exception_message}')


class MissingPositionalArguments(CustomError):
    ''' This exception is raised when a function is missing a required
        positonal argument.
    '''

    def __init__(self, positonal_argument):
        super().__init__('MissingPositionalArguments',
                         f'Missing positional argument: {positonal_argument}')


class MissingGranuleDownloadLinks(CustomError):
    ''' This exception is raised when a granule record does not contain links
        to download data.
    '''

    def __init__(self, download_link):
        super().__init__('MissingGranuleDownloadLinks',
                         f'No links for granule record: {download_link}')


class GranuleDownloadException(CustomError):
    ''' This exception is raised when the requests modules fails.
    '''

    def __init__(self, granule_download_exception_message):
        super().__init__('GranuleDownloadException',
                         'requests module failed with the following error: '
                         f'{granule_download_exception_message}')


class DirectoryCreationException(CustomError):
    ''' This exception is raised when creating a directory fails.
    '''

    def __init__(self, directory_creation_exception_message):
        super().__init__('DirectoryCreationException',
                         'directory creation failed with the following error: '
                         f'{directory_creation_exception_message}')
