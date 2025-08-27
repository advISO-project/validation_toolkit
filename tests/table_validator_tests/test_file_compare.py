import pytest
import json
import filecmp
import difflib
from importlib_resources import files

from validation_toolkit.TableValidator.file_io import File_IO
from validation_toolkit.TableValidator.file_compare import FileCompare
from validation_toolkit.TableValidator.custom_exceptions import SchemaMismatchWarning, ValueMismatchWarning

from pathlib import Path

TEST_DATA_DIR = files('tests.table_validator_tests.test_data')

@pytest.fixture
def test_init():

    test_object = FileCompare(left_file=TEST_DATA_DIR / "ref_toy_csv.csv", right_file=TEST_DATA_DIR / "ref_toy_json.json", l_sample_id_key="sample_id")
    assert test_object, "A test file_compare object should be built"
    return test_object

@pytest.fixture
def test_init_config():

    test_object_no_config = FileCompare(left_file=TEST_DATA_DIR / "data_map_test_left.csv", right_file=TEST_DATA_DIR / "data_map_test_right.csv", l_sample_id_key="col_left_1", r_sample_id_key="col_right_1")
    test_object_w_config = FileCompare(left_file=TEST_DATA_DIR / "data_map_test_left.csv", right_file=TEST_DATA_DIR / "data_map_test_right.csv", l_sample_id_key="col_left_1", r_sample_id_key="col_right_1", config=TEST_DATA_DIR / "sample_config.yaml")

    return test_object_no_config, test_object_w_config

def test_create_schema(test_init):
    test_object = test_init
    test_object._create_schema()

    assert len(test_object.sample_schema.keys()) == 4, "There should be 4 fields in the schema"
    assert test_object.sample_schema["sample_id"]["valid_types"] == test_object.sample_schema["field1"]["valid_types"] == set([str])

def test_confirm_schema(test_init):
    test_object = test_init
    test_object._create_schema()
    test_object._confirm_schema()
    assert test_object.schema_errors["sample_1"] == {"sample_id": "SchemaMatch", "field1": "SchemaMatch", "field2": "SchemaMatch", "field3": "SchemaMatch"}

def test_compare_values(test_init):
    test_object = test_init
    test_object.compare_values()
    assert test_object.value_mismatches["sample_1"] == {"sample_id": "ValueMatch", "field1": "ValueMatch", "field2": "ValueMatch", "field3": "ValueMatch"}

def test_confirm_schema_fail():
    test_object_lenient = FileCompare(left_file=TEST_DATA_DIR / "ref_toy_csv.csv", right_file=TEST_DATA_DIR / "query_toy_json_schemamismatch.json", l_sample_id_key="sample_id")
    test_object_lenient._create_schema()

    ## there should be a schema check failure here
    with pytest.warns(SchemaMismatchWarning):
        test_object_lenient._confirm_schema()

    ## using strict mode, this warning should now be an exception -- pytest.raises needed to catch it
    test_object_strict = FileCompare(left_file=TEST_DATA_DIR / "ref_toy_csv.csv", right_file=TEST_DATA_DIR / "query_toy_json_schemamismatch.json", l_sample_id_key="sample_id", strict=True)
    test_object_strict._create_schema()
    with pytest.raises(SchemaMismatchWarning) as error_info:
        test_object_strict._confirm_schema()

def test_compare_values_fail():

    test_object = FileCompare(left_file=TEST_DATA_DIR / "ref_toy_csv.csv", right_file=TEST_DATA_DIR / "query_toy_json_valmismatch.json", l_sample_id_key="sample_id")
    test_object._create_schema()
    test_object._confirm_schema()
    ## there should be a value mismatch flagged here
    with pytest.warns(ValueMismatchWarning, match="Mismatch in value of field field2 for sample sample_4. Expected: 42 Found: fourtwo"):
        test_object.compare_values()

def test_compare_values_specific_fields():

    test_object = FileCompare(left_file=TEST_DATA_DIR / "ref_toy_csv.csv", right_file=TEST_DATA_DIR / "query_toy_json_valmismatch.json", l_sample_id_key="sample_id")
    test_object._create_schema()
    test_object._confirm_schema()
    ## even though this test uses a value_mismatch test fixture
    ## there should be no warnings as the field in question is not included in the provided list of field names to check
    test_object.compare_values(field_names=["sample_id", "field1", "field3"])
    assert test_object.value_mismatches["sample_1"] == {"sample_id": "ValueMatch", "field1": "ValueMatch", "field2": "Field not checked", "field3": "ValueMatch"}

def test_compare_fail_with_no_config(test_init_config):
    test_object_no_config, _ = test_init_config
    test_object_no_config._create_schema()
    with pytest.raises(Exception):
        test_object_no_config._confirm_schema()

