#!/usr/bin/env python3
from __future__ import annotations
import json, re, time, warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import requests
from scipy.stats import mannwhitneyu, pointbiserialr, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedGroupKFold, GroupKFold
from sklearn.metrics import f1_score, balanced_accuracy_score, accuracy_score, average_precision_score, roc_auc_score
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')
OUT=Path('ml_eval/final_results'); OUT.mkdir(parents=True, exist_ok=True)
KSP_ROOT=Path('ml_eval/ksp_artifacts')
S=requests.Session(); S.headers.update({'User-Agent':'GPCR-MUSIKALL-KSP-ML-reanalysis/2026'})

# ---------- corrected MUSIKALL outputs ----------
def load_ksp():
    fps=list(KSP_ROOT.rglob('KSP_frequencies_all.csv'))
    qps=list(KSP_ROOT.rglob('QC_summary.csv'))
    if not fps: raise RuntimeError('No KSP frequency artifacts found')
    freq=pd.concat([pd.read_csv(p) for p in fps],ignore_index=True)
    qc=pd.concat([pd.read_csv(p) for p in qps],ignore_index=True).drop_duplicates('protein_root',keep='last') if qps else pd.DataFrame()
    freq=freq.drop_duplicates(['protein_root','generic'],keep='last')
    freq['generic']=freq['generic'].astype(str).replace({'nan':np.nan})
    ok=set(qc.loc[qc.status.eq('ok'),'protein_root'].astype(str)) if len(qc) else set(freq.protein_root.astype(str))
    freq=freq[freq.protein_root.astype(str).isin(ok)].copy()
    freq.to_csv(OUT/'KSP_frequencies_merged_49receptors.csv',index=False)
    qc.to_csv(OUT/'KSP_QC_summary.csv',index=False)
    return freq,qc,ok

# ---------- GPCRdb current mutation snapshot ----------
def get_json(url, tries=4):
    err=None
    for i in range(tries):
        try:
            r=S.get(url,timeout=120); r.raise_for_status(); return r.json()
        except Exception as e:
            err=e; time.sleep(1.5*(i+1))
    raise RuntimeError(f'{url}: {err}')

def norm_generic(x):
    if x is None: return None
    s=str(x).strip()
    if not s: return None
    if 'x' in s:
        left,right=s.rsplit('x',1); seg=left.split('.',1)[0]
        return f'{seg}x{right}'
    return s

def fetch_classA_entries(ksp_roots):
    urls=[
        'https://gpcrdb.org/services/proteinfamily/proteins/001/',
        'https://gpcrdb.org/services/proteinfamily/proteins/001_001/'
    ]
    data=None
    for u in urls:
        try:
            x=get_json(u)
            if isinstance(x,list) and x: data=x; break
        except Exception: pass
    if data is None:
        raise RuntimeError('Could not retrieve Class A protein family list from GPCRdb')
    entries=[]
    for r in data:
        e=r.get('entry_name') or r.get('entry') or r.get('protein')
        if not e: continue
        root=str(e).split('_')[0]
        if root in ksp_roots: entries.append(str(e))
    return sorted(set(entries)), data

def fetch_mutants(entry):
    try:
        d=get_json(f'https://gpcrdb.org/services/mutants/{entry}/')
        return entry,d if isinstance(d,list) else []
    except Exception:
        return entry,[]

def fetch_residues(entry):
    try:
        d=get_json(f'https://gpcrdb.org/services/residues/extended/{entry}/')
        mp={}
        for r in d:
            try: pos=int(r.get('sequence_number'))
            except Exception: continue
            g=norm_generic(r.get('display_generic_number'))
            mp[pos]=g
        return entry,mp
    except Exception:
        return entry,{}

QUAL_TO_LABEL={
 'abolished effect':'decrease','abolished':'decrease','decreased effect':'decrease','decreased':'decrease',
 'increased effect':'increase','increased':'increase','gained effect':'increase','gained':'increase',
 'no effect':'no_effect','unchanged':'no_effect','no response':'no_effect'
}
SIGN_TO_LABEL={'>':'increase','<':'decrease','0':'no_effect','+':'increase','-':'decrease'}
def lab(row):
    q=str(row.get('exp_mu_effect_qual') or '').strip().lower()
    if q in QUAL_TO_LABEL: return QUAL_TO_LABEL[q]
    s=str(row.get('exp_mu_effect_sign') or '').strip()
    return SIGN_TO_LABEL.get(s)

