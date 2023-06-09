""" Scaffolding for the earthdata-varinfo package

    Note: license and classifier list:
    https://pypi.org/pypi?%3Aaction=list_classifiers

"""
from typing import List
import io
import pathlib
import os

from setuptools import find_packages, setup


CURRENT_DIRECTORY = pathlib.Path(__file__).parent.resolve()


def parse_dependencies(file_path: str) -> List[str]:
    """ Parse a Pip requirements file, and extract the dependencies. """
    with open(file_path, 'r') as file_handler:
        dependencies = file_handler.read().strip().split('\n')

    return dependencies


def get_readme(current_directory: str) -> str:
    """ Parse the README.md in the root of the repository, for the long
        description of this Python package.

    """
    with io.open(os.path.join(current_directory, 'README.md'),
                 'r', encoding='utf-8') as file_handler:
        readme = file_handler.read()

    return readme


def get_semantic_version(current_directory: str) -> str:
    """ Parse the VERSION file in the root of the repository for the semantic
        version number of the version.

    """
    with open(os.path.join(current_directory, 'VERSION'), 'r') as file_handler:
        semantic_version = file_handler.read().strip()

    return semantic_version


setup(
    name='earthdata-varinfo',
    version=get_semantic_version(CURRENT_DIRECTORY),
    author='NASA EOSDIS SDPS Data Services Team',
    author_email='owen.m.littlejohns@nasa.gov',
    description=('A package for parsing Earth Observation science granule '
                 'structure and extracting relations between science variables'
                 ' and their associated metadata, such as coordinates.'),
    long_description=get_readme(CURRENT_DIRECTORY),
    long_description_content_type='text/markdown',
    url='https://github.com/nasa/earthdata-varinfo',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    include_package_data=True,
    install_requires=parse_dependencies('requirements.txt'),
    extras_require={'dev': parse_dependencies('dev-requirements.txt')},
    test_suite='tests',
    python_requires='>=3.7',
    license='License :: OSI Approved :: Apache Software License',
    classifiers=['Programming Language :: Python',
                 'Programming Language :: Python :: 3',
                 'Operating System :: OS Independent'],
)
