import os, argparse
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
    file_compare_mode.add_argument("-s", "--sampleid_key", type=str, required=True, help="The column/field name that contains sample IDs.")
    file_compare_mode.add_argument("-e", "--strict", action = "store_true", required=False, help="Whether to raise warnings as exceptions or not.")
    file_compare_mode.add_argument("-m", "--mode", type=str, required=False, default="quick_compare", help="How to execute comparison. [quick_compare, compare_subset, compare_custom]")
    file_compare_mode.add_argument("-l", "--field_list", type=str, required=False, help="Comma-separated list of column names/fields to compare, required and used ONLY if using mode 'compare_subset'.")
    file_compare_mode.add_argument("-c", "--custom_config", type=str, required=False, help="Custom config file, required and used ONLY if using mode 'compare_custom'. CURRENTLY NOT IMPLEMENTED")

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
    args = collect_args()

    try:
        assert args.mode in ["quick_compare", "compare_subset", "compare_custom"]
    except AssertionError:
        raise ValueError("args.mode should be in [quick_compare, compare_subset, compare_custom]")

    if args.run_mode == "validate":
        r_file = os.path.abspath(args.ref_table)
        q_file = os.path.abspath(args.query_table)
        r_table = File_IO(input_file=r_file, sample_id_key=args.sampleid_key)
        q_table = File_IO(input_file=q_file, sample_id_key=args.sampleid_key)

        validator = FileCompare(left_data=r_table.data_reader, right_data=q_table.data_reader, strict=args.strict)
        validator.create_schema()
        validator.confirm_schema()

        if args.mode == "quick_compare":
            validator.compare_values()

        elif args.mode == "compare_subset":
            if not args.field_list:
                raise ValueError("Cannot run custom comparison without a list of fields to compare.")
            fields_to_compare = args.field_list.split(",")
            validator.compare_values(field_names=fields_to_compare)

        elif args.mode == "compare_custom":
            raise NotImplementedError("This mode has not currently been implemented.")
            if not args.custom_config:
                raise ValueError("Cannot run custom comparison without a config file.")

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
