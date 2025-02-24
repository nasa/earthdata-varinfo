"""This module contains lower-level functionality that can be abstracted into
functions. Primarily this improves readability of the source code, and
allows finer-grained unit testing of each smaller part of functionality.

For CF-Convention reference attributes see the following sections of the
Conventions:

- Section 3.4: ancillary_variables
- Sections 4 and 5: coordinates
- Section 5.6: grid_mapping
- Section 7.1: bounds
- Section 7.2: cell_measure
- Section 7.5: geometry, interior_ring, node_coordinates, node_count,
               nodes, part_node_count

susbset_control_variables is a new attribute introduced by the Data
Services team, primarily for use with references for segmented data.

"""

from __future__ import annotations

from typing import Any
from xml.etree.ElementTree import Element
import functools
import re

from netCDF4 import Dataset as NetCDF4Dataset
import numpy as np

from varinfo.exceptions import DmrNamespaceError


CF_REFERENCE_ATTRIBUTES = [
    'ancillary_variables',
    'bounds',
    'cell_measures',
    'coordinates',
    'geometry',
    'grid_mapping',
    'interior_ring',
    'node_coordinates',
    'node_count',
    'nodes',
    'part_node_count',
    'subset_control_variables',
]

DAP4_TO_NUMPY_MAP = {
    'Char': np.uint8,
    'Byte': np.uint8,
    'Int8': np.int8,
    'UInt8': np.uint8,
    'Int16': np.int16,
    'UInt16': np.uint16,
    'Int32': np.int32,
    'UInt32': np.uint32,
    'Int64': np.int64,
    'UInt64': np.uint64,
    'Float32': np.float32,
    'Float64': np.float64,
    'String': str,
    'URL': str,
}


def recursive_get(input_dictionary: dict, keys: list[str]):
    """Extract a value from an arbitrarily nested dictionary."""
    try:
        nested_value = functools.reduce(dict.get, keys, input_dictionary)
    except TypeError:
        # This catches when there is a missing intermediate key
        nested_value = None

    return nested_value


def split_attribute_path(full_path: str) -> list[str]:
    """Take the full path to a metadata attribute and return the list of
    keys that locate that attribute within the global attributes.
    This function can account for the input path to having, or omitting, a
    leading '/' character.

    """
    return full_path.lstrip('/').split('/')


def get_xml_namespace(root_element: Element) -> str:
    """Given the root element of an XML document, extract the associated
    namespace. This allows for the full qualification of child elements.
    The root element of a dmr file is expected to be a Dataset tag.

    """
    match = re.match('(.+)Dataset', root_element.tag)

    if match:
        xml_namespace = match.groups()[0]
    else:
        raise DmrNamespaceError(root_element.tag)

    return xml_namespace


def get_xml_attribute(
    variable: Element,
    attribute_name: str,
    namespace: str,
    default_value: Any | None = None,
) -> Any | None:
    """Extract the value of an XML Attribute tag from a `.dmr`. First search
    the supplied variable element for a fully qualified Attribute child
    element, with a name property matching the requested attribute name. If
    there is no matching tag, return the `default_value`, which can be
    user-defined, or default to `None`. If present, the returned value is
    cast as the type indicated by the Attribute tag's `type` property.

    Attributes with multiple Value children will return a list of all those
    children, cast as the indicated type. Attributes that are containers of
    nested attributes will return a dictionary structure.

    """
    attribute_element = variable.find(
        f'{namespace}Attribute' f'[@name="{attribute_name}"]'
    )

    if attribute_element is not None:
        value_type = attribute_element.get('type', 'String')

        if value_type != 'Container':
            attribute_value = get_xml_attribute_value(
                attribute_element,
                namespace,
                value_type,
                default_value,
            )
        else:
            attribute_value = get_xml_container_attribute(attribute_element, namespace)

    else:
        attribute_value = default_value

    return attribute_value


def get_xml_attribute_value(
    attribute_element: Element,
    namespace: str,
    value_type: str,
    default_value: Any | None = None,
) -> Any | None:
    """Extract the value (single or list) for an XML attribute. If there are
    no attributes matching the required name, then return the supplied default
    value. If no default value is supplied, the default used is `None`.

    """
    numpy_type = DAP4_TO_NUMPY_MAP.get(value_type, str)

    value_elements = attribute_element.findall(f'{namespace}Value')

    if len(value_elements) > 1:
        attribute_value = [
            numpy_type(value_element.text) for value_element in value_elements
        ]
    elif len(value_elements) == 1:
        attribute_value = numpy_type(value_elements[0].text)
    else:
        attribute_value = default_value

    return attribute_value


def get_xml_container_attribute(
    container_element: Element, namespace: str
) -> dict[str, Any | None]:
    """Extract a dictionary of attribute values when an attribute is a container
    for further attributes. This function is recursive, and so nested containers
    will be treated in the same way.

    """
    attribute_dictionary = {}

    for child in list(container_element):
        child_name = child.get('name')
        child_type = child.get('type', 'String')

        if child_type != 'Container':
            attribute_dictionary[child_name] = get_xml_attribute_value(
                child,
                namespace,
                child_type,
            )
        else:
            attribute_dictionary[child_name] = get_xml_container_attribute(
                child,
                namespace,
            )

    return attribute_dictionary


def get_full_path_xml_attribute(
    dmr_document: Element,
    attribute_path: str,
    namespace: str,
) -> Any | None:
    """Helper function that retrieves the value of an XML attribute, given the
    full path to that attribute. If the XML attribute is not present, then
    `None` is returned.

    """
    attribute_element = dmr_document

    try:
        for path_part in attribute_path.lstrip('/').split('/')[:-1]:
            attribute_element = attribute_element.find(f'.//*[@name="{path_part}"]')

        attribute_value = get_xml_attribute(
            attribute_element,
            attribute_path.split('/')[-1],
            namespace,
        )
    except AttributeError:
        attribute_value = None

    return attribute_value


def get_full_path_netcdf4_attribute(
    netcdf_dataset: NetCDF4Dataset,
    attribute_path: str,
) -> Any | None:
    """Helper function that retrieves the value of a metadata attribute from a
    NetCDF-4 file, given the full path to that attribute. If the metadata
    attribute is not present, then `None` is returned.

    """
    container_path = '/'.join(attribute_path.split('/')[:-1])
    attribute_name = attribute_path.split('/')[-1]

    try:
        if container_path != '':
            attribute_container = netcdf_dataset[container_path]
        else:
            attribute_container = netcdf_dataset

        attribute_value = attribute_container.getncattr(attribute_name)
    except (KeyError, IndexError, AttributeError):
        attribute_value = None

    return attribute_value
