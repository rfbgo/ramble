# lib/ramble/ramble/schema/generic_sql_schema.py

# Define generic SQL types
class DataTypes:
    INTEGER = "INTEGER"
    TEXT = "TEXT"        # For general text, potentially long
    STRING = "STRING"    # For shorter strings (can be mapped to TEXT if DB doesn't distinguish)
    BOOLEAN = "BOOLEAN"  # Typically 0 or 1, or TRUE/FALSE
    TIMESTAMP = "TIMESTAMP" # Store as ISO 8601 format string in text representation
    JSON_TEXT = "JSON_TEXT" # For storing JSON objects as text; validation of content is separate

# Schema definition
GENERIC_SCHEMA = {
    "experiments": {
        "columns": [
            {"name": "id", "type": DataTypes.INTEGER, "nullable": False, "primary_key": True, "description": "Unique hash of the experiment object"},
            {"name": "name", "type": DataTypes.STRING, "nullable": False, "description": "Name of the experiment"},
            {"name": "application_name", "type": DataTypes.STRING, "nullable": False, "description": "Name of the application"},
            {"name": "workspace_name", "type": DataTypes.STRING, "nullable": False, "description": "Name of the workspace"},
            {"name": "workspace_hash", "type": DataTypes.STRING, "nullable": False, "description": "Hash of the workspace configuration"},
            {"name": "workload_name", "type": DataTypes.STRING, "nullable": False, "description": "Name of the workload"},
            {"name": "bulk_hash", "type": DataTypes.STRING, "nullable": True, "description": "Hash for grouping experiments, e.g., from workspace and timestamp"},
            {"name": "n_nodes", "type": DataTypes.INTEGER, "nullable": True},
            {"name": "processes_per_node", "type": DataTypes.INTEGER, "nullable": True},
            {"name": "n_ranks", "type": DataTypes.INTEGER, "nullable": True},
            {"name": "n_threads", "type": DataTypes.INTEGER, "nullable": True},
            {"name": "node_type", "type": DataTypes.STRING, "nullable": True, "description": "Type or model of the node"},
            {"name": "status", "type": DataTypes.STRING, "nullable": False, "description": "Final status of the experiment (e.g., SUCCESS, FAILED)"},
            {"name": "user", "type": DataTypes.STRING, "nullable": True, "description": "User who ran the experiment"},
            {"name": "timestamp", "type": DataTypes.TIMESTAMP, "nullable": False, "description": "Timestamp of experiment data recording (ISO 8601)"},
            {"name": "data", "type": DataTypes.JSON_TEXT, "nullable": True, "description": "Full original experiment data as a JSON string"},
            # The 'foms' field from the original BigQuery schema was a JSON string of FOMs.
            # In a normalized SQL schema, FOMs are in their own table.
            # If there's a need to store the raw FOMs JSON string with the experiment,
            # it could be added here, e.g., as 'raw_foms_json'.
            # For now, we assume FOMs are handled via the separate 'foms' table.
        ]
    },
    "foms": {
        "columns": [
            # Assuming a surrogate primary key for FOMs if needed, or composite.
            # For simplicity, not defining one explicitly here unless required by an ORM or DB.
            {"name": "experiment_id", "type": DataTypes.INTEGER, "nullable": False, "description": "Foreign key linking to the experiments table (experiment.id)"},
            {"name": "experiment_name", "type": DataTypes.STRING, "nullable": False, "description": "Name of the experiment this FOM belongs to (for convenience)"},
            {"name": "name", "type": DataTypes.STRING, "nullable": False, "description": "Name of the Figure of Merit (FOM)"},
            {"name": "value", "type": DataTypes.TEXT, "nullable": True, "description": "Value of the FOM (can be numeric or textual, stored as text)"},
            {"name": "unit", "type": DataTypes.STRING, "nullable": True, "description": "Unit of the FOM value"},
            {"name": "origin", "type": DataTypes.STRING, "nullable": True, "description": "Origin of the FOM data (e.g., filename, parser name)"},
            {"name": "origin_type", "type": DataTypes.STRING, "nullable": True, "description": "Type of the FOM origin (e.g., 'log_file', 'stdout')"},
            {"name": "context", "type": DataTypes.STRING, "nullable": True, "description": "Context in which the FOM was generated (e.g., stage name, specific part of a test)"},
        ]
    }
}

# Helper function to get a schema for jsonschema validation from the generic schema
# This is a basic version and might need to be more sophisticated
def get_jsonschema_for_table(table_name):
    if table_name not in GENERIC_SCHEMA:
        return None

    table_schema = GENERIC_SCHEMA[table_name]
    properties = {}
    required = []

    type_mapping = {
        DataTypes.INTEGER: "integer",
        DataTypes.STRING: "string",
        DataTypes.TEXT: "string",
        DataTypes.BOOLEAN: "boolean",
        DataTypes.TIMESTAMP: "string", # format: date-time can be added
        DataTypes.JSON_TEXT: "string",
    }

    for col in table_schema["columns"]:
        col_name = col["name"]
        js_type = type_mapping.get(col["type"])
        if js_type:
            properties[col_name] = {"type": js_type}
            if col.get("description"):
                properties[col_name]["description"] = col["description"]
            if col["type"] == DataTypes.TIMESTAMP:
                properties[col_name]["format"] = "date-time" # Suggests ISO8601
        if not col["nullable"]:
            required.append(col_name)

    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required) # Sort for consistent output
    }

# Example of how one might generate the jsonschema for experiments table
# This would replace the manually crafted bigquery_schema_v1.json
# EXPERIMENTS_JSONSCHEMA = get_jsonschema_for_table("experiments")
# FOMS_JSONSCHEMA = get_jsonschema_for_table("foms")
