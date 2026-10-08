"""Small helpers that build test files on the fly (no binary fixtures in git)."""
import io
import zipfile

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon

KML_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Plot A</name>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>
        77.5900,12.9700 77.5910,12.9700 77.5910,12.9710 77.5900,12.9710 77.5900,12.9700
      </coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
    <Placemark>
      <name>Road B</name>
      <LineString><coordinates>77.5900,12.9700 77.5920,12.9720</coordinates></LineString>
    </Placemark>
    <Placemark>
      <name>Gate C</name>
      <Point><coordinates>77.5905,12.9705</coordinates></Point>
    </Placemark>
  </Document>
</kml>"""


def make_shapefile_zip(tmp_path, crs="EPSG:4326") -> bytes:
    # a shapefile can only hold one geometry type, so this one is all polygons
    gdf = gpd.GeoDataFrame(
        {
            "name": ["Plot A", "Plot B", "Plot C"],
            "owner": ["Ravi", None, "Meena"],
        },
        geometry=[
            Polygon([(77.59, 12.97), (77.591, 12.97), (77.591, 12.971), (77.59, 12.971)]),
            Polygon([(77.60, 12.97), (77.601, 12.97), (77.601, 12.971)]),
            MultiPolygon(
                [
                    Polygon([(77.61, 12.97), (77.611, 12.97), (77.611, 12.971)]),
                    Polygon([(77.62, 12.97), (77.621, 12.97), (77.621, 12.971)]),
                ]
            ),
        ],
        crs=crs,
    )
    folder = tmp_path / "shp_build"
    folder.mkdir()
    gdf.to_file(folder / "survey.shp")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for f in folder.iterdir():
            zf.write(f, arcname=f.name)
    return buf.getvalue()