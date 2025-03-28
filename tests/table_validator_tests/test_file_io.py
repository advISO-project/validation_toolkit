import pytest
from importlib_resources import files
from pathlib import Path

from validation_toolkit.TableValidator.file_io import File_IO
from validation_toolkit.TableValidator.custom_exceptions import UnsupportedFileFormatError

TEST_DATA_DIR = files('tests.table_validator_tests.test_data')

def test_init():
    my_fileio_object = File_IO(input_file= TEST_DATA_DIR / "ref_toy_csv.csv", sample_id_key="sample_id")
    assert my_fileio_object.input_file_type == "csv", "Wrong file type found"
    assert len(my_fileio_object.data_reader.keys()) == 5, "Expected 5 sample_ids in the test data"
    assert len(my_fileio_object.fields) == 4, f"Expected 4 columns/fields in data"
    assert sorted(my_fileio_object.fields) == sorted(["sample_id", "field1", "field2", "field3"]), "Did not find all expected fields"

def test_read_from_tsv():
    my_fileio_object = File_IO(input_file= TEST_DATA_DIR / "ref_toy_tsv.tsv", sample_id_key="sample_id")
    assert my_fileio_object.input_file_type == "tsv", "Wrong file type found"
    assert len(my_fileio_object.data_reader.keys()) == 5, "Expected 5 sample_ids in the test data"
    assert len(my_fileio_object.fields) == 4, f"Expected 4 columns/fields in data"
    assert sorted(my_fileio_object.fields) == sorted(["sample_id", "field1", "field2", "field3"]), "Did not find all expected fields"

def test_read_from_json():
    my_fileio_object = File_IO(input_file= TEST_DATA_DIR / "ref_toy_json.json", sample_id_key="sample_id")
    assert my_fileio_object.input_file_type == "json", "Wrong file type found"
    assert len(my_fileio_object.data_reader.keys()) == 5, "Expected 5 sample_ids in the test data"
    assert len(my_fileio_object.fields) == 4, f"Expected 4 columns/fields in data"
    assert sorted(my_fileio_object.fields) == sorted(["sample_id", "field1", "field2", "field3"]), "Did not find all expected fields"

def test_read_from_yaml():
    my_fileio_object = File_IO(input_file= TEST_DATA_DIR / "ref_toy_yaml.yaml", sample_id_key="sample_id")
    assert my_fileio_object.input_file_type == "yaml", "Wrong file type found"
    assert len(my_fileio_object.data_reader.keys()) == 5, "Expected 5 sample_ids in the test data"
    assert len(my_fileio_object.fields) == 4, f"Expected 4 columns/fields in data"
    assert sorted(my_fileio_object.fields) == sorted(["sample_id", "field1", "field2", "field3"]), "Did not find all expected fields"

def test_equality_from_different_input_formats():
    my_fileio_object_csv = File_IO(input_file= TEST_DATA_DIR / "ref_toy_csv.csv", sample_id_key="sample_id")
    my_fileio_object_tsv = File_IO(input_file= TEST_DATA_DIR / "ref_toy_tsv.tsv", sample_id_key="sample_id")
    my_fileio_object_json = File_IO(input_file= TEST_DATA_DIR / "ref_toy_json.json", sample_id_key="sample_id")
    my_fileio_object_yaml = File_IO(input_file= TEST_DATA_DIR / "ref_toy_yaml.yaml", sample_id_key="sample_id")

    assert sorted(my_fileio_object_csv.fields) == sorted(my_fileio_object_tsv.fields) == sorted(my_fileio_object_json.fields) == sorted(my_fileio_object_yaml.fields), \
        "Fields from all input types should be the same"

def test_format_inference():
    my_fileio_object_csv = File_IO(input_file= TEST_DATA_DIR / "ref_toy_csv.txt", sample_id_key="sample_id")
    assert my_fileio_object_csv.input_file_type == "csv", "Expected to infer as csv from txt file"

    my_fileio_object_tsv = File_IO(input_file= TEST_DATA_DIR / "ref_toy_tsv.txt", sample_id_key="sample_id")
    assert my_fileio_object_tsv.input_file_type == "tsv", "Expected to infer as tsv from txt file"

def test_format_inference_error():
    with pytest.raises(UnsupportedFileFormatError) as error1_info:
        my_fileio_object_faulty_simple = File_IO(input_file= TEST_DATA_DIR / "test_true_txt_simple.txt", sample_id_key="sample_id")
        assert str(error1_info.value) == "Given file does not appear to be in an accepted format. Accepted formats are:\n{self.SUPPORTED_FILE_TYPES}"
    with pytest.raises(UnsupportedFileFormatError) as error2_info:
        my_fileio_object_faulty_complex = File_IO(input_file= TEST_DATA_DIR / "test_true_txt_complex.txt", sample_id_key="sample_id")
        assert str(error2_info.value) == "Given file does not appear to be in an accepted format. Accepted formats are:\n{self.SUPPORTED_FILE_TYPES}"

def test_infer_types():
    my_fileio_object = File_IO(input_file= TEST_DATA_DIR / "ref_toy_csv.csv", sample_id_key="sample_id")
    assert my_fileio_object._infer_type(var="42") == 42, "Integer inference fails"
    assert my_fileio_object._infer_type(var="True") == True, "Bool inference fails"
    assert my_fileio_object._infer_type(var="fAlse") == False, "Bool inference fails"
    assert my_fileio_object._infer_type(var="3.14") == 3.14, "Float inference fails"
    assert my_fileio_object._infer_type(var="simple_string") == "simple_string", "Inference incorrectly applied to string"

def test_data_mapping():
    my_ref_fileio_object = File_IO(input_file= TEST_DATA_DIR / "data_map_test_left.csv", sample_id_key="col_left_1", config= TEST_DATA_DIR / "sample_config.yaml")
    my_ref_fileio_object_no_config = File_IO(input_file= TEST_DATA_DIR / "data_map_test_left.csv", sample_id_key="col_left_1")
    my_query_fileio_object = File_IO(input_file= TEST_DATA_DIR / "data_map_test_right.csv", sample_id_key="col_right_1")

    assert list(my_ref_fileio_object.data_reader.keys()) == list(my_query_fileio_object.data_reader.keys()), "Config mapping erroneously altered sample_ids"
    assert sorted(my_ref_fileio_object.fields) == sorted(my_query_fileio_object.fields), "Config mapping on column names went wrong"
    assert not sorted(my_ref_fileio_object_no_config.fields) == sorted(my_query_fileio_object.fields), "Column names should not match when config is not used"
