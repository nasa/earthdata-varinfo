""" This module contains a class designed to read information from a `.dmr`
    file. This should group the input into science variables, metadata,
    coordinates, dimensions and ancillary data sets.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from os.path import exists
from typing import Any, Union
import json
import re
import xml.etree.ElementTree as ET

from netCDF4 import Dataset, Group

from varinfo.cf_config import CFConfig
from varinfo.exceptions import (
    InvalidConfigFileFormatError,
    MissingConfigurationFileError,
)
from varinfo.group import GroupFromDmr, GroupFromNetCDF4
from varinfo.utilities import (
    DAP4_TO_NUMPY_MAP,
    get_full_path_netcdf4_attribute,
    get_full_path_xml_attribute,
    get_xml_namespace,
)
from varinfo.variable import VariableFromDmr, VariableFromNetCDF4


DimensionsGroupType = dict[tuple[str], set[str]]
OutputGroupType = Union[GroupFromDmr, GroupFromNetCDF4]
OutputVariableType = Union[VariableFromDmr, VariableFromNetCDF4]


class VarInfoBase(ABC):
    """An abstract base class to represent the full dataset of a granule,
    having reading information from a representation of that granule. Currently
    supported granule representations: OPeNDAP Dataset Metadata Response (DMR),
    NetCDF-4 file.

    """

    def __init__(
        self,
        file_path: str,
        short_name: str | None = None,
        config_file: str | None = None,
    ):
        """Distinguish between variables containing references to other
        datasets, and those that do not. The former are considered science
        variables, providing they are not considered coordinates or
        dimensions for another variable.

        Each variable contains references to their specific coordinates and
        dimensions, allowing the retrieval of all required variables for a
        specified list of science variables.

        """
        self.config_file = config_file
        self.short_name = short_name
        self.mission = None
        self.namespace = None
        self.groups: dict[str, OutputGroupType] = {}
        self.variables: dict[str, OutputVariableType] = {}
        self.references: set[str] = set()
        self.metadata: dict[str, OutputVariableType] = {}
        self.all_dimensions_sizes: dict[str, int] = {}

        self._set_var_info_config()
        self._read_dataset(file_path)
        self._set_mission_and_short_name()
        self.cf_config = self._set_cf_config()
        self._extract_variables()

    @abstractmethod
    def _read_dataset(self, file_path: str):
        """This method parses a file at the specified location using
        functionality specific to the type of input (e.g. a `.dmr` file).

        """

    @abstractmethod
    def _extract_variables(self):
        """Iterate through all variables in the retrieved dataset. For each
        variable create an instance of a `Variable` (using the relevant
        child class), and assign it to either the `metadata_variables`
        or the `variable_with_coordinates` dictionary accordingly.

        """

    def _assign_variable(self, variable_object):
        """Save the `Variable` instance in the dictionary containing all
        variables. Additionally, the set of references for all variables is
        updated.

        """
        self.references.update(variable_object.get_references())
        self.variables[variable_object.full_name_path] = variable_object

    def _set_var_info_config(self):
        """Read the VarInfo configuration JSON file, containing locations to
        search for the collection short_name attribute, and the mapping
        from short_name to satellite mission.

        """
        if self.config_file is not None and not exists(self.config_file):
            raise MissingConfigurationFileError(self.config_file)
        elif self.config_file is not None and self.config_file.endswith('.json'):
            with open(self.config_file, 'r', encoding='utf-8') as file_handler:
                self.var_info_config = json.load(file_handler)
        elif self.config_file is not None:
            raise InvalidConfigFileFormatError(self.config_file)
        else:
            self.var_info_config = {}

    def _set_cf_config(self) -> CFConfig:
        """Instantiate a CFConfig object, to contain any rules for exclusions,
        required fields and augmentations to CF attributes that are not
        contained within a granule from the specified collection.

        """
        return CFConfig(self.mission, self.short_name, self.config_file)

    def _set_mission_and_short_name(self):
        """Check a series of potential locations for the collection short name
        of the granule. Once that is determined, match that short name to its
        associated mission.

        """
        if self.short_name is None:
            self._set_short_name()

        if self.short_name is not None:
            self.mission = next(
                (
                    name
                    for pattern, name in self.var_info_config.get('Mission', {}).items()
                    if re.match(pattern, self.short_name) is not None
                ),
                None,
            )

    @abstractmethod
    def _set_short_name(self):
        """Iterate through the locations in the data granule representation to
        find the first value entry for the collections short name in the granule
        metadata.

        """

    def get_variable(self, variable_path: str) -> OutputVariableType | None:
        """Retrieve a variable specified by an absolute path. First check the
        variables with coordinates, before checking those without. If there
        are no matching variables, a value of `None` is returned.

        """
        return self.variables.get(variable_path)

    def get_all_variables(self) -> set[str]:
        """Retrieve a set of names for all variables in the granule."""
        return set(self.variables.keys())

    def get_variables_with_coordinates(self) -> dict[str, OutputVariableType]:
        """Return only variables with a `coordinates` metadata attribute.
        This list excludes any variables listed as an excluded science
        variable in the configuration file supplied to the object.

        """
        exclusion_pattern = re.compile(
            '|'.join(self.cf_config.excluded_science_variables)
        )

        return {
            variable_path: variable
            for variable_path, variable in self.variables.items()
            if variable.references.get('coordinates') is not None
            and not self.variable_is_excluded(variable, exclusion_pattern)
        }

    def _is_spatial_temporal_dimension(self, dimension_path: str) -> bool:
        """A helper method simplifying the list comprehension in
        `is_science_variable`.
        """
        dimension = self.get_variable(dimension_path)
        return dimension is not None and (
            dimension.is_geographic()
            or dimension.is_temporal()
            or dimension.is_projection_x_or_y()
        )

    def is_science_variable(self, variable: OutputVariableType) -> bool:
        """Determine if a variable is a science variable.
        A science variable is classified as a variable that is NOT
        a spatial temporal dimension variable. But contains
        geographic, temporal, and or projected spatial dimensions, or
        a coordinate or grid mapping reference attribute.

        """
        if any(
            self._is_spatial_temporal_dimension(dimension)
            for dimension in variable.dimensions
            if dimension != variable.full_name_path
            and not variable.full_name_path.endswith('_bnds')
        ):
            return True

        if (
            variable.references.get('coordinates') is not None
            or variable.references.get('grid_mapping') is not None
        ):
            return True

        return False

    def get_science_variables(self) -> set[str]:
        """Retrieve a set of names for all variables that have coordinate
        references, that are not themselves used as dimensions, coordinates
        or ancillary date for another variable.

        """
        exclusions_pattern = re.compile(
            '|'.join(self.cf_config.excluded_science_variables)
        )

        filtered_with_coordinates = {
            variable_path
            for variable_path, variable in self.variables.items()
            if variable_path is not None
            and self.is_science_variable(variable)
            and not self.variable_is_excluded(variable_path, exclusions_pattern)
        }

        return filtered_with_coordinates - self.references

    def get_metadata_variables(self) -> set[str]:
        """Retrieve set of names for all variables that do no have
        coordinates references, that are not themselves used as dimensions,
        coordinates, ancillary data for another variable, or are
        science variables.

        Additionally, any excluded science variables, that are contained
        in the variables class attribute should be considered a metadata
        variable.

        """
        exclusions_pattern = re.compile(
            '|'.join(self.cf_config.excluded_science_variables)
        )

        non_coordinate_variables = {
            variable_path
            for variable_path, variable in self.variables.items()
            if variable_path is not None
            and (
                not self.variable_is_excluded(variable_path, exclusions_pattern)
                and not self.is_science_variable(variable)
                and not variable.full_name_path.endswith('_bnds')
            )
        }

        return non_coordinate_variables - self.references

    @staticmethod
    def variable_is_excluded(
        variable_name: str, exclusions_pattern: re.Pattern
    ) -> bool:
        """Ensure the variable name does not match any collection specific
        exclusion rules.

        """
        if exclusions_pattern.pattern != '':
            exclude_variable = exclusions_pattern.match(variable_name) is not None
        else:
            exclude_variable = False

        return exclude_variable

    def get_required_variables(self, requested_variables: set[str]) -> set[str]:
        """Retrieve requested variables and recursively search for all
        associated dimension and coordinate variables. The returned set
        should be the union of the science variables, coordinates and
        dimensions.

        The requested variables are also augmented to include required
        variables for the collection, as indicated by the CFConfig class
        instance, and any references within those variables.

        """
        if self.cf_config.required_variables:
            cf_required_pattern = re.compile(
                '|'.join(self.cf_config.required_variables)
            )

            cf_required_variables = {
                variable
                for variable in self.get_all_variables()
                if variable is not None and re.match(cf_required_pattern, variable)
            }
        else:
            cf_required_variables = set()

        requested_variables.update(cf_required_variables)
        required_variables: set[str] = set()

        while len(requested_variables) > 0:
            variable_name = requested_variables.pop()
            required_variables.add(variable_name)

            variable = self.get_variable(variable_name)

            if variable is not None:
                # Add variable. Enqueue references not already present in
                # required set. (Also checking that they are real variables,
                # and not non-variable dimensions)
                variable_references = {
                    reference_variable
                    for reference_variable in variable.get_references()
                    if self.get_variable(reference_variable) is not None
                }
                requested_variables.update(
                    variable_references.difference(required_variables)
                )

        return self.exclude_fake_dimensions(required_variables)

    def get_required_dimensions(self, variables: set[str]) -> set[str]:
        """Return a single set of all variables that are used as dimensions
        for any of the listed variables.

        """
        return set(
            dimension
            for variable in variables
            for dimension in getattr(self.get_variable(variable), 'dimensions', [])
            if self.get_variable(dimension) is not None
        )

    def get_missing_variable_attributes(self, variable_name: str) -> dict[str, Any]:
        """Return a dictionary of all attributes for a variable that is not present
        in the granule file (e.g. grid_mapping variable in collections that are not
        fully CF compliant). The metadata attributes and the overrides for the
        variables would need to be in the configuration file.

        """
        return self.cf_config.get_metadata_overrides(variable_name)

    def get_references_for_attribute(
        self, list_of_variables: list[str], reference_attribute_name: str
    ) -> set[str]:
        """Return a single set of all references in a specific metadata attribute
        for a list of variables (e.g. bounds, coordinates, cf attributes). The full
        list of supported metadata attributes can be found in
        varinfo.utilities::CF_REFERENCE_ATTRIBUTES

        Iterate through all requested variables and extract a list of
        references for the metadata attribute. This will produce a list of lists,
        which should be flattened into a single list and then combined into a set
        to remove duplicates.

        """
        reference_set = [
            self.get_variable(variable).references.get(reference_attribute_name)
            for variable in list_of_variables
            if self.get_variable(variable).references.get(reference_attribute_name)
            is not None
        ]
        return set(
            variable_reference
            for variable_references in reference_set
            for variable_reference in variable_references
        )

    def get_spatial_dimensions(self, variables: set[str]) -> set[str]:
        """Return a single set of all variables that are both used as
        dimensions for any of the input variables, and that are horizontal
        spatial dimensions (either geographic or projected).

        """
        return set().union(
            self.get_geographic_spatial_dimensions(variables),
            self.get_projected_spatial_dimensions(variables),
        )

    def get_geographic_spatial_dimensions(self, variables: set[str]) -> set[str]:
        """Return a single set of all the variables that are both used as
        dimensions for any of the input variables, and that are geographic
        in nature (as determined by the `units` metadata attribute).

        Not all variables have dimensions, which necessitates a check on
        their existence before determining the dimension is geographic.

        """
        return set(
            dimension
            for dimension in self.get_required_dimensions(variables)
            if self.get_variable(dimension).is_geographic()
        )

    def get_projected_spatial_dimensions(self, variables: set[str]) -> set[str]:
        """Return a single set of all the variables that are both used as
        dimensions for any of the input variables, and that are projected
        in nature (as determined by the `standard_name` metadata
        attribute).

        """
        return set(
            dimension
            for dimension in self.get_required_dimensions(variables)
            if self.get_variable(dimension).is_projection_x_or_y()
        )

    def get_temporal_dimensions(self, variables: set[str]) -> set[str]:
        """Return a single set of all variables that are both used as
        dimensions for any of the input variables, and that are temporal
        in nature (as determined by the `units` metadata attribute).

        Not all variables have dimensions, which necessitates a check on
        their existence before determining the dimension is temporal.

        """
        return set(
            dimension
            for dimension in self.get_required_dimensions(variables)
            if self.get_variable(dimension).is_temporal()
        )

    def get_variables_with_dimensions(self, dimensions: set[str]) -> set[str]:
        """Return a single set of all variables that include all the supplied
        dimensions as a subset of their own dimensions.

        """
        return set(
            variable
            for variable in self.get_all_variables()
            if dimensions.issubset(set(self.get_variable(variable).dimensions))
        )

    def group_variables_by_dimensions(self) -> DimensionsGroupType:
        """Retrieve a dictionary that groups all variables in a file by the
        dimensions for their arrays. Example output for M2I3NPASM:

        ```
        {
            ('/time', '/lev', '/lat', '/lon'): {'/EPV', '/H', ...},
            ('/time', '/lat', '/lon'): {'/PHIS', '/PS', '/SLP'},
            ('/lev', ): {'/lev', },
            ('/lat', ): {'/lat', },
            ('/lon', ): {'/lon', },
            ('/time', ): {'/time', },
        }
        ```

        """
        grouped_variables = {}

        for variable_name in self.get_all_variables():
            variable = self.get_variable(variable_name)
            variable_dimensions = tuple(variable.dimensions)

            if variable_dimensions in grouped_variables:
                grouped_variables[variable_dimensions].add(variable_name)
            else:
                grouped_variables[variable_dimensions] = {
                    variable_name,
                }

        return grouped_variables

    def group_variables_by_horizontal_dimensions(self) -> DimensionsGroupType:
        """Retrieve a dictionary that groups all variables by shared
        horizontal spatial dimensions (e.g., (lon, lat) or (x, y)),
        regardless of other dimensions. This will, for example, group
        variables with dimensions (time, lat, lon) with variables only
        having dimensions (lat, lon). Note, though, the ordering is
        considered, so variables with dimensions (lat, lon) will not be
        grouped with variables having dimensions (lon, lat).

        """
        grid_groups = self.group_variables_by_dimensions()

        horizontal_groups = {}

        for grid_dimensions, variables in grid_groups.items():
            horizontal_dimensions = tuple(
                dimension
                for dimension in grid_dimensions
                if (
                    self.get_variable(dimension) is not None
                    and (
                        self.get_variable(dimension).is_geographic()
                        or self.get_variable(dimension).is_projection_x_or_y()
                    )
                )
            )

            if horizontal_dimensions in horizontal_groups:
                horizontal_groups[horizontal_dimensions].update(variables)
            else:
                horizontal_groups[horizontal_dimensions] = variables

        return horizontal_groups

    @staticmethod
    def exclude_fake_dimensions(variable_set: set[str]) -> set[str]:
        """An OPeNDAP `.dmr` can contain fake dimensions, used to supplement
        missing information for a granule. These cannot be retrieved when
        requesting a subset from an OPeNDAP server, and must be removed
        from the list of required variables.

        """
        fakedim_pattern = re.compile(r'.*/FakeDim\d+')

        return {
            variable for variable in variable_set if not fakedim_pattern.match(variable)
        }


class VarInfoFromDmr(VarInfoBase):
    """A child class that inherits from `VarInfoBase` and implements functions
    to retrieve a dataset from a `.dmr` file, and the extract variables
    from the resulting XML tree.

    """

    def _read_dataset(self, file_path: str):
        """Extract the XML tree and namespace from an OPeNDAP `.dmr` file."""
        with open(file_path, 'r', encoding='utf-8') as file_handler:
            dmr_content = file_handler.read()

        self.dataset = ET.fromstring(dmr_content)
        self.namespace = get_xml_namespace(self.dataset)

    def _set_short_name(self):
        """Iterate through all suggested locations for the collection short
        name, as listed in the configuration file. For each location, perform a
        search for an XML element in the DMR document for that element and, if
        found, retrieve the value of that element.

        """

        self.short_name = next(
            (
                get_full_path_xml_attribute(
                    self.dataset, short_name_path, self.namespace
                )
                for short_name_path in self.var_info_config.get(
                    'CollectionShortNamePath', []
                )
                if get_full_path_xml_attribute(
                    self.dataset, short_name_path, self.namespace
                )
                is not None
            ),
            None,
        )

    def _extract_variables(self):
        """Iterate through all children of the `.dmr` root dataset element.
        If the child matches one of the DAP4 variable types, then create an
        instance of the `VariableFromDmr` class, and assign it to either
        the `variables_with_coordinates` or the `metadata_variables`
        dictionary accordingly.

        """

        def save_variable(output, group_path, element):
            element_path = '/'.join([group_path, element.get('name')])
            variable = VariableFromDmr(
                element,
                self.cf_config,
                self.namespace,
                element_path,
                self.all_dimensions_sizes,
            )
            output[variable.full_name_path] = variable
            self._assign_variable(variable)

        self.find_all_dimensions_sizes(
            self.dataset,
            set(DAP4_TO_NUMPY_MAP.keys()),
            '/',
        )

        all_variables = {}

        self.traverse_elements(
            self.dataset,
            set(DAP4_TO_NUMPY_MAP.keys()),
            save_variable,
            all_variables,
            '/',
        )

        self._remove_non_variable_references()

    def _remove_non_variable_references(self):
        """After all references have been combined, remove those that point to
        non-existent variables. For example dimensions that are present in
        a variable to only denote array size in that dimension. This must
        be done after all variables are parsed, to ensure a reference isn't
        being made to a variable that hasn't yet been extracted.

        """
        self.references = {
            reference
            for reference in self.references
            if self.get_variable(reference) is not None
        }

    def find_all_dimensions_sizes(
        self,
        element: ET.Element,
        element_types: set[str],
        group_path: str,
    ):
        """Perform a depth first search of the `.dmr` `Dimension` element
        before parsing the variables. This ensures that any variable can
        reference a dimension defined later in the dataset. Once an element
        is found, it is then assigned to the `all_dimensions_sizes{}` dictionary.

        """
        group_path = group_path.rstrip('/')

        for child in list(element):
            # Ff it is a Dimension, assign dictionary all_dimensions_sizes{}
            # else, if it is a Group, call this function again
            element_type = child.tag.replace(self.namespace, '')

            if element_type == 'Dimension':
                if child.attrib['size'] is not None:
                    dim_name = '/'.join([group_path, child.get('name')])
                    self.all_dimensions_sizes[dim_name] = int(child.attrib['size'])
            elif element_type == 'Group':
                new_group_path = '/'.join([group_path, child.get('name')])

                self.find_all_dimensions_sizes(child, element_types, new_group_path)

    def traverse_elements(
        self,
        element: ET.Element,
        element_types: set[str],
        operation,
        output,
        group_path: str,
    ):
        """Perform a depth first search of the `.dmr` `Dataset` element.
        When a variable is located perform an operation on the supplied
        output object, using the supplied function or class.

        """
        self.groups[group_path] = GroupFromDmr(
            element,
            self.cf_config,
            namespace=self.namespace,
            full_name_path=group_path,
        )

        group_path = group_path.rstrip('/')

        for child in list(element):
            # If it is in the DAP4 list: use the function
            # else, if it is a Group, assign to dictionary and call this
            # function again
            element_type = child.tag.replace(self.namespace, '')

            if element_type in element_types:
                operation(output, group_path, child)
            elif element_type == 'Group':
                new_group_path = '/'.join([group_path, child.get('name')])

                self.traverse_elements(
                    child, element_types, operation, output, new_group_path
                )


class VarInfoFromNetCDF4(VarInfoBase):
    """A child class that inherits from `VarInfoBase` and implements functions
    to retrieve a dataset from a NetCDF-4 file, and extract the variables
    by traversing the granule structure.

    """

    def _read_dataset(self, file_path: str):
        """Set the dataset to the file path for the NetCDF-4 file. This is
        done instead of assigning a `netCDF4.Dataset` instance, so that the
        file is not still in memory after being parsed, so that other
        services can interact with the NetCDF-4 file without any conflicts.

        """
        self.dataset = file_path

    def _set_short_name(self):
        """Iterate through all suggested locations for the collection short
        name, as listed in the configuration file. For each location, perform a
        search for a metadata attribute in the NetCDF-4 file for that attribute
        and, if found, retrieve the value of that attribute.

        """

        with Dataset(self.dataset, 'r') as dataset:
            self.short_name = next(
                (
                    get_full_path_netcdf4_attribute(dataset, short_name_path)
                    for short_name_path in self.var_info_config.get(
                        'CollectionShortNamePath', []
                    )
                    if get_full_path_netcdf4_attribute(dataset, short_name_path)
                    is not None
                ),
                None,
            )

    def _extract_variables(self):
        """Traverse all groups of the NetCDF-4 file, beginning at the  root
        group.

        """
        with Dataset(self.dataset, 'r') as dataset:
            self._parse_group(dataset)

    def _parse_group(self, group: Dataset | Group):
        """If the child matches one of the DAP4 variable types, then create an
        instance of the `VariableFromNetCDF4` class, and assign it to either
        the `variables_with_coordinates` or the `metadata_variables`
        dictionary accordingly. Child groups are added to the `groups`
        dictionary under the fully resolved path to that group.

        """
        self.groups[group.path] = GroupFromNetCDF4(
            group,
            self.cf_config,
            namespace=self.namespace,
            full_name_path=group.path,
        )

        for netcdf4_variable in group.variables.values():
            variable_path = '/'.join([group.path, netcdf4_variable.name])
            variable_path = f'/{variable_path.lstrip("/")}'

            variable = VariableFromNetCDF4(
                netcdf4_variable,
                self.cf_config,
                namespace=self.namespace,
                full_name_path=variable_path,
            )

            for index, dimensions_name in enumerate(variable.dimensions):
                self.all_dimensions_sizes[dimensions_name] = variable.shape[index]

            self._assign_variable(variable)

        for child_group in group.groups.values():
            self._parse_group(child_group)
