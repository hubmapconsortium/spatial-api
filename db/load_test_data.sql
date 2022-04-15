-- https://postgis.net/docs/ST_GeomFromText.html
INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_GeomFromText('MULTIPOLYGON Z(
        ((10 10 10, 10 10 20, 10 20 20, 10 20 10, 10 10 10)),
        ((10 10 10, 20 10 10, 20 20 10, 10 20 10, 10 10 10)),
        ((10 10 10, 10 10 20, 20 10 20, 20 10 10, 10 10 10)),
        ((10 20 10, 10 20 20, 20 20 20, 20 20 10, 10 20 10)),
        ((10 10 20, 10 20 20, 20 20 20, 10 20 20, 10 10 20)),
        ((20 10 10, 20 10 20, 20 20 20, 20 20 10, 20 10 10)) )', 0));

-- https://postgis.net/docs/ST_Translate.html
INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Translate(ST_GeomFromText('MULTIPOLYGON Z(
        ((10 10 10, 10 10 20, 10 20 20, 10 20 10, 10 10 10)),
        ((10 10 10, 20 10 10, 20 20 10, 10 20 10, 10 10 10)),
        ((10 10 10, 10 10 20, 20 10 20, 20 10 10, 10 10 10)),
        ((10 20 10, 10 20 20, 20 20 20, 20 20 10, 10 20 10)),
        ((10 10 20, 10 20 20, 20 20 20, 10 20 20, 10 10 20)),
        ((20 10 10, 20 10 20, 20 20 20, 20 20 10, 20 10 10)) )'),
         100, 0, 0));

INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Translate(ST_GeomFromText('MULTIPOLYGON Z(
        ((10 10 10, 10 10 20, 10 20 20, 10 20 10, 10 10 10)),
        ((10 10 10, 20 10 10, 20 20 10, 10 20 10, 10 10 10)),
        ((10 10 10, 10 10 20, 20 10 20, 20 10 10, 10 10 10)),
        ((10 20 10, 10 20 20, 20 20 20, 20 20 10, 10 20 10)),
        ((10 10 20, 10 20 20, 20 20 20, 10 20 20, 10 10 20)),
        ((20 10 10, 20 10 20, 20 20 20, 20 20 10, 20 10 10)) )'),
         0, 200, 0));

-- http://postgis.net/docs/manual-2.0/ST_Scale.html
-- NOTE: The order is IMPORTANT! You need to scale first and then translate or you get the wrong geometry.
INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Translate(ST_Scale(ST_GeomFromText('MULTIPOLYGON Z(
        ((10 10 10, 10 10 20, 10 20 20, 10 20 10, 10 10 10)),
        ((10 10 10, 20 10 10, 20 20 10, 10 20 10, 10 10 10)),
        ((10 10 10, 10 10 20, 20 10 20, 20 10 10, 10 10 10)),
        ((10 20 10, 10 20 20, 20 20 20, 20 20 10, 10 20 10)),
        ((10 10 20, 10 20 20, 20 20 20, 10 20 20, 10 10 20)),
        ((20 10 10, 20 10 20, 20 20 20, 20 20 10, 20 10 10)) )'),
         0.5, 0.5, 0.5), 0, 300, 0));

-- http://postgis.net/docs/manual-2.0/ST_Affine.html
-- ST_Scale(geomA, XFactor, YFactor, ZFactor) => ST_Affine(geomA, XFactor, 0, 0, 0, YFactor, 0, 0, 0, ZFactor, 0, 0, 0)
-- ST_Translate(geomA, XFactor, YFactor, ZFactor) => ST_Affine(geomA, 0, 0, 0, 0, 0, 0, 0, 0, 0, XFactor, YFactor, ZFactor)
-- NOTE: That the output of this "translate then scale" using AT_Affine matches the one above when you look in the database.
INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Affine(ST_GeomFromText('MULTIPOLYGON Z(
        ((10 10 10, 10 10 20, 10 20 20, 10 20 10, 10 10 10)),
        ((10 10 10, 20 10 10, 20 20 10, 10 20 10, 10 10 10)),
        ((10 10 10, 10 10 20, 20 10 20, 20 10 10, 10 10 10)),
        ((10 20 10, 10 20 20, 20 20 20, 20 20 10, 10 20 10)),
        ((10 10 20, 10 20 20, 20 20 20, 10 20 20, 10 10 20)),
        ((20 10 10, 20 10 20, 20 20 20, 20 20 10, 20 10 10)) )'),
         0.5, 0, 0, 0, 0.5, 0, 0, 0, 0.5, 0, 300, 0));

-- https://postgis.net/docs/ST_RotateX.html
-- ST_RotateX(geomA, rotRadians) => ST_Affine(geomA, 1, 0, 0, 0, cos(rotRadians), -sin(rotRadians), 0, sin(rotRadians), cos(rotRadians), 0, 0, 0)
-- https://postgis.net/docs/ST_RotateY.html
-- ST_RotateY(geomA, rotRadians) is short-hand for ST_Affine(geomA, cos(rotRadians), 0, sin(rotRadians), 0, 1, 0, -sin(rotRadians), 0, cos(rotRadians), 0, 0, 0)
-- https://postgis.net/docs/ST_RotateZ.html
-- ST_RotateZ(geomA, rotRadians) is short-hand for SELECT ST_Affine(geomA, cos(rotRadians), -sin(rotRadians), 0, sin(rotRadians), cos(rotRadians), 0, 0, 0, 1, 0, 0, 0)

-- http://postgis.net/docs/manual-2.0/ST_Rotate.html

-- https://postgis.net/docs/ST_Centroid.html
