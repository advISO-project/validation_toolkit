import pytest
from TableValidator.file_io import File_IO
from TableValidator.file_compare import FileCompare
from TableValidator.custom_exceptions import SchemaMismatchWarning, ValueMismatchWarning

@pytest.fixture
def test_init():
    left_data = File_IO(input_file="tests/test_data/ref_toy_csv.csv", sample_id_key="sample_id")
    right_data = File_IO(input_file="tests/test_data/ref_toy_json.json", sample_id_key="sample_id")

    test_object = FileCompare(left_data=left_data.data_reader, right_data=right_data.data_reader)
    assert test_object, "A test file_compare object should be built"
    return test_object

def test_create_schema(test_init):
    test_object = test_init
    test_object.create_schema()

    assert len(test_object.sample_schema.keys()) == 4, "There should be 4 fields in the schema"
    assert test_object.sample_schema["sample_id"]["valid_types"] == test_object.sample_schema["field1"]["valid_types"] == set([str])

def test_confirm_schema(test_init):
    test_object = test_init
    test_object.create_schema()
    test_object.confirm_schema()

def test_compare_values(test_init):
    test_object = test_init
    test_object.create_schema()
    test_object.compare_values()

def test_confirm_schema_fail():
    left_data = File_IO(input_file="tests/test_data/ref_toy_csv.csv", sample_id_key="sample_id")
    right_data = File_IO(input_file="tests/test_data/query_toy_json_schemamismatch.json", sample_id_key="sample_id")
    test_object_lenient = FileCompare(left_data=left_data.data_reader, right_data=right_data.data_reader)
    test_object_lenient.create_schema()

    ## there should be a schema check failure here
    with pytest.warns(SchemaMismatchWarning, match="Field field2 is of type <class 'bool'>, expected types are {<class 'int'>, <class 'str'>}" or "Field field2 is of type <class 'bool'>, expected types are {<class 'str'>, <class 'int'>}"):
        test_object_lenient.confirm_schema()

    ## using strict mode, this warning should now be an exception -- pytest.raises needed to catch it
    test_object_strict = FileCompare(left_data=left_data.data_reader, right_data=right_data.data_reader, strict=True)
    test_object_strict.create_schema()
    with pytest.raises(SchemaMismatchWarning) as error_info:
        test_object_strict.confirm_schema()

def test_compare_values_fail():
    left_data = File_IO(input_file="tests/test_data/ref_toy_csv.csv", sample_id_key="sample_id")
    right_data = File_IO(input_file="tests/test_data/query_toy_json_valmismatch.json", sample_id_key="sample_id")
    test_object = FileCompare(left_data=left_data.data_reader, right_data=right_data.data_reader)
    test_object.create_schema()
    test_object.confirm_schema()
    ## there should be a value mismatch flagged here
    with pytest.warns(ValueMismatchWarning, match="Mismatch in value of field field2 for sample sample_4. Expected: 42 Found: fourtwo"):
        test_object.compare_values()

def test_compare_values_specific_fields():
    left_data = File_IO(input_file="tests/test_data/ref_toy_csv.csv", sample_id_key="sample_id")
    right_data = File_IO(input_file="tests/test_data/query_toy_json_valmismatch.json", sample_id_key="sample_id")
    test_object = FileCompare(left_data=left_data.data_reader, right_data=right_data.data_reader)
    test_object.create_schema()
    test_object.confirm_schema()
    ## even though this test uses a value_mismatch test fixture
    ## there should be no warnings as the field in question is not included in the provided list of field names to check
    test_object.compare_values(field_names=["sample_id", "field1", "field3"])
