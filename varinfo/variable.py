"""This module contains classes designed to read information from an OPeNDAP
DMR or NetCDF-4 file. These classes will group the input into science
variables, metadata, coordinates, dimensions and ancillary data sets.

"""

from __future__ import annotations

from abc import abstractmethod
from typing import Union
import re
import xml.etree.ElementTree as ET

from netCDF4 import Variable as NetCDF4Variable

from varinfo.attribute_container import (
    AttributeContainerBase,
    AttributeContainerFromDmr,
    AttributeContainerFromNetCDF4,
)
from varinfo.cf_config import CFConfig
from varinfo.utilities import CF_REFERENCE_ATTRIBUTES


InputVariableType = Union[ET.Element, NetCDF4Variable]


class VariableBase(AttributeContainerBase):
    """A class to represent a single variable contained within a granule
    representation. It will produce an object in which references are
    fully qualified, and also augmented by any overrides from the supplied
    configuration file.

    """

    def __init__(
        self,
        variable: InputVariableType,
        cf_config: CFConfig,
        namespace: str,
        full_name_path: str,
    ):
        """Extract the references contained within the appropriate
        CF-Convention attributes of the variable. These should be augmented
        by information from the `CFConfig` instance passed to the class.

        Additionally, store all metadata attributes in a dictionary.

        """
        super().__init__(variable, cf_config, namespace, full_name_path)
        self.group_path, self.name = self._extract_group_and_name()
        self.data_type = self._get_data_type(variable)
        self.references = self._get_all_cf_references()
        self.dimensions = self._extract_dimensions(variable)
        self.shape = self._get_shape(variable)

    @abstractmethod
    def _get_data_type(self, variable: InputVariableType):
        """Extract a string representation of the variable data type."""

    @abstractmethod
    def _get_shape(self, variable: InputVariableType):
        """Extract the shape of the variable array."""

    @abstractmethod
    def _get_raw_dimensions(self, variable: InputVariableType):
        """Retrieve the dimension names as they are stored within the
        variable.

        """

    def get_range(self) -> list[float] | None:
        """Retrieve the range of valid data from the variable metadata. First,
        try to parse the `valid_range` metadata attribute. If this is
        absent, check for a combination of `valid_min` and `valid_max`.

        If insufficient range information is present in the metadata, this
        method will return `None`.

        """
        valid_range = self.attributes.get('valid_range')

        if valid_range is None:
            valid_min = self.attributes.get('valid_min')
            valid_max = self.attributes.get('valid_max')

            if valid_min is not None and valid_max is not None:
                valid_range = [valid_min, valid_max]

        return valid_range

    def get_valid_min(self) -> float | None:
        """Retrieve the minimum valid value for variable data from the
        associated metadata. First try to retrieve data from the
        `valid_min` metadata attribute. If this is absent, then try to
        retrieve the same information from the `valid_range` metadata.

        If insufficient range information is present in the metadata, this
        method will return `None`.

        """
        valid_min = self.attributes.get('valid_min')

        if valid_min is None:
            valid_range = self.attributes.get('valid_range')
            if isinstance(valid_range, list) and len(valid_range) == 2:
                valid_min = valid_range[0]

        return valid_min

    def get_valid_max(self) -> float | None:
        """Retrieve the maximum valid value for variable data from the
        associated metadata. First try to retrieve data from the
        `valid_max` metadata attribute. If this is absent, then try to
        retrieve the same information from the `valid_range` metadata.

        If insufficient range information is present in the metadata, this
        method will return `None`.

        """
        valid_max = self.attributes.get('valid_max')

        if valid_max is None:
            valid_range = self.attributes.get('valid_range')
            if isinstance(valid_range, list) and len(valid_range) == 2:
                valid_max = valid_range[1]

        return valid_max

    def get_references(self) -> set[str]:
        """Combine the references extracted from the ancillary_variables,
        coordinates and dimensions data into a single set for VarInfo to
        use directly.

        The variable dimensions are cast as a set to allow combination with
        the other set attributes of the `VariableBase` class. The
        dimensions attribute is kept as a list prior to combination in the
        full set of variable references to ensure that the ordering of the
        dimensions is preserved.

        """
        return set(self.dimensions).union(*self.references.values())

    def is_geographic(self) -> bool:
        """Use heuristics to determine if the variable is a geographic
        coordinate based on its units. A latitude variable will have units
        'degrees_north' and a longitude variable with have units
        'degrees_east'.

        """
        return self.is_longitude() or self.is_latitude()

    def is_latitude(self) -> bool:
        """Determine if the variable is a latitude based on the `units`
        metadata attribute being 'degrees_north' or other similar options
        as defined in section 4.1 of the CF Conventions (v1.8).

        """
        return self.attributes.get('units') in [
            'degrees_north',
            'degree_north',
            'degrees_N',
            'degree_N',
            'degreesN',
            'degreeN',
        ]

    def is_longitude(self) -> bool:
        """Determine if the variable is a longitude based on the `units`
        metadata attribute being 'degrees_east' or other similar options
        as defined in section 4.2 of the CF Conventions (v1.8).

        """
        return self.attributes.get('units') in [
            'degrees_east',
            'degree_east',
            'degrees_E',
            'degree_E',
            'degreesE',
            'degreeE',
        ]

    def is_projection_x_or_y(self) -> bool:
        """Determine if the variable is a projected x or y horizontal spatial
        coordinate based on the `standard_name` metadata attribute being
        `projection_x_coordinate` or `projection_y_coordinate`, as defined
        by the CF Conventions (v1.9). Note, geostationary projections have
        coordinates with `standard_name` metadata attribute values of
        `projection_x_angular_coordinate` and
        `projection_y_angular_coordinate`.

        """
        return self.is_projection_x() or self.is_projection_y()

    def is_projection_x(self) -> bool:
        """Determine if the variable is a projected x spatial coordinate based
        on the `standard_name` metadata attribute being
        `projection_x_coordinate`, as defined by the CF Conventions
        (v1.9). Note, geostationary projections have coordinate with
        `standard_name` metadata attribute value of
        `projection_x_angular_coordinate`.

        """
        return self.attributes.get('standard_name') in [
            'projection_x_coordinate',
            'projection_x_angular_coordinate',
        ]

    def is_projection_y(self) -> bool:
        """Determine if the variable is a projected y spatial coordinate based
        on the `standard_name` metadata attribute being
        `projection_y_coordinate`, as defined by the CF Conventions
        (v1.9). Note, geostationary projections have coordinate with
        `standard_name` metadata attribute value of
        `projection_y_angular_coordinate`.

        """
        return self.attributes.get('standard_name') in [
            'projection_y_coordinate',
            'projection_y_angular_coordinate',
        ]

    def is_temporal(self) -> bool:
        """Determine if the variable is a time based on the `units`
        metadata attribute being 'since' or other similar options
        as defined in section 4.4 of the CF Conventions (v1.8).

        """
        return ' since ' in self.attributes.get('units', '')

    def _get_all_cf_references(self) -> dict[str, set[str]]:
        """Retrieve a dictionary containing all CF-Convention attributes
        within the variable that have references to other variables in the
        granule. These variable references will be fully qualified paths.

        """
        return {
            attribute_name: self._get_cf_references(attribute_name)
            for attribute_name in CF_REFERENCE_ATTRIBUTES
            if attribute_name in self.attributes
        }

    def _get_cf_references(self, attribute_name: str) -> set[str]:
        """Retrieve an attribute from the parsed variable metadata, correcting
        for any known artefacts (missing or incorrect references). Then
        split this string and qualify the individual references.

        """
        return self._extract_references(self.attributes.get(attribute_name))

    def _extract_references(self, attribute_string: str) -> set[str]:
        """Given a string value of an attribute, which may contain multiple
        references to dataset, split that string based on either commas,
        or spaces (or both together). Then if any reference is a relative
        path, make it absolute.

        """
        if attribute_string is not None:
            raw_references = re.split(r'\s+|,\s*', attribute_string)
            references = set(self._qualify_references(raw_references))
        else:
            references = set()

        return references

    def _extract_dimensions(self, variable: ET.Element) -> list[str]:
        """Find the dimensions for the variable in question. If there are
        overriding dimensions from the `earthdata-varinfo` configuration
        file, these are used instead of the raw dimensions from the `.dmr`. All
        references are converted to absolute paths in the granule. A set of all
        fully qualified references is returned.

        """
        dimensions_override = self.metadata_overrides.get('dimensions')

        if dimensions_override is not None:
            dimensions = re.split(r'\s+|,\s*', dimensions_override)
        else:
            dimensions = [
                dimension
                for dimension in self._get_raw_dimensions(variable)
                if dimension is not None
            ]

        return self._qualify_references(dimensions)

    def _qualify_references(self, raw_references: list[str]) -> list[str]:
        """Take a list of local references to other variables, and produce a
        list of absolute references.

        Trailing colons are removed from variable references. These might
        occur in some CF-Convention defined formats of the grid_mapping
        metadata attribute. E.g. "crs: grid_y crs: grid_x" (See section 5.6
        of CF-Conventions).

        """
        references = []

        if self.group_path is not None:
            for reference in raw_references:
                reference = reference.rstrip(':')

                if reference.startswith('../'):
                    # Reference is relative, and requires manipulation
                    absolute_path = self._construct_absolute_path(reference)
                elif reference.startswith('/'):
                    # Reference is already absolute
                    absolute_path = reference
                elif reference.startswith('./'):
                    # Reference is in the same group as this variable
                    absolute_path = self.group_path + reference[1:]
                else:
                    # Reference is in the same group as this variable
                    absolute_path = '/'.join([self.group_path, reference])

                references.append(absolute_path)

        else:
            for reference in raw_references:
                reference = reference.rstrip(':')

                if reference.startswith('/'):
                    absolute_path = reference
                else:
                    absolute_path = f'/{reference}'

                references.append(absolute_path)

        return references

    def _construct_absolute_path(self, reference: str) -> str:
        """For a relative reference to another variable (e.g. '../latitude'),
        construct an absolute path by combining the reference with the
        group path of the variable.

        """
        relative_prefix = '../'
        group_path_pieces = self.group_path.split('/')

        while reference.startswith(relative_prefix):
            reference = reference[len(relative_prefix) :]
            group_path_pieces.pop()

        absolute_path = group_path_pieces + [reference]
        return '/'.join(absolute_path)

    def _extract_group_and_name(self) -> tuple[str, str]:
        """Extract the group and base name of a variable from the full path,
        e.g. '/this/is/my/variable' should return a two-element tuple:
        ('/this/is/my', 'variable').

        """
        split_full_path = self.full_name_path.split('/')
        name = split_full_path.pop(-1)
        group_path = '/'.join(split_full_path) or None

        return group_path, name


