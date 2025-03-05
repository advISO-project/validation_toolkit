import warnings
from TableValidator.custom_exceptions import KeyMismatchWarning, SchemaMismatchWarning, FieldMismatchWarning, ValueMismatchWarning, MissingSampleWarning

class FileCompare():
    def __init__(self, left_data: dict, right_data: dict = None, strict: bool = False):
        """Initialise a file comparison object with reference and query datasets

        Args:
            left_data (dict): Data formatted by FileIO from the reference table
            right_data (dict, optional): Data formatted by FileIO from the query/subject table
            strict (bool, optional): Whether to elevate warnings to exceptions and terminate the program. Defaults to False.
        """
        self.ref_table = left_data
        self.query_table = right_data

        ## if strict, ask warnings to be elevated to terminating exceptions
        if strict:
            warnings.filterwarnings("error")

    def create_schema(self, required_fields: list = None):
        """Using the reference data, infer a "schema": expected field names and expected data types for each field

        Args:
            required_fields (list, optional): List of field names to mark as required. Defaults to None.
        """
        self.sample_schema = {}
        example_id = min(sample_id for sample_id in self.ref_table.keys())
        example_data = self.ref_table[example_id]
        ## set up a first pass schema using data from the first arbitrary sample ID
        ## here schema looks like {field_name: {"valid_types": set(type(field_value))}}
        for k, v in example_data.items():
            self.sample_schema[k] = {"valid_types": set([type(v)])}

        ## now iterate over all values and update the schema if field X is seen to have other data types
        for data_values in self.ref_table.values():
            for k, v in data_values.items():
                ## print message if new field found and add it to schema.
                ## practically this should never happen
                if k not in self.sample_schema.keys():
                    print(f"Did not find field {k} in data from example record, updating schema.")
                    self.sample_schema[k]["valid_types"] = [type(v)]
                ## check if the current value for the current value is of type that is already seen
                ## if not, add the new data type to the schema for that field
                elif not type(v) in self.sample_schema[k]:
                    self.sample_schema[k]["valid_types"].add(type(v))

        ## now, add another property per-field in the schema
        ## after this schema looks like: {field_name: {"valid_types": set(type(field_value)), "required": bool}}
        ## if list of required fields is given, set those fields to required = True
        if required_fields:
            for k in self.sample_schema.keys():
                if k in required_fields:
                    self.sample_schema[k].update({"required": True})
                else:
                    self.sample_schema[k].update({"required": False})
        ## if list of required fields is NOT given, set required = True for all fields
        else:
            for k in self.sample_schema.keys():
                self.sample_schema[k].update({"required": True})

    def confirm_schema(self):
        """Function to check data types in the query/subject table to ensure it matches the schema inferred from the reference table
        """
        for sample_id, data_value in self.query_table.items():
            for k, v in data_value.items():
                try:
                    ## first check if a given field exists in the schema
                    ## throw a warning if not
                    field_features = self.sample_schema.get(k, {})
                    assert field_features
                except AssertionError:
                    warnings.warn(FieldMismatchWarning(f"Field {k} found in query table but not in schema!"))
                    continue


                ## explicitly collect expected types from schema and whether the field is required
                expected_types = field_features["valid_types"]
                field_required = field_features["required"]

                ## also collect the type of the data in the query/subject
                ## and check if that type is expected
                type_found = type(v)
                try:
                    assert type_found in expected_types
                except AssertionError:
                    ## if this assertion fails, check if this field is required
                    ## if not then it's fine to print a warning but not have it be a formal "warning"
                    if field_required:
                        warnings.warn(SchemaMismatchWarning(f"Field {k} is of type {type_found}, expected types are {expected_types}"))
                        continue
                    else:
                        print(f"Field {k} not found for sample ID {sample_id}. Skipping as this field is specified as optional")
                        continue

    def compare_values(self, field_names: list = None, col_maps: dict = None):
        """Function to actually compare field values between reference and query/subject datasets

        Args:
            field_names (list, optional): List of field names to compare values for. Defaults to None and all fields are checked.
            col_maps (dict, optional): Mapping of column names between reference and query datasets if the schemas are not identical. Defaults to None.
        """
        if col_maps:
            raise NotImplementedError("Operation mode that uses this argument is not yet implemented.")

        ## first check if reference and query tables have the same set of sample IDs, raise warning if not
        try:
            assert sorted(list(self.ref_table.keys())) == sorted(list(self.query_table.keys()))
        except AssertionError:
            warnings.warn(KeyMismatchWarning("Sample IDs do not match between the two given datasets."))

        ## now on a per sample basis, compare values for each field
        for sample_id in self.ref_table:
            ref_data_dict = self.ref_table.get(sample_id, {})
            query_data_dict = self.query_table.get(sample_id, {})

            ## make sure that the program can retrieve sample data form both datasets
            ## this is a redundant check and given the previous try/assert block, should never evaluate to the else condition
            if ref_data_dict and query_data_dict:
                for k, v in ref_data_dict.items():
                    ## only check fields specified in field_names IF this arg is provided
                    if field_names and k not in field_names:
                        continue
                    else:
                        try:
                            ## compare data values, raise warnings on mismatch
                            assert v == query_data_dict[k]
                        except AssertionError:
                            warnings.warn(ValueMismatchWarning(f"Mismatch in value of field {k} for sample {sample_id}. Expected: {v} Found: {query_data_dict[k]}"))
                            continue
            ## if for given sample ID, data from either reference or query/subject is not found, throw a warning
            ## practically this code should never be accessed if using strict mode as there will be a failure in the sample_id matching try/assert block above
            else:
                warnings.warn(MissingSampleWarning(f"Sample ID {sample_id} not found in query table."))