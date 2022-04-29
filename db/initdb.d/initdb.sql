CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;

SELECT postgis_version();

DROP TABLE IF EXISTS "public"."sample";
CREATE TABLE IF NOT EXISTS "public"."sample" (
    "id" serial,
    "organ_uuid" text NOT NULL,
    "organ_code" text NOT NULL,
    "donor_uuid" text NOT NULL,
    "donor_sex" text NOT NULL,
    "sample_uuid" text NOT NULL,
    "sample_hubmap_id" text NOT NULL,
    "sample_specimen_type" text NOT NULL,
    "sample_spatial_data" text NOT NULL,
    PRIMARY KEY ("id")
);
-- https://gis.stackexchange.com/questions/36924/adding-geometry-column-in-postgis
-- http://www.bostongis.com/postgis_quickguide_1_4.bqg
ALTER TABLE "public"."sample" ADD COLUMN IF NOT EXISTS sample_geom geometry(MULTIPOLYGONZ,0);
ALTER TABLE "public"."sample" ALTER COLUMN sample_geom SET NOT NULL;
CREATE INDEX IF NOT EXISTS "geom_sample_index" ON "public"."sample" USING GIST(sample_geom);

DROP TABLE IF EXISTS "public"."geom_test";
CREATE TABLE IF NOT EXISTS "public"."geom_test" (
    "id" serial,
    PRIMARY KEY ("id")
);
ALTER TABLE "public"."geom_test" ADD COLUMN IF NOT EXISTS geom geometry(MULTIPOLYGONZ,0);
ALTER TABLE "public"."geom_test" ALTER COLUMN geom SET NOT NULL;
CREATE INDEX IF NOT EXISTS "geom_test_index" ON "public"."geom_test" USING GIST(geom);
-- ST_IsValid only works for 2D objects
-- https://trac.osgeo.org/postgis/ticket/4364
-- ALTER TABLE "public"."geom_test" ADD CONSTRAINT "geom_valid_check" CHECK (ST_IsValid(geom));
-- Use ST_Force3D instead of ST_Force_2d which was deprecated in 2.1.0.
-- This just "tacks on" the Z if not specified, which is not what is wanted here.
-- ALTER TABLE "public"."geom_test" ALTER COLUMN geom TYPE geometry(MULTIPOLYGONZ) USING ST_Force3D(geom);

-- Load Test Data
-- This data must be seeded for the script 'run_test.sql' to be able to run.

-- 1) Create the object so that the centroid corresponds to POINT(0,0,0),
-- 2) Then Rotate (default rotation is about POINT(0,0,0),
-- 3) Then Scale, and Translate (remember when you translate you need to reduce it by the amount that you scaled).
-- NOTE: The order is IMPORTANT! You need to scale first and then translate or you get the wrong geometry.

-- https://postgis.net/docs/ST_Translate.html
-- https://postgis.net/docs/ST_GeomFromText.html
-- Create the cube (10x10x10) at the origin POINT(0,0,0) and then translate it....
INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Translate(ST_GeomFromText('MULTIPOLYGON Z(
        ((-5 -5 -5, -5 -5 5, -5 5 5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, -5 -5 5, 5 -5 5, 5 -5 -5, -5 -5 -5)),
        ((-5 5 -5, -5 5 5, 5 5 5, 5 5 -5, -5 5 -5)),
        ((-5 -5 5, -5 5 5, 5 5 5, -5 5 5, -5 -5 5)),
        ((5 -5 -5, 5 -5 5, 5 5 5, 5 5 -5, 5 -5 -5)) )'),
         15, 15, 15));

INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Translate(ST_GeomFromText('MULTIPOLYGON Z(
        ((-5 -5 -5, -5 -5 5, -5 5 5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, -5 -5 5, 5 -5 5, 5 -5 -5, -5 -5 -5)),
        ((-5 5 -5, -5 5 5, 5 5 5, 5 5 -5, -5 5 -5)),
        ((-5 -5 5, -5 5 5, 5 5 5, -5 5 5, -5 -5 5)),
        ((5 -5 -5, 5 -5 5, 5 5 5, 5 5 -5, 5 -5 -5)) )'),
         115, 15, 15));

INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Translate(ST_GeomFromText('MULTIPOLYGON Z(
        ((-5 -5 -5, -5 -5 5, -5 5 5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, -5 -5 5, 5 -5 5, 5 -5 -5, -5 -5 -5)),
        ((-5 5 -5, -5 5 5, 5 5 5, 5 5 -5, -5 5 -5)),
        ((-5 -5 5, -5 5 5, 5 5 5, -5 5 5, -5 -5 5)),
        ((5 -5 -5, 5 -5 5, 5 5 5, 5 5 -5, 5 -5 -5)) )'),
         15, 215, 15));

-- https://postgis.net/docs/ST_RotateX.html
-- https://postgis.net/docs/ST_RotateY.html
-- https://postgis.net/docs/ST_RotateZ.html
-- Since it's being rotated through 2*PI on all axis, it should be the same orientation as if it were never rotated.
-- NOTE: Modulus the round-off error.
INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Translate(ST_Scale(ST_RotateZ(ST_RotateY(ST_RotateX(ST_GeomFromText('MULTIPOLYGON Z(
        ((-5 -5 -5, -5 -5 5, -5 5 5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, -5 -5 5, 5 -5 5, 5 -5 -5, -5 -5 -5)),
        ((-5 5 -5, -5 5 5, 5 5 5, 5 5 -5, -5 5 -5)),
        ((-5 -5 5, -5 5 5, 5 5 5, -5 5 5, -5 -5 5)),
        ((5 -5 -5, 5 -5 5, 5 5 5, 5 5 -5, 5 -5 -5)) )'),
         pi()*2), pi()*2), pi()*2), 0.5, 0.5, 0.5), 7.5, 307.5, 7.5));
