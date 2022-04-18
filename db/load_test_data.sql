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

-- http://postgis.net/docs/manual-2.0/ST_Scale.html
--INSERT INTO "public"."geom_test" (geom)
--  VALUES (ST_Translate(ST_Scale(ST_GeomFromText('MULTIPOLYGON Z(
--        ((-5 -5 -5, -5 -5 5, -5 5 5, -5 5 -5, -5 -5 -5)),
--        ((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5)),
--        ((-5 -5 -5, -5 -5 5, 5 -5 5, 5 -5 -5, -5 -5 -5)),
--        ((-5 5 -5, -5 5 5, 5 5 5, 5 5 -5, -5 5 -5)),
--        ((-5 -5 5, -5 5 5, 5 5 5, -5 5 5, -5 -5 5)),
--        ((5 -5 -5, 5 -5 5, 5 5 5, 5 5 -5, 5 -5 -5)) )'),
--         0.5, 0.5, 0.5), 7.5, 307.5, 7.5));

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

-- http://postgis.net/docs/manual-2.0/ST_Affine.html
-- ST_Scale(geomA, XFactor, YFactor, ZFactor) => ST_Affine(geomA, XFactor, 0, 0, 0, YFactor, 0, 0, 0, ZFactor, 0, 0, 0)
-- ST_Translate(geomA, XFactor, YFactor, ZFactor) => ST_Affine(geomA, 0, 0, 0, 0, 0, 0, 0, 0, 0, XFactor, YFactor, ZFactor)
-- NOTE: That the output of this "translate then scale" using AT_Affine matches the one above when you look in the database.
-- NOTE: This should produce the same geometry as the above.
--INSERT INTO "public"."geom_test" (geom)
--  VALUES (ST_Affine(ST_GeomFromText('MULTIPOLYGON Z(
--        ((-5 -5 -5, -5 -5 5, -5 5 5, -5 5 -5, -5 -5 -5)),
--        ((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5)),
--        ((-5 -5 -5, -5 -5 5, 5 -5 5, 5 -5 -5, -5 -5 -5)),
--        ((-5 5 -5, -5 5 5, 5 5 5, 5 5 -5, -5 5 -5)),
--        ((-5 -5 5, -5 5 5, 5 5 5, -5 5 5, -5 -5 5)),
--        ((5 -5 -5, 5 -5 5, 5 5 5, 5 5 -5, 5 -5 -5)) )'),
--         0.5, 0, 0, 0,  0.5, 0, 0, 0,  0.5, 15, 315, 15));
-- ST_Affine(geom, a, b, c, d,  e, f, g, h,  i, xoff, yoff, zoff)