class VariableFromDmr(VariableBase, AttributeContainerFromDmr):
    """This child class inherits from the `VariableBase` class, and implements
    the abstract methods assuming the variable source is part of an XML
    element tree.

    """

    def __init__(
        self,
        element: ET.Element,
        cf_config: CFConfig,
        namespace: str,
        full_name_path: str,
        all_dimensions_sizes: dict[str, int],
    ):
        self.all_dimensions_sizes = all_dimensions_sizes
        super().__init__(element, cf_config, namespace, full_name_path)

    def _get_data_type(self, variable: ET.Element) -> str:
        """Extract a string representation of the variable data type."""
        return variable.tag.lstrip(self.namespace).lower()

    def _get_shape(self, variable: ET.Element) -> tuple[int]:
        """Extract the shape of the variable data array. First explore
        XML for - DIM child elements with a size
        attribute - true for HDF5 files and anonymous dimensions
        (note no name). If found (with or without names), use them. If
        not found, use all_dimensions_sizes dictionary with matching dimension
        names to define the variable shape. Note the all_dimensions_sizes
        dictionary is filled when parsing xml for variables, capturing
        dimensions names and sizes for dimension entries - as found in
        NetCDF files with named dimensions.
        """

        # Retrieve the shape from the dimension size in the
        # <Dim size=xx/> element.
        shape = [
            int(dim_size.attrib['size'])
            for dim_size in variable.findall(f'.//{self.namespace}Dim[@size]')
        ]

        # Retrieve the shape from dimension size in the
        # <Dimension size=xx/> element
        if len(shape) != len(self.dimensions):
            for dim_name in self.dimensions:
                if dim_name in self.all_dimensions_sizes:
                    index = self.dimensions.index(dim_name)
                    shape.insert(index, self.all_dimensions_sizes[dim_name])

        return shape

    def _get_raw_dimensions(self, variable: ET.Element) -> list[str]:
        """Extract the raw dimension names from a <Dim /> XML element."""
        return [
            dimension.get('name')
            for dimension in variable.findall(f'{self.namespace}Dim')
        ]


class VariableFromNetCDF4(VariableBase, AttributeContainerFromNetCDF4):
    """This child class inherits from the `VariableBase` class, and implements
    the abstract methods assuming the variable source is part of a NetCDF-4
    file.

    """

    def _get_data_type(self, variable: NetCDF4Variable) -> str:
        """Extract a string representation of the variable data type.

        * First try `variable.datatype.name`. This can be `None` for some
          string type variables.
        * If `variable.datatype.name` is `None`, try `variable.datatype.dtype`.

        """
        return variable.datatype.name or variable.datatype.dtype.__name__

    def _get_shape(self, variable: NetCDF4Variable) -> tuple[int]:
        """Extract the shape of the variable data array."""
        return variable.shape

    def _get_raw_dimensions(self, variable: NetCDF4Variable) -> list[str]:
        """Retrieve the dimension names as they are stored within the
        variable.

        """
        return list(variable.dimensions)