ENDPOINT_MAP={
 'Biing - Surface plasmon resonance':'ligand_binding','Binding - Other':'ligand_binding',
 'Binding - Radioligand competition/displacement':'ligand_binding','Binding - Radioligand kinetics (association/dissociation)':'ligand_binding',
 'Binding - Radioligand saturation':'ligand_binding','Functional - [35S]GPTγS binding':'ligand_binding','radioligand binding':'ligand_binding',
 'CRE-luciferase':'signaling_activity','Ca2+ accumulaion':'signaling_activity','Calcium mobilization assay':'signaling_activity',
 'Functional - CRE-luciferase':'signaling_activity','Functional - Ca2+ accumulation':'signaling_activity','Functional - ERK activation':'signaling_activity',
 'Functional - G protein complex dissociation':'signaling_activity','Functional - IP accumulation':'signaling_activity','Functional - Other':'signaling_activity',
 'Functional - cAMP accumulation':'signaling_activity','Functional - β-arrestin recruitment':'signaling_activity','SRE-luciferase':'signaling_activity','cAMP accumulation':'signaling_activity'
}

STD=set('ALREQCFYKDSIMTWVNHGP')
SIZE={'tiny':set('GASCTP'),'small':set('VNDEQHM'),'big':set('LIFYWRK')}
SURF={'Hydrophilic':set('STNQDEKRH'),'Amphipathic':set('YWCM'),'Hydrophobic':set('GAVLIPF')}
AROM=set('FYWH'); ALIPH=set('IVL')
ACID={'acidic':set('DE'),'basic':set('KRH'),'neutral':STD-set('DEKRH')}
CHARGE={'positive':set('HKR'),'negative':set('DE'),'neutral':STD-set('HKRDE')}
KD={'A':1.8,'R':-4.5,'N':-3.5,'D':-3.5,'C':2.5,'Q':-3.5,'E':-3.5,'G':-0.4,'H':-3.2,'I':4.5,'L':3.8,'K':-3.9,'M':1.9,'F':2.8,'P':-1.6,'S':-0.8,'T':-0.7,'W':-0.9,'Y':-1.3,'V':4.2}
VOL={'A':88.6,'R':173.4,'N':114.1,'D':111.1,'C':108.5,'Q':143.8,'E':138.4,'G':60.1,'H':153.2,'I':166.7,'L':166.7,'K':168.6,'M':162.9,'F':189.9,'P':112.7,'S':89.0,'T':116.1,'W':227.8,'Y':193.6,'V':140.0}
def lookup(a,m):
    for k,v in m.items():
        if a in v:return k
    return 'Unknown'
def parse_generic(g):
    m=re.match(r'^(\d+)x(\d+)$',str(g)) if pd.notna(g) else None
    return (int(m.group(1)),int(m.group(2))) if m else (-1,-1)

