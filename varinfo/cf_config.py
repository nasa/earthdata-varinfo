"""This module contains a class designed to read and present information from
a JSON configuration file. This configuration file provides overriding
information for attributes provided by granules on a per-collection basis.
This information is primarily intended to augment the CF-Convention
attributes for a dataset, but can also be used to alter non CF-Convention
metadata within a granule.

Information within the configuration file is split into rules that have
an Applicability. This section should define a mission, collection short
name and (optionally) a regular expression compatible string for relevant
variable paths.

The configuration file also specifies variables that are incorrectly
considered as science variables by the VarInfo class, due to them having
references in the coordinates attribute. Further, there are required
variables that have to be included in the output of any variable subset
request for a specific collection.

"""

from __future__ import annotations

from os.path import exists
from typing import Any
import json
import re

from varinfo.exceptions import (
    InvalidConfigFileFormatError,
    MissingConfigurationFileError,
)


class CFConfig:
    """This class should read the main configuration file,
    see e.g. sample_config.json, which defines overriding values for the
    attributes stored in fields such as ancillary_variables, or dimensions.

    Given a mission and collection short name, upon instantiation, the
    object should only retain information relevant to that specific
    collection.

    """

    def __init__(
        self,
        mission: str | None,
        collection_short_name: str | None,
        config_file: str | None = None,
    ):
        """Set supplied class attributes. Then read the designated
        configuration file to obtain mission and short name specific
        attributes.

        """
        self.config_file = config_file
        self.mission = mission
        self.short_name = collection_short_name

        self.metadata_overrides: dict[str, dict[str, Any]] = {}
        self.excluded_science_variables: set[str] = set()
        self.required_variables: set[str] = set()

        if self.mission is not None:
            self._read_config_file()

    def _read_config_file(self):
        """Open the main configuration JSON file and extract only those parts
        of it pertaining to the mission and collection specified upon
        instantiating the class.

        Note: Applicable rules for `RequiredVariables` will be applied to all
        variables in a collection when trying to identify required variables
        for a given subset of requested variables. The `VariablePattern` of
        the `ApplicabilityType` is not taken into account.

        """
        if self.config_file is not None and not exists(self.config_file):
            raise MissingConfigurationFileError(self.config_file)
        elif self.config_file is not None and self.config_file.endswith('.json'):
            with open(self.config_file, 'r', encoding='utf-8') as file_handler:
                config = json.load(file_handler)
        elif self.config_file is not None:
            raise InvalidConfigFileFormatError(self.config_file)
        else:
            config = {}

        self.excluded_science_variables = {
            pattern
            for item in config.get('ExcludedScienceVariables', [])
            if self._is_applicable(
                item['Applicability'].get('Mission'),
                item['Applicability'].get('ShortNamePath'),
            )
            for pattern in item['VariablePattern']
        }

        self.required_variables = {
            pattern
            for item in config.get('RequiredVariables', [])
            if self._is_applicable(
                item['Applicability'].get('Mission'),
                item['Applicability'].get('ShortNamePath'),
            )
            for pattern in item['VariablePattern']
        }

        for override in config.get('MetadataOverrides', []):
            self._process_cf_item(override, self.metadata_overrides)

    def _is_applicable(self, mission: str, short_name: str | None = None) -> bool:
        """Given a mission, and optionally also a collection short name, of an
        applicability within the configuration file, check for a match
        against the mission and short name specified when instantiating the
        class object.

        """
        mission_matches = re.match(mission, self.mission) is not None

        short_name_matches = (
            short_name is None or re.match(short_name, self.short_name) is not None
        )

        return mission_matches and short_name_matches

    def _process_cf_item(
        self,
        cf_item: dict,
        results: dict[str, dict],
        input_mission: str | None = None,
        input_short_name: str | None = None,
    ):
        """Process a single block in the `MetadataOverrides` region of the
        configuration file. First check that the applicability matches the
        mission and short name for the class. Next, check for a variable
        pattern. This is indicative of there being overriding attributes in
        this list item. Assign any information to the results dictionary, with
        a key of that variable pattern.

        """
        mission = cf_item['Applicability'].get('Mission') or input_mission
        short_name = cf_item['Applicability'].get('ShortNamePath') or input_short_name

        if mission is not None and self._is_applicable(mission, short_name):
            # Some outer Applicability items have attributes, but no
            # variable path - the assumption here is that the applicability is
            # to all variables (see ICESat2 dimensions override, SPL4.* and
            # SPL3FTA grid_mapping overrides)
            pattern = cf_item['Applicability'].get('VariablePattern', '.*')
            results[pattern] = self._create_attributes_object(cf_item)

    @staticmethod
    def _create_attributes_object(cf_item: dict) -> dict[str, str]:
        """Construct a dictionary object containing all contained attributes,
        which are specified as list items with Name and Value keys.

        """
        return {
            attribute['Name']: attribute['Value']
            for attribute in cf_item.get('Attributes', {})
        }

    def get_metadata_overrides(self, variable_path: str) -> dict[str, Any]:
        """Return the MetadataOverrides that match a given variable. If there
        are no overrides, then empty dictionaries will be returned instead.

        First iterate through the self.metadata_overrides and find all items
        with a variable pattern that matches the supplied variable (or group)
        path.

        Next sort that dictionary, so that matching patterns are:

        * Primarily sorted from shallowed to deepest, by counting the total
          number of slashes in the string.
        * Within each depth (with the same number of slashes), patterns are
          sorted from shortest to longest string length.

        It is assumed that regular expressions that match deeper elements of
        a file hierarchy are intended to be more specifically applied, and that
        within a given depth, the string length is a proxy for specificity.

        Last, combine the attribute names and values from each matching
        override item. Because of the ordering in the previous step, if there
        are multiple values supplied for the same metadata attribute, the value
        retained will be the one with the longest variable pattern, which is a
        proxy for how specific the override is.

        Note: Depth is approximated by counting the _total_ number of slashes
        in the VariablePattern regular expression, and does not account for
        alternation. As such:

        ```
        "Applicability": {
          "VariablePattern": "/(group_one|group_two)/.*
        }
        ```

        will correctly determine a depth of 2, whereas:

        ```
        "Applicability": {
          "VariablePattern": "(/group_one/.*|/group_two/.*)"
        }
        ```
        will incorrectly determine a depth of 4.

        """
        matching_overrides = {
            pattern: attributes
            for pattern, attributes in self.metadata_overrides.items()
            if re.match(pattern, variable_path) is not None
        }

        # Order MetadataOverrides items by:
        # First: Depth of the variable hierarchy included in the regular
        # expression pattern (number of slashes), shallowest to deepest.
        # Second: The length of the variable pattern, from shorted to longest.
        # The second ordering is applied in to regular expressions specifying
        # the same depth of variable hierarchy.
        sorted_overrides = dict(
            sorted(
                matching_overrides.items(),
                key=lambda pattern: (pattern[0].count('/'), len(pattern[0])),
            ),
        )

        # Combine all overrides. In the case a metadata attribute appears in
        # multiple matching overrides, the value that comes later based on the
        # previous sorting of variable patterns will take precedence.
        return {
            attribute_name: attribute_value
            for sorted_override in sorted_overrides.values()
            for attribute_name, attribute_value in sorted_override.items()
        }
