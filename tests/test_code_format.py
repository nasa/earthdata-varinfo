from pathlib import Path
from unittest import TestCase

from pycodestyle import StyleGuide


class TestCodeFormat(TestCase):
    """ This test class should ensure all earthdata-varinfo Python code adheres
        to standard Python code styling.

        Ignored errors and warnings:

        * E501: Line length, which defaults to 80 characters. This is a
                preferred feature of the code, but not always easily achieved.
        * W503: Break before binary operator. Have to ignore one of W503 or
                W504 to allow for breaking of some long lines. PEP8 suggests
                breaking the line before a binary operator is more "Pythonic".

    """
    @classmethod
    def setUpClass(cls):
        cls.python_files = Path('varinfo').rglob('*.py')

    def test_pycodestyle_adherence(self):
        """ Ensure all code in the `varinfo` directory adheres to PEP8 defined
            standards.

        """
        style_guide = StyleGuide(ignore=['E501', 'W503'])
        results = style_guide.check_files(self.python_files)
        self.assertEqual(results.total_errors, 0, 'Found code style issues.')
