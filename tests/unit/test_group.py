from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase
import xml.etree.ElementTree as ET

from netCDF4 import Dataset

from varinfo.cf_config import CFConfig
from varinfo.group import GroupFromDmr, GroupFromNetCDF4

from tests.utilities import netcdf4_global_attributes, write_skeleton_netcdf4


class TestGroupFromDmr(TestCase):
    """Tests for the `Group` class using `xml.etree.ElementTree` input."""

    @classmethod
    def setUpClass(cls):
        """Set up properties of the class that do not need to be reset between
        tests.

        """
        cls.config_file = 'tests/unit/data/test_config.json'
        cls.fakesat_config = CFConfig('FakeSat', 'FAKE99', config_file=cls.config_file)
        cls.namespace = 'namespace_string'
        cls.dmr_group = ET.fromstring(
            f'<{cls.namespace}Group name="science_group">'
            f'  <{cls.namespace}Float64 name="variable_one">'
            f'  </{cls.namespace}Float64>'
            f'  <{cls.namespace}Float64 name="variable_two">'
            f'  </{cls.namespace}Float64>'
            f'  <{cls.namespace}Attribute name="coordinates">'
            f'    <{cls.namespace}Value>lat lon</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Group>'
        )
        cls.group_path = '/science_group'

    def test_group_instantiation(self):
        """Ensure a group can be created from an input DMR XML element.

        This group should contain the correct metadata attributes, accounting
        for any metadata overrides from CFConfig.

        Child variables should be listed via the `variables` class attribute.

        """
        # First attribute comes from CFConfig, the second from the DMR.
        expected_attributes = {
            'collection_override': 'collection value',
            'coordinates': 'lat lon',
        }

        group = GroupFromDmr(
            self.dmr_group,
            self.fakesat_config,
            self.namespace,
            self.group_path,
        )

        # Class attributes from AttributeContainer:
        self.assertEqual(group.namespace, self.namespace)
        self.assertEqual(group.full_name_path, self.group_path)
        self.assertDictEqual(group.attributes, expected_attributes)

        # Group specific class attributes:
        self.assertSetEqual(
            group.variables,
            {'/science_group/variable_one', '/science_group/variable_two'},
        )


class TestGroupFromNetCDF4(TestCase):
    """Tests for the `Group` class using NetCDF-4 input."""

    @classmethod
    def setUpClass(cls):
        """Set up properties of the class that do not need to be reset between
        tests.

        """
        cls.config_file = 'tests/unit/data/test_config.json'
        cls.fakesat_config = CFConfig('FakeSat', 'FAKE99', config_file=cls.config_file)
        cls.namespace = 'namespace string'

    def setUp(self):
        """Set up properties to be reset for every test."""
        self.output_dir = mkdtemp()

    def tearDown(self):
        """Perform clean-up after every test."""
        rmtree(self.output_dir)

    def test_group_instantiation(self):
        """Ensure a group can be created from an input NetCDF-4 file."""
        expected_attributes = {
            'collection_override': 'collection value',
            'global_override': 'GLOBAL',
            **netcdf4_global_attributes,
        }

        netcdf4_path = write_skeleton_netcdf4(self.output_dir)

        with Dataset(netcdf4_path) as dataset:
            group = GroupFromNetCDF4(
                dataset,
                self.fakesat_config,
                self.namespace,
                dataset.path,
            )

        # Class attributes from AttributeContainer:
        self.assertEqual(group.namespace, self.namespace)
        self.assertEqual(group.full_name_path, '/')
        self.assertDictEqual(group.attributes, expected_attributes)

        # Group specific class attributes
        self.assertSetEqual(
            group.variables,
            {'/lat', '/lon', '/time', '/science1', '/scalar1'},
        )
