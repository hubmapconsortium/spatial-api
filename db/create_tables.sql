CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;

SELECT postgis_version();

CREATE TABLE IF NOT EXISTS "public"."sample" (
    "id" serial,
    "uuid" text NOT NULL,
    "hubmap_id" text NOT NULL,
    "organ_uuid" text NOT NULL,
    "organ_organ" text NOT NULL,
    PRIMARY KEY ("id")
);
-- https://gis.stackexchange.com/questions/36924/adding-geometry-column-in-postgis
ALTER TABLE "public"."sample" ADD COLUMN IF NOT EXISTS geom geometry(MULTIPOLYGONZ,0);
CREATE INDEX IF NOT EXISTS "geom_sample_index" ON "public"."sample" USING GIST ( "geom" );

DROP TABLE IF EXISTS "public"."geom_test";
CREATE TABLE IF NOT EXISTS "public"."geom_test" (
    "id" serial,
    PRIMARY KEY ("id")
);
ALTER TABLE "public"."geom_test" ADD COLUMN IF NOT EXISTS geom geometry(MULTIPOLYGONZ,0);
CREATE INDEX IF NOT EXISTS "geom_test_index" ON "public"."geom_test" USING GIST ( "geom" );
-- ST_IsValid only works for 2D objects
-- https://trac.osgeo.org/postgis/ticket/4364
-- ALTER TABLE "public"."geom_test" ADD CONSTRAINT "geom_valid_check" CHECK (ST_IsValid(geom));
-- Use ST_Force3D instead of ST_Force_2d which was deprecated in 2.1.0.
-- This just "tacks on" the Z if not specified, which is not what is wanted here.
-- ALTER TABLE "public"."geom_test" ALTER COLUMN geom TYPE geometry(MULTIPOLYGONZ) USING ST_Force3D(geom);
