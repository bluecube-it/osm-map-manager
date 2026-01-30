# OSM Map Manager

Docker image for extracting and filtering OSM PBF files using osmium and a custom Python script that preserves road attributes while ensuring graph connectivity for routing engines like OSRM/VROOM.

## Features

- **Polygon-based extraction**: Extract OSM data within a specific geographic boundary
- **LineString filtering**: Create custom road networks from GeoJSON geometries
- **Tag preservation**: Maintains original OSM road attributes (speed limits, surface types, etc.)
- **Graph connectivity**: Ensures proper node snapping for routing engine compatibility
- **Flexible workflow**: Use extraction only, or combine with custom linestring filtering

## Build

```bash
docker build -t osm-map-manager .
```

## Usage

### Basic extraction (polygon only)

Extract OSM data within a polygon boundary:

```bash
docker run --rm \
  -v /path/to/data:/tmp \
  osm-map-manager reduce \
  --source /tmp/sourceMap.osm.pbf \
  --polygon /tmp/polygon.geojson \
  --output /tmp/destinationMap.osm.pbf \
  --overwrite
```

### Advanced filtering (extraction + linestring filtering)

Extract and filter to specific road segments while preserving OSM attributes:

```bash
docker run --rm \
  -v /path/to/data:/tmp \
  osm-map-manager reduce \
  --source /tmp/sourceMap.osm.pbf \
  --polygon /tmp/polygon.geojson \
  --output /tmp/destinationMap.osm.pbf \
  --linestrings /tmp/lineStrings.geojson \
  --overwrite
```

## Parameters

- `--source` **(required)**: Input OSM PBF file
- `--polygon` **(required)**: GeoJSON polygon file defining the extraction area
- `--output` **(required)**: Output OSM PBF file path
- `--overwrite` *(optional)*: Overwrite the output file if it already exists
- `--linestrings` *(optional)*: GeoJSON file with LineString/MultiLineString geometries for custom filtering

## How It Works

### Step 1: Polygon Extraction
Uses `osmium extract` to extract OSM data within the polygon boundary.

### Step 2: LineString Filtering (Optional)
If `--linestrings` is provided, the `reduce.py` script:
1. Reads the extracted OSM PBF file to analyze existing road tags
2. Processes the GeoJSON linestrings
3. Matches linestrings to original OSM ways to preserve attributes
4. Creates new OSM nodes with coordinate snapping (7 decimal precision)
5. Generates a filtered PBF with proper graph connectivity for routing

### Step 3: Output
Produces the final OSM PBF file ready for use with routing engines like OSRM or VROOM.

## Technical Details

### Node Snapping
The reduce.py script implements coordinate rounding to 7 decimal places (~1cm precision) to ensure that road segments share nodes where they connect, which is critical for routing graph connectivity.

### Tag Matching
The script attempts to match custom linestrings with original OSM ways based on coordinate overlap. If a match is found (>50% overlap), the original tags are preserved. Otherwise, fallback tags are applied.

### Supported Geometries
- LineString
- MultiLineString (automatically expanded to individual LineStrings)

## Requirements

All dependencies are included in the Docker image:
- osmium-tool (for polygon extraction)
- Python 3 with osmium and shapely libraries (for linestring filtering)

## Notes

- All file paths should be accessible via volume mounting
- The `/tmp` directory is the standard path used within the container
- Input files must exist before running the command
- GeoJSON files must use valid geometry types (Polygon for extraction, LineString/MultiLineString for filtering)