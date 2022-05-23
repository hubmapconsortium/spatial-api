CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;

SELECT postgis_version();

DROP TABLE IF EXISTS "public"."sample";
CREATE TABLE IF NOT EXISTS "public"."sample" (
    "id" SERIAL PRIMARY KEY,
    "organ_uuid" text NOT NULL,
    "organ_code" text NOT NULL,
    "donor_uuid" text NOT NULL,
    "donor_sex" text NOT NULL,
    "relative_spatial_entry_iri" text NOT NULL,
    "sample_uuid" text NOT NULL,
    "sample_hubmap_id" text NOT NULL,
    "sample_specimen_type" text NOT NULL,
    "sample_rui_location" text NOT NULL
);
-- https://gis.stackexchange.com/questions/36924/adding-geometry-column-in-postgis
-- http://www.bostongis.com/postgis_quickguide_1_4.bqg
ALTER TABLE "public"."sample" ADD COLUMN IF NOT EXISTS sample_geom geometry(MULTIPOLYGONZ,0);
ALTER TABLE "public"."sample" ALTER COLUMN sample_geom SET NOT NULL;
CREATE INDEX IF NOT EXISTS "geom_sample_index" ON "public"."sample" USING GIST(sample_geom);

-- Identify tissue samples that are registered in the spatial database by the types of cells contained within.

-- These tables (cell_annotation_details, cell_marker, cell_annotation_details_marker) come from data found in the
-- HTML annotation.l3 table under the Kidney reference for azimuth.
-- https://azimuth.hubmapconsortium.org/references/#Human%20-%20Kidney

DROP TABLE IF EXISTS "public"."cell_annotation_details";
CREATE TABLE IF NOT EXISTS "public"."cell_annotation_details" (
    "id" SERIAL PRIMARY KEY,
    -- 'cell_type_name' is the column 'Label' from the Annotation Details annotation.l3
    "cell_type_name" text NOT NULL UNIQUE,
    "obo_ontology_id_uri" text NOT NULL,
    -- JUST the OBO label from the 'obo_ontology_id_uri' but with underscores turned into spaces
    "ontology_id" text NOT NULL
);

DROP TABLE IF EXISTS "public"."cell_marker";
CREATE TABLE IF NOT EXISTS "public"."cell_marker" (
    "id" SERIAL PRIMARY KEY,
    "marker" text NOT NULL UNIQUE
);

DROP TABLE IF EXISTS "public"."cell_annotation_details_marker";
CREATE TABLE IF NOT EXISTS "public".cell_annotation_details_marker (
    cell_annotation_details_id INT REFERENCES cell_annotation_details (id),
    cell_marker_id INT REFERENCES cell_marker (id) ON DELETE CASCADE,
    CONSTRAINT cell_annotation_details_id_cell_marker_id_pkey PRIMARY KEY (cell_annotation_details_id, cell_marker_id)
);

-- This table holds a row per cell type per sample.
-- The cell information can be found in the secondary_analysis.h5ad files in the associated datasets (at the PSC)
DROP TABLE IF EXISTS "public"."cell_types";
CREATE TABLE IF NOT EXISTS "public"."cell_types" (
    "id" SERIAL PRIMARY KEY,
    "sample_uuid" text NOT NULL UNIQUE,
    "cell_annotation_details_id" SERIAL REFERENCES cell_annotation_details (id) ON DELETE CASCADE,
    "cell_type_count" BIGINT NOT NULL,
    CONSTRAINT cell_types_sample_uuid_cell_annotation_details_id_key UNIQUE (sample_uuid, cell_annotation_details_id)
);

--
-- Stored Procedures

-- Create the marker if it does not exist, but always return the marker id.
-- Note: OUT arguments are currently not supported.
CREATE OR REPLACE PROCEDURE get_cell_marker_sp (
      P_marker IN VARCHAR,
      P_id INOUT INT
      )
LANGUAGE plpgsql AS
$$
BEGIN
    INSERT INTO public.cell_marker (marker) VALUES (P_marker) ON CONFLICT DO NOTHING;
    SELECT id INTO P_id FROM public.cell_marker WHERE marker = P_marker;
END
$$;

CREATE OR REPLACE PROCEDURE create_cell_markers_sp (
    P_markers IN VARCHAR[],
    P_marker_ids INOUT INT[]
    )
LANGUAGE plpgsql AS
$$
DECLARE
    marker VARCHAR;
    marker_id INT;
BEGIN
    FOREACH marker IN ARRAY P_markers
    LOOP
        CALL get_cell_marker_sp(marker, marker_id);
        P_marker_ids = array_append(P_marker_ids, marker_id);
    END LOOP;
END
$$;

CREATE OR REPLACE PROCEDURE create_annotation_details_sp (
    P_cell_type_name IN VARCHAR,
    P_obo_ontology_id_uri IN VARCHAR,
    P_ontology_id IN VARCHAR,
    P_markers IN VARCHAR[],
    P_cell_annotation_details_id INOUT INT
    )
LANGUAGE plpgsql AS
$$
DECLARE
    cell_marker_ids INT[];
    cell_marker_id INT;
BEGIN
    INSERT INTO public.cell_annotation_details (cell_type_name, obo_ontology_id_uri, ontology_id) VALUES (P_cell_type_name, P_obo_ontology_id_uri, P_ontology_id) RETURNING id INTO P_cell_annotation_details_id;
    CALL create_cell_markers_sp(P_markers, cell_marker_ids);
    FOREACH cell_marker_id IN ARRAY cell_marker_ids
    LOOP
        INSERT INTO public.cell_annotation_details_marker (cell_annotation_details_id, cell_marker_id) VALUES (P_cell_annotation_details_id, cell_marker_id);
    END LOOP;
END
$$;

--
-- TEST DATA

DROP TABLE IF EXISTS "public"."geom_test";
CREATE TABLE IF NOT EXISTS "public"."geom_test" (
    "id" SERIAL PRIMARY KEY
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
