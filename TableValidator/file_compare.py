import warnings
import json
from collections import defaultdict
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
        self.schema_errors = defaultdict(dict)
        self.value_mismatches = defaultdict(dict)

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

        col_name_warnings = 0
        for sample_id, data_value in self.query_table.items():
            self.schema_errors[sample_id] = {"sample_id": sample_id}
            for k, v in data_value.items():
                ## first check if a given field exists in the schema
                ## throw a warning if not
                field_features = self.sample_schema.get(k, {})
                if not field_features:
                    warnings.warn(FieldMismatchWarning(f"Field {k} found in query table but not in schema!"))
                    col_name_warnings += 1
                    ## if the number of column mismatches equals the number of columns, this use case likely needs to employ the config.
                    if col_name_warnings == len(data_value.keys()):
                        raise Exception(f"No column names seem to match between the schema and the query table. You must provide a config file when column names differ between the reference and query tables.")
                    continue

                ## explicitly collect expected types from schema and whether the field is required
                expected_types = field_features["valid_types"]
                field_required = field_features["required"]

                ## also collect the type of the data in the query/subject
                ## and check if that type is expected
                type_found = type(v)
                if type_found in expected_types:
                    self.schema_errors[sample_id].update({k: "SchemaMatch"})
                else:
                    if field_required:
                        warnings.warn(SchemaMismatchWarning(f"Field {k} is of type {type_found}, expected types are {expected_types}"))
                        self.schema_errors[sample_id].update({k: f"SchemaMismatch. Expected {expected_types} Found {type_found}"})
                        continue
                    else:
                        self.schema_errors[sample_id].append({k: f"SchemaMismatch (optional field). Expected {expected_types} Found {type_found}"})
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
        if not sorted(list(self.ref_table.keys())) == sorted(list(self.query_table.keys())):
            warnings.warn(KeyMismatchWarning("Sample IDs do not match between the two given datasets."))

        ## now on a per sample basis, compare values for each field
        for sample_id in self.ref_table:
            self.value_mismatches[sample_id] = {"sample_id": sample_id}
            ref_data_dict = self.ref_table.get(sample_id, {})
            query_data_dict = self.query_table.get(sample_id, {})

            ## make sure that the program can retrieve sample data form both datasets
            ## this is a redundant check and given the previous try/assert block, should never evaluate to the else condition
            if ref_data_dict and query_data_dict:
                for k, v in ref_data_dict.items():
                    ## only check fields specified in field_names IF this arg is provided
                    if field_names and k not in field_names:
                        self.value_mismatches[sample_id].update({k: f"Field not checked"})
                        continue
                    else:
                        if v == query_data_dict[k]:
                            self.value_mismatches[sample_id].update({k: "ValueMatch"})
                        else:
                            self.value_mismatches[sample_id].update({k: f"ValueMismatch. Expected {v} Found {query_data_dict[k]}"})
                            warnings.warn(ValueMismatchWarning(f"Mismatch in value of field {k} for sample {sample_id}. Expected: {v} Found: {query_data_dict[k]}"))
                            continue
            ## if for given sample ID, data from either reference or query/subject is not found, throw a warning
            ## practically this code should never be accessed if using strict mode as there will be a failure in the sample_id matching try/assert block above
            else:
                warnings.warn(MissingSampleWarning(f"Sample ID {sample_id} not found in query table."))
                self.value_mismatches[sample_id].append({k: f"Missing field"})

    def _format_csv_output(self, metadata: dict, output: str):
        """Format output data into CSV format. When CSV is used as the output file type,
            two files are produced, using the basename of the output file provided:
                {basename}_schema_check.csv: contains results of schema comparison
                {basename}_value_check.csv: contains results of value comparison
            NB: metadata is written as comments starting with "##" to both of the above files.

        Args:
            metadata (dict): Metadata dict containing info on comparison run
            output (str): Path to output file path
        """
        metadata_lines = []
        schema_lines = []
        value_lines = []

        for k, v in metadata.items():
            metadata_lines.append(f"## {k}: {v}\n")

        example_key = min([k for k in self.schema_errors.keys()])
        example_val = self.schema_errors[example_key]
        header = ",".join([k for k in example_val.keys()])+"\n"

        schema_lines.append(header)
        for k, v in self.schema_errors.items():
            line = []
            for val_v in v.values():
                line.append(val_v)
            schema_lines.append(",".join(line)+"\n")

        value_lines.append(header)
        for k, v in self.value_mismatches.items():
            line = []
            for val_v in v.values():
                line.append(val_v)
            value_lines.append(",".join(line)+"\n")

        ## set up output files
        schema_out = output.strip(".csv") + "_schema_check" + ".csv"
        value_out = output.strip(".csv") + "_value_check" + ".csv"

        with open(schema_out, "w") as schema_outhandle:
            for line in metadata_lines:
                schema_outhandle.write(line)
            for line in schema_lines:
                schema_outhandle.write(line)

        schema_outhandle.close()

        with open(value_out, "w") as value_outhandle:
            for line in metadata_lines:
                value_outhandle.write(line)
            for line in value_lines:
                value_outhandle.write(line)

        value_outhandle.close()

    def write_results(self, metadata: dict, output: str, out_format: str = "json"):
        """Function to write comparison outputs to file

        Args:
            metadata (dict): Dict containing metadata of the current comparison run
            output (str): Path to output file
            out_format (str, optional): Format to write outputs to ['json', 'csv']. Defaults to "json".
                                        if 'csv' is provided, two files are produced,
                                            {output_basename}_schema_check.csv
                                            {output_basename}_value_check.csv
        """
        ## if output format is json, format all dicts in a single one and write to file
        if out_format == "json":
            out_dict = {
                        "metadata": metadata,
                        "schema_check": self.schema_errors,
                        "value_check": self.value_mismatches
                        }

            with open(output, "w") as outhandle:
                json.dump(out_dict, outhandle, indent=4)

        ## if output format is csv, convert data from all 3 dicts to lines
        ## write metadata and schema results to {output_basename}_schema_check.csv
        ## write metadata (again) and schema results to {output_basename}_value_check.csv
        elif out_format == "csv":
            self._format_csv_output(metadata=metadata, output=output)