import os, sys, argparse, datetime
from TableValidator.file_io import File_IO
from TableValidator.file_compare import FileCompare

try:
    from TableValidator.version import __version__
except ImportError:
    __version__ = "0.0.1dev"
    version_tuple = (0, 0, "1dev")

def collect_args():
    parser = argparse.ArgumentParser(description="A tool to compare tabular data against specified reference data.")
    parser.add_argument("-v", "--version", action="version", version=f"TableValidator: {__version__}")

    subparsers = parser.add_subparsers(title="subcommands", help="TableValidator sub-commands", dest="run_mode")

    file_compare_mode = subparsers.add_parser("validate")
    file_compare_mode.add_argument("-r", "--ref_table", type=str, required=True, help="Reference tabular dataset.")
    file_compare_mode.add_argument("-q", "--query_table", type=str, required=True, help="Subject tabular dataset to compare.")
    file_compare_mode.add_argument("-rs", "--ref_sampleid_key", type=str, required=True, help="The column/field name that contains sample IDs in the reference table.")
    file_compare_mode.add_argument("-qs", "--query_sampleid_key", type=str, required=True, help="The column/field name that contains sample IDs in the query table.")
    file_compare_mode.add_argument("-e", "--strict", action = "store_true", required=False, help="Whether to raise warnings as exceptions or not.")
    file_compare_mode.add_argument("-m", "--mode", type=str, required=False, default="quick_compare", help="How to execute comparison. [quick_compare, compare_subset, compare_custom]")
    file_compare_mode.add_argument("-l", "--field_list", type=str, required=False, help="Comma-separated list of column names/fields to compare, required and used ONLY if using mode 'compare_subset'.")
    file_compare_mode.add_argument("-c", "--custom_config", type=str, required=False, help="Custom config file containing col_name and value mappings in .yaml format.")
    file_compare_mode.add_argument("-o", "--output_filename", type=str, required=True, help="Path to output file to be written.")
    file_compare_mode.add_argument("-f", "--write_format", type=str, required=False, default="json", help="File format to write comparison output to ['json', 'csv'].")

    format_convert_mode = subparsers.add_parser("convert_format")
    format_convert_mode.add_argument("-i", "--input_filepath", type=str, required=False, help="File path to read data from for conversion to new format.")
    ## code duplication, consider alternatives
    format_convert_mode.add_argument("-s", "--sampleid_key", type=str, required=True, help="The column/field name that contains sample IDs.")
    format_convert_mode.add_argument("-o", "--output_filename", type=str, required=False, help="File name to write converted data to.")
    format_convert_mode.add_argument("-d", "--output_dir", type=str, required=False, default=".", help="Directory path to write converted data to.")
    format_convert_mode.add_argument("-f", "--write_format", type=str, required=False, help="File format to convert input data to.")

    args = parser.parse_args()
    return args

def main():
    ## collect basic run metadata
    NOW = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    PROG = __name__.split(".")[0]
    metadata = {
                    "prog": f"{PROG}",
                    "prog_version": f"{__version__}",
                    "datetime": f"{NOW}",
                    "cli": " ".join(sys.argv),
                }

    args = collect_args()

    ## confirm accepted mode
    try:
        assert args.mode in ["quick_compare", "compare_subset"]
    except AssertionError:
        raise ValueError("args.mode should be in [quick_compare, compare_subset]")

    ## set up output file
    ## if file with given name exists, use timestamp to prevent overwriting
    if args.write_format == "json":
        try:
            assert not os.path.exists(args.output_filename)
            validator_output_file = args.output_filename
        except AssertionError:
            print(f"Path: {args.output_filename} already exists. Using timestamp to prevent overwriting.")
            validator_output_file = args.output_filename.strip(f".json") + "_" + ".".join(NOW.split(" ")[1].split(":")) + ".json"

    ## if output format is csv, 2 files are generated, so two filenames need to be checked
    elif args.write_format == "csv":
        base = args.output_filename.strip(f".csv")
        files_to_check = [f"{base}_schema_check.csv", f"{base}_value_check.csv"]
        try:
            for file in files_to_check:
                assert not os.path.exists(file)
            validator_output_file = args.output_filename
        except AssertionError:
            print(f"Paths using basename: {base} already exist. Using timestamp to prevent overwriting.")
            validator_output_file = f"{base}_" + ".".join(NOW.split(" ")[1].split(":")) + ".csv"
            print(validator_output_file)

    ## when run_mode is to validate, collect ref and query filepaths
    if args.run_mode == "validate":
        r_file = os.path.abspath(args.ref_table)
        q_file = os.path.abspath(args.query_table)

        ## add file paths to run metadata
        metadata["ref"] = r_file
        metadata["query"] = q_file

        ## if only ref sample_id_key provided, assume it is the same in query
        r_key = args.ref_sampleid_key
        if r_key and not args.query_sampleid_key:
            q_key = r_key
        else:
            q_key = args.query_sampleid_key


        print("Reading data from files...")
        ## if custom config given, use it to map colnames and values onto reference file
        ## colnames and values in ref should now match representations in the query
        if args.custom_config:
            r_table = File_IO(input_file=r_file, sample_id_key=r_key, config=args.custom_config)
        else:
            r_table = File_IO(input_file=r_file, sample_id_key=r_key)
        q_table = File_IO(input_file=q_file, sample_id_key=q_key)

        ## initialise validator object
        validator = FileCompare(left_data=r_table.data_reader, right_data=q_table.data_reader, strict=args.strict)

        print("Setting up and validating schema...")
        ## create and confirm schema
        validator.create_schema()
        validator.confirm_schema()

        ## in quick_compare, nothing else needs to be done before comparing values
        if args.mode == "quick_compare":
            print("Running quick_compare...")
            validator.compare_values()
            print(f"Writing output to: {validator_output_file}")
            validator.write_results(metadata=metadata, output=validator_output_file, out_format=args.write_format)

        ## if subset of colnames to be compared, make sure user-provided list of this subset exists
        elif args.mode == "compare_subset":
            print("Running compare_subset...")
            if not args.field_list:
                raise ValueError("Cannot run subset comparison without a list of fields to compare.")
            fields_to_compare = args.field_list.split(",")
            validator.compare_values(field_names=fields_to_compare)
            print(f"Writing output to: {validator_output_file}")
            validator.write_results(metadata=metadata, output=validator_output_file, out_format=args.write_format)

        print("Success!")

    ## when run_mode is "convert_format"
    ## simply read data in, and write out to provided format
    elif args.run_mode == "convert_format":
        ## admin
        input_file = os.path.abspath(args.input_filepath)
        output_dir = os.path.abspath(args.output_dir)
        output_file = os.path.join(output_dir, args.output_filepath)
        reader_object = File_IO(input_file=input_file, sample_id_key=args.sampleid_key)
        if args.write_format == "csv":
            reader_object.write_to_csv(output_file=output_file)
        if args.write_format == "tsv":
            reader_object.write_to_tsv(output_file=output_file)
        if args.write_format == "json":
            reader_object.write_to_json(output_file=output_file)
        if args.write_format == "yaml":
            reader_object.write_to_yaml(output_file=output_file)

if __name__ == "main":
    main()