def build_dataset(ksp_roots):
    entries,fam=fetch_classA_entries(ksp_roots)
    print('Class A entries in KSP roots:',len(entries),flush=True)
    mut_by={}
    with ThreadPoolExecutor(max_workers=18) as ex:
        fut=[ex.submit(fetch_mutants,e) for e in entries]
        for f in as_completed(fut):
            e,d=f.result()
            if d: mut_by[e]=d
    active_entries=sorted(mut_by)
    print('Entries with mutation records:',len(active_entries),'raw rows',sum(map(len,mut_by.values())),flush=True)
    resmaps={}
    with ThreadPoolExecutor(max_workers=18) as ex:
        fut=[ex.submit(fetch_residues,e) for e in active_entries]
        for f in as_completed(fut):
            e,m=f.result(); resmaps[e]=m
    rows=[]
    for e,d in mut_by.items():
        for r in d:
            rr=dict(r); rr['_api_entry']=e; rr['protein_root']=str(rr.get('protein') or e).split('_')[0]
            try: pos=int(rr.get('mutation_pos'))
            except Exception: continue
            rr['mutation_pos']=pos; rr['generic']=resmaps.get(e,{}).get(pos); rr['y_label']=lab(rr)
            if rr['y_label'] is None: continue
            a=str(rr.get('mutation_from') or '').strip().upper(); b=str(rr.get('mutation_to') or '').strip().upper()
            if a not in STD or b not in STD: continue
            rr['mutation_from']=a; rr['mutation_to']=b
            rows.append(rr)
    df=pd.DataFrame(rows)
    if df.empty: raise RuntimeError('No labeled GPCR mutation rows reconstructed')
    # Features: exactly the revised 33-feature conceptual set (pre-one-hot)
    for pre,col in [('from','mutation_from'),('to','mutation_to')]:
        df[f'{pre}_size']=df[col].map(lambda a:lookup(a,SIZE)); df[f'{pre}_surface']=df[col].map(lambda a:lookup(a,SURF))
        df[f'{pre}_aromatic']=df[col].map(lambda a:int(a in AROM)); df[f'{pre}_aliphatic']=df[col].map(lambda a:int(a in ALIPH))
        df[f'{pre}_acidity']=df[col].map(lambda a:lookup(a,ACID)); df[f'{pre}_charge']=df[col].map(lambda a:lookup(a,CHARGE))
        df[f'{pre}_hydrophobicity']=df[col].map(KD); df[f'{pre}_volume']=df[col].map(VOL)
    df['mutation_combination']=df.mutation_from+df.mutation_to
    df['delta_aromatic']=df.to_aromatic-df.from_aromatic; df['delta_aliphatic']=df.to_aliphatic-df.from_aliphatic
    df['delta_hydrophobicity']=df.to_hydrophobicity-df.from_hydrophobicity
    df['delta_volume']=df.to_volume-df.from_volume; df['abs_delta_volume']=df.delta_volume.abs()
    pp=df.generic.map(parse_generic); df['tm_segment']=pp.map(lambda x:x[0]); df['tm_position']=pp.map(lambda x:x[1])
    for c in ['ligand_name','ligand_class','exp_func','exp_type']:
        if c not in df: df[c]=''
        df[c]=df[c].fillna('').astype(str)
    df['endpoint_domain']=df.exp_func.map(ENDPOINT_MAP).fillna('other_ambiguous')
    df['mutation_id']=df.protein_root+'|'+df.mutation_pos.astype(str)+'|'+df.mutation_from+'|'+df.mutation_to
    audit=pd.DataFrame([
      ['records_reconstructed',len(df)],['protein_constructs',df.protein.nunique()],['receptor_roots',df.protein_root.nunique()],
      ['unique_mutations',df.mutation_id.nunique()],['generic_positions',df.generic.nunique()],['ligands',df.ligand_name.nunique()]
    ],columns=['metric','value'])
    audit.to_csv(OUT/'current_GPCRdb_mutation_snapshot_audit.csv',index=False)
    pd.DataFrame({'entry':entries,'has_labeled_mutations':[e in active_entries for e in entries]}).to_csv(OUT/'queried_classA_entries.csv',index=False)
    return df

CAT=['ligand_name','protein_root','generic','exp_type','ligand_class','mutation_combination','exp_func','mutation_to','from_size','mutation_from','to_acidity','to_charge','from_surface','to_size','from_acidity','from_charge','endpoint_domain','to_surface']
NUM=['to_hydrophobicity','delta_hydrophobicity','delta_aromatic','from_aromatic','abs_delta_volume','from_hydrophobicity','tm_segment','tm_position','delta_volume','to_aliphatic','from_volume','delta_aliphatic','to_aromatic','from_aliphatic','to_volume']
assert len(CAT)+len(NUM)==33
LABELS=['decrease','increase','no_effect']; YMAP={x:i for i,x in enumerate(LABELS)}; POS=YMAP['increase']

def model_pipe(features,ksp=False):
    cats=[c for c in CAT if c in features]; nums=[c for c in features if c not in cats]
    pre=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',min_frequency=2),cats),('num','passthrough',nums)],remainder='drop')
    clf=XGBClassifier(n_estimators=260,max_depth=6,learning_rate=.05,subsample=.9,colsample_bytree=.9,objective='multi:softprob',eval_metric='mlogloss',random_state=42,n_jobs=2,tree_method='hist')
    return Pipeline([('pre',pre),('clf',clf)])

def scores(y,p,prob):
    d={'macro_f1':f1_score(y,p,average='macro'),'balanced_accuracy':balanced_accuracy_score(y,p),'accuracy':accuracy_score(y,p)}
    yy=(np.asarray(y)==POS).astype(int)
    d['increase_AP']=average_precision_score(yy,prob[:,POS]) if yy.sum() else np.nan
    try:d['increase_ROCAUC']=roc_auc_score(yy,prob[:,POS])
    except Exception:d['increase_ROCAUC']=np.nan
    return d

