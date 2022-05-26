#!/usr/bin/env python

import anndata

analysis_file = '/hive/hubmap/data/public/7646a8a89555a123a56446b66c183d58/secondary_analysis.h5ad'
sec_an = anndata.read_h5ad(analysis_file)  #  Import the data file
df = sec_an.obs[['predicted.ASCT.celltype','predicted.ASCT.celltype.score']]  # convert to Pandas dataframe
import pdb; pdb.set_trace()