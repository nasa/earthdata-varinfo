from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase
import xml.etree.ElementTree as ET

from netCDF4 import Dataset

from varinfo.attribute_container import (
    AttributeContainerFromDmr,
    AttributeContainerFromNetCDF4,
)
from varinfo.cf_config import CFConfig

from tests.utilities import netcdf4_global_attributes, write_skeleton_netcdf4


class TestAttributeContainerFromDmr(TestCase):
    """Tests to ensure the `AttributeContainerFromDmr` class instantiates
    correctly. This is the superclass for `GroupFromDmr` and
    `VariableFromDmr`.

    """

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that can be reused between tests."""
        cls.config_file = 'tests/unit/data/test_config.json'
        cls.fakesat_config = CFConfig('FakeSat', 'FAKE99', config_file=cls.config_file)
        cls.namespace = 'namespace_string'
        cls.dmr_group = ET.fromstring(
            f'<{cls.namespace}Group name="science_group">'
            f'  <{cls.namespace}Attribute name="coordinates">'
            f'    <{cls.namespace}Value>lat_for_group lon_for_group</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Group>'
        )
        cls.group_path = '/science_group'
        cls.dmr_variable = ET.fromstring(
            f'<{cls.namespace}Float64 name="variable">'
            f'  <{cls.namespace}Attribute name="units" type="String">'
            f'    <{cls.namespace}Value>m</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.variable_path = '/group/variable'

    def test_instantiation_for_group(self):
        """Ensure an `AttributeContainerFromDmr` can be created from a group."""
        expected_attributes = {
            'collection_override': 'collection value',
            'coordinates': 'lat_for_group lon_for_group',
        }

        container = AttributeContainerFromDmr(
            self.dmr_group,
            self.fakesat_config,
            self.namespace,
            self.group_path,
        )

        self.assertEqual(container.namespace, self.namespace)
        self.assertEqual(container.full_name_path, self.group_path)
        self.assertDictEqual(
            container.attributes,
            expected_attributes,
        )

    def test_instantiation_for_variable(self):
        """Ensure an `AttributeContainerFromDmr` can be created from a variable."""
        expected_attributes = {
            'collection_override': 'collection value',
            'group_override': 'group value',
            'units': 'm',
            'variable_override': 'variable value',
        }

        container = AttributeContainerFromDmr(
            self.dmr_variable,
            self.fakesat_config,
            self.namespace,
            self.variable_path,
        )

        self.assertEqual(container.namespace, self.namespace)
        self.assertEqual(container.full_name_path, self.variable_path)
        self.assertDictEqual(
            container.attributes,
            expected_attributes,
        )

    def test_get_attribute_value(self):
        """Ensure attribute values can be correctly retrieved."""
        container = AttributeContainerFromDmr(
            self.dmr_group,
            self.fakesat_config,
            self.namespace,
            self.group_path,
        )

        with self.subTest('Value from DMR'):
            self.assertEqual(
                container.get_attribute_value('coordinates'),
                'lat_for_group lon_for_group',
            )

        with self.subTest('Override from CFConfig'):
            self.assertEqual(
                container.get_attribute_value('collection_override'),
                'collection value',
            )


class TestAttributeContainerFromNetCDF4(TestCase):
    """Tests to ensure the `AttributeContainerFromNetCDF4` class instantiates
    correctly. This is the superclass for `GroupFromNetCDF4` and
    `VariableFromNetCDF4`.

    """

    @classmethod
    def setUpClass(cls):
        """Set up properties of the class that do not need to reset between
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

    def test_instantatiation_for_root_group(self):
        """Ensure an `AttributeContainerFromNetCDF4` can be created from a
        group.

        """
        netcdf4_path = write_skeleton_netcdf4(self.output_dir)
        expected_attributes = {
            'collection_override': 'collection value',
            'global_override': 'GLOBAL',
            **netcdf4_global_attributes,
        }

        with Dataset(netcdf4_path) as dataset:
            container = AttributeContainerFromNetCDF4(
                dataset,
                self.fakesat_config,
                self.namespace,
                dataset.path,
            )

        self.assertEqual(container.namespace, self.namespace)
        self.assertEqual(container.full_name_path, '/')
        self.assertDictEqual(
            container.attributes,
            expected_attributes,
        )

    def test_instantatiation_for_nested_group(self):
        """Ensure an `AttributeContainerFromNetCDF4` can be created from a
        group.

        """
        netcdf4_path = write_skeleton_netcdf4(self.output_dir)
        expected_attributes = {
            'collection_override': 'collection value',
        }

        with Dataset(netcdf4_path) as dataset:
            container = AttributeContainerFromNetCDF4(
                dataset['/group'],
                self.fakesat_config,
                self.namespace,
                dataset['/group'].path,
            )

        self.assertEqual(container.namespace, self.namespace)
        self.assertEqual(container.full_name_path, '/group')
        self.assertDictEqual(
            container.attributes,
            expected_attributes,
        )

    def test_instantiation_for_variable(self):
        """Ensure an `AttributeContainerFromNetCDF4` can be created from a
        variable.

        """
        netcdf4_path = write_skeleton_netcdf4(self.output_dir)
        expected_attributes = {
            'collection_override': 'collection value',
            'coordinates': '/lat /lon',
            'description': 'A science variable for testing',
            'group_override': 'group value',
        }

        with Dataset(netcdf4_path) as dataset:
            container = AttributeContainerFromNetCDF4(
                dataset['/group/science2'],
                self.fakesat_config,
                self.namespace,
                '/group/science2',
            )

        self.assertEqual(container.namespace, self.namespace)
        self.assertEqual(container.full_name_path, '/group/science2')
        self.assertDictEqual(
            container.attributes,
            expected_attributes,
        )

    def test_get_attribute_value(self):
        """Ensure attribute values can be correctly retrieved."""
        netcdf4_path = write_skeleton_netcdf4(self.output_dir)

        with Dataset(netcdf4_path) as dataset:
            container = AttributeContainerFromNetCDF4(
                dataset['/group/science2'],
                self.fakesat_config,
                self.namespace,
                '/group/science2',
            )

        with self.subTest('Value from NetCDF4 variable'):
            self.assertEqual(
                container.get_attribute_value('description'),
                'A science variable for testing',
            )

        with self.subTest('Override from CFConfig'):
            self.assertEqual(
                container.get_attribute_value('collection_override'),
                'collection value',
            )
