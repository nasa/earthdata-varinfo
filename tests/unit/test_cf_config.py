from unittest import TestCase

from varinfo import CFConfig
from varinfo.exceptions import (
    InvalidConfigFileFormatError,
    MissingConfigurationFileError,
)


class TestCFConfig(TestCase):
    """Perform unit tests to establish the CFConfig class can be successfully
    instantiated, with the expected class attributes and methods. Also
    test public methods within the class to ensure they return the expected
    results.

    """

    @classmethod
    def setUpClass(cls):
        """Set attributes for the class that can be shared between tests."""
        cls.test_config = 'tests/unit/data/test_config.json'
        cls.mission = 'FakeSat'
        cls.short_name = 'FAKE99'
        cls.expected_excluded_science_variables = {
            '/exclude_one/.*',
            '/exclude_two/.*',
            '/exclude_three/.*',
        }
        cls.required_variables = {'/required_group/.*'}
        cls.expected_cf_overrides = {
            '.*': {'collection_override': 'collection value'},
            '/$': {'global_override': 'GLOBAL'},
            '/absent_variable': {'extra_override': 'overriding value'},
            '/coordinates_group/.*': {'coordinates': 'lat, lon'},
            '/group/.*': {'group_override': 'group value'},
            '/group/variable': {'variable_override': 'variable value'},
        }

    def test_instantiation(self):
        """Ensure the attributes of an object are set upon class
        instantiation. This should include mission, short_name and information
        from the configuration file. It should also exclude all attributes with
        applicabilities that do not match the supplied mission and short name.

        """
        config = CFConfig(self.mission, self.short_name, self.test_config)

        self.assertEqual(self.mission, config.mission)
        self.assertEqual(self.short_name, config.short_name)

        self.assertSetEqual(
            self.expected_excluded_science_variables,
            config.excluded_science_variables,
        )

        self.assertSetEqual(self.required_variables, config.required_variables)
        self.assertDictEqual(self.expected_cf_overrides, config.cf_overrides)

    def test_instantiation_no_file(self):
        """Ensure an instance of the `CFConfig` class can be produced when no
        file is specified. This should result in largely empty attributes.

        """
        config = CFConfig(self.mission, self.short_name)

        self.assertEqual(self.mission, config.mission)
        self.assertEqual(self.short_name, config.short_name)
        self.assertSetEqual(set(), config.excluded_science_variables)
        self.assertSetEqual(set(), config.required_variables)
        self.assertDictEqual({}, config.cf_overrides)

    def test_instantiation_missing_configuration_file(self):
        """Ensure a MissingConfigurationFileError is raised when a path to a
        non-existent configuration file is specified.

        """
        with self.assertRaises(MissingConfigurationFileError):
            CFConfig(self.mission, self.short_name, 'bad_file_path.json')

    def test_instantiation_invalid_configuration_file_format(self):
        """Ensure an InvalidConfigFileFormatError is raised when the specified
        configuration file path is for a non-JSON file.

        """
        with self.assertRaises(InvalidConfigFileFormatError):
            CFConfig(
                self.mission,
                self.short_name,
                config_file='tests/unit/data/ATL03_example.dmr',
            )

    def test_get_cf_overrides_variable(self):
        """Ensure the CFConfig.get_cf_overrides method returns all overriding
        attributes where the variable pattern matches the supplied variable or
        group name. If multiple patterns match the variable name, then the
        pattern that is the most specific, as determined by a combination of
        hierarchical depth in the regular expression and, secondarily, the
        length of the variable pattern string, will be returned.

        """
        expected_collection_overrides = {'collection_override': 'collection value'}
        expected_group_overrides = {
            'collection_override': 'collection value',
            'group_override': 'group value',
        }
        expected_variable_overrides = {
            'collection_override': 'collection value',
            'group_override': 'group value',
            'variable_override': 'variable value',
        }

        test_args = [
            [
                'Collection only',
                'random_variable',
                expected_collection_overrides,
            ],
            [
                'Group overrides',
                '/group/random',
                expected_group_overrides,
            ],
            [
                'Variable overrides',
                '/group/variable',
                expected_variable_overrides,
            ],
        ]

        config = CFConfig(self.mission, self.short_name, self.test_config)

        for description, variable, expected_overrides in test_args:
            with self.subTest(description):
                self.assertDictEqual(
                    config.get_cf_overrides(variable),
                    expected_overrides,
                )

    def test_get_cf_overrides_variable_conflicts(self):
        """Ensure that if a variable matches multiple override rules that
        specify conflicting values for a metadata attribute, the most specific
        matching metadata attribute takes precedence.

        The primary measure of specificity is the depth of the variable
        hierarchy specified in the VariablePattern, with secondary sorting
        based upon the length of strings at the same hierarchy.

        """
        config = CFConfig(self.mission, 'FAKE97', self.test_config)

        with self.subTest('Deeper matches takes precedence over shallower'):
            self.assertDictEqual(
                config.get_cf_overrides('/group/variable'),
                {
                    'conflicting_attribute_global_and_group': 'applies to /group/.*',
                    'conflicting_attribute_group_and_variable': 'applies to /group/variable',
                },
            )

        with self.subTest('Depth takes precedence over string length'):
            self.assertDictEqual(
                config.get_cf_overrides('/other_group/variable'),
                {
                    'conflicting_attribute_global_and_group': 'applies to all',
                    'test_depth_priority_over_string_length': 'applies to /other_group/variable',
                },
            )

        with self.subTest('String length decides between matches of equal depth'):
            self.assertDictEqual(
                config.get_cf_overrides('/string_length/variable'),
                {
                    'conflicting_attribute_global_and_group': 'applies to all',
                    'test_string_length_same_depth': 'applies to /string_length/variable',
                },
            )
