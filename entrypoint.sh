#!/bin/bash
set -e

show_help() {
    echo "Usage: reduce --source <source.osm.pbf> --polygon <polygon.geojson> --output <output.osm.pbf> [--overwrite] [--linestrings <linestrings.geojson>]"
    echo ""
    echo "Options:"
    echo "  --source      Input OSM PBF file"
    echo "  --polygon     GeoJSON polygon file for extraction"
    echo "  --output      Output OSM PBF file"
    echo "  --overwrite   Overwrite output file if it exists"
    echo "  --linestrings Optional GeoJSON linestrings file for reduction"
    exit 1
}

if [ "$1" != "reduce" ]; then
    echo "Error: First argument must be 'reduce'"
    show_help
fi

shift

SOURCE=""
POLYGON=""
OUTPUT=""
OVERWRITE=""
LINESTRINGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            SOURCE="$2"
            shift 2
            ;;
        --polygon)
            POLYGON="$2"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --overwrite)
            OVERWRITE="--overwrite"
            shift
            ;;
        --linestrings)
            LINESTRINGS="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

if [ -z "$SOURCE" ] || [ -z "$POLYGON" ] || [ -z "$OUTPUT" ]; then
    echo "Error: --source, --polygon, and --output are required"
    show_help
fi

if [ ! -f "$SOURCE" ]; then
    echo "Error: Source file not found: $SOURCE"
    exit 1
fi

if [ ! -f "$POLYGON" ]; then
    echo "Error: Polygon file not found: $POLYGON"
    exit 1
fi

if [ -n "$LINESTRINGS" ] && [ ! -f "$LINESTRINGS" ]; then
    echo "Error: Linestrings file not found: $LINESTRINGS"
    exit 1
fi

EXTRACTED_FILE="extracted.osm.pbf"

echo "=== Step 1: Extracting with osmium ==="
echo "Command: osmium extract -p $POLYGON $SOURCE -o $EXTRACTED_FILE $OVERWRITE"

if ! osmium extract -p "$POLYGON" "$SOURCE" -o "$EXTRACTED_FILE" $OVERWRITE; then
    echo "ERROR: osmium extract failed"
    exit 1
fi

# Verify that the extracted file was created
if [ ! -f "$EXTRACTED_FILE" ]; then
    echo "ERROR: Extraction completed but output file not found: $EXTRACTED_FILE"
    exit 1
fi

echo "✓ Extraction completed successfully"

if [ -n "$LINESTRINGS" ]; then
    echo ""
    echo "=== Step 2: Reducing with linestrings ==="
    echo "Command: python3 /app/reduce.py $EXTRACTED_FILE $LINESTRINGS $OUTPUT"

    if ! python3 /app/reduce.py "$EXTRACTED_FILE" "$LINESTRINGS" "$OUTPUT"; then
        echo "ERROR: reduce.py failed"
        exit 1
    fi

    # Verify output file was created
    if [ ! -f "$OUTPUT" ]; then
        echo "ERROR: reduce.py completed but output file not found: $OUTPUT"
        exit 1
    fi

    echo "✓ Reduction completed successfully"
else
    echo ""
    echo "=== Step 2: No linestrings specified, renaming extracted file ==="
    echo "Command: mv $EXTRACTED_FILE $OUTPUT"

    if ! mv "$EXTRACTED_FILE" "$OUTPUT"; then
        echo "ERROR: Failed to move extracted file to output location"
        exit 1
    fi

    echo "✓ File renamed successfully"
fi

echo ""
echo "=== Process completed successfully ==="
echo "Output file: $OUTPUT"