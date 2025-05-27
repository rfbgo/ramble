# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest
import unittest
from unittest.mock import patch, MagicMock
import os
import json
import sys
from datetime import datetime

import ramble.config
import ramble.pipeline
import ramble.workspace
from ramble.main import RambleCommand
from ramble.uploader import ConfigError, upload_results, BigQueryUploader, format_data, _prepare_data, Experiment
from ramble.util.logger import logger, logging # Import logging for assertLogs
from ramble.schema.generic_sql_schema import GENERIC_SCHEMA, DataTypes, get_jsonschema_for_table

# Attempt to import jsonschema for tests that rely on it
try:
    import jsonschema
    jsonschema_available = True
except ImportError:
    jsonschema = None # Will be mocked in specific tests if its absence is the scenario
    jsonschema_available = False


pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

_empty_results = {"experiments": []}

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "upload_uri,upload_type,results,expected_err_msg",
    [
        (None, None, _empty_results, "No upload type"),
        (None, "UnknownUploader", _empty_results, "Upload type UnknownUploader is not valid"),
        (None, "BigQuery", _empty_results, "No upload URI"),
        ("fake-zeppelin", "PrintOnly", [], "Does not contain valid data to upload"),
    ],
)
def test_upload_results_errs(upload_uri, upload_type, results, expected_err_msg):
    with ramble.config.override("config:upload", {"uri": upload_uri, "type": upload_type}):
        with pytest.raises(ConfigError, match=expected_err_msg):
            upload_results(results)


@pytest.mark.maybeslow
def test_data_preparation(request, mock_applications):
    ws_name = request.node.name
    global_args = ["-w", ws_name]
    app_name = "zlib"
    wl_name = "ensure_installed"

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage", "experiments", app_name, "-w", wl_name, "-p", "spack",
            global_args=global_args,
        )
        workspace("concretize", global_args=global_args)
        workspace("setup", global_args=global_args)

        filters = ramble.filters.Filters()
        ap = ramble.pipeline.AnalyzePipeline(ws, filters)
        ap._prepare()
        ap._execute()

        # format_data now expects Experiment's timestamp to be a datetime object or ISO string
        # The ws.results should be fine as is, format_data internally uses datetime.now()
        formatted_data = ramble.uploader.format_data(ws.results)
        uri = "not_used_in_test"
        exp_table_id, exps_to_insert, fom_table_id, foms_to_insert = ramble.uploader._prepare_data(
            formatted_data, uri
        )
        # exps_to_insert now contains dicts based on GENERIC_SCHEMA
        if exps_to_insert:
            assert "application_name" in exps_to_insert[0]
            assert isinstance(exps_to_insert[0]["id"], int)
            assert isinstance(exps_to_insert[0]["timestamp"], str) # ISO format

# --- Test Data for Schema Validation ---
# This raw data is processed by format_data, which creates Experiment objects.
# Experiment.__init__ now takes the raw 'data' dict and a timestamp (datetime or ISO string).
# Experiment.to_json() then creates a dict based on GENERIC_SCHEMA.

# For VALID_RAW_DATA_FOR_FORMAT, 'data' field within 'experiments' list is the raw exp data.
VALID_RAW_DATA_FOR_FORMAT = {
    "experiments": [{
        "name": "test_exp_valid",
        "RAMBLE_VARIABLES": {"workspace_name": "test_ws"},
        "application_name": "test_app", "workload_name": "test_wl",
        "n_nodes": 1, "processes_per_node": 1, "n_ranks": 1, "n_threads": 1,
        "RAMBLE_STATUS": "SUCCESS", 
        # 'data' here is the original experiment data passed to Experiment constructor
        "data": {"some_key": "some_value", "application_name": "test_app", "workload_name": "test_wl", 
                 "n_nodes": 1, "processes_per_node": 1, "n_ranks": 1, "n_threads": 1, "RAMBLE_STATUS": "SUCCESS",
                 "RAMBLE_VARIABLES": {"workspace_name": "test_ws"}},
        "CONTEXTS": [{"name": "ctx1", "foms": [{"name": "fom1", "value": "42", "units": "N", "origin": "orig", "origin_type": "type"}]}]
    }],
    "workspace_hash": "valid_hash"
}

