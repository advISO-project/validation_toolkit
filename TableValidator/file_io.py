import os, sys
import csv
import json
import yaml
from TableValidator.custom_exceptions import UnsupportedFileFormatError, UnexpectedFileFormatError

class File_IO():
    """Read, write and intercovert between a range of file types.
        Currently supports csv, tsv, json, and yaml
    """
    def __init__(self, input_file: str, sample_id_key: str, data_reader: dict = None):
        """Initialising a File_IO object

        Args:
            input_file (str/pathlike): File to read from.
            data_reader (dict, optional): Dictionary formatted as {sample_id: {field1: val1, field2: val2...}}. Defaults to None.
                                            This is the output/internal structure of data in File_IO
                                            File_IO can alternatively start with such a dict
            sample_id_key (str, optional): The name of the field or column in the input file corresponding to sample IDs.

        """
        ## raise error if sample_id column not provided
        ## TODO: add code to possibly try and infer sample_id column
        if not sample_id_key:
            raise NotImplementedError("Code to handle this must be written and does not yet exist.")

        ## set up a list of accepted file formats
        self.SUPPORTED_FILE_TYPES = [".csv", ".tsv", ".json", ".yaml"]
        ## set up map of file format to corresponding read functions for ease of use
        read_functions = {
                            "csv": self._read_table,
                            "tsv": self._read_table,
                            "json": self._read_serialized,
                            "yaml": self._read_serialized,
                        }

        ## if data_reader is provided, use that to initialise
        ## if input file is ALSO provided, it is ignored
        if data_reader or data_reader and input_file:
            self.data_reader = data_reader

        ## if ONLY input file provided, read it in
        elif input_file and not data_reader:
            self.full_path_input_file = os.path.abspath(input_file)

            ## get file type of input file from its extension
            self.input_file_type = self._get_file_type(self.full_path_input_file)

            ## if csv or tsv, pass to tabular file reader function
            if self.input_file_type in ["csv", "tsv"]:
                tmp_data_reader = read_functions[self.input_file_type](self.full_path_input_file, sample_id_key)
                self.data_reader = self._recover_types_in_data(tmp_data_reader)

            ## if json or yaml, pass to serialized file reader function
            else:
                self.data_reader = read_functions[self.input_file_type](self.full_path_input_file)

            ## collect a list of fields/column names from the input
            self.fields = []
            example_key = list(self.data_reader.keys())[0]
            self.fields.extend(list(self.data_reader[example_key].keys()))

    def _get_file_type(self, input_file: str):
        """Use file extension to infer file type

        Args:
            input_file (str/pathlike): File to read from

        Returns:
            file_type (str): The inferred file format. Currently support formats are: csv, tsv, json, yaml
        """
        file_type = None

        ## get file extension
        file_tuple = os.path.splitext(input_file)
        extension = file_tuple[1]

        ## if extension not in known formats but it is txt, try to check if it is csv or tsv
        if extension not in self.SUPPORTED_FILE_TYPES:
            if extension == ".txt":
                sys.stderr.write("Found a .txt file, checking if it is a csv or tsv...\n")

                ## use helper function to check delimiters
                try:
                    file_type = "csv" if self._check_delimiter(input_file=input_file, sep_to_check=",") else "tsv" if self._check_delimiter(input_file=input_file, sep_to_check="\t") else None
                    print(f"found: {file_type}")
                except StopIteration:
                    file_type = None
                    print(f"Bad file! Found: {file_type}")

            ## at this point, if at all possible, file_type should have a value
            if not file_type:
                raise UnsupportedFileFormatError(f"Given file does not appear to be in an accepted format. Accepted formats are:\n{self.SUPPORTED_FILE_TYPES}")

        else:
            file_type = extension.strip(".")

        return file_type

    def _check_delimiter(self, input_file:str, sep_to_check:str):
        """Check if given file has a delimiter that the program supports checking of ([",", "\t"])

        Args:
            input_file (str): Path to input file to check
            sep_to_check (str): Field separator to check for

        Returns:
            bool: Whether the given input file is delimited using the given sep_to_check
        """
        with open(input_file, "rt") as in_file_handle:
            ## use given sep to load file
            reader = csv.DictReader(in_file_handle, delimiter=f"{sep_to_check}")
            try:
                ## try getting the first line, likely the header
                ## this invocation of next will fail for invalid files
                ## return False if it does
                header = next(reader)
            except StopIteration:
                return False

            ## if this does not fail, also get the putative first "row"
            row = next(reader)
            num_cols = len(header)
        in_file_handle.close()

        ## if only one "column" is found, this is likely not an appropriately formatted table, return False
        if num_cols == 1:
            return False
        ## if >1 "column" found, check the same for the first "row"
        ## if cols >1 and len(row) == 1, this is not a valid table
        else:
            if len(row) == 1:
                return False

        ## if all of the above pass, this file probably IS delimited by the given sep_to_check, return True
        return True

    def _read_table(self, csv_or_tsv_file: str, sample_id_key: str):
        """Read in a tabular file (csv/tsv) and format the data into the required internal representation

        Args:
            csv_or_tsv_file (str): Path to data file
            sample_id_key (str): Column name containing sample ID info

        Returns:
            data (dict): Dictionary representation of the data, formatted as follows:
                key: sample_id
                value: a dict where
                    key: field/column name
                    value: field/column value
        """
        try:
            ## first make sure the file_type is csv or tsv
            ## this is a redundant check and should never evaluate to False
            assert self.input_file_type in ["csv", "tsv"]
        except AssertionError as ae:
            raise UnexpectedFileFormatError("Found unexpected file format. Supported formats are: [csv, tsv]")

        ## use the file type to read file in with the correct delimiter
        with open(csv_or_tsv_file, "rt") as in_csv_or_tsv_handle:
            if self.input_file_type == "csv":
                file_reader = csv.DictReader(in_csv_or_tsv_handle, delimiter=",")
            else:
                file_reader = csv.DictReader(in_csv_or_tsv_handle, delimiter="\t")

            ## populate the data dictionary
            data = {}
            for row in file_reader:
                sample_id = row[sample_id_key]
                sample_data = {k: v for k, v in row.items()}
                data[sample_id] = sample_data
        in_csv_or_tsv_handle.close()

        return data

    def _read_serialized(self, json_or_yaml_file: str):
        """Read in from a serialized file format (json/yaml)

        Args:
            json_or_yaml_file (str): Path to input file

        Returns:
            serial_reader (dict): The serialized data, which is already expected to be in the required structure
        """
        try:
            ## first make sure the file_type is json or yaml
            ## this is a redundant check and should never evaluate to False
            assert self.input_file_type in ["json", "yaml"]
        except AssertionError as ae:
            raise UnexpectedFileFormatError("Found unexpected file format. Supported formats are: [json, yaml]")

        with open(json_or_yaml_file, "rt") as in_json_to_yaml_handle:
            if self.input_file_type == "json":
                serial_reader = json.load(in_json_to_yaml_handle)
            if self.input_file_type == "yaml":
                serial_reader = yaml.safe_load(in_json_to_yaml_handle)

        return serial_reader

    def _recover_types_in_data(self, data_dict: dict):
        """Wrapper function that applies fn _infer_type to a formatted data dictionary. Only applied if the input file was tabular.

        Args:
            data_dict (dict): Dictionary representation of the data, formatted as follows:
                                key: sample_id
                                value: a dict where
                                    key: field/column name
                                    value: field/column value

        Returns:
            updated_data (dict): Updated data dict where data types are inferred and non string data is converted appropriately
        """
        updated_data = {}
        for sample_id, row_data in data_dict.items():
            new_row_data = {}
            for k, v in row_data.items():
                ## iterating over field data in the data dict
                ## infer (and convert if needed) data types
                converted_value = self._infer_type(v)
                new_row_data.update({k: converted_value})
            updated_data.update({sample_id: new_row_data})
        return updated_data

    def _infer_type(self, var: str):
        """Function to take string values and convert to other primitive types if applicable

        Args:
            var (str): Input value in strring form, as it will be found in tabular files

        Returns:
            str | int | float | bool: The var input, converted to int/float/bool as applicable
        """
        bool_map = {"true": True, "false": False}
        ## first check if the string is numeric
        ## if yes, return the int
        if var.isnumeric():
            return int(var)
        ## next check if string might contain a bool expression
        ## if so, return the correct bool
        elif var.lower() in ["true", "false"]:
                return bool_map[var.lower()]
        else:
            try:
                ## next try casting it to float
                ## this only works if the string format can be resolved to str(float)
                return float(var)
            except ValueError:
                ## if the str really cannot be cast to anything else, return as is
                return var

    def write_to_csv(self, output_file: str):
        """Function to write data to csv

        Args:
            output_file (str): Path to output file
        """
        rows_to_write = []
        for sample_id in self.data_reader.keys():
            row = {"sample_id": sample_id}
            row.update(self.data_reader[sample_id])
            rows_to_write.append(row)
        with open(output_file, "w") as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=self.fields, delimiter=",")
            writer.writeheader()
            for row in rows_to_write:
                writer.writerow(row)

    def write_to_tsv(self, output_file: str):
        """Function to write data to tsv

        Args:
            output_file (str): Path to output file
        """
        rows_to_write = []
        for sample_id in self.data_reader.keys():
            row = {"sample_id": sample_id}
            row.update(self.data_reader[sample_id])
            rows_to_write.append(row)
        with open(output_file, "w") as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=self.fields, delimiter="\t")
            writer.writeheader()
            for row in rows_to_write:
                writer.writerow(row)

    def write_to_json(self, output_file: str):
        """Function to write data to JSON

        Args:
            output_file (str): Path to output file
        """
        with open(output_file, "w") as outhandle:
            json.dump(self.data_reader, outhandle, indent=4)

    def write_to_yaml(self, output_file: str):
        """Function to write data to yaml

        Args:
            output_file (str): Path to output file
        """
        with open(output_file, "w") as outhandle:
            yaml.dump(self.data_reader, outhandle, indent=4)
