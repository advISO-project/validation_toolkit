# Validation Toolkit

A Python package to compare tabular datasets and record discrepancies.

# Install

From source

```bash
git clone path/to/repo
cd path/to/repo
pip install .
```

With pip

```bash
pip install validation_toolkit@git+path/to/repo
```

# Usage
Using this package, you can compare a known "reference" table to a new "query" table. When verifying that a change in your data pipeline did not change the output table, the older iteration of the table is the reference and the new one generated after your change is the query; when comparing the outputs of your pipeline to those of another existing one, the outputs of the existing pipeline can be considered the reference. Depending on your use case, you may want to compare two tables that have identical schemas; or compare two such tables but only on a subset of columns; or else compare two tables that have entirely different schemas -- the CLI for each case is shown below.

To compare two tables that have the same column names and data vocabularies:

```bash
validation_toolkit compare \
    -r path/to/reference/data_table \
    -q path/to/query/data_table \
    -rs sample_id_colname \
    -o path/to/output/file \
    -f output_file_format
```

To compare **a subset of columns** from two tables that have the same column names and data vocabularies:
```bash
validation_toolkit compare \
    -r path/to/reference/data_table \
    -q path/to/query/data_table \
    -m compare_subset \
    -l col_name_1,col_name_2,col_name3 \
    -rs sample_id_colname \
    -o path/to/output/file \
    -f output_file_format
```

To compare two tables that have **different** column names and/or data vocabularies:
```bash
validation_toolkit compare \
    -r path/to/reference/data_table \
    -q path/to/query/data_table \
    -l col_name_1,col_name_2,col_name3 \
    -rs sample_id_colname_in_ref \
    -qs sample_id_colname_in_query \
    -c path/to/custom_config.yaml \
    -o path/to/output/file \
    -f output_file_format
```

# Using Custom Configs

If comparing tabular data that may have been produced by different data pipelines, a custom configuration file in YAML format can be provided using the `-c` flag as shown above. When such a config file is used, the internal representation of the **reference** table is mapped to the provided mappings in the config, and the data in the query table is represented as-is.  

The custom config file has the following structure:  

```yaml
col_1_ref:
  col_name: col_1_query
  value_map: null
col_2_ref:
  col_name: col_2_query
  value_map:
    true: 1
    false: 0
    unknown: null
col_3_ref:
  col_name: col_3_query
  value_map:
    resistant: 1
    sensitive: 0
    unknown: 2
```

The example config above says: the column `col_1_ref` in the reference table maps to the column called `col_1_query` in the query dataset. In terms of data vocabularies, however, this first column is the same across both datasets.  

This is not true for the column `col_2_ref` in the reference table: this column has a different name in the query table (`col_2_query`) but also, a `boolean true` in the reference table is represented as a `int 1` in the query, and so on.  

# Output Files
This progam can produce outputs in either JSON or CSV formats. If using JSON, the output file will contain the following data:

```json
{
    "metadata": {
        "prog": "validation_toolkit",
        "prog_version": "0.0.1dev",
        "datetime": "2025-03-25 15:52:19",
        "cli": "path/to/validation_toolkit compare -r tests/test_data/data_map_test_left.csv -q tests/test_data/data_map_test_right.csv -rs col_left_1 -qs col_right_1 -c tests/test_data/sample_config.yaml -m compare_subset -l col_right_2,col_right_3 -o test_out.json -f json",
        "ref": "path/to/ref_table.csv",
        "query": "path/to/query_table.csv"
    },
    "schema_check": {
        "sample1": {
            "sample_id": "sample1",
            "col_right_1": "SchemaMatch",
            "col_right_2": "SchemaMatch",
            "col_right_3": "SchemaMatch"
        },
        ...
    },
    "value_check": {
        "sample1": {
            "sample_id": "sample1",
            "col_right_1": "Field not checked",
            "col_right_2": "ValueMatch",
            "col_right_3": "ValueMatch"
        },
        ...
    }
}
```
The three pieces of data in this JSON are the `metadata`, which stores information on the features of the comparison run you just executed; the `schema_check`, which stores information on whether the structure of the two tables (after applying config-based mapping if this is applicable) matches or not; and the `value_check`, which stores information on whether the corresponiding values across the tables match or not.

Alternatively, the user can output this information in CSV format, whereby two files are written (assuming the output file provided by the user is `output_basename.csv`):
- `{output_basename}_schema_check.csv` contains `schema_check` data
- `{output_basename}_value_check.csv` contains `value_check` data

Metadata lines are formatted as comments starting with two hashes; these are written to the top of both of the above CSV files.

# List of Options
- `-h`, `--help`: show this help message and exit
- `-r`, `--ref_table`: Reference tabular dataset. [REQUIRED: TRUE]
- `-q`, `--query_table`: Subject tabular dataset to compare. [REQUIRED: TRUE]
- `-rs`, `--ref_sampleid_key`: The column/field name that contains sample IDs in the reference table. [REQUIRED: TRUE]
- `-qs`, `--query_sampleid_key`: The column/field name that contains sample IDs in the query table. [OPTIONAL] [DEFAULT: same as provided value for `--ref_sampleid_key`]
- `-e`, `--strict`: Whether to raise warnings as exceptions or not. **NB** Using this option will cause the program to quit upon encountering differences in the datasets and consequenctly, no output files will be generated. Ordinarily, this flag should never be used.
- `-m`, `--mode`: How to execute comparison. [VALID: quick_compare, compare_subset] [DEFAULT: quick_compare]
- `-l`, `--field_list`: Comma-separated list of column names/fields to compare, required and used ONLY if using mode 'compare_subset'.
- `-c`, `--custom_config`: Custom config file containing col_name and value mappings in .yaml format.
- `-o`, `--output_filename`: Path to output file to be written. [REQUIRED: TRUE]
- `-f`, `--write_format`: File format to write comparison output to. [VALID: 'csv', 'json']
