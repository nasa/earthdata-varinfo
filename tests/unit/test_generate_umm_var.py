from shutil import copy
from unittest import TestCase
from unittest.mock import ANY, patch

from varinfo.generate_umm_var import generate_collection_umm_var, is_variable_concept_id


class TestGenerateUmmVar(TestCase):
    """A class for testing the module containing simplified functionality to
    generate UMM-Var records, including publication, with a fewer function
    calls for the end-user.

    """

    @classmethod
    def setUpClass(cls):
        """Define information that can be reused by each test."""
        cls.bearer_token_header = 'Bearer this-is-a-token'
        cls.collection_concept_id = 'C1234567890-PROV'
        cls.launchpad_token_header = 'launchpad-token'
        cls.netcdf4_basename = 'f16_ssmis_20210426v7.nc'
        cls.netcdf4_url = f'https://example.com/{cls.netcdf4_basename}'
        cls.example_dmr_basename = 'M2I3NPASM_example.dmr'
        cls.opendap_url = (
            f'https://fake.opendap.earthdata.nasa.gov/{cls.example_dmr_basename}'
        )
        cls.opendap_xml_download_url = (
            f'https://fake.opendap.earthdata.nasa.gov/{cls.example_dmr_basename}.xml'
        )
        cls.query_granule_return = [
            {
                'links': [
                    {
                        'href': cls.netcdf4_url,
                        'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#',
                    }
                ]
            }
        ]
        cls.query_granule_return_opendap = [
            {
                'links': [
                    {
                        'rel': 'http://esipfed.org/ns/fedsearch/1.1/service#',
                        'title': 'OPeNDAP request URL (GET DATA : OPENDAP DATA)',
                        'hreflang': 'en-US',
                        'href': cls.opendap_url,
                    }
                ]
            }
        ]
        cls.rssmif16d_variables = [
            'atmosphere_cloud_liquid_water_content',
            'atmosphere_water_vapor_content',
            'latitude',
            'longitude',
            'rainfall_rate',
            'sst_dtime',
            'time',
            'wind_speed',
        ]

    @staticmethod
    def download_granule_side_effect(granule_link, auth_header, out_directory):
        """A helper method that will copy the test file to the temporary
        directory being used for a specific test.

        Static methods do not have access to class attributes, so the test
        file path is defined in this method as well as setUpClass.

        """
        netcdf4_file_path = 'tests/unit/data/f16_ssmis_20210426v7.nc'
        return copy(netcdf4_file_path, out_directory)

    @staticmethod
    def download_dmr_side_effect(granule_link, auth_header, out_directory):
        """A helper method that will copy a test dmr file to the temporary
        directory being used for a specific test.

        Static methods do not have access to class attributes, so the test
        file path is defined in this method as well as setUpClass.

        """
        dmr_file_path = 'tests/unit/data/M2I3NPASM_example.dmr'
        return copy(dmr_file_path, out_directory)

    @patch('varinfo.umm_var.publish_umm_var')
    @patch('varinfo.cmr_search.GranuleQuery')
    @patch('varinfo.generate_umm_var.download_granule')
    def test_generate_collection_umm_var_no_publication(
        self, mock_download_granule, mock_granule_query, mock_publish_umm_var
    ):
        """A request with all the necessary information should succeed.
        This test is moderately end-to-end, but mocks the full
        download_granule function for simplicity. That function is tested
        in detail in test_cmr_search.py.

        """
        mock_granule_query.return_value.get.return_value = self.query_granule_return

        # Add side effect that will copy test file to the temporary directory,
        # simulating a download.
        mock_download_granule.side_effect = self.download_granule_side_effect

        # Run the test:
        generated_umm_var = generate_collection_umm_var(
            self.collection_concept_id, self.bearer_token_header
        )

        # Ensure the granule query used expected query parameters
        mock_granule_query.return_value.parameters.assert_called_once_with(
            downloadable=True,
            sort_key='-start_date',
            concept_id=self.collection_concept_id,
        )

        # Ensure the call to download the granule had correct parameters
        mock_download_granule.assert_called_once_with(
            self.netcdf4_url, self.bearer_token_header, out_directory=ANY
        )

        # Ensure the output looks as expected - full record comparison is
        # not performed to avoid test brittleness.
        expected_variables = set(self.rssmif16d_variables)

        actual_variables = set([record['Name'] for record in generated_umm_var])

        self.assertSetEqual(actual_variables, expected_variables)

        # Check that no attempt was made to publish a UMM-Var record to CMR:
        mock_publish_umm_var.assert_not_called()

    @patch('varinfo.umm_var.publish_umm_var')
    @patch('varinfo.cmr_search.GranuleQuery')
    @patch('varinfo.generate_umm_var.download_granule')
    def test_generate_collection_umm_var_with_publication(
        self, mock_download_granule, mock_granule_query, mock_publish_umm_var
    ):
        """A request with all the necessary information should succeed."""
        expected_concept_ids = [
            'V0000000001-PROV',
            'V0000000002-PROV',
            'V0000000003-PROV',
            'V0000000004-PROV',
            'V0000000005-PROV',
            'V0000000006-PROV',
            'V0000000007-PROV',
            'V0000000008-PROV',
        ]
        mock_granule_query.return_value.get.return_value = self.query_granule_return

        # Add side effect that will copy test file to the temporary directory,
        # simulating a download.
        mock_download_granule.side_effect = self.download_granule_side_effect

        mock_publish_umm_var.side_effect = expected_concept_ids

        # Run the test:
        published_umm_var = generate_collection_umm_var(
            self.collection_concept_id, self.bearer_token_header, publish=True
        )

        # Ensure the granule query used expected query parameters
        mock_granule_query.return_value.parameters.assert_called_once_with(
            downloadable=True,
            sort_key='-start_date',
            concept_id=self.collection_concept_id,
        )

        # Ensure the call to download the granule had correct parameters
        mock_download_granule.assert_called_once_with(
            self.netcdf4_url, self.bearer_token_header, out_directory=ANY
        )

        # Ensure the output looks as expected
        self.assertSetEqual(set(published_umm_var), set(expected_concept_ids))

    @patch('varinfo.umm_var.publish_umm_var')
    @patch('varinfo.generate_umm_var.get_dmr_xml_url')
    @patch('varinfo.cmr_search.GranuleQuery')
    @patch('varinfo.generate_umm_var.download_granule')
    def test_generate_collection_umm_var_dmr(
        self,
        mock_download_granule,
        mock_granule_query,
        mock_get_dmr_xml_url,
        mock_publish_umm_var,
    ):
        """Test an end-to-end request for a DMR file."""
        mock_granule_query.return_value.get.return_value = (
            self.query_granule_return_opendap
        )

        # Add side effect that will copy test file to the temporary directory,
        # simulating a download.
        mock_download_granule.side_effect = self.download_dmr_side_effect

        # Set return value for get_dmr_xml_url
        mock_get_dmr_xml_url.return_value = self.opendap_xml_download_url

        # Check call arguments when use_dmr=True
        generate_collection_umm_var(
            self.collection_concept_id,
            self.bearer_token_header,
            use_dmr=True,
        )

        mock_get_dmr_xml_url.assert_called_once_with(self.query_granule_return_opendap)
        # Ensure the granule query used expected query parameters
        mock_granule_query.return_value.parameters.assert_called_once_with(
            downloadable=True,
            sort_key='-start_date',
            concept_id=self.collection_concept_id,
        )

        # Ensure the call to download the granule had correct parameters
        mock_download_granule.assert_called_once_with(
            self.opendap_xml_download_url, self.bearer_token_header, out_directory=ANY
        )

        # Check that no attempt was made to publish a UMM-Var record to CMR:
        mock_publish_umm_var.assert_not_called()

    @patch('varinfo.umm_var.publish_umm_var')
    @patch('varinfo.cmr_search.GranuleQuery')
    @patch('varinfo.generate_umm_var.download_granule')
    def test_error_from_search_is_raised(
        self, mock_download_granule, mock_granule_query, mock_publish_umm_var
    ):
        """Ensure an error raised during search is propagated out to the
        user.

        """
        # Simulate no results found to trigger an IndexError
        mock_granule_query.return_value.get.return_value = []

        # Run the test, ensuring expected exception is raised:
        with self.assertRaises(IndexError) as context_manager:
            generate_collection_umm_var(
                self.collection_concept_id, self.bearer_token_header
            )

        self.assertEqual(
            str(context_manager.exception),
            'No granules were found with selected parameters ' 'and user permissions',
        )

        # Ensure the granule query used expected query parameters
        mock_granule_query.return_value.parameters.assert_called_once_with(
            downloadable=True,
            sort_key='-start_date',
            concept_id=self.collection_concept_id,
        )

        # Ensure no attempt was made to download the granule after failure:
        mock_download_granule.assert_not_called()

        # Ensure no attempt was made to publish UMM-Var after the failure:
        mock_publish_umm_var.assert_not_called()

    @patch('varinfo.umm_var.publish_umm_var')
    @patch('varinfo.cmr_search.GranuleQuery')
    @patch('varinfo.generate_umm_var.download_granule')
    def test_publishing_errors(
        self, mock_download_granule, mock_granule_query, mock_publish_umm_var
    ):
        """Show the output list from publication will correctly handle a
        response with an error.

        """
        error_message = 'Invalid JSON'
        concept_ids = [
            'V0000000001-PROV',
            'V0000000002-PROV',
            'V0000000003-PROV',
            'V0000000004-PROV',
            'V0000000005-PROV',
            'V0000000006-PROV',
            'V0000000007-PROV',
        ]

        # Create combined list of concept IDs and one error:
        # ['V0000000001-PROV', 'V0000000002-PROV', ..., 'Invalid JSON']
        concept_ids_and_error = concept_ids + [error_message]

        mock_granule_query.return_value.get.return_value = self.query_granule_return

        # Add side effect that will copy test file to the temporary directory,
        # simulating a download.
        mock_download_granule.side_effect = self.download_granule_side_effect

        mock_publish_umm_var.side_effect = concept_ids_and_error

        # Run the test:
        published_umm_var = generate_collection_umm_var(
            self.collection_concept_id, self.bearer_token_header, publish=True
        )

        # Ensure the granule query used expected query parameters
        mock_granule_query.return_value.parameters.assert_called_once_with(
            downloadable=True,
            sort_key='-start_date',
            concept_id=self.collection_concept_id,
        )

        # Ensure the call to download the granule had correct parameters
        mock_download_granule.assert_called_once_with(
            self.netcdf4_url, self.bearer_token_header, out_directory=ANY
        )

        # Ensure the output looks as expected
        # First check all the expected concept IDs are present:
        self.assertEqual(
            set(concept_ids), set(published_umm_var).intersection(concept_ids)
        )

        # Next check the error matches the expected format,
        # e.g.: '/variable_name: Error Message'.
        # This is done in pieces, in case dictionary ordering means the
        # variable associated with the error varies between test runs.

        # First get any element that isn't a UMM-Var concept ID:
        error_messages = set(published_umm_var).difference(concept_ids)

        # Check there is only one error, as expected
        self.assertEqual(len(error_messages), 1)

        # Split the error string: ['/variable_name', 'Error message']
        error_pieces = list(error_messages)[0].split(': ')

        # Confirm the second half of the error string was the error from CMR
        self.assertEqual(error_pieces[1], error_message)

        # Check the first half of the error string (without the leading slash)
        # is one of the known variables in RSSMIF16D
        self.assertIn(error_pieces[0].lstrip('/'), self.rssmif16d_variables)

    def test_is_variable_concept_id(self):
        """Check the function can recognise correctly formatted variable
        concept ID.

        """
        with self.subTest('Provider with no slash returns True'):
            self.assertTrue(is_variable_concept_id('V1234567890-PROV'))

        with self.subTest('Provider with slash returns True'):
            self.assertTrue(is_variable_concept_id('V1234567890-PROV_IDER'))

        with self.subTest('Collection returns False'):
            self.assertFalse(is_variable_concept_id('C1234567890-PROV'))

        with self.subTest('Granule returns False'):
            self.assertFalse(is_variable_concept_id('G1234567890-PROV'))

        with self.subTest('Random string returns False'):
            self.assertFalse(is_variable_concept_id('Random string'))

    @patch('varinfo.generate_umm_var.VarInfoFromNetCDF4')
    @patch('varinfo.cmr_search.GranuleQuery')
    @patch('varinfo.generate_umm_var.download_granule')
    def test_generate_collection_umm_var_config_file(
        self, mock_download_granule, mock_granule_query, mock_varinfo_from_netcdf4
    ):
        """This test just verifies the config file that is passed in to the
        generate_collection_umm_var method is picked up by VarInfoFromNetCDF4 that
        would use it. The granule query and download methods are mocked to make it
        simpler test.
        """
        mock_granule_query.return_value.get.return_value = self.query_granule_return

        # Add side effect that will copy test file to the temporary directory,
        # simulating a download.
        mock_download_granule.side_effect = self.download_granule_side_effect

        # Run the test:
        generate_collection_umm_var(
            self.collection_concept_id,
            self.bearer_token_header,
            config_file='tests/unit/data/test_config.json',
        )

        # Ensure the the config file provided is passed to the VarInfo class
        mock_varinfo_from_netcdf4.assert_called_once_with(
            ANY,
            config_file='tests/unit/data/test_config.json',
        )

    @patch('varinfo.generate_umm_var.VarInfoFromNetCDF4')
    @patch('varinfo.cmr_search.GranuleQuery')
    @patch('varinfo.generate_umm_var.download_granule')
    def test_generate_collection_umm_var_with_no_config_file(
        self, mock_download_granule, mock_granule_query, mock_varinfo_from_netcdf4
    ):
        """This test just verifies if the config file is 'None' in the
        generate_collection_umm_var method, the VarInfoFromNetCDF4 would still succeed
        and continue with a 'None' value for that parameter. The granule query and
        download methods are mocked to make it simpler test.
        """
        mock_granule_query.return_value.get.return_value = self.query_granule_return

        # Add side effect that will copy test file to the temporary directory,
        # simulating a download.
        mock_download_granule.side_effect = self.download_granule_side_effect

        # Run the test:
        generate_collection_umm_var(
            self.collection_concept_id, self.bearer_token_header
        )

        # Ensure that the VarInfoFromNetCDF4 invocation includes NONE for the config file
        mock_varinfo_from_netcdf4.assert_called_with(ANY, config_file=None)