# For INVALID_RAW_DATA_FOR_FORMAT_MISSING_FOM_NAME, a FOM is missing its 'name'.
# The 'data' field for the experiment needs to be self-contained as above.
INVALID_RAW_DATA_FOR_FORMAT_MISSING_FOM_NAME = {
    "experiments": [{
        "name": "test_exp_invalid_fom",
        "RAMBLE_VARIABLES": {"workspace_name": "test_ws_inv"},
        "application_name": "test_app_inv", "workload_name": "test_wl_inv",
        "n_nodes": 1, "processes_per_node": 1, "n_ranks": 1, "n_threads": 1,
        "RAMBLE_STATUS": "SUCCESS",
        "data": {"another_key": "another_value", "application_name": "test_app_inv", "workload_name": "test_wl_inv",
                 "n_nodes": 1, "processes_per_node": 1, "n_ranks": 1, "n_threads": 1, "RAMBLE_STATUS": "SUCCESS",
                 "RAMBLE_VARIABLES": {"workspace_name": "test_ws_inv"}},
        "CONTEXTS": [{"name": "ctx_inv", "foms": [{"value": "100", "units": "m", "origin": "orig_inv", "origin_type": "type_inv"}]}] # FOM is missing 'name'
    }],
    "workspace_hash": "invalid_hash_fom_name"
}

VALID_RAW_DATA_FOR_MANUAL_CORRUPTION = {
    "experiments": [{
        "name": "test_exp_to_corrupt",
        "RAMBLE_VARIABLES": {"workspace_name": "test_ws_corrupt"},
        "application_name": "test_app_corrupt", "workload_name": "test_wl_corrupt",
        "n_nodes": 1, "processes_per_node": 1, "n_ranks": 1, "n_threads": 1,
        "RAMBLE_STATUS": "SUCCESS",
        "data": {"corrupt_key": "corrupt_value", "application_name": "test_app_corrupt", "workload_name": "test_wl_corrupt",
                 "n_nodes": 1, "processes_per_node": 1, "n_ranks": 1, "n_threads": 1, "RAMBLE_STATUS": "SUCCESS",
                 "RAMBLE_VARIABLES": {"workspace_name": "test_ws_corrupt"}},
        "CONTEXTS": [{"name": "ctx_corrupt", "foms": [{"name": "fom_corrupt", "value": "200", "units": "Pa", "origin": "orig_c", "origin_type": "type_c"}]}]
    }],
    "workspace_hash": "corrupt_hash"
}


class TestBigQueryUploaderSchemaValidation(unittest.TestCase):

    def setUp(self):
        self.uploader = BigQueryUploader()
        self.test_uri = "test_project.test_dataset"
        patcher = patch('ramble.uploader.get_user', return_value="test_user")
        self.mock_get_user = patcher.start()
        self.addCleanup(patcher.stop)

        # format_data calls Experiment.__init__ which now takes a datetime or ISO string.
        # It uses datetime.now() internally, so this should be fine.
        with patch('ramble.config.get', side_effect=lambda key, default=None: default if key != "config:upload:push_failed" else False):
            self.formatted_valid_results = format_data(VALID_RAW_DATA_FOR_FORMAT)
            self.formatted_invalid_fom_results = format_data(INVALID_RAW_DATA_FOR_FORMAT_MISSING_FOM_NAME)
            self.formatted_results_for_manual_corruption = format_data(VALID_RAW_DATA_FOR_MANUAL_CORRUPTION)

    def _get_prepared_invalid_experiment_data(self):
        # This helper creates data that would be invalid for the 'experiments' table schema
        # by removing a required field ('name') after _prepare_data has run.
        _, exps_to_insert, _, _ = _prepare_data(self.formatted_results_for_manual_corruption, self.test_uri)
        if exps_to_insert:
            if 'name' in exps_to_insert[0]:
                del exps_to_insert[0]['name']
        return exps_to_insert

    # --- Tests for _get_validation_schemas ---
    def test_get_validation_schemas_success(self):
        """Test that _get_validation_schemas returns correct jsonschemas."""
        schemas = self.uploader._get_validation_schemas()
        self.assertIsNotNone(schemas)
        self.assertIn("experiments", schemas)
        self.assertIn("foms", schemas)
        self.assertIsNotNone(schemas["experiments"])
        self.assertIsNotNone(schemas["foms"])
        self.assertEqual(schemas["experiments"]["type"], "object")
        self.assertEqual(schemas["foms"]["type"], "object")
        self.assertIn("name", schemas["experiments"]["required"])
        self.assertIn("experiment_id", schemas["foms"]["required"])

    @patch('ramble.uploader.get_jsonschema_for_table')
    def test_get_validation_schemas_generation_failure(self, mock_get_jsonschema_for_table):
        """Test behavior when get_jsonschema_for_table returns None."""
        mock_get_jsonschema_for_table.return_value = None
        with self.assertLogs(logger.name, level='ERROR') as log_cm:
            schemas = self.uploader._get_validation_schemas()
        
        self.assertIsNone(schemas["experiments"])
        self.assertIsNone(schemas["foms"])
        self.assertTrue(any("Could not generate jsonschema for 'experiments' table" in msg for msg in log_cm.output))
        self.assertTrue(any("Could not generate jsonschema for 'foms' table" in msg for msg in log_cm.output))

    # --- Tests for Schema Validation in insert_data ---
    @patch('ramble.uploader.BigQueryUploader.chunked_upload', return_value=[])
    @patch('ramble.config.get')
    def test_validation_valid_data_schema_enabled(self, mock_config_get, mock_chunked_upload):
        if not jsonschema_available:
            self.skipTest("jsonschema library not available")

        def config_side_effect(key, default=None):
            return True if key == "config:upload:validate_schema" else default
        mock_config_get.side_effect = config_side_effect

        with self.assertLogs(logger.name, level='INFO') as log_cm:
            self.uploader.insert_data(self.test_uri, self.formatted_valid_results)
        
        log_output = "\n".join(log_cm.output)
        self.assertIn("Validating experiments against schema...", log_output)
        self.assertIn("Validating FOMs against schema...", log_output)
        self.assertNotIn("validation failed", log_output.lower())
        self.assertNotIn("jsonschema library not found", log_output)

    @patch('ramble.uploader.BigQueryUploader.chunked_upload', return_value=[])
    @patch('ramble.config.get')
    def test_validation_invalid_experiment_data_schema_enabled(self, mock_config_get, mock_chunked_upload):
        if not jsonschema_available:
            self.skipTest("jsonschema library not available")

        def config_side_effect(key, default=None):
            return True if key == "config:upload:validate_schema" else default
        mock_config_get.side_effect = config_side_effect

        prepared_invalid_exps = self._get_prepared_invalid_experiment_data() # 'name' is removed
        _, _, _, valid_foms_to_insert = _prepare_data(self.formatted_valid_results, self.test_uri)

        # Temporarily mock jsonschema.validate to raise error for this specific case
        original_validate = jsonschema.validate
        def mock_validate(instance, schema):
            if schema.get("properties", {}).get("application_name"): # Exp schema
                if 'name' not in instance: # The specific invalidity
                    raise jsonschema.exceptions.ValidationError("'name' is a required property")
            original_validate(instance, schema) # Call original for other cases

        jsonschema.validate = mock_validate
        
        with patch('ramble.uploader._prepare_data', return_value=(
            "mock_exp_table", prepared_invalid_exps, "mock_fom_table", valid_foms_to_insert
        )):
            with self.assertLogs(logger.name, level='WARN') as log_cm:
                self.uploader.insert_data(self.test_uri, []) # results arg is less important due to mock
        
        jsonschema.validate = original_validate # Restore

        self.assertTrue(any("Experiment validation failed for N/A: 'name' is a required property" in msg for msg in log_cm.output), f"Log output: {log_cm.output}")

    @patch('ramble.uploader.BigQueryUploader.chunked_upload', return_value=[])
    @patch('ramble.config.get')
    def test_validation_invalid_fom_data_schema_enabled(self, mock_config_get, mock_chunked_upload):
        if not jsonschema_available:
            self.skipTest("jsonschema library not available")

        def config_side_effect(key, default=None):
            return True if key == "config:upload:validate_schema" else default
        mock_config_get.side_effect = config_side_effect

        # Mock jsonschema.validate for FOMs
        original_validate = jsonschema.validate
        fom_error_msg = "'name' is a required property in FOM"
        def mock_validate_fom(instance, schema):
            if schema.get("properties", {}).get("experiment_id"): # FOM schema
                if 'name' not in instance:
                    raise jsonschema.exceptions.ValidationError(fom_error_msg)
            # Don't call original_validate here to isolate FOM validation failure
        
        jsonschema.validate = mock_validate_fom

        with self.assertLogs(logger.name, level='WARN') as log_cm:
            # self.formatted_invalid_fom_results already has FOMs missing 'name'
            self.uploader.insert_data(self.test_uri, self.formatted_invalid_fom_results)
        
        jsonschema.validate = original_validate # Restore

        expected_exp_id = self.formatted_invalid_fom_results[0].id
        self.assertTrue(
            any(f"FOM validation failed for N/A (Experiment ID: {expected_exp_id}): {fom_error_msg}" in msg for msg in log_cm.output),
            f"Log output: {log_cm.output}"
        )

    @patch('ramble.uploader.BigQueryUploader.chunked_upload', return_value=[])
    @patch('ramble.config.get')
    def test_validation_schema_disabled(self, mock_config_get, mock_chunked_upload):
        def config_side_effect(key, default=None):
            return False if key == "config:upload:validate_schema" else default
        mock_config_get.side_effect = config_side_effect

        with self.assertLogs(logger.name, level='INFO') as log_cm:
            self.uploader.insert_data(self.test_uri, self.formatted_invalid_fom_results) 
        
        log_output = "\n".join(log_cm.output)
        self.assertNotIn("Validating experiments against schema...", log_output)
        self.assertNotIn("Validating FOMs against schema...", log_output)
        self.assertNotIn("validation failed", log_output.lower())

    @patch('ramble.uploader.BigQueryUploader.chunked_upload', return_value=[])
    @patch('ramble.config.get')
    @patch('ramble.uploader.jsonschema', None) # Mock jsonschema as unavailable in uploader module
    def test_validation_jsonschema_not_available_schema_enabled(self, mock_config_get, mock_chunked_upload):
        def config_side_effect(key, default=None):
            return True if key == "config:upload:validate_schema" else default
        mock_config_get.side_effect = config_side_effect

        with self.assertLogs(logger.name, level='WARN') as log_cm:
            self.uploader.insert_data(self.test_uri, self.formatted_valid_results)
        
        log_output = "\n".join(log_cm.output)
        self.assertIn("jsonschema library not found. Skipping schema validation for experiments.", log_output)
        # Depending on execution path, FOM warning might also appear if experiment schema was also missing
        # For this test, we only ensure the warning about jsonschema library appears at least once.
        self.assertTrue(any("jsonschema library not found. Skipping schema validation" in msg for msg in log_cm.output))


# --- Tests for generic_sql_schema.get_jsonschema_for_table ---
class TestGenericSchemaHelpers(unittest.TestCase):
    def test_get_jsonschema_for_experiments_basic_structure(self):
        schema = get_jsonschema_for_table('experiments')
        self.assertIsNotNone(schema)
        self.assertEqual(schema['type'], 'object')
        self.assertIn('properties', schema)
        self.assertIn('required', schema)
        self.assertTrue(len(schema['properties']) > 0)

    def test_get_jsonschema_for_experiments_id_field(self):
        schema = get_jsonschema_for_table('experiments')
        self.assertIn('id', schema['properties'])
        self.assertEqual(schema['properties']['id']['type'], 'integer')
        self.assertIn('id', schema['required']) 

    def test_get_jsonschema_for_foms_value_field(self):
        schema = get_jsonschema_for_table('foms')
        self.assertIn('value', schema['properties'])
        self.assertEqual(schema['properties']['value']['type'], 'string')
        self.assertNotIn('value', schema['required']) # value is nullable

    def test_get_jsonschema_for_foms_experiment_id_field(self):
        schema = get_jsonschema_for_table('foms')
        self.assertIn('experiment_id', schema['properties'])
        self.assertEqual(schema['properties']['experiment_id']['type'], 'integer')
        self.assertIn('experiment_id', schema['required'])

    def test_get_jsonschema_timestamp_format(self):
        exp_schema = get_jsonschema_for_table('experiments')
        self.assertIn('timestamp', exp_schema['properties'])
        self.assertEqual(exp_schema['properties']['timestamp']['type'], 'string')
        self.assertEqual(exp_schema['properties']['timestamp']['format'], 'date-time')
        self.assertIn('timestamp', exp_schema['required'])

    def test_get_jsonschema_for_unknown_table(self):
        schema = get_jsonschema_for_table('non_existent_table')
        self.assertIsNone(schema)

if __name__ == '__main__':
    unittest.main()
