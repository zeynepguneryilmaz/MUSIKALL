#!/usr/bin/env python3
"""Recompute Class A GPCR KSP frequencies with the corrected MUSIKALL contact/cost definition.

Scientific definitions mirrored from current MUSIKALL:
  a_ij = N_ij / sqrt(N_i*N_j)
  edge cost = 1/(a_ij + 1e-6)
  rcutt = 4.5 A
  Yen/NetworkX k shortest simple paths, k=20
  per-PDB frequency = percent of all source-sink paths containing a residue as an internal node.

Reference source/sink residues are canonical ADRB2 positions from the original project.
Equivalent target positions are mapped with GPCRdb generic numbering.
"""
from __future__ import annotations
import io, math, os, shutil, time, zipfile
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import requests
from Bio.PDB import PDBParser, PDBIO, Select
from Bio.PDB.Polypeptide import is_aa
from scipy.spatial import cKDTree

OUT = Path(os.environ.get("KSP_OUT", "analysis_gpcr_ksp/results"))
RAW = OUT / "raw_models"
CLEAN = OUT / "clean_pdbs"
MATS = OUT / "matrices"
PATHS = OUT / "paths"
FREQ = OUT / "frequencies"
for p in [OUT, RAW, CLEAN, MATS, PATHS, FREQ]: p.mkdir(parents=True, exist_ok=True)

RCUTT = 4.5
K = 20
REF_ENTRY = "adrb2_human"
REF_SOURCE_SEQ = [203, 207, 113, 312]
REF_SINK_SEQ = [131, 219, 272, 326]

ENTRIES = [
("5ht1a","5ht1a_human"),("5ht1b","5ht1b_human"),("5ht1d","5ht1d_human"),("5ht1e","5ht1e_human"),
("5ht1f","5ht1f_human"),("5ht2a","5ht2a_human"),("5ht2b","5ht2b_human"),("5ht2c","5ht2c_human"),
("5ht4r","5ht4r_human"),("5ht5a","5ht5a_human"),("5ht6r","5ht6r_human"),("5ht7r","5ht7r_human"),
("aa1r","aa1r_human"),("aa2ar","aa2ar_human"),("aa2br","aa2br_human"),("aa3r","aa3r_human"),
("acm1","acm1_human"),("acm2","acm2_human"),("acm3","acm3_human"),("acm4","acm4_human"),("acm5","acm5_human"),
("ada1a","ada1a_human"),("ada1b","ada1b_human"),("ada1d","ada1d_human"),("ada2a","ada2a_human"),("ada2b","ada2b_human"),
("adrb1","adrb1_human"),("adrb2","adrb2_human"),("adrb3","adrb3_human"),
("ccr1","ccr1_human"),("ccr2","ccr2_human"),("ccr3","ccr3_human"),("ccr5","ccr5_human"),("ccr8","ccr8_human"),
("cnr2","cnr2_human"),("cxcr1","cxcr1_human"),("cxcr2","cxcr2_human"),("cxcr3","cxcr3_human"),("cxcr4","cxcr4_human"),
("drd1","drd1_human"),("drd2","drd2_human"),("drd3","drd3_human"),("drd4","drd4_human"),("drd5","drd5_human"),
("ednrb","ednrb_human"),("hrh1","hrh1_human"),("hrh2","hrh2_human"),("hrh3","hrh3_human"),("hrh4","hrh4_human"),
("mc4r","mc4r_human"),("p2ry2","p2ry2_human"),("p2y12","p2y12_human")]

S = requests.Session()
S.headers.update({"User-Agent":"MUSIKALL-GPCR-KSP-reanalysis/2026"})

def get_json(url, tries=4):
    err=None
    for i in range(tries):
        try:
            r=S.get(url,timeout=120); r.raise_for_status(); return r.json()
        except Exception as e:
            err=e; time.sleep(2*(i+1))
    raise RuntimeError(f"GET failed {url}: {err}")

def get_bytes(url, tries=4):
    err=None
    for i in range(tries):
        try:
            r=S.get(url,timeout=180); r.raise_for_status(); return r.content
        except Exception as e:
            err=e; time.sleep(2*(i+1))
    raise RuntimeError(f"GET failed {url}: {err}")

