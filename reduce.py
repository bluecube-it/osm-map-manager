#!/usr/bin/env python3
"""
Create a filtered OSM.PBF file based on GeoJSON geometries.
Ensures graph connectivity for OSRM/VROOM via node snapping (merging coordinates).
Matches original OSM tags to preserve road properties like speed limits and surface.
"""

import osmium
import osmium.osm as osm
from shapely.geometry import shape
import json
import sys
import os

class OSMDataExtractor(osmium.SimpleHandler):
    """
    Extracts tags and coordinates from existing Ways in the original OSM file.
    This allows us to re-apply real-world road attributes to our GeoJSON segments.
    """
    def __init__(self):
        super().__init__()
        self.nodes = {}  # Map: node_id -> (lon, lat)
        self.ways = {}   # Map: way_id -> {'tags': {...}, 'coords': [...]}

    def node(self, n):
        # Store node coordinates for geometry reconstruction
        self.nodes[n.id] = (n.location.lon, n.location.lat)

    def way(self, w):
        # Only process ways that represent roads
        if 'highway' not in w.tags:
            return

        # Reconstruct the original road geometry
        coords = []
        for node_ref in w.nodes:
            if node_ref.ref in self.nodes:
                coords.append(self.nodes[node_ref.ref])

        # Store way data if it has a valid geometry
        if len(coords) >= 2:
            self.ways[w.id] = {
                'tags': dict(w.tags),
                'coords': coords
            }

class OSMCreator:
    """
    Generates the new PBF file by injecting GeoJSON geometries as OSM objects.
    """
    def __init__(self, output_file, osm_data):
        self.writer = osmium.SimpleWriter(output_file)
        self.osm_data = osm_data
        self.node_id = 1
        self.way_id = 1
        self.node_cache = {}  # Map: rounded (lon, lat) -> node_id (for snapping)

    def find_matching_tags(self, linestring):
        """
        Attempts to find the closest original OSM way to copy its tags.
        Uses a simple coordinate intersection score.
        """
        ls_coords = [(round(c[0], 6), round(c[1], 6)) for c in linestring.coords]
        best_match_tags = None
        max_score = 0

        for way_id, data in self.osm_data.items():
            way_coords = [(round(c[0], 6), round(c[1], 6)) for c in data['coords']]
            # Intersection of coordinates to find the best matching road
            score = len(set(ls_coords) & set(way_coords))
            ratio = score / len(ls_coords)

            if ratio > max_score:
                max_score = ratio
                best_match_tags = data['tags']

        # Returns tags only if at least 50% of points match
        return best_match_tags if max_score > 0.5 else None

    def add_linestring(self, linestring):
        """Adds a GeoJSON LineString as an OSM Way with node snapping."""

        # 1. Recover original metadata (tags)
        tags = self.find_matching_tags(linestring)
        if not tags:
            # Fallback tags if no match is found
            tags = {
                'highway': 'unclassified',
                'oneway': 'no',
                'source': 'custom_geojson'
            }

        # 2. Node Management with SNAPPING
        # This is CRITICAL for VROOM: connecting segments via shared node IDs
        way_node_refs = []
        for lon, lat in linestring.coords:
            # Round to 7 decimals (~1cm precision) to fuse incident points
            coord_key = (round(lon, 7), round(lat, 7))

            if coord_key not in self.node_cache:
                # Create a new node if this coordinate hasn't been seen yet
                n = osm.mutable.Node(id=self.node_id, location=osm.Location(*coord_key))
                n.version = 1
                n.visible = True
                self.writer.add_node(n)
                self.node_cache[coord_key] = self.node_id
                self.node_id += 1

            way_node_refs.append(self.node_cache[coord_key])

        # 3. Create the Way object
        w = osm.mutable.Way(id=self.way_id, nodes=way_node_refs)
        w.tags = tags
        w.version = 1
        w.visible = True
        self.writer.add_way(w)
        self.way_id += 1

    def close(self):
        """Finalize and close the PBF writer."""
        self.writer.close()

def run_conversion(input_pbf, geojson_path, output_pbf):
    if os.path.exists(output_pbf):
        print(f"File '{output_pbf}' already exists. Overriding...")
        os.remove(output_pbf)

    # Load and parse GeoJSON
    print(f"Loading geometries from {geojson_path}...")
    with open(geojson_path, 'r') as f:
        gj_data = json.load(f)

    # Handle both FeatureCollection and single Feature
    features = gj_data['features'] if gj_data['type'] == 'FeatureCollection' else [gj_data]
    linestrings = []
    for f in features:
        geom = shape(f['geometry'])
        if geom.geom_type == 'LineString':
            linestrings.append(geom)
        elif geom.geom_type == 'MultiLineString':
            linestrings.extend(geom.geoms)

    # Step 1: Extract tags from the original source
    print(f"Reading {input_pbf} to extract road tags...")
    extractor = OSMDataExtractor()
    # locations=False since we handle geometry reconstruction manually
    extractor.apply_file(input_pbf, locations=False)

    # Step 2: Write the filtered PBF
    print(f"Creating {output_pbf} with {len(linestrings)} custom segments...")
    creator = OSMCreator(output_pbf, extractor.ways)
    for ls in linestrings:
        creator.add_linestring(ls)

    creator.close()
    print("✓ Filtered OSM PBF created successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <input.osm.pbf> <routes.geojson> <output.osm.pbf>")
    else:
        run_conversion(sys.argv[1], sys.argv[2], sys.argv[3])