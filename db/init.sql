-- https://download.osgeo.org/postgis/docs/postgis-3.0.5.pdf
--
-- Enable PostGIS (as of 3.0 contains just geometry/geography)
CREATE EXTENSION postgis;
-- enable raster support (for 3+)
CREATE EXTENSION postgis_raster;
-- Enable Topology
CREATE EXTENSION postgis_topology;
-- Enable PostGIS Advanced 3D
-- and other geoprocessing algorithms
-- sfcgal not available with all distributions
CREATE EXTENSION postgis_sfcgal;
-- fuzzy matching needed for Tiger
CREATE EXTENSION fuzzystrmatch;
CREATE EXTENSION postgis_tiger_geocoder;
-- if you installed with pcre
-- you should have address standardizer extension as well
CREATE EXTENSION address_standardizer;
