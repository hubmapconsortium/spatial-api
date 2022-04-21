
-- https://postgis.net/docs/ST_3DDistance.html
-- https://postgis.net/docs/ST_GeomFromText.html
--SELECT id FROM "public"."geom_test"
--   WHERE ST_3DDistance(geom, ST_GeomFromText('POINTZ(1 1 1)')) < 5;

-- https://postgis.net/docs/ST_3DDWithin.html

-- sqrt(10^2 + 10^2 + 10^2) = 17.321
SELECT id FROM "public"."geom_test"
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 17.32);

SELECT id FROM "public"."geom_test"
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 17.321);

-- sqrt(110^2 + 10^2 + 10^2) = 110.91
SELECT id FROM "public"."geom_test"
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 110.9);

SELECT id FROM "public"."geom_test"
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 110.91);

-- sqrt(210^2 + 10^2 + 10^2) = 210.476
SELECT id FROM "public"."geom_test"
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 210.475);

SELECT id FROM "public"."geom_test"
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 210.476);

-- Only works for 2D :-(
SELECT ST_AsText(ST_centroid(geom)) FROM "public"."geom_test";

-- Yes, these should be closed!
SELECT ST_IsClosed(geom) FROM "public"."geom_test";

-- https://postgis.net/docs/ST_PointOnSurface.html
-- ST_AsText is the reverse of ST_GeomFromText.
WITH test AS (SELECT geom from "public"."geom_test" WHERE id = 1)
SELECT ST_AsEWKT(ST_PointOnSurface(geom)) median
FROM test;
