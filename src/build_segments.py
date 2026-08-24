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

NODES_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "nodes.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "segments.csv"
)


# --------------------------------------------------
# 2. Load nodes.csv
# --------------------------------------------------

coordinate_to_node = {}

with open(NODES_FILE, "r", encoding="utf-8") as file:

    reader = csv.DictReader(file)

    for row in reader:

        coordinate = (
            float(row["longitude"]),
            float(row["latitude"])
        )

        node_id = int(row["node_id"])

        coordinate_to_node[coordinate] = node_id


# --------------------------------------------------
# 3. Load GeoJSON
# --------------------------------------------------

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    geojson_data = json.load(file)


# --------------------------------------------------
# 4. Create processed folder if needed
# --------------------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 5. Create segments.csv
# --------------------------------------------------

segment_count = 0

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    # CSV header
    writer.writerow([
        "segment_id",
        "new_segment_id",
        "from_node",
        "to_node",
        "distance",
        "speed_limit",
        "frc",
        "street_name"
    ])


    # ----------------------------------------------
    # Process every GeoJSON feature
    # ----------------------------------------------

    for feature in geojson_data["features"]:

        geometry = feature.get("geometry")

        # Skip Feature 0 / features without geometry
        if geometry is None:
            continue

        # Only process LineStrings
        if geometry.get("type") != "LineString":
            continue

        coordinates = geometry.get("coordinates")

        # Skip invalid geometry
        if not coordinates or len(coordinates) < 2:
            continue


        # ------------------------------------------
        # Find the two graph nodes
        # ------------------------------------------

        start_coord = tuple(coordinates[0])
        end_coord = tuple(coordinates[-1])

        from_node = coordinate_to_node.get(start_coord)
        to_node = coordinate_to_node.get(end_coord)


        # Safety check
        if from_node is None or to_node is None:

            print(
                f"Warning: Node not found for feature "
                f"{segment_count + 1}"
            )

            continue


        # ------------------------------------------
        # Extract road metadata
        # ------------------------------------------

        properties = feature.get("properties", {})

        segment_id = properties.get("segmentId")
        new_segment_id = properties.get("newSegmentId")
        distance = properties.get("distance")
        speed_limit = properties.get("speedLimit")
        frc = properties.get("frc")
        street_name = properties.get("streetName")


        # ------------------------------------------
        # Write one road segment
        # ------------------------------------------

        writer.writerow([
            segment_id,
            new_segment_id,
            from_node,
            to_node,
            distance,
            speed_limit,
            frc,
            street_name
        ])

        segment_count += 1


# --------------------------------------------------
# 6. Print summary
# --------------------------------------------------

print("Segments created successfully!")
print(f"Total segments: {segment_count}")
print(f"Output file: {OUTPUT_FILE}")