def test_compare_values_config(test_init_config):
    _, test_object_w_config = test_init_config

    test_object_w_config.compare_values()
    assert test_object_w_config.schema_errors["sample1"] == {"sample_id": "sample1", "col_right_1": "SchemaMatch", "col_right_2": "SchemaMatch", "col_right_3": "SchemaMatch"}
    assert test_object_w_config.value_mismatches["sample1"] == {"sample_id": "sample1", "col_right_1": "ValueMatch", "col_right_2": "ValueMatch", "col_right_3": "ValueMatch"}

def _files_are_identical(file1, file2):
    return filecmp.cmp(f1=file1, f2=file2, shallow=False)

def test_output_files_json(test_init, tmp_path):
    test_object = test_init

    test_object.compare_values()
    metadata = {
                "prog": "TableValidator_pytest",
                "prog_version": "0.0.1dev",
                }

    test_object.write_results(metadata=metadata, output=f"{tmp_path}/test_out_all_match.json", out_format="json")
    with open(f"{tmp_path}/test_out_all_match.json", "r") as created_json:
        out_data = json.load(created_json)
    created_json.close()
    expected_keys = ["metadata", "schema_check", "value_check"]
    assert sorted(list(out_data.keys())) == expected_keys, f"Did not find all expected keys in output JSON. Expected: f{expected_keys}, found: {sorted(list(out_data.keys()))}"

def test_output_files_csv(test_init, tmp_path):
    test_object = test_init

    test_object.compare_values()
    metadata = {
                "prog": "TableValidator_pytest",
                "prog_version": "0.0.1dev",
                }
    test_object.write_results(metadata=metadata, output=f"{tmp_path}/test_out_all_match.csv", out_format="csv")

    ## using fixture files here as it is useful to check this in a static way
    ## fixtures can also be used as a reference for expected FileCompare output when using CSV as output format
    assert _files_are_identical(file1= TEST_DATA_DIR / "pytest_out_all_match_schema_check.csv", file2=f"{tmp_path}/test_out_all_match_schema_check.csv"), "Files should be identical!"
    assert _files_are_identical(file1= TEST_DATA_DIR / "pytest_out_all_match_value_check.csv", file2=f"{tmp_path}/test_out_all_match_value_check.csv"), "Files should be identical!"

def test_output_files_schema_mismatch():

    test_object_lenient = FileCompare(left_file=TEST_DATA_DIR / "ref_toy_csv.csv", right_file=TEST_DATA_DIR / "query_toy_json_schemamismatch.json", l_sample_id_key="sample_id")
    test_object_lenient._create_schema()

    ## there should be a schema check failure here
    with pytest.warns(SchemaMismatchWarning):
        test_object_lenient._confirm_schema()

    assert test_object_lenient.schema_errors["sample_4"]["field2"] in ["SchemaMismatch. Expected {<class 'int'>, <class 'str'>} Found <class 'bool'>", "SchemaMismatch. Expected {<class 'str'>, <class 'int'>} Found <class 'bool'>"]

def test_output_files_value_mismatch(tmp_path):

    test_object = FileCompare(left_file=TEST_DATA_DIR / "ref_toy_csv.csv", right_file=TEST_DATA_DIR / "query_toy_json_valmismatch.json", l_sample_id_key="sample_id")

    ## there should be a value mismatch flagged here
    with pytest.warns(ValueMismatchWarning, match="Mismatch in value of field field2 for sample sample_4. Expected: 42 Found: fourtwo"):
        test_object.compare_values()

    metadata = {
                "prog": "TableValidator_pytest",
                "prog_version": "0.0.1dev",
                }
    test_object.write_results(metadata=metadata, output=f"{tmp_path}/test_out_value_mismatch.json", out_format="json")

    with open(f"{tmp_path}/test_out_value_mismatch.json", "r") as created_json:
        out_data = json.load(created_json)
    created_json.close()
    assert out_data["value_check"]["sample_4"]["field2"] == "ValueMismatch. Expected 42 Found fourtwo"
    assert out_data["metadata"] == metadata

def test_composite_ids_compare_with_config():
    comp_object = FileCompare(left_file= TEST_DATA_DIR / "composite_ids_test_left.csv", right_file=TEST_DATA_DIR / "composite_ids_test_right.csv", l_sample_id_key="sample_id,uid", r_sample_id_key="sample_id,uuid", config=TEST_DATA_DIR / "composite_ids_test_config.yaml")
    with pytest.warns(ValueMismatchWarning):
        comp_object.compare_values()

    assert comp_object.value_mismatches["sample_1.1"]["data_col_alt_2"] == "ValueMismatch. Expected 1 Found 0", "Failed to find expected value mismatch!"
    assert comp_object.value_mismatches["sample_2.3"]["data_col_alt_2"] == "ValueMismatch. Expected 1 Found 0", "Failed to find expected value mismatch!"
    assert comp_object.value_mismatches["sample_3.3"]["data_col_1"] == "ValueMismatch. Expected False Found True", "Failed to find expected value mismatch!"