def gpcr_info(entry):
    return get_json(f"https://gpcrdb.org/services/residues/extended/{entry}/")

def norm_generic(x):
    if x is None: return None
    s=str(x).strip()
    if not s: return None
    if "x" in s:
        left,right=s.rsplit("x",1)
        seg=left.split(".",1)[0]
        return f"{seg}x{right}"
    return s

def info_maps(info):
    seq_to = {}; gen_to = {}
    for row in info:
        try: seq=int(row.get("sequence_number"))
        except Exception: continue
        raw=row.get("display_generic_number"); g=norm_generic(raw)
        rec={"sequence_number":seq,"amino_acid":row.get("amino_acid"),"protein_segment":row.get("protein_segment"),"raw_generic":raw,"generic":g}
        seq_to[seq]=rec
        if g: gen_to[g]=rec
    return seq_to,gen_to

def download_active_model(entry, root):
    stem=entry.replace("_human","")
    url=f"https://gpcrdb.org/structure/homology_models/{stem}_human_active_full/download_pdb"
    b=get_bytes(url)
    (RAW/f"{root}_active_full.zip").write_bytes(b)
    try:
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            names=[n for n in z.namelist() if n.lower().endswith('.pdb')]
            if not names: raise RuntimeError("zip contains no PDB")
            text=z.read(names[0]).decode('utf-8','ignore')
    except zipfile.BadZipFile:
        text=b.decode('utf-8','ignore')
        if 'ATOM' not in text: raise
    p=RAW/f"{root}_active_full.pdb"; p.write_text(text)
    return p,url

class ProteinHeavySelect(Select):
    def accept_residue(self,residue):
        return int(residue.id[0]==' ' and is_aa(residue, standard=True))
    def accept_atom(self,atom):
        el=(atom.element or '').strip().upper()
        return int(el!='H' and not atom.get_name().strip().upper().startswith('H'))

def clean_pdb(raw_path, root):
    parser=PDBParser(QUIET=True); st=parser.get_structure(root,str(raw_path))
    out=CLEAN/f"{root}_active_clean.pdb"; io_obj=PDBIO(); io_obj.set_structure(st); io_obj.save(str(out), ProteinHeavySelect())
    return out

def parse_residues(clean_path):
    parser=PDBParser(QUIET=True); st=parser.get_structure('x',str(clean_path)); model=next(st.get_models()); residues=[]
    for chain in model:
        for res in chain:
            if res.id[0] != ' ' or not is_aa(res, standard=True): continue
            atoms=[]
            for a in res:
                el=(a.element or '').strip().upper()
                if el=='H' or a.get_name().strip().upper().startswith('H'): continue
                atoms.append({"name":a.get_name().strip(),"coord":np.asarray(a.coord,dtype=float)})
            if atoms:
                residues.append({"index":len(residues),"chain":chain.id,"resseq":int(res.id[1]),"icode":res.id[2].strip() or None,"resname":res.get_resname(),"atoms":atoms})
    return residues

def adjacency(residues):
    R=len(residues); adj=np.zeros((R,R),float); ew=np.zeros((R,R),float)
    coords=[np.array([a['coord'] for a in r['atoms']],float) for r in residues]; trees=[cKDTree(c) if len(c) else None for c in coords]
    for i in range(R):
        if trees[i] is None: continue
        Ni=len(coords[i])
        for j in range(i+1,R):
            if trees[j] is None: continue
            Nj=len(coords[j]); Nij=trees[i].count_neighbors(trees[j],RCUTT)
            if Nij>0:
                aij=float(Nij)/math.sqrt(Ni*Nj); adj[i,j]=adj[j,i]=aij
                ew[i,j]=ew[j,i]=1.0/(aij+1e-6)
    return adj,ew

def save_sparse(A,path):
    rows,cols=np.nonzero(A)
    with open(path,'w') as f:
        f.write(f"# shape {A.shape[0]} {A.shape[1]}\n# row_index\tcolumn_index\tvalue\n")
        for i,j in zip(rows,cols): f.write(f"{i}\t{j}\t{A[i,j]:.6f}\n")

def graph_from(adj,ew):
    G=nx.Graph(); G.add_nodes_from(range(len(adj))); rows,cols=np.where((adj!=0)&(np.arange(len(adj))[:,None]!=np.arange(len(adj))))
    for i,j in zip(rows,cols):
        if i<j: G.add_edge(int(i),int(j),weight=float(ew[i,j]))
    return G

def write_colored(clean_path, out_path, freq_by_resseq):
    lines=[]
    for line in Path(clean_path).read_text().splitlines(True):
        if line.startswith('ATOM') and len(line)>=66:
            try: rn=int(line[22:26].strip()); v=float(freq_by_resseq.get(rn,0.0)); line=line[:60]+f"{v:6.2f}"+line[66:]
            except Exception: pass
        lines.append(line)
    Path(out_path).write_text(''.join(lines))

def main():
    ref_info=gpcr_info(REF_ENTRY); ref_seq,_=info_maps(ref_info)
    source_labels=[]; sink_labels=[]; ref_rows=[]
    for kind,positions,out in [('source',REF_SOURCE_SEQ,source_labels),('sink',REF_SINK_SEQ,sink_labels)]:
        for seq in positions:
            rec=ref_seq.get(seq)
            if not rec or not rec.get('generic'): raise RuntimeError(f"Reference ADRB2 {seq} has no GPCRdb generic mapping")
            out.append(rec['generic']); ref_rows.append({"kind":kind,"reference_entry":REF_ENTRY,"reference_sequence_number":seq,**rec})
    pd.DataFrame(ref_rows).to_csv(OUT/'reference_source_sink_generic_mapping.csv',index=False)
    print('Reference source labels:',source_labels); print('Reference sink labels:',sink_labels)

    all_freq=[]; all_map=[]; qc=[]
    for root,entry in ENTRIES:
        print(f"\n=== {root} {entry} ===",flush=True); q={"protein_root":root,"entry":entry,"status":"started"}
        try:
            info=gpcr_info(entry); seq_map,gen_map=info_maps(info); raw,url=download_active_model(entry,root); clean=clean_pdb(raw,root); residues=parse_residues(clean)
            resseq_to_idx={r['resseq']:r['index'] for r in residues}; idx_to_r={r['index']:r for r in residues}
            mapping=[]; src_idx=[]; snk_idx=[]
            for kind,labels,out_idx in [('source',source_labels,src_idx),('sink',sink_labels,snk_idx)]:
                for g in labels:
                    rec=gen_map.get(g); seq=None if rec is None else rec['sequence_number']; idx=resseq_to_idx.get(seq) if seq is not None else None
                    mapping.append({"protein_root":root,"entry":entry,"kind":kind,"reference_generic":g,"target_sequence_number":seq,"target_index":idx,"target_amino_acid":None if rec is None else rec['amino_acid'],"target_segment":None if rec is None else rec['protein_segment']})
                    if idx is not None: out_idx.append(idx)
            all_map.extend(mapping)
            if len(src_idx)!=len(source_labels) or len(snk_idx)!=len(sink_labels): raise RuntimeError(f"incomplete endpoint mapping: {len(src_idx)}/{len(source_labels)} sources, {len(snk_idx)}/{len(sink_labels)} sinks")
            adj,ew=adjacency(residues); save_sparse(adj,MATS/f'{root}_adj_matrix.txt'); save_sparse(ew,MATS/f'{root}_edgeweight_matrix.txt')
            pd.DataFrame([{"index":r['index'],"chain":r['chain'],"sequence_number":r['resseq'],"icode":r['icode'],"residue_name":r['resname'],"generic":seq_map.get(r['resseq'],{}).get('generic')} for r in residues]).to_csv(MATS/f'{root}_node_index_map.csv',index=False)
            G=graph_from(adj,ew); comps=list(nx.connected_components(G)); largest=max((len(c) for c in comps),default=0)
            presence=Counter(); path_rows=[]; total_paths=0; failed_pairs=0
            import itertools
            for si in src_idx:
                for ti in snk_idx:
                    if si==ti: continue
                    try: pp=list(itertools.islice(nx.shortest_simple_paths(G,si,ti,weight='weight'),K))
                    except (nx.NetworkXNoPath,nx.NodeNotFound): pp=[]
                    if not pp: failed_pairs+=1; continue
                    for pno,p in enumerate(pp,1):
                        cost=nx.path_weight(G,p,weight='weight'); total_paths+=1
                        for node in set(p[1:-1]): presence[node]+=1
                        toks=[f"{idx_to_r[i]['chain']}:{idx_to_r[i]['resseq']}" for i in p]; gens=[seq_map.get(idx_to_r[i]['resseq'],{}).get('generic') for i in p]
                        path_rows.append({"protein_root":root,"entry":entry,"source_index":si,"source_sequence_number":idx_to_r[si]['resseq'],"sink_index":ti,"sink_sequence_number":idx_to_r[ti]['resseq'],"path_no":pno,"cost":cost,"path_indices":";".join(map(str,p)),"path_residues":";".join(toks),"path_generics":";".join('' if x is None else str(x) for x in gens)})
            pd.DataFrame(path_rows).to_csv(PATHS/f'{root}_ksp_paths.csv',index=False)
            freq_by_resseq={}; rows=[]
            for r in residues:
                count=int(presence.get(r['index'],0)); pct=(count/total_paths*100.0) if total_paths else 0.0; freq_by_resseq[r['resseq']]=pct; inf=seq_map.get(r['resseq'],{})
                row={"protein_root":root,"entry":entry,"sequence_number":r['resseq'],"generic":inf.get('generic'),"amino_acid":inf.get('amino_acid'),"protein_segment":inf.get('protein_segment'),"ksp_presence_count":count,"ksp_frequency_pct":pct,"total_paths":total_paths}
                rows.append(row); all_freq.append(row)
            pd.DataFrame(rows).to_csv(FREQ/f'{root}_ksp_frequency.csv',index=False); write_colored(clean,CLEAN/f'{root}_active_clean_ksp_colored.pdb',freq_by_resseq)
            q.update(status='ok',model_url=url,n_residues=len(residues),n_edges=G.number_of_edges(),n_components=len(comps),largest_component=largest,total_paths=total_paths,failed_pairs=failed_pairs,n_sources=len(src_idx),n_sinks=len(snk_idx),frequency_nonzero=sum(v>0 for v in freq_by_resseq.values()))
        except Exception as e:
            q.update(status='failed',error=repr(e)); print('FAILED',root,e,flush=True)
        qc.append(q); pd.DataFrame(qc).to_csv(OUT/'QC_summary.csv',index=False); pd.DataFrame(all_freq).to_csv(OUT/'KSP_frequencies_all.csv',index=False); pd.DataFrame(all_map).to_csv(OUT/'source_sink_alignment_all.csv',index=False)

    af=pd.DataFrame(all_freq)
    if not af.empty:
        af=af[af['generic'].notna()].copy(); af.pivot_table(index='generic',columns='protein_root',values='ksp_frequency_pct',aggfunc='mean').to_csv(OUT/'KSP_frequency_generic_by_receptor.csv')
    (OUT/'METHOD.txt').write_text(f"MUSIKALL-compatible KSP rerun\nrcutt={RCUTT} A\nk={K}\ncontact strength aij=Nij/sqrt(Ni*Nj)\nedge cost=1/(aij+1e-6)\nfrequency=100*(number of all source-sink paths containing residue internally)/(total source-sink paths)\nreference={REF_ENTRY}\nsource sequence positions={REF_SOURCE_SEQ}\nsink sequence positions={REF_SINK_SEQ}\nequivalent residues mapped by GPCRdb structure-based generic numbering\nstructures=GPCRdb active full homology models\n")
    shutil.make_archive(str(OUT.parent/'GPCR_MUSIKALL_KSP_FULL_OUTPUTS'),'zip',root_dir=OUT)
    print('\nDONE'); print(pd.DataFrame(qc)['status'].value_counts(dropna=False))

if __name__=='__main__': main()