def run_paired(df,cv_name='mutation_grouped',n_splits=5):
    y=df.y_label.map(YMAP).to_numpy(); X=df.copy()
    if cv_name=='mutation_grouped':
        splitter=StratifiedGroupKFold(n_splits=n_splits,shuffle=True,random_state=42); splits=list(splitter.split(X,y,groups=df.mutation_id))
    else:
        splitter=GroupKFold(n_splits=n_splits); splits=list(splitter.split(X,y,groups=df.protein_root))
    rows=[]
    base_features=CAT+NUM
    for fi,(tr,te) in enumerate(splits,1):
        yt=y[tr]; counts=Counter(yt); sw=np.array([len(yt)/(3*counts[v]) for v in yt],float)
        for name,features in [('base33',base_features),('base33_plus_KSP',base_features+['ksp_frequency_pct'])]:
            pipe=model_pipe(features); pipe.fit(X.iloc[tr][features],yt,clf__sample_weight=sw)
            prob=pipe.predict_proba(X.iloc[te][features]); pred=np.argmax(prob,axis=1)
            d=scores(y[te],pred,prob); d.update(cv=cv_name,fold=fi,model=name,n_train=len(tr),n_test=len(te)); rows.append(d)
    fr=pd.DataFrame(rows)
    sm=fr.groupby(['cv','model']).agg({c:'mean' for c in ['macro_f1','balanced_accuracy','accuracy','increase_AP','increase_ROCAUC']}).reset_index()
    # explicit paired deltas per fold
    w=fr.pivot(index='fold',columns='model',values=['macro_f1','balanced_accuracy','accuracy','increase_AP','increase_ROCAUC'])
    deltas=[]
    for fold in sorted(fr.fold.unique()):
        r={'cv':cv_name,'fold':fold}
        for metric in ['macro_f1','balanced_accuracy','accuracy','increase_AP','increase_ROCAUC']:
            r['delta_'+metric]=float(w.loc[fold,(metric,'base33_plus_KSP')]-w.loc[fold,(metric,'base33')])
        deltas.append(r)
    return fr,sm,pd.DataFrame(deltas)

def association(df):
    rec=df[['y_label','ksp_frequency_pct','mutation_id','protein_root','generic']].copy()
    out=[]
    for labname in LABELS:
        z=(rec.y_label==labname).astype(int)
        r,p=pointbiserialr(z,rec.ksp_frequency_pct) if z.nunique()>1 else (np.nan,np.nan)
        a=rec.loc[z.eq(1),'ksp_frequency_pct']; b=rec.loc[z.eq(0),'ksp_frequency_pct']
        try:u,pu=mannwhitneyu(a,b,alternative='two-sided')
        except Exception:u,pu=np.nan,np.nan
        out.append({'level':'record','class':labname,'n_class':len(a),'mean':a.mean(),'median':a.median(),'q25':a.quantile(.25),'q75':a.quantile(.75),'point_biserial_r':r,'point_biserial_p':p,'mannwhitney_p':pu})
    # Fully concordant unique substitutions only
    g=rec.groupby('mutation_id').agg(protein_root=('protein_root','first'),generic=('generic','first'),ksp_frequency_pct=('ksp_frequency_pct','first'),labels=('y_label',lambda s:'|'.join(sorted(set(s))))).reset_index()
    g['concordant']=~g.labels.str.contains(r'\|')
    gu=g[g.concordant].copy(); gu['y_label']=gu.labels
    for labname in LABELS:
        z=(gu.y_label==labname).astype(int); a=gu.loc[z.eq(1),'ksp_frequency_pct']; b=gu.loc[z.eq(0),'ksp_frequency_pct']
        r,p=pointbiserialr(z,gu.ksp_frequency_pct) if z.nunique()>1 else (np.nan,np.nan)
        try:u,pu=mannwhitneyu(a,b,alternative='two-sided')
        except Exception:u,pu=np.nan,np.nan
        out.append({'level':'unique_concordant_mutation','class':labname,'n_class':len(a),'mean':a.mean(),'median':a.median(),'q25':a.quantile(.25),'q75':a.quantile(.75),'point_biserial_r':r,'point_biserial_p':p,'mannwhitney_p':pu})
    pd.DataFrame(out).to_csv(OUT/'KSP_outcome_association.csv',index=False); gu.to_csv(OUT/'KSP_unique_concordant_mutations.csv',index=False)
    return pd.DataFrame(out)

def main():
    ksp,qc,ok=load_ksp(); df=build_dataset(ok)
    # Merge only strict KSP-covered receptor+generic combinations; never zero-fill missing KSP.
    km=ksp[['protein_root','generic','ksp_frequency_pct','total_paths']].dropna(subset=['generic']).drop_duplicates(['protein_root','generic'])
    merged=df.merge(km,on=['protein_root','generic'],how='inner')
    merged.to_csv(OUT/'ML_ready_KSP_covered_records.csv',index=False)
    cov=pd.DataFrame([
      ['labeled_records_current_snapshot',len(df)],['KSP_covered_records',len(merged)],['KSP_covered_fraction',len(merged)/len(df)],
      ['KSP_covered_unique_mutations',merged.mutation_id.nunique()],['KSP_covered_roots',merged.protein_root.nunique()],['KSP_successful_roots',len(ok)]
    ],columns=['metric','value']); cov.to_csv(OUT/'KSP_ML_coverage.csv',index=False)
    assoc=association(merged)
    fr1,sm1,de1=run_paired(merged,'mutation_grouped',5)
    fr2,sm2,de2=run_paired(merged,'receptor_grouped',5)
    folds=pd.concat([fr1,fr2],ignore_index=True); summary=pd.concat([sm1,sm2],ignore_index=True); deltas=pd.concat([de1,de2],ignore_index=True)
    folds.to_csv(OUT/'paired_CV_fold_metrics.csv',index=False); summary.to_csv(OUT/'paired_CV_summary.csv',index=False); deltas.to_csv(OUT/'paired_CV_fold_deltas.csv',index=False)
    # decision table
    dec=[]
    for cv in ['mutation_grouped','receptor_grouped']:
        s=summary[summary.cv.eq(cv)].set_index('model')
        r={'cv':cv}
        for m in ['macro_f1','balanced_accuracy','accuracy','increase_AP','increase_ROCAUC']:
            r['base_'+m]=s.loc['base33',m]; r['ksp_'+m]=s.loc['base33_plus_KSP',m]; r['delta_'+m]=s.loc['base33_plus_KSP',m]-s.loc['base33',m]
        dec.append(r)
    decision=pd.DataFrame(dec); decision.to_csv(OUT/'KSP_incremental_value_decision.csv',index=False)
    # text report
    lines=['# Corrected MUSIKALL KSP × GPCR mutation ML — paired reanalysis','',
      '## Structural rerun','- Corrected MUSIKALL: aij=Nij/sqrt(NiNj), edge cost=1/(aij+1e-6), cutoff=4.5 Å, k=20.',
      f'- Strict source/sink mapping succeeded for {len(ok)}/52 true Class A receptor roots; MC4R, CNR2 and P2Y12 are excluded rather than force-mapped.',
      '- KSP feature is path-presence percentage from corrected active-state GPCRdb models; missing KSP is never imputed as zero.','',
      '## Current mutation snapshot / coverage']
    for _,r in cov.iterrows(): lines.append(f"- {r.metric}: {r.value}")
    lines += ['', '## Paired ML comparison', summary.to_markdown(index=False), '', '## Mean KSP incremental changes', decision.to_markdown(index=False), '', '## KSP-outcome associations', assoc.to_markdown(index=False)]
    # rule-based conservative interpretation
    dm=float(decision.loc[decision.cv.eq('mutation_grouped'),'delta_macro_f1'].iloc[0]); dr=float(decision.loc[decision.cv.eq('receptor_grouped'),'delta_macro_f1'].iloc[0]); apr=float(decision.loc[decision.cv.eq('receptor_grouped'),'delta_increase_AP'].iloc[0])
    if dm>=.02 and dr>=.02 and apr>0:
        verdict='KSP provides a meaningful and transferable independent structural signal; it can be promoted into the main mechanistic/ML story.'
    elif dm>0 and (dr<=.01 or apr<=0):
        verdict='KSP adds limited within-domain information but does not materially improve new-receptor transferability; keep it as a secondary structural descriptor, not mechanistic validation.'
    else:
        verdict='KSP does not provide robust incremental predictive value beyond the existing structural/context descriptors; keep it supplementary/exploratory.'
    lines += ['', '## Conservative verdict', verdict]
    (OUT/'KSP_ML_FINAL_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(summary.to_string(index=False)); print('\n',decision.to_string(index=False)); print('\nVERDICT:',verdict)

if __name__=='__main__': main()
