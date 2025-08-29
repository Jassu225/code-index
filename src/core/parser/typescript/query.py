from typing import Final


JS_EXPORT_QUERIES: Final[str] = """
(export_statement 
  (export_clause 
    (export_specifier 
      name: (identifier) @export.identifier)))

(export_statement 
  declaration: (function_declaration 
    name: (identifier) @export.function.name))

(export_statement 
  declaration: (class_declaration 
    name: (identifier) @export.class.name
    body: (class_body 
      (method_definition 
        name: (property_name) @export.class.method.name)
      (field_definition 
        property: (property_name) @export.class.field.name))))
"""

TS_EXPORT_QUERY: Final[str] = """
(program
	(export_statement) @export
) @program
"""

TS_IMPORT_QUERY: Final[str] = """
(program
	(import_statement) @import
) @program
"""