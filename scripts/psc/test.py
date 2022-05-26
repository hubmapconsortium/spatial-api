#!/usr/bin/env python3

import anndata
import json
from os.path import exists
import time
from datetime import timedelta

def h5ad_file_analysis(data: dict):
    sec_an = anndata.read_h5ad(data['psc_file'])
    if 'predicted.ASCT.celltype' in sec_an.obs:
        data['predicted.ASCT.celltype'] = True
        df = sec_an.obs[['predicted.ASCT.celltype']]
        cell_type_counts: dict = {}
        for index, row in df.iterrows():
            #import pdb; pdb.set_trace()
            cell_type: str = row.tolist()[0]
            if cell_type not in cell_type_counts:
                cell_type_counts[cell_type] = 1
            else:
                cell_type_counts[cell_type] = cell_type_counts[cell_type] + 1
        data['cell_type_counts'] = cell_type_counts
    else:
        data['predicted.ASCT.celltype'] = False
        print(f"$$ 'predicted.ASCT.celltype' NOT in sec_an.obs for analysis_file: {data['psc_file']}")

start_time = time.time()
input_file = open ('data.json')
data_array = json.load(input_file)
for data in data_array:
    if 'psc_file' in data:
        analysis_file = data['psc_file']
        if exists(data['psc_file']):
            data['psc_file_exists'] = True
            print(f"Exists: analysis_file: {data['psc_file']}")
            h5ad_file_analysis(data)
        else:
            data['psc_file_exists'] = False
            print(f"** Does NOT exist: analysis_file: {data['psc_file']}")

with open('data_out.json', 'w') as f:
    json.dump(data_array, f)

run_time_sec = time.time() - start_time
print(f'Run time: {str(timedelta(seconds=run_time_sec))}')
print("Done!")
