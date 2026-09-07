#!/usr/bin/env python3
import os
from pathlib import Path
import gpcr_ksp_rerun_action as m

chunk = int(os.environ.get('KSP_CHUNK', '0'))
nchunks = int(os.environ.get('KSP_NCHUNKS', '4'))
if chunk < 0 or chunk >= nchunks:
    raise SystemExit(f'Invalid chunk {chunk}/{nchunks}')

m.ENTRIES = [x for i, x in enumerate(m.ENTRIES) if i % nchunks == chunk]
m.OUT = Path(f'analysis_gpcr_ksp/results_chunk_{chunk}')
m.RAW = m.OUT / 'raw_models'
m.CLEAN = m.OUT / 'clean_pdbs'
m.MATS = m.OUT / 'matrices'
m.PATHS = m.OUT / 'paths'
m.FREQ = m.OUT / 'frequencies'
for p in [m.OUT, m.RAW, m.CLEAN, m.MATS, m.PATHS, m.FREQ]:
    p.mkdir(parents=True, exist_ok=True)

print(f'Running chunk {chunk}/{nchunks}: {len(m.ENTRIES)} receptors')
print([x[0] for x in m.ENTRIES])
m.main()
