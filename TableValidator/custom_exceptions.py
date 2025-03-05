
class UnsupportedFileFormatError(Exception):
    pass

class UnexpectedFileFormatError(Exception):
    pass

## warnings
class KeyMismatchWarning(Warning):
    pass

class FieldMismatchWarning(Warning):
    pass

class SchemaMismatchWarning(Warning):
    pass

class ValueMismatchWarning(Warning):
    pass

class MissingSampleWarning(Warning):
    pass
