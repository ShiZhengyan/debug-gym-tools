import json
import sys
import os

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Get the JSON file path from command line arguments
if len(sys.argv) > 1:
    json_path = sys.argv[1]
    # If relative path is provided, make it absolute from the current working directory
    if not os.path.isabs(json_path):
        json_path = os.path.join(os.getcwd(), json_path)
else:
    print("Usage: python app.py <path_to_json_file>")
    sys.exit(1)

# Load the JSON file
try:
    with open(json_path, "r") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Error: File not found - {json_path}")
    sys.exit(1)
except PermissionError:
    print(f"Error: Permission denied - {json_path}")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"Error: Invalid JSON file - {json_path}")
    sys.exit(1)


def to_pretty_json(value):
    return json.dumps(value, sort_keys=True, indent=4, separators=(",", ": "))


app.jinja_env.filters["tojson_pretty"] = to_pretty_json


@app.route("/")
def index():
    # Pass metadata to the template
    metadata = {
        "problem": data["problem"],
        "config": data["config"],
        "uuid": data["uuid"],
        "success": data["success"],
    }
    total_steps = len(data["log"])
    return render_template("index.html", metadata=metadata, total_steps=total_steps)


@app.route("/get_step/<int:step_id>")
def get_step(step_id):
    # Return the specific step data as JSON
    if 0 <= step_id < len(data["log"]):
        step = data["log"][step_id]
        return jsonify(step)
    return jsonify({"error": "Step not found"}), 404


if __name__ == "__main__":
    print(f"Viewing debug data from: {json_path}")
    app.run(host="0.0.0.0", debug=True)