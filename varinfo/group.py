""" This module contains classes that represent groups (e.g., containers of
    variables within a NetCDF-4 file). A group has metadata attributes and
    child variables.

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
    """Blah"""

    def __init__(
        self,
        group: InputGroupType,
        cf_config: CFConfig,
        namespace: str,
        full_name_path: str,
    ):
        """ """
        super().__init__(group, cf_config, namespace, full_name_path)
        self.variables = self._parse_variables(group)

    @abstractmethod
    def _parse_variables(self, group: InputGroupType) -> set[str]:
        """Blah"""


class GroupFromDmr(GroupBase, AttributeContainerFromDmr):
    """Blah"""

    def _parse_variables(self, group: ET.Element) -> set[str]:
        """Currently returns full paths of all variables."""
        return {
            '/'.join([self.full_name_path, child.get('name', '')])
            for child in group
            if child.tag.replace(self.namespace, '') in DAP4_TO_NUMPY_MAP
        }


class GroupFromNetCDF4(GroupBase, AttributeContainerFromNetCDF4):
    """Blah"""

    def _parse_variables(self, group: NetCDF4Group) -> set[str]:
        """Currently returns full paths of variables."""
        return {
            '/'.join([self.full_name_path, variable]) for variable in group.variables
        }
