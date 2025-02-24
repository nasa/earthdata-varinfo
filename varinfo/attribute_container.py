"""This module contains classes designed to capture information regarding
metadata attributes as read from either an OPeNDAP DMR or a NetCDF-4 file.
These classes are inherited by both representations of groups and of
variables.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Union
import xml.etree.ElementTree as ET

from netCDF4 import Group as NetCDF4Group
from netCDF4 import Variable as NetCDF4Variable

from varinfo.cf_config import CFConfig
from varinfo.utilities import get_xml_attribute


InputContainerType = Union[ET.Element, NetCDF4Group, NetCDF4Variable]


class AttributeContainerBase(ABC):
    """A class to represent objects that have metadata attributes, such as
    groups or variables within a NetCDF-4 file or OPeNDAP DMR.

    """

    def __init__(
        self,
        container: InputContainerType,
        cf_config: CFConfig,
        namespace: str,
        full_name_path: str,
    ):
        """Extract metadata attributes, including any overrides defined in the
        supplied `CFConfig` instance.

        """
        self.namespace = namespace
        self.full_name_path = full_name_path
        self.metadata_overrides = cf_config.get_metadata_overrides(self.full_name_path)
        self.attributes = self._get_attributes(container)
        self._add_additional_attributes()

    @abstractmethod
    def _get_attributes(self, container: InputContainerType) -> dict[str, Any]:
        """Extract all attributes for the container. The contents of the output
        dictionary will be as stored in the granule metadata, with any
        applicable overrides from `CFConfig`.

        """

    @abstractmethod
    def _get_attribute(self, container: InputContainerType, attribute_name: str) -> Any:
        """Extract an attribute value from the source granule metadata. Any
        applicable overrides from `CFConfig` will be applied before returning
        the attribute value.

        """

    def get_attribute_value(
        self, attribute_name: str, default_value: Any | None = None
    ) -> Any:
        """A convenience function for the end-user to retrieve the value of a
        specified attribute, or use an optional default value if that
        attribute is not present in the container metadata. If no default
        value is supplied, requesting the value of an absent attribute will
        return `None`.

        """
        return self.attributes.get(attribute_name, default_value)

    def _add_additional_attributes(self) -> None:
        """Check the `CFConfig` instance for any metadata attributes that are
        listed, but not included in the original granule metadata. These should
        be added to the variable metadata attributes.

        """
        self._add_missing_attributes(self.metadata_overrides)

    def _add_missing_attributes(self, extra_attributes: dict) -> None:
        """Iterate through a dictionary of attributes from the `CFConfig`
        instance matching this container. If there are any attributes listed
        that are not already present in the `self.attributes` dictionary,
        then add them to with the value from the configuration file.

        """
        for attribute_name, attribute_value in extra_attributes.items():
            if attribute_name not in self.attributes:
                self.attributes[attribute_name] = attribute_value

    def _get_configured_attribute(
        self, attribute_name: str, raw_attribute_value: Any
    ) -> Any:
        """Check the `CFConfig` instance associated with the container for any
        metadata attribute overrides that should be applied to the attribute
        value.

        """
        return self.metadata_overrides.get(attribute_name, raw_attribute_value)


class AttributeContainerFromDmr(AttributeContainerBase):
    """This child class inherits from the `AttributeContainerBase` class and
    implements the abstract methods assuming the container source is part of an
    XML element tree.

    """

    def _get_attributes(self, container: ET.Element) -> dict[str, Any]:
        """Locate all child Attribute elements of the container and extract
        their associated values.

        """
        return {
            attribute.get('name'): self._get_attribute(container, attribute.get('name'))
            for attribute in container.findall(f'{self.namespace}Attribute')
            if attribute.get('name') is not None
        }

    def _get_attribute(self, container: ET.Element, attribute_name: str) -> Any:
        """Extract the value of an XML Attribute element, casting it to the
        appropriate type, applying any necessary metadata overrides.

        """
        raw_value = get_xml_attribute(container, attribute_name, self.namespace)
        return self._get_configured_attribute(attribute_name, raw_value)


class AttributeContainerFromNetCDF4(AttributeContainerBase):
    """This child class inherits from the `AttributeContainerBase` class and
    implements the abstract metadata assuming the container source is part of a
    NetCDF-4 file.

    """

    def _get_attributes(
        self, container: NetCDF4Group | NetCDF4Variable
    ) -> dict[str, Any]:
        """Identify all variable attributes and save them to a dictionary."""
        return {
            attribute_name: self._get_attribute(container, attribute_name)
            for attribute_name in container.ncattrs()
        }

    def _get_attribute(
        self, container: NetCDF4Group | NetCDF4Variable, attribute_name: str
    ) -> Any:
        """Extract the value of the metadata attribute, applying any necessary
        override from the `CFConfig` instance.

        """
        raw_value = container.__dict__.get(attribute_name)
        return self._get_configured_attribute(attribute_name, raw_value)
