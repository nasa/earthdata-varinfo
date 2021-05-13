""" This module contains a class designed to read information from a `.dmr`
    file. This should group the input into science variables, metadata,
    coordinates, dimensions and ancillary data sets.

"""
from abc import ABC, abstractmethod
from typing import List, Optional, Set, Tuple, Union
import re
import xml.etree.ElementTree as ET

from varinfo.cf_config import CFConfig
from varinfo.utilities import get_xml_attribute


InputVariableType = Union[ET.Element]


class VariableBase(ABC):
    """ A class to represent a single variable contained within a granule
        representation. It will produce an object in which references are
        fully qualified, and also augmented by any overrides or supplements
        from the supplied configuration file.

    """
    def __init__(self, variable: InputVariableType, cf_config: CFConfig,
                 namespace: str, full_name_path: str):
        """ Extract the references contained within the variable's coordinates,
            ancillary_variables or dimensions. These should be augmented by
            information from the CFConfig instance passed to the class.

            Additionally, store other information required for UMM-Var record
            production in an attributes dictionary. (These attributes may not
            be an exhaustive list).

        """
        self.namespace = namespace
        self.full_name_path = full_name_path

        self.cf_config = cf_config.get_cf_attributes(self.full_name_path)
        self.group_path, self.name = self._extract_group_and_name()

        self.ancillary_variables = self._get_cf_references(variable,
                                                           'ancillary_variables')
        self.coordinates = self._get_cf_references(variable, 'coordinates')
        self.subset_control_variables = self._get_cf_references(
            variable, 'subset_control_variables'
        )
        self.dimensions = self._extract_dimensions(variable)

        self.attributes = {
            'acquisition_source_name': self._get_attribute(variable, 'source'),
            'data_type': self._get_data_type(variable),
            'definition': self._get_attribute(variable, 'description'),
            'fill_value': self._get_attribute(variable, '_FillValue'),
            'long_name': self._get_attribute(variable, 'long_name'),
            'offset': self._get_attribute(variable, 'offset', 0),
            'scale': self._get_attribute(variable, 'scale', 1),
            'units': self._get_attribute(variable, 'units'),
            'valid_max': self._get_attribute(variable, 'valid_max'),
            'valid_min': self._get_attribute(variable, 'valid_min')
        }

    @abstractmethod
    def _get_data_type(self, variable: InputVariableType):
        """ Extract a string representation of the variable data type. """

    @abstractmethod
    def _get_raw_dimensions(self, variable: InputVariableType):
        """ Retrieve the dimension names as they are stored within the
            variable.

        """

    @abstractmethod
    def _get_attribute(self, variable: InputVariableType, attribute_name: str,
                       default_value: Optional = None) -> Optional:
        """ Extract the attribute value, falling back to a default value if the
            attribute is absent.

        """

    def get_references(self) -> Set[str]:
        """ Combine the references extracted from the ancillary_variables,
            coordinates and dimensions data into a single set for VarInfo to
            use directly.

            The variable dimensions are cast as a set to allow combination with
            the other set attributes of the `VariableBase` class. The
            dimensions attribute is kept as a list prior to combination in the
            full set of variable references to ensure that the ordering of the
            dimensions is preserved.

        """
        return self.ancillary_variables.union(self.coordinates,
                                              set(self.dimensions),
                                              self.subset_control_variables)

    def _get_cf_references(self, variable: InputVariableType,
                           attribute_name: str) -> Set[str]:
        """ Obtain the string value of a metadata attribute, which should have
            already been corrected for any known artefacts (missing or
            incorrect references). Then split this string and qualify the
            individual references.

        """
        attribute_string = self._get_cf_attribute(variable, attribute_name)
        return self._extract_references(attribute_string)

    def _get_cf_attribute(self, variable: InputVariableType,
                          attribute_name: str) -> str:
        """ Given the name of a CF-convention attribute, extract the string
            value from the variable metadata. Then check the output from the
            CF configuration file, to see if this value should be replaced, or
            supplemented with more data.

        """
        cf_overrides = self.cf_config['cf_overrides'].get(attribute_name)
        cf_supplements = self.cf_config['cf_supplements'].get(attribute_name)

        if cf_overrides is not None:
            attribute_value = cf_overrides
        else:
            attribute_value = self._get_attribute(variable, attribute_name)
        if cf_supplements is not None and attribute_value is not None:
            attribute_value += f', {cf_supplements}'
        elif cf_supplements is not None:
            attribute_value = cf_supplements

        return attribute_value

    def _extract_references(self, attribute_string: str) -> Set[str]:
        """ Given a string value of an attribute, which may contain multiple
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

    def _extract_dimensions(self, variable: ET.Element) -> List[str]:
        """ Find the dimensions for the variable in question. If there are
            overriding or supplemental dimensions from the CF configuration
            file, these are used instead of, or in addition to, the raw
            dimensions from the `.dmr`. All references are converted to
            absolute paths in the granule. A set of all fully qualified
            references is returned.

        """
        overrides = self.cf_config['cf_overrides'].get('dimensions')
        supplements = self.cf_config['cf_supplements'].get('dimensions')

        if overrides is not None:
            dimensions = re.split(r'\s+|,\s*', overrides)
        else:
            dimensions = [dimension
                          for dimension in self._get_raw_dimensions(variable)
                          if dimension is not None]

        if supplements is not None:
            dimensions += re.split(r'\s+|,\s*', supplements)

        return self._qualify_references(dimensions)

    def _qualify_references(self, raw_references: List[str]) -> List[str]:
        """ Take a list of local references to other variables, and produce a
            list of absolute references.

        """
        references = []

        if self.group_path is not None:
            for reference in raw_references:
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
                if reference.startswith('/'):
                    absolute_path = reference
                else:
                    absolute_path = f'/{reference}'

                references.append(absolute_path)

        return references

    def _construct_absolute_path(self, reference: str) -> str:
        """ For a relative reference to another variable (e.g. '../latitude'),
            construct an absolute path by combining the reference with the
            group path of the variable.

        """
        relative_prefix = '../'
        group_path_pieces = self.group_path.split('/')

        while reference.startswith(relative_prefix):
            reference = reference[len(relative_prefix):]
            group_path_pieces.pop()

        absolute_path = group_path_pieces + [reference]
        return '/'.join(absolute_path)

    def _extract_group_and_name(self) -> Tuple[str]:
        """ Extract the group and base name of a variable from the full path,
            e.g. '/this/is/my/variable' should return a two-element tuple:
            ('/this/is/my', 'variable').

        """
        split_full_path = self.full_name_path.split('/')
        name = split_full_path.pop(-1)
        group_path = '/'.join(split_full_path) or None

        return group_path, name


class VariableFromDmr(VariableBase):
    """ This child class inherits from the `VariableBase` class, and implements
        the abstract methods assuming the variable source is part of an XML
        element tree.

    """
    def _get_data_type(self, variable: ET.Element) -> str:
        """ Extract a string representation of the variable data type. """
        return variable.tag.lstrip(self.namespace).lower()

    def _get_attribute(self, variable: ET.Element, attribute_name: str,
                       default_value: Optional = None) -> Optional:
        """ Use a utility function to retrieve an attribute from a Variable
            XML element in the `.dmr`. If the attribute is absent, use the
            provided default value.

        """
        return get_xml_attribute(variable, attribute_name, self.namespace,
                                 default_value)

    def _get_raw_dimensions(self, variable: ET.Element) -> List[str]:
        """ Extract the raw dimension names from a <Dim /> XML element. """
        return [dimension.get('name')
                for dimension
                in variable.findall(f'{self.namespace}Dim')]
