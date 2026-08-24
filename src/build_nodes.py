import json
import csv
from pathlib import Path


# --------------------------------------------------
# 1. Define project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "probe_counts"
    / "geojson"
    / "new_delhi__2024-08-11_to_2024-08-11_.geojson"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "nodes.csv"
)


# --------------------------------------------------
# 2. Load the GeoJSON file
# --------------------------------------------------

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    geojson_data = json.load(file)


# --------------------------------------------------
# 3. Store unique nodes
# --------------------------------------------------

node_map = {}

next_node_id = 1


# --------------------------------------------------
# 4. Process every feature
# --------------------------------------------------

for feature in geojson_data["features"]:

    geometry = feature.get("geometry")

    # Skip features without geometry
    if geometry is None:
        continue

    # We only want road LineStrings
    if geometry.get("type") != "LineString":
        continue

    coordinates = geometry.get("coordinates")

    # Skip invalid LineStrings
    if not coordinates or len(coordinates) < 2:
        continue

    # Extract endpoints
    start_coord = tuple(coordinates[0])
    end_coord = tuple(coordinates[-1])

    # Add start node if it doesn't exist
    if start_coord not in node_map:
        node_map[start_coord] = next_node_id
        next_node_id += 1

    # Add end node if it doesn't exist
    if end_coord not in node_map:
        node_map[end_coord] = next_node_id
        next_node_id += 1


# --------------------------------------------------
# 5. Create processed folder if needed
# --------------------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 6. Write nodes.csv
# --------------------------------------------------

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:

    writer = csv.writer(file)

    writer.writerow([
        "node_id",
        "longitude",
        "latitude"
    ])

    for coordinate, node_id in node_map.items():

        longitude, latitude = coordinate

        writer.writerow([
            node_id,
            longitude,
            latitude
        ])


print("Nodes created successfully!")
print(f"Total unique nodes: {len(node_map)}")
print(f"Output file: {OUTPUT_FILE}")