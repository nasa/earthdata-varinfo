"""This module contains classes that represent groups (e.g., containers of
variables within a NetCDF-4 file or OPeNDAP DMR). A group has metadata
attributes and child variables.

"""

from __future__ import annotations

from abc import abstractmethod
from typing import Union
import xml.etree.ElementTree as ET

from netCDF4 import Group as NetCDF4Group

from varinfo.attribute_container import (
    AttributeContainerBase,
    AttributeContainerFromDmr,
    AttributeContainerFromNetCDF4,
)
from varinfo.cf_config import CFConfig
from varinfo.utilities import DAP4_TO_NUMPY_MAP


InputGroupType = Union[ET.Element, NetCDF4Group]


class GroupBase(AttributeContainerBase):
    """A class to represent a single group contained within a granule
    representation. It will produce an object with attributes and a set of
    fully qualified variables within the group.

    """

    def __init__(
        self,
        group: InputGroupType,
        cf_config: CFConfig,
        namespace: str,
        full_name_path: str,
    ):
        """First extract all metadata attributes on the group, accounting for
        overrides defined in the CFConfig file. Then parse the paths of all
        child variables in the group.

        """
        super().__init__(group, cf_config, namespace, full_name_path)
        self.variables = self._parse_variables(group)

    @abstractmethod
    def _parse_variables(self, group: InputGroupType) -> set[str]:
        """An abstract method to retrieve a set of all variables that are
        direct children of the group.

        """


class GroupFromDmr(GroupBase, AttributeContainerFromDmr):
    """This child class inherits from the `GroupBase` class and implements the
    abstract methods assuming the group source is a Dataset Metadata Response
    (DMR) XML document retrieved from OPeNDAP.

    """

    def _parse_variables(self, group: ET.Element) -> set[str]:
        """Returns full paths of all child variables in the group."""
        return {
            '/'.join([self.full_name_path.rstrip('/'), child.get('name', '')])
            for child in group
            if child.tag.replace(self.namespace, '') in DAP4_TO_NUMPY_MAP
        }


class GroupFromNetCDF4(GroupBase, AttributeContainerFromNetCDF4):
    """This child class inherits from the `GroupBase` class and implements the
    abstract methods assuming the group source is a NetCDF-4 file.

    """

    def _parse_variables(self, group: NetCDF4Group) -> set[str]:
        """Returns full paths of all child variables in the group."""
        return {
            '/'.join([self.full_name_path.rstrip('/'), variable])
            for variable in group.variables
        }
