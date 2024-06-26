""" This module contains classes that represent groups (e.g., containers of
    variables within a NetCDF-4 file). A group has metadata attributes and
    child variables.

"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from netCDF4 import Group as NetCDF4Group

from varinfo.attribute_container import (
    AttributeContainerFromDmr,
    AttributeContainerFromNetCDF4,
)
from varinfo.cf_config import CFConfig


class GroupFromDmr(AttributeContainerFromDmr):
    """Blah"""

    def __init__(
        self,
        group: ET.Element,
        cf_config: CFConfig,
        namespace: str,
        full_name_path: str,
    ):
        """ """
        super().__init__(group, cf_config, namespace, full_name_path)
        self.variables = self._parse_variables()

    def _parse_variables(self):
        """ """
        return {}


class GroupFromNetCDF4(AttributeContainerFromNetCDF4):
    """Blah"""

    def __init__(
        self,
        group: NetCDF4Group,
        cf_config: CFConfig,
        namespace: str,
        full_name_path: str,
    ):
        super().__init__(group, cf_config, namespace, full_name_path)
        self.variables = self._parse_variables(group)

    def _parse_variables(self, group: NetCDF4Group):
        """ """
        return {}
