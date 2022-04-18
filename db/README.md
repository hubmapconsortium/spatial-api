# Various database scripts

## create_tables.sql

Load the appropriate extensions and define the appropriate tables, metadata fields, and geometric data fields.

## load_test_data.sql

Load data contrived to provide results from simple queries.

## run_test.sql

Run queries to determine if the contrived geometeries return the expected results.
The results of the Pythagorean Theorem used to determing the appropriate radius
from a point are shown and are used in the queries.

## Translating, scaling, and rotating geometries

Shifting, scaling, and rotating constitute affine transformations on a plane.
PostGIS has (2D) built-in functions to perform all three: ST_Translate, ST_Scale, and ST_Rotate.
All three fall under the umbrella function ST_Affine (rarely used directly) that lets you explicitly specify the transformation matrix.

### Rotate a geometry

ST_Rotate, ST_RotateX, ST_RotateY, and ST_RotateZ are used to rotate a geometry around the X, Y, or Z axis in radian units.
ST_Rotate and ST_RotateZ are exactly the same because the default axis rotation is Z for 2D applications.
These functions are rarely used in isolation because their default behavior is to rotate the geometry around the origin
rather than about the centroid. ST_Rotate is almost always combined with two translations to achieve rotation about the centroid;
an example is shown in the following listing, and the results are diagrammed in figure 8.9. 