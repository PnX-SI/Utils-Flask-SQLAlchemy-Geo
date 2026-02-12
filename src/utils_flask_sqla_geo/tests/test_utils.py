import json
import pytest
from unittest.mock import Mock, MagicMock
from geoalchemy2 import WKBElement
from shapely.geometry import Point, LineString
from shapely import to_wkb

from utils_flask_sqla_geo.utilsgeometry import valid_GeoJSON, parse_geom, rows_to_geojson

# Assuming the functions are in a module called 'geo_utils'
# from geo_utils import validGeoJSON, parseGeom, rows_to_geojson


class TestValidGeoJSON:
    """Tests for validGeoJSON function"""

    def test_valid_geojson_point(self):
        """Test with valid Point GeoJSON"""
        geojson = {"type": "Point", "coordinates": [100.0, 0.0]}
        result = valid_GeoJSON(geojson)
        assert result == geojson

    def test_valid_geojson_linestring(self):
        """Test with valid LineString GeoJSON"""
        geojson = {"type": "LineString", "coordinates": [[100.0, 0.0], [101.0, 1.0]]}
        result = valid_GeoJSON(geojson)
        assert result == geojson

    def test_missing_coordinates(self):
        """Test that missing coordinates raises ValueError"""
        geojson = {"type": "Point"}
        with pytest.raises(ValueError, match="Not a valid GeoJSON"):
            valid_GeoJSON(geojson)

    def test_missing_type(self):
        """Test that missing type raises ValueError"""
        geojson = {"coordinates": [100.0, 0.0]}
        with pytest.raises(ValueError, match="Not a valid GeoJSON"):
            valid_GeoJSON(geojson)

    def test_empty_dict(self):
        """Test that empty dict raises ValueError"""
        with pytest.raises(ValueError, match="Not a valid GeoJSON"):
            valid_GeoJSON({})


from unittest.mock import Mock, patch


class TestParseGeom:
    """Tests for parseGeom function"""

    def test_wkbelement_input(self):
        """Test parsing WKBElement"""
        point = Point(100.0, 0.0)
        wkb = to_wkb(point)
        result = parse_geom(wkb)
        assert isinstance(result, dict)
        assert result["type"] == "Point"
        assert result["coordinates"] == [100.0, 0.0]

    def test_dict_input_valid(self):
        """Test parsing valid GeoJSON dict"""
        geojson = {"type": "Point", "coordinates": [100.0, 0.0]}
        result = parse_geom(geojson)
        assert result == geojson

    def test_dict_input_invalid(self):
        """Test parsing invalid GeoJSON dict"""
        geojson = {"invalid": "data"}
        with pytest.raises(ValueError, match="Not a valid GeoJSON"):
            parse_geom(geojson)

    def test_string_input_valid(self):
        """Test parsing valid GeoJSON string"""
        geojson_str = '{"type": "Point", "coordinates": [100.0, 0.0]}'
        result = parse_geom(geojson_str)
        assert result["type"] == "Point"
        assert result["coordinates"] == [100.0, 0.0]

    def test_string_input_invalid_json(self):
        """Test parsing invalid JSON string"""
        invalid_json = '{"type": "Point", invalid}'
        with pytest.raises(ValueError, match="Not a valid JSON"):
            parse_geom(invalid_json)

    def test_string_input_invalid_geojson(self):
        """Test parsing JSON string that's not valid GeoJSON"""
        invalid_geojson = '{"invalid": "data"}'
        with pytest.raises(ValueError, match="Not a valid GeoJSON"):
            parse_geom(invalid_geojson)

    def test_invalid_type_input(self):
        """Test parsing unsupported type"""
        with pytest.raises(ValueError, match="Not a valid type of geometry"):
            parse_geom(123)

        with pytest.raises(ValueError, match="Not a valid type of geometry"):
            parse_geom([1, 2, 3])


class TestRowsToGeoJSON:
    """Tests for rows_to_geojson function"""

    def test_single_row_with_geometry(self):
        """Test converting single row with geometry"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "name": "Test Point",
            "id": 1,
        }

        result = rows_to_geojson([mock_row], "geom")

        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1
        assert result["features"][0]["type"] == "Feature"
        assert result["features"][0]["geometry"]["type"] == "Point"
        assert result["features"][0]["properties"]["name"] == "Test Point"
        assert result["features"][0]["properties"]["id"] == 1
        assert "geom" not in result["features"][0]["properties"]

    def test_multiple_rows(self):
        """Test converting multiple rows"""
        mock_row1 = Mock()
        mock_row1._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "name": "Point 1",
        }

        mock_row2 = Mock()
        mock_row2._mapping = {
            "geom": {"type": "Point", "coordinates": [101.0, 1.0]},
            "name": "Point 2",
        }

        result = rows_to_geojson([mock_row1, mock_row2], "geom")

        assert len(result["features"]) == 2
        assert result["features"][0]["properties"]["name"] == "Point 1"
        assert result["features"][1]["properties"]["name"] == "Point 2"

    def test_row_without_geometry(self):
        """Test converting row without geometry field"""
        mock_row = Mock()
        mock_row._mapping = {"name": "No Geometry", "id": 1}

        result = rows_to_geojson([mock_row], "geom")

        assert len(result["features"]) == 1
        assert result["features"][0]["geometry"] is None
        assert result["features"][0]["properties"]["name"] == "No Geometry"

    def test_empty_rows(self):
        """Test converting empty list of rows"""
        result = rows_to_geojson([], "geom")

        assert result["type"] == "FeatureCollection"
        assert result["features"] == []

    def test_row_with_null_geometry(self):
        """Test converting row with null geometry"""
        mock_row = Mock()
        mock_row._mapping = {"geom": None, "name": "Null Geometry"}

        result = rows_to_geojson([mock_row], "geom")

        assert result["features"][0]["geometry"] is None

    def test_row_with_string_geometry(self):
        """Test converting row with geometry as string"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": '{"type": "Point", "coordinates": [100.0, 0.0]}',
            "name": "String Geometry",
        }

        result = rows_to_geojson([mock_row], "geom")

        assert result["features"][0]["geometry"]["type"] == "Point"
        assert result["features"][0]["geometry"]["coordinates"] == [100.0, 0.0]

    def test_properties_exclude_geometry_field(self):
        """Test that geometry field is excluded from properties"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "prop1": "value1",
            "prop2": "value2",
        }

        result = rows_to_geojson([mock_row], "geom")

        properties = result["features"][0]["properties"]
        assert "geom" not in properties
        assert "prop1" in properties
        assert "prop2" in properties

    def test_unnest_properties_with_dot_separator(self):
        """Test nesting properties with dot separator"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "last_validation.date": "2022-01-01",
            "last_validation.cd_nomenclature": "2",
            "name": "Test Point",
        }

        result = rows_to_geojson([mock_row], "geom", nest_properties=True)

        properties = result["features"][0]["properties"]
        assert "last_validation" in properties
        assert isinstance(properties["last_validation"], dict)
        assert properties["last_validation"]["date"] == "2022-01-01"
        assert properties["last_validation"]["cd_nomenclature"] == "2"
        assert properties["name"] == "Test Point"

    def test_unnest_properties_false(self):
        """Test that unnest=False keeps properties flat"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "last_validation.date": "2022-01-01",
            "last_validation.cd_nomenclature": "2",
        }

        result = rows_to_geojson([mock_row], "geom", nest_properties=False)

        properties = result["features"][0]["properties"]
        assert "last_validation.date" in properties
        assert "last_validation.cd_nomenclature" in properties
        assert "last_validation" not in properties

    def test_unnest_with_custom_separator(self):
        """Test unnesting with custom prefix separator"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "validation_date": "2022-01-01",
            "validation_code": "2",
        }

        result = rows_to_geojson(
            [mock_row], "geom", nest_properties=True, nesting_prefix_separator="_"
        )

        properties = result["features"][0]["properties"]
        assert "validation" in properties
        assert isinstance(properties["validation"], dict)
        assert properties["validation"]["date"] == "2022-01-01"
        assert properties["validation"]["code"] == "2"

    def test_unnest_mixed_properties(self):
        """Test unnesting with mix of nested and non-nested properties"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "metadata.author": "John",
            "metadata.date": "2022-01-01",
            "id": 1,
            "name": "Test",
        }

        result = rows_to_geojson([mock_row], "geom", nest_properties=True)

        properties = result["features"][0]["properties"]
        assert "metadata" in properties
        assert properties["metadata"]["author"] == "John"
        assert properties["metadata"]["date"] == "2022-01-01"
        assert properties["id"] == 1
        assert properties["name"] == "Test"

    def test_unnest_multiple_prefixes(self):
        """Test unnesting with multiple different prefixes"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "user.name": "Alice",
            "user.id": 123,
            "location.city": "Paris",
            "location.country": "France",
        }

        result = rows_to_geojson([mock_row], "geom", nest_properties=True)

        properties = result["features"][0]["properties"]
        assert "user" in properties
        assert properties["user"]["name"] == "Alice"
        assert properties["user"]["id"] == 123
        assert "location" in properties
        assert properties["location"]["city"] == "Paris"
        assert properties["location"]["country"] == "France"

    def test_unnest_with_multiple_dots(self):
        """Test nesting only splits on first dot"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "deep.nested.value": "test",
        }

        result = rows_to_geojson([mock_row], "geom", nest_properties=True)

        properties = result["features"][0]["properties"]
        assert "deep" in properties
        assert properties["deep"]["nested.value"] == "test"

    def test_unnest_excludes_geometry_field(self):
        """Test that geometry field is excluded even with nest_properties=True"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "data.field1": "value1",
            "data.field2": "value2",
        }

        result = rows_to_geojson([mock_row], "geom", nest_properties=True)

        properties = result["features"][0]["properties"]
        assert "geom" not in properties
        assert "data" in properties

    def test_add_id_in_properties(self):
        """Test unnesting with mix of nested and non-nested properties"""
        mock_row = Mock()
        mock_row._mapping = {
            "geom": {"type": "Point", "coordinates": [100.0, 0.0]},
            "metadata.author": "John",
            "metadata.date": "2022-01-01",
            "id": 1,
            "name": "Test",
        }

        result = rows_to_geojson([mock_row], "geom", nest_properties=True, id_field="id")

        properties = result["features"][0]
        assert "id" in properties
        assert properties["id"] == 1
