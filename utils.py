from passlib.context import CryptContext
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from geoalchemy2.elements import WKTElement
from shapely.geometry import Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def to_wkt(geometry, geom_type):
    if geom_type == "POINT":
        return WKTElement(Point(geometry).wkt, srid=4326)
    elif geom_type == "LINESTRING":
        return WKTElement(LineString(geometry).wkt, srid=4326)
    elif geom_type == "POLYGON":
        return WKTElement(Polygon(geometry).wkt, srid=4326)
    elif geom_type == "MULTIPOINT":
        return WKTElement(MultiPoint(geometry).wkt, srid=4326)
    elif geom_type == "MULTILINESTRING":
        return WKTElement(MultiLineString(geometry).wkt, srid=4326)
    elif geom_type == "MULTIPOLYGON":
        return WKTElement(MultiPolygon(geometry).wkt, srid=4326)
    else:
        raise ValueError("Unsupported geometry type")


def geometry_to_geojson(wkt_element):
    shape = to_shape(wkt_element)
    return mapping(shape)