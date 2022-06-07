
--SELECT sample_hubmap_id, sample_uuid
--FROM public.sample
--WHERE sample.relative_spatial_entry_iri = 'VHFemale'
--AND ST_3DDWithin(sample_geom, ST_GeomFromText('POINTZ(23 18 5)'), 200.0);
--
--SELECT sample_hubmap_id
--FROM public.sample
--INNER JOIN public.cell_types
--ON sample.sample_uuid = cell_types.sample_uuid
--INNER JOIN public.cell_annotation_details
--ON cell_annotation_details.id = cell_types.cell_annotation_details_id
--WHERE cell_annotation_details.cell_type_name = 'Ascending Vasa Recta Endothelial'
-- AND sample.relative_spatial_entry_iri = 'VHFemale'
-- AND ST_3DDWithin(sample_geom, ST_GeomFromText('POINTZ(23 18 5)'), 200.0);

select DISTINCT cell_type_name
FROM cell_annotation_details
INNER JOIN cell_types
ON cell_annotation_details.id = cell_types.cell_annotation_details_id
INNER JOIN sample
ON cell_types.sample_uuid = sample.sample_uuid
WHERE sample.sample_hubmap_id = 'HBM562.WMRL.498';
