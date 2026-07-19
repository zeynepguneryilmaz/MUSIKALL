# =======================
# Standard library
# =======================
import datetime
import shutil, re
from pathlib import Path
from collections import  defaultdict
from dataclasses import dataclass
import json, os
# =======================
# Scientific / data
# =======================
import numpy as np
from scipy.spatial import cKDTree

# =======================
# Visualization
# =======================
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch

# =======================
# Bio / structure
# =======================
from Bio.PDB import (
    PDBParser,
    Superimposer,
    MMCIFParser,
)

# =======================
# UI / audio / output
# =======================
import pygame
import xlsxwriter

# =======================
# Init
# =======================
parser = PDBParser(QUIET=True)

from datetime import datetime
import uuid

def _now_run_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
import sys

def _hex_from_value_0_100(v: float) -> str:
    """
    0-100 -> blue/cyan/green/yellow/red
    """
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors

    v = max(0.0, min(float(v), 100.0)) / 100.0
    rgba = cm.get_cmap("jet")(v)
    return mcolors.to_hex(rgba, keep_alpha=False)

def _resource_path_local(rel: str) -> str:
    import os
    import sys

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base, rel)

def _get_user_config_dir(app_name: str = "MUSIKALL") -> Path:
    """
    Cross-platform user config directory.
    Windows : %APPDATA%/MUSIKALL
    macOS   : ~/Library/Application Support/MUSIKALL
    Linux   : $XDG_CONFIG_HOME/MUSIKALL or ~/.config/MUSIKALL
    """
    if sys.platform.startswith("win"):
        base = os.getenv("APPDATA")
        if base:
            return Path(base) / app_name
        return Path.home() / "AppData" / "Roaming" / app_name

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name

    base = os.getenv("XDG_CONFIG_HOME")
    if base:
        return Path(base) / app_name
    return Path.home() / ".config" / app_name


APP_DIR = _get_user_config_dir("MUSIKALL")
APP_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = APP_DIR / "settings.json"

from Bio.PDB.Polypeptide import is_aa
from Bio.Align import PairwiseAligner

aligner = PairwiseAligner()
aligner.mode = "global"

_NA_3TO1 = {
    "A":"A","C":"C","G":"G","U":"U",
    "DA":"A","DC":"C","DG":"G","DT":"T",
}


def _is_polymer_residue(res):
    # hetero / water skip
    return res.id[0] == " "


def _log(logger, msg: str):
    if logger is None:
        return
    try:
        if callable(logger):
            logger(msg)
        elif hasattr(logger, "log_output"):
            logger.log_output(msg)
    except Exception:
        pass


_TOKEN_FLEX_RE = re.compile(r"^\s*(?:(?P<seg>[^:\s]+):)?(?P<chain>[^:\s]+):(?P<resseq>-?\d+)(?P<icode>[A-Za-z]?)\s*$")


def split_residue_token_flex(token, default_seg=""):
    """
    Accepts:
      - "CHAIN:123" / "CHAIN:123A"
      - "SEG:CHAIN:123" / "SEG:CHAIN:123A"
    Returns always: (seg, chain, resseq:int, icode_or_None)

    NOTE:
      - If seg is missing, seg will be "" (empty) unless you explicitly pass default_seg.
      - This prevents "NOSEG:" from polluting labels/keys in segname-less proteins.
    """
    if isinstance(token, dict):
        seg = token.get("segname", None)
        ch  = token.get("chain")
        rn  = token.get("residue_num")
        ic  = token.get("icode", None)

        if not ch or rn is None:
            raise ValueError(f"Token dict missing chain/residue_num: {token}")

        rn = int(rn)
        ic = (str(ic).strip() or None) if ic is not None else None

        seg = (str(seg).strip() if seg not in (None, "", " ") else "")
        if not seg and default_seg:
            seg = str(default_seg).strip()

        return (seg, str(ch).strip(), rn, ic)

    if not isinstance(token, str):
        raise ValueError(f"Residue token must be str or dict, got {type(token)}")

    m = _TOKEN_FLEX_RE.match(token)
    if not m:
        raise ValueError(f"Invalid residue token: {token}")

    seg = (m.group("seg") or "").strip()
    if not seg and default_seg:
        seg = str(default_seg).strip()

    ch  = m.group("chain").strip()
    rn  = int(m.group("resseq"))
    ic  = (m.group("icode") or "").strip() or None

    return (seg, ch, rn, ic)


def flex_parse_residue_token(token, strict=True, default_seg=""):
    """
    Backward-compatible wrapper for residue token parsing.

    ALWAYS returns:
        (seg, chain, resseq:int|None, icode:str|None)

    Parameters
    ----------
    token : str | tuple | dict
        Residue token (e.g. "MC:D:2451A", "MC:D:2451:A", dict, tuple)
    strict : bool
        Kept for compatibility; parsing errors return empty fields if False.
    default_seg : str
        Segment name to use when seg is missing or empty.
        Critical for ribosome / large structures.
    """
    if token is None:
        return (default_seg, "", None, None)

    try:
        seg, ch, rn, ic = split_residue_token_flex(token, default_seg="")
    except Exception:
        if strict:
            raise
        return (default_seg, "", None, None)

    # Normalize outputs
    seg = (seg or default_seg or "").strip()
    ch  = (ch or "").strip()

    try:
        rn = int(rn) if rn is not None else None
    except Exception:
        rn = None

    ic = (str(ic).strip() if ic not in (None, "", " ") else None)

    if strict and (rn is None or ch == ""):
        raise ValueError(f"Unparseable residue token: {token}")

    return (seg, ch, rn, ic)


def _sort_residue_token_key(token):
    """
    Stable sort key for residue tokens.

    Accepts tokens like:
      - "SEG:CHAIN:123"
      - "SEG:CHAIN:123A"
      - "SEG:CHAIN:123:A"
      - dict / tuple forms accepted by flex_parse_residue_token

    Returns a tuple sortable in Python:
        (seg, chain, resseq, icode_order)
    where icode_order makes None come before letters.
    """
    seg, ch, rn, ic = flex_parse_residue_token(token, strict=False, default_seg="")

    # Normalize for sorting
    seg = (seg or "").strip()
    ch  = (ch or "").strip()

    # Put missing residue numbers at end (very defensive)
    rn_sort = rn if isinstance(rn, int) else 10**12

    # Insertion code sorting: None first, then alphabetical
    if ic in (None, "", " "):
        ic_sort = ("", 0)
    else:
        ic_sort = (str(ic).strip(), 1)

    return (seg, ch, rn_sort, ic_sort)


def _res_kind(res):
    """Return 'protein' | 'na' | None."""
    if not _is_polymer_residue(res):
        return None
    rn = (res.get_resname() or "").strip().upper()
    if is_aa(res, standard=True):
        return "protein"
    if rn in _NA_3TO1:
        return "na"
    return None


def _res_1letter(res):
    kind = _res_kind(res)
    if kind == "protein":
        # BioPython AA 3->1 (robust fallback)
        try:
            from Bio.SeqUtils import seq1
            return seq1(res.get_resname())
        except Exception:
            return "X"
    if kind == "na":
        return _NA_3TO1.get(res.get_resname().strip().upper(), "N")
    return None


def _anchor_atom(res):
    """
    Protein: CA
    NA: P fallback C4'/C4* fallback C3'/C3*
    """
    if not _is_polymer_residue(res):
        return None
    if res.has_id("CA"):
        return res["CA"]
    for an in ["P", "C4'", "C4*", "C3'", "C3*"]:
        if res.has_id(an):
            return res[an]
    return None


def _chain_polymer_profile(structure):
    """
    Returns dict:
      chain_id -> {
        'res_list': [Residue...],      # only polymer residues (protein/NA)
        'seq': '...',                  # 1-letter seq with X/N for unknown
        'idx_to_res': {i: residue},    # sequence index -> residue
        'resid_key_to_i': {(resseq,icode,kind): i}  # optional
      }
    """
    out = {}
    # use first model only for determinism
    model = next(structure.get_models())
    for chain in model:
        res_list = []
        seq_chars = []
        resid_key_to_i = {}
        for res in chain:
            kind = _res_kind(res)
            if kind is None:
                continue
            aa = _res_1letter(res)
            if aa is None:
                continue
            i = len(res_list)
            res_list.append(res)
            seq_chars.append(aa)
            resseq = res.id[1]
            icode = (res.id[2].strip() or None)
            resid_key_to_i[(resseq, icode, kind)] = i

        if res_list:
            out[chain.id] = {
                "res_list": res_list,
                "seq": "".join(seq_chars),
                "idx_to_res": {i:r for i,r in enumerate(res_list)},
                "resid_key_to_i": resid_key_to_i
            }
    return out


def _load_settings():
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_settings(d: dict):
    try:
        SETTINGS_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except Exception:
        pass


def _which(program: str) -> Path | None:
    p = shutil.which(program)
    return Path(p) if p else None


def get_structure_any(structure_id: str, path: str):
    ext = os.path.splitext(path)[1].lower()
    local_parser = MMCIFParser(QUIET=True) if ext in (".cif", ".mmcif") else PDBParser(QUIET=True)
    return local_parser.get_structure(structure_id, path)


def _job_dir_and_label(jobname: str):
    job_dir = _resolve_job_dir(jobname)
    job_label = os.path.basename(os.path.normpath(job_dir))
    return job_dir, job_label


def _base_only(p) -> str:
    s = os.path.basename(str(p)).strip()
    sL = s.lower()
    for ext in (".pdb", ".cif", ".mmcif"):
        if sL.endswith(ext):
            s = s[:-len(ext)]
            break
    return s  # .53 gibi kısımlar KALIR

def _base_key(p) -> str:
    return _base_only(p).lower()


def extract_start_end_residues_safe(paths_dict_2, pdb_key):
    """
    Return (start_residues, end_residues) as lists of (chain, resnum_str)
    for the given pdb_key (key may be with or without .pdb, may be canonized).
    """
    paths_dict_2 = paths_dict_2 or {}

    base = _base_only(pdb_key)
    try:
        canon = _base_key(base)
    except Exception:
        canon = base

    # ✅ Deterministic priority order (canon first)
    candidates = [
        canon,
        f"{canon}.pdb",
        base,
        f"{base}.pdb",
        str(pdb_key),
        str(pdb_key).lower(),
        base.lower(),
        canon.lower(),
    ]

    # Build lookup maps: base_only(key)->original key (and lowercase variant)
    by_base = {}
    by_base_lower = {}
    for k in paths_dict_2.keys():
        try:
            kb = _base_only(k)
        except Exception:
            kb = str(k)
        if kb not in by_base:
            by_base[kb] = k
        kbL = str(kb).lower()
        if kbL not in by_base_lower:
            by_base_lower[kbL] = k

    resolved_key = None

    # 1) direct hits (fast path)
    for c in candidates:
        if c in paths_dict_2:
            resolved_key = c
            break

    # 2) base_only hits
    if resolved_key is None:
        for c in candidates:
            try:
                cb = _base_only(c)
            except Exception:
                cb = str(c)
            if cb in by_base:
                resolved_key = by_base[cb]
                break

    # 3) case-insensitive base_only hits
    if resolved_key is None:
        for c in candidates:
            try:
                cb = _base_only(c)
            except Exception:
                cb = str(c)
            cbL = str(cb).lower()
            if cbL in by_base_lower:
                resolved_key = by_base_lower[cbL]
                break

    if resolved_key is None:
        return [], []

    path_entries = paths_dict_2.get(resolved_key) or {}
    start_residues, end_residues = set(), set()

    for _, values in path_entries.items():
        paths = (values or {}).get("paths") or []
        if not paths:
            continue

        first_path = paths[0]
        if len(first_path) < 2:
            continue

        s_seg, s_ch, s_rn, s_ic = flex_parse_residue_token(first_path[0])
        e_seg, e_ch, e_rn, e_ic = flex_parse_residue_token(first_path[-1])

        if s_ch and s_rn is not None:
            start_residues.add((s_ch.strip(), str(int(s_rn))))
        if e_ch and e_rn is not None:
            end_residues.add((e_ch.strip(), str(int(e_rn))))

    return list(start_residues), list(end_residues)


def _resolve_job_dir(jobname: str) -> str:
    p = Path(jobname)
    if p.is_absolute():
        p.mkdir(parents=True, exist_ok=True)
        return str(p)
    # Göreli ise Belgelerim/MUSIKALL Projects altına yaz
    root = get_projects_root() / jobname
    root.mkdir(parents=True, exist_ok=True)
    return str(root)


APP_FOLDER = "MUSIKALL Projects"

def _get_documents_dir() -> Path:
    """
    Cross-platform best-effort Documents directory.
    Falls back to home directory if Documents does not exist.
    """
    home = Path.home()

    # Windows / macOS / Linux için en basit ve sağlam yaklaşım:
    docs = home / "Documents"
    if docs.exists():
        return docs

    # Linux'ta Documents olmayabilir
    return home

def get_projects_root() -> Path:
    root = _get_documents_dir() / APP_FOLDER
    root.mkdir(parents=True, exist_ok=True)
    return root

def create_job_folder(jobname: str) -> str:
    """Belgelerim/MUSIKALL Projects/jobname klasörü oluştur ve döndür."""
    job_folder = get_projects_root() / jobname
    job_folder.mkdir(parents=True, exist_ok=True)
    return str(job_folder)


def remove_hydrogens_from_pdb_file(pdb_path):
    cleaned_lines = []

    with open(pdb_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith(("ATOM", "HETATM")):
                atom_name = line[12:16].strip()
                element = line[76:78].strip() if len(line) >= 78 else ""

                # Element kolonu varsa onu kullan; yoksa atom adına bak
                if element.upper() == "H":
                    continue
                if not element and atom_name.upper().startswith("H"):
                    continue

            cleaned_lines.append(line)

    with open(pdb_path, "w", encoding="utf-8") as f:
        f.writelines(cleaned_lines)

def load_pdb_files(jobname, file_paths, pdb_info_dict=None, logger=None):

    if pdb_info_dict is None:
        pdb_info_dict = {}
    parser = PDBParser(QUIET=True)

    # Job klasörü
    job_folder = _resolve_job_dir(jobname)
    pdb_folder = os.path.join(job_folder, "pdb_files")
    os.makedirs(pdb_folder, exist_ok=True)

    for file_path in file_paths:
        pdb_name = os.path.basename(file_path)
        pdb_id   = os.path.splitext(pdb_name)[0]
        canon    = _base_key(pdb_id)

        pdb_target_path = os.path.join(pdb_folder, pdb_name)

        try:
            # 1) PDB'yi job klasörüne kopyala
            if os.path.abspath(file_path) != os.path.abspath(pdb_target_path):
                shutil.copy2(file_path, pdb_target_path)
            remove_hydrogens_from_pdb_file(pdb_target_path)
            # 1.5) SEGNAME HARİTASI: PDB satırından oku
            # (chain_id, resseq_int, icode_str_or_None) -> set([segname_str, ...])
            from collections import Counter
            seg_map_full = defaultdict(Counter)
            try:
                with open(pdb_target_path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        if not (line.startswith("ATOM") or line.startswith("HETATM")):
                            continue
                        if len(line) < 80:
                            continue

                        chain_id = line[21]  # chain kolonu, strip etmiyoruz

                        resseq_str = line[22:26].strip()
                        if not resseq_str:
                            continue
                        try:
                            resseq_int = int(resseq_str)
                        except ValueError:
                            continue

                        icode_char = line[26]
                        icode_str  = icode_char.strip() or None

                        seg_str = line[72:76].strip()  # SEGID (73–76)
                        if not seg_str:
                            continue

                        key = (chain_id, resseq_int, icode_str)
                        seg_map_full[key][seg_str] += 1
            except Exception as e:
                _log(logger,f"⚠️ Could not pre-scan segnames from {pdb_name}: {e}\n")
                seg_map_full = {}

            # 2) Bio.PDB ile yapıyı oku
            structure = get_structure_any(canon, pdb_target_path)

            # 3) Sözlükleri kur
            pdb_info_dict[canon] = {
                'file_path': pdb_target_path,
                'structure': structure,
                'residue_chain_map': {},
                'edgeweight_matrix': None,
                'b_factors': {},
                'residue_dict': {'source_residues': [], 'sink_residues': []},
                'atom_info': {},
                'residue_atom_count': {},
                'atom_info_segchain': {},
                'residue_atom_count_segchain': {},
            }

            residue_chain_map           = pdb_info_dict[canon]['residue_chain_map']
            atom_info                   = pdb_info_dict[canon]['atom_info']
            residue_atom_count          = pdb_info_dict[canon]['residue_atom_count']
            atom_info_segchain          = pdb_info_dict[canon]['atom_info_segchain']
            residue_atom_count_segchain = pdb_info_dict[canon]['residue_atom_count_segchain']

            global_index = 0

            for model in structure:
                for chain in model:
                    chain_id = chain.get_id()

                    for residue in chain:
                        hetflag, resseq, icode = residue.id
                        if hetflag != ' ':
                            continue  # sadece standart aa/nükleotid

                        norm_icode = icode if icode != " " else None
                        key_full   = (chain_id, resseq, norm_icode)

                        # Bu residue için tüm segname'ler
                        seg_counter = seg_map_full.get(key_full, Counter())
                        all_segnames = sorted(seg_counter.keys())
                        primary_seg = seg_counter.most_common(1)[0][0] if seg_counter else None

                        first_atom_serial = None
                        ca_atom_serial = None

                        for atom in residue:
                            try:
                                s = atom.get_serial_number()  # PDB ATOM serial
                                if s:
                                    s = int(s)
                                    if first_atom_serial is None:
                                        first_atom_serial = s
                                    if atom.get_name().strip() == "CA":
                                        ca_atom_serial = s
                            except Exception:
                                pass

                        atom_list = [
                            {
                                "name": atom.get_name(),
                                "coord": atom.get_coord().tolist(),
                                "bfactor": float(getattr(atom, "get_bfactor", lambda: atom.bfactor)()),
                                "occupancy": float(getattr(atom, "get_occupancy", lambda: atom.occupancy)()),
                            }
                            for atom in residue
                        ]

                        simple_key = (chain_id, resseq)

                        res_info = {
                            'index':        global_index,
                            'residue_num':  resseq,
                            'residue_name': residue.get_resname(),
                            'atoms':        atom_list,
                            'chain':        chain_id,
                            'segname':      primary_seg,     # özet amaçlı
                            'all_segnames': all_segnames,   # tam liste
                            'icode':        norm_icode,
                            'first_atom_serial': first_atom_serial,
                            'ca_atom_serial': ca_atom_serial,

                        }

                        chain_key = f"{primary_seg}:{chain_id}" if primary_seg else chain_id
                        residue_chain_map.setdefault(chain_key, []).append(res_info)

                        # chain + resi sözlükleri
                        std_key = (chain_id, resseq, norm_icode)
                        residue_atom_count[std_key] = len(atom_list)
                        atom_info[std_key] = atom_list

                        # permissive fallback da tutmak isterseniz:
                        residue_atom_count[(chain_id, resseq, None)] = len(atom_list)
                        atom_info[(chain_id, resseq, None)] = atom_list

                        # segname + chain + resi + icode sözlükleri:
                        # bu residue'da görülen TÜM segname'ler için kayıt aç
                        if all_segnames:
                            for segname in all_segnames:
                                seg_key = (segname, chain_id, resseq, norm_icode)
                                residue_atom_count_segchain[seg_key] = len(atom_list)
                                atom_info_segchain[seg_key]          = atom_list
                        else:
                            seg_key = (None, chain_id, resseq, norm_icode)
                            residue_atom_count_segchain[seg_key] = len(atom_list)
                            atom_info_segchain[seg_key]          = atom_list

                        global_index += 1

            # 🔎 Chain + TÜM segname'ler (all_segnames) ile özet
            chain_details = []
            seg_to_chains = {}

            for chain_id, residues in sorted(residue_chain_map.items()):
                n_res = len(residues)

                # Bu chain'de kullanılan tüm segname'leri topla
                segs_for_chain = set()
                for r in residues:
                    all_segs = r.get("all_segnames")
                    if all_segs:
                        segs_for_chain.update(all_segs)
                    else:
                        if r.get("segname"):
                            segs_for_chain.add(r["segname"])

                if segs_for_chain:
                    seg_list = ", ".join(sorted(segs_for_chain))
                    chain_details.append(
                        f"   • {chain_id} (segname(s)={seg_list}): {n_res} residues"
                    )
                    for s in segs_for_chain:
                        seg_to_chains.setdefault(s, set()).add(chain_id)
                else:
                    chain_details.append(f"   • {chain_id}: {n_res} residues")

            # GUI log
            _log(logger,
                f"✅ {pdb_name} was processed and saved to:\n"
                f"   {pdb_target_path}\n"
                f"📌 Chains read:\n"
            )
            for line in chain_details:
                _log(logger,line + "\n")

            _log(logger, f"📌 Total nodes (standard residues): {global_index}\n")

        except Exception as e:
            _log(logger, f"❌ Error loading {pdb_name}: {e}\n")

    return pdb_info_dict


def calculate_adj_and_edgeweight_matrix(pdb_data, rcutt):
    """
    Fast contact-based adjacency and cost matrices (residue = node).

    For each residue i and j, counts the number of atom-atom contacts within
    distance rcutt using KDTree:
        Nij = # of atom pairs within rcutt
        aij = Nij/sqrt(Ni*Nj)
        edgeweight = 1/(aij + 1e-6)

    IMPORTANT:
    This function also returns node_index_map to guarantee a stable and correct
    mapping between graph node indices [0..R-1] and residue tokens used across
    the pipeline.

    Residue token format:
      - "CHAIN:RES"       (default)
      - "SEG:CHAIN:RES"   (if segname is present)

    Returns
    -------
    adj_matrix : (R, R) float
    edgeweight_matrix : (R, R) float
    node_index_map : dict[int, str]
        graph_index -> residue_token (stable, consistent with matrix indices)
    """
    rcm = (pdb_data or {}).get("residue_chain_map", {}) or {}

    # ---- Flatten residues in a deterministic, stable order ----
    # Use sorted chain IDs for stable ordering; within each chain we keep the original residue order.
    residues = []
    node_index_map = {}

    gi = 0
    for ch in sorted(rcm.keys(), key=lambda x: str(x)):
        for res in (rcm.get(ch) or []):
            residues.append(res)

            # Build token: SEG:CHAIN:RES or CHAIN:RES
            chain = (res.get("chain") or ch)
            chain = str(chain).strip() or "?"

            seg = res.get("segname", None)
            seg = seg.strip() if isinstance(seg, str) and seg.strip() else ""

            rn = res.get("residue_num", None)
            try:
                rn = int(rn)
            except Exception:
                rn = "?"

            seg = seg if seg else ""

            ic = res.get("icode", None)
            ic = ic if (ic not in ("", " ")) else None
            ic_suffix = (str(ic) if ic else "")

            if seg:
                token = f"{seg}:{chain}:{int(rn)}{ic_suffix}"
            else:
                token = f"{chain}:{int(rn)}{ic_suffix}"

            node_index_map[gi] = token
            gi += 1

    R = len(residues)

    adj_matrix = np.zeros((R, R), dtype=float)
    edgeweight_matrix = np.zeros((R, R), dtype=float)

    # ---- Precompute coords and KD-trees ----
    residue_coords = []
    residue_trees = []
    for res in residues:
        atoms = res.get("atoms", []) or []
        coords = np.array([a["coord"] for a in atoms if "coord" in a], dtype=float)

        if coords.size == 0:
            residue_coords.append(coords)
            residue_trees.append(None)
        else:
            residue_coords.append(coords)
            residue_trees.append(cKDTree(coords))

    # ---- Use symmetry: compute only i < j ----
    for i in range(R):
        tree_i = residue_trees[i]
        Ni = len(residue_coords[i])
        if Ni == 0 or tree_i is None:
            continue

        for j in range(i + 1, R):
            tree_j = residue_trees[j]
            Nj = len(residue_coords[j])
            if Nj == 0 or tree_j is None:
                continue

            # Number of atom-atom contact pairs within rcutt
            Nij = tree_i.count_neighbors(tree_j, rcutt)

            if Nij > 0:
                aij = Nij / np.sqrt((Ni * Nj))
                adj_matrix[i, j] = aij
                adj_matrix[j, i] = aij

                w = 1.0 / (aij + 1e-6)
                edgeweight_matrix[i, j] = w
                edgeweight_matrix[j, i] = w

    return adj_matrix, edgeweight_matrix, node_index_map


def save_matrix_to_file(matrix, filename):
    """
    Matrisi bir `.txt` dosyasına kaydeder.
    """

    np.savetxt(filename, matrix, fmt='%.6f')


def get_filename_without_extension(filepath):
    """
    Dosya adını uzantısı olmadan döndürür.
    """
    return os.path.splitext(os.path.basename(filepath))[0]


def ensure_reference_in_dict(jobname, pdb_info_dict, reference_pdb_path, gui=None, logger=None):
    """
    Ensure the reference PDB is present in `pdb_info_dict` using the same
    schema as `load_pdb_files`.

    Returns:
        canon (str): canonical key for this reference structure in pdb_info_dict
    """

    ref_name = os.path.basename(reference_pdb_path)
    ref_id   = os.path.splitext(ref_name)[0]
    canon    = _base_key(ref_id)

    # Already loaded & file exists → reuse
    if canon in pdb_info_dict and os.path.exists(pdb_info_dict[canon].get("file_path", "")):  # type: ignore[index]
        if gui:
            _log(logger,
                f"ℹ️ Using already loaded reference '{canon}' from "
                f"{pdb_info_dict[canon]['file_path']}\n"
            )
        return canon

    # Ensure jobdir/pdb_files exists
    job_folder = _resolve_job_dir(jobname)
    pdb_folder = os.path.join(job_folder, "pdb_files")
    os.makedirs(pdb_folder, exist_ok=True)

    # Copy reference into job folder (best effort)
    target_path = os.path.join(pdb_folder, ref_name)
    if os.path.abspath(reference_pdb_path) != os.path.abspath(target_path):
        try:
            shutil.copy2(reference_pdb_path, target_path)
        except Exception as e:
            if gui:
                _log(logger,f"⚠️ Reference copy failed ({e}); using original path.\n")
            target_path = reference_pdb_path

    try:
        # ---------------------------------------------------------------------
        # 1) Pre-scan segname from PDB columns 73–76 (0-based slice 72:76)
        # ---------------------------------------------------------------------
        seg_map_full = {}  # (chain, resseq, icode|None) -> set(segname)
        try:
            with open(target_path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if not (line.startswith("ATOM") or line.startswith("HETATM")):
                        continue

                    # Chain is column 22 (0-based 21)
                    if len(line) <= 21:
                        continue
                    chain_id = line[21]

                    # resseq is columns 23–26 (0-based 22:26)
                    if len(line) < 26:
                        continue
                    resseq_str = line[22:26].strip()
                    if not resseq_str:
                        continue
                    try:
                        resseq_int = int(resseq_str)
                    except ValueError:
                        continue

                    # icode is column 27 (0-based 26)
                    icode_char = line[26] if len(line) > 26 else " "
                    icode_str  = icode_char.strip() or None

                    # segname is columns 73–76 (0-based 72:76) if present
                    seg_str = line[72:76].strip() if len(line) >= 76 else ""
                    if not seg_str:
                        continue

                    key = (chain_id, resseq_int, icode_str)
                    seg_map_full.setdefault(key, set()).add(seg_str)

        except Exception as e:
            if gui:
                _log(logger,f"⚠️ Could not pre-scan segnames from reference {ref_name}: {e}\n")
            seg_map_full = {}

        # ---------------------------------------------------------------------
        # 2) Parse structure
        # ---------------------------------------------------------------------
        structure = get_structure_any(ref_id, target_path)

        # ---------------------------------------------------------------------
        # 3) Create info entry (match your load_pdb_files schema)
        # ---------------------------------------------------------------------
        info = {
            "file_path": target_path,
            "structure": structure,
            "residue_chain_map": {},

            "edgeweight_matrix": None,
            "b_factors": {},

            "residue_dict": {"source_residues": [], "sink_residues": []},

            "atom_info": {},                      # (chain, resseq, icode) -> atom_list
            "residue_atom_count": {},             # (chain, resseq, icode) -> int
            "atom_info_segchain": {},             # (seg, chain, resseq, icode) -> atom_list
            "residue_atom_count_segchain": {},    # (seg, chain, resseq, icode) -> int

            "index_to_residue_obj": {},           # int -> Bio.PDB.Residue
            "index_to_atom_objs": {},             # int -> list[Bio.PDB.Atom]
            "index_to_meta": {},                  # int -> dict(chain, resseq, icode, segname_mode, all_segnames)
        }
        pdb_info_dict[canon] = info

        residue_chain_map           = info["residue_chain_map"]
        atom_info                   = info["atom_info"]
        residue_atom_count          = info["residue_atom_count"]
        atom_info_segchain          = info["atom_info_segchain"]
        residue_atom_count_segchain = info["residue_atom_count_segchain"]

        idx_to_res  = info["index_to_residue_obj"]
        idx_to_atoms = info["index_to_atom_objs"]
        idx_to_meta = info["index_to_meta"]

        global_index = 0

        # ---------------------------------------------------------------------
        # 4) Build residue_chain_map + atom maps + index maps
        # ---------------------------------------------------------------------
        for model in structure:
            for chain in model:
                chain_id = chain.get_id()
                residue_list = []
                residue_chain_map[chain_id] = residue_list

                for residue in chain:
                    hetflag, resseq, icode = residue.id
                    if hetflag != " ":
                        continue

                    norm_icode = icode if icode != " " else None
                    key_full   = (chain_id, resseq, norm_icode)

                    seg_set = seg_map_full.get(key_full, set())
                    all_segnames = sorted(seg_set) if seg_set else []
                    primary_seg  = all_segnames[0] if all_segnames else None

                    atoms_obj_list = [atom for atom in residue]
                    atom_list = [
                        {"name": atom.get_name(), "coord": atom.get_coord().tolist()}
                        for atom in atoms_obj_list
                    ]

                    # Use icode-aware key to avoid collisions
                    std_key = (chain_id, resseq, norm_icode)

                    res_info = {
                        "index":        global_index,
                        "residue_num":  resseq,
                        "residue_name": residue.get_resname(),
                        "atoms":        atom_list,
                        "chain":        chain_id,
                        "segname":      primary_seg,
                        "all_segnames": all_segnames,
                        "icode":        norm_icode,
                    }
                    residue_list.append(res_info)

                    residue_atom_count[std_key] = len(atom_list)
                    atom_info[std_key]          = atom_list

                    # segchain maps
                    if all_segnames:
                        for segname in all_segnames:
                            seg_key = (segname, chain_id, resseq, norm_icode)
                            residue_atom_count_segchain[seg_key] = len(atom_list)
                            atom_info_segchain[seg_key]          = atom_list
                    else:
                        seg_key = (None, chain_id, resseq, norm_icode)
                        residue_atom_count_segchain[seg_key] = len(atom_list)
                        atom_info_segchain[seg_key]          = atom_list

                    # index maps (you declared them; now actually fill them)
                    idx_to_res[global_index] = residue
                    idx_to_atoms[global_index] = atoms_obj_list
                    idx_to_meta[global_index] = {
                        "chain": chain_id,
                        "resseq": resseq,
                        "icode": norm_icode,
                        "segname_mode": primary_seg,
                        "all_segnames": all_segnames,
                    }

                    global_index += 1

        # ---------------------------------------------------------------------
        # 5) GUI summary
        # ---------------------------------------------------------------------
        if gui:
            res_map = info.get("residue_chain_map", {})
            chain_details = []
            seg_to_chains = {}

            for chain_id, residues in sorted(res_map.items()):
                n_res = len(residues)

                segs_for_chain = set()
                for r in residues:
                    all_segs = r.get("all_segnames") or []
                    if all_segs:
                        segs_for_chain.update(all_segs)
                    elif r.get("segname"):
                        segs_for_chain.add(r["segname"])

                if segs_for_chain:
                    seg_list = ", ".join(sorted(segs_for_chain))
                    chain_details.append(f"   • {chain_id} (segname(s)={seg_list}): {n_res} residues")
                    for s in segs_for_chain:
                        seg_to_chains.setdefault(s, set()).add(chain_id)
                else:
                    chain_details.append(f"   • {chain_id}: {n_res} residues")

            _log(logger,
                f"✅ Reference PDB '{ref_name}' was processed and saved to:\n"
                f"   {target_path}\n"
                f"📌 Chains read for reference ({canon}):\n"
            )
            for line in chain_details:
                _log(logger,line + "\n")

            if seg_to_chains:
                _log(logger,"📌 Segments in reference (segname → chains):\n")
                for seg, chains in sorted(seg_to_chains.items()):
                    _log(logger,f"   • {seg}: chains {', '.join(sorted(chains))}\n")
            else:
                _log(logger,"📌 Segments in reference: (no segment IDs found)\n")

            _log(logger,f"📌 Total residues in reference (standard): {global_index}\n")

    except Exception as e:
        if gui:
            _log(logger,f"❌ Reference parse error: {e}\n")

    return canon


def parse_residue_input(text, gui=None, logger=None):
    """
    Kullanıcı input'unu source/sink için parse eder.

    Beklenen formatlar:
      - "CHAIN,RES"                  ->  DA,1047
      - "CHAIN,START-END"           ->  DA,1047-1050
      - "SEGNAME:CHAIN,RES"         ->  MC:DA,1047
      - "SEGNAME:CHAIN,START-END"   ->  MC:DA,1047-1050

    Birden fazla giriş:
      - "MC:DA,1047-1050; MC:DA,2000"
      - satır satır da yazılabilir.

    Dönen liste elemanları:
      { 'chain': 'DA', 'residue_num': 1047, 'segname': 'MC' (veya None) }
    """
    if not text:
        return []

    residues = []

    # ; veya yeni satıra göre tokenize et
    tokens = re.split(r"[;\n]+", text)
    for token in tokens:
        chunk = token.strip()
        if not chunk:
            continue

        try:
            # "SEG:CHAIN,..." ya da "CHAIN,..." kısmını ayır
            segment = None
            chain_segment_part = chunk
            residue_part = ""

            if "," in chunk:
                chain_segment_part, residue_part = map(str.strip, chunk.split(",", 1))
            else:
                chain_segment_part, residue_part = chunk, ""

            segname = None
            chain   = chain_segment_part
            if ":" in chain_segment_part:
                segname, chain = map(str.strip, chain_segment_part.split(":", 1))

            chain = chain.strip()
            if not chain:
                raise ValueError("Empty chain ID")

            resnums = []

            if residue_part:
                # aralık mı, tek tek mi?
                for part in residue_part.split(","):
                    p = part.strip()
                    if not p:
                        continue

                    if "-" in p:
                        start_s, end_s = map(str.strip, p.split("-", 1))
                        start_i = int(start_s)
                        end_i   = int(end_s)
                        if end_i < start_i:
                            raise ValueError(f"Invalid range '{p}'")
                        resnums.extend(range(start_i, end_i + 1))
                    else:
                        resnums.append(int(p))
            else:
                # Sadece "CHAIN" veya "SEG:CHAIN" yazılmışsa şimdilik hata verelim
                raise ValueError("No residue numbers given")

            for rn in resnums:
                rec = {
                    'chain':       chain,
                    'residue_num': rn,
                }
                if segname is not None:
                    rec['segname'] = segname

                residues.append(rec)

        except Exception as e:
            if gui:
                _log(logger,f"⚠ Residue input parse error in '{token}': {e}\n")

    # 🔍 DEBUG: parse sonucu özet
    if gui:
        if residues:
            _log(logger,
                f"🧪 Parsed {len(residues)} residues from input:\n"
            )
            for r in residues:
                seg = r.get("segname")
                seg_txt = f", segname={seg}" if seg else ""
                _log(logger,
                    f"   - chain={r['chain']}, res={r['residue_num']}{seg_txt}\n"
                )
        else:
            _log(logger,"⚠ No valid residues parsed from input.\n")

    return residues


def extract_reference_residues_from_structure(pdb_data):
    """
    Return reference residues WITHOUT any 'index' field.

    Expected pdb_data structure (minimum):
      pdb_data["residue_chain_map"] = {
          "A": [ {"residue_num": 12, "residue_name": "GLY", "icode": None, "segname": "AA", ...}, ... ],
          ...
      }

    Output:
      {
        "A": [
          {"residue_num": 12, "residue_name": "GLY", "icode": None, "segname": "AA"},
          ...
        ],
        ...
      }
    """
    out = {}
    rcm = (pdb_data or {}).get("residue_chain_map", {}) or {}

    for ch, residues in rcm.items():
        ch = str(ch)
        cleaned = []
        for r in (residues or []):
            rn = r.get("residue_num", None)
            resn = r.get("residue_name", None)
            icode = r.get("icode", None)
            seg = r.get("segname", None)

            # normalize
            try:
                rn = int(rn)
            except Exception:
                continue

            icode = icode if (icode not in ("", " ")) else None
            seg = seg.strip() if isinstance(seg, str) and seg.strip() else None
            resn = (str(resn).strip().upper() if resn is not None else None)

            cleaned.append({
                "residue_num": rn,
                "residue_name": resn,
                "icode": icode,
                "segname": seg,
            })
        out[ch] = cleaned

    return out


def _best_chain_match(ref_prof, tgt_prof, min_len=20, max_pairs=2500):
    """
    Returns mapping ref_chain -> tgt_chain based on best global alignment score.
    Adds guardrails for very large multi-chain systems (e.g., ribosome).
    """
    # chain -> dominant kind (protein/na/mixed)
    def _chain_kind(prof_entry):
        kinds = set()
        for r in prof_entry.get("res_list", [])[:50]:  # first 50 is enough
            k = _res_kind(r)
            if k:
                kinds.add(k)
        if len(kinds) == 1:
            return next(iter(kinds))
        if len(kinds) == 0:
            return None
        return "mixed"

    ref_items = []
    for rc, e in (ref_prof or {}).items():
        rs = e.get("seq", "")
        if len(rs) >= min_len:
            ref_items.append((rc, rs, _chain_kind(e)))

    tgt_items = []
    for tc, e in (tgt_prof or {}).items():
        ts = e.get("seq", "")
        if len(ts) >= min_len:
            tgt_items.append((tc, ts, _chain_kind(e)))

    if not ref_items or not tgt_items:
        return {}

    # Guardrail: do not attempt full O(n^2) scoring if it explodes
    # max_pairs default 2500 ~ 50x50. Ribosome would exceed massively.
    if len(ref_items) * len(tgt_items) > int(max_pairs):
        return {}

    from Bio.Align import PairwiseAligner
    aligner = PairwiseAligner()
    aligner.mode = "global"
    try:
        aligner.algorithm = "Myers"
    except Exception:
        pass
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -0.5

    scored = []
    for rc, rs, rk in ref_items:
        for tc, ts, tk in tgt_items:
            # only compare same dominant polymer type when possible
            if rk and tk and rk != "mixed" and tk != "mixed" and rk != tk:
                continue
            alns = aligner.align(rs, ts)
            aln0 = next(iter(alns), None)
            if aln0 is None:
                continue
            scored.append((aln0.score, rc, tc))
    try:
        aligner.max_number_of_alignments = 1
    except Exception:
        pass

    scored.sort(reverse=True, key=lambda x: x[0])

    mapping = {}
    used_t = set()
    for score, rc, tc in scored:
        if rc in mapping:
            continue
        if tc in used_t:
            continue
        mapping[rc] = tc
        used_t.add(tc)

    return mapping


def _alignment_index_map(ref_seq, tgt_seq):
    """
    Align ref_seq vs tgt_seq and return list of matched indices:
      [(i_ref, i_tgt), ...] for positions where both are not gaps.
    """
    from Bio.Align import PairwiseAligner

    aligner = PairwiseAligner()
    aligner.mode = "global"

    try:
        aligner.algorithm = "Myers"
    except Exception:
        pass

    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -0.5

    # ✅ combinatorial patlamayı azalt
    try:
        aligner.max_number_of_alignments = 1
    except Exception:
        pass

    alns = aligner.align(ref_seq, tgt_seq)
    a = next(iter(alns), None)
    if a is None:
        return []

    # ✅ Biopython sürümlerinde seqA/seqB yok → format() üzerinden gapped stringleri çek
    ref_aln = None
    tgt_aln = None
    try:
        fmt = a.format()
    except Exception:
        fmt = str(a)

    lines = [ln.rstrip("\n") for ln in fmt.splitlines() if ln.strip()]
    # PairwiseAligner çıktısında tipik olarak:
    # target  <start>  <gapped_seq>  <end>
    # query   <start>  <gapped_seq>  <end>
    for ln in lines:
        s = ln.strip()
        low = s.lower()
        if low.startswith("target"):
            parts = s.split()
            if len(parts) >= 3:
                ref_aln = parts[2]
        elif low.startswith("query"):
            parts = s.split()
            if len(parts) >= 3:
                tgt_aln = parts[2]

        if ref_aln and tgt_aln:
            break

    # Ek fallback: target/query parse edilemezse, en azından '-' içeren iki satırı al
    if not (ref_aln and tgt_aln):
        cand = []
        for ln in lines:
            ss = ln.strip()
            # çok kaba ama pratik: gap/harf içeren satırları yakala
            if "-" in ss and any(ch.isalpha() for ch in ss):
                cand.append(ss.split()[-1] if ss.split() else ss)
        if len(cand) >= 2:
            ref_aln, tgt_aln = cand[0], cand[1]

    if not (ref_aln and tgt_aln):
        return []

    # ✅ senin eski index-pair mantığını aynen koruyoruz
    pairs = []
    i_ref = 0
    i_tgt = 0
    for rch, tch in zip(ref_aln, tgt_aln):
        if rch != "-" and tch != "-":
            pairs.append((i_ref, i_tgt))
        if rch != "-":
            i_ref += 1
        if tch != "-":
            i_tgt += 1
    return pairs


def align_structures(ref_structure, target_structure, gui=None,
                     min_anchor_atoms=30, min_chain_len=20,
                     max_total_polymer_res=4000, max_chain_count=60,logger=None):
    """
    Sequence-aware alignment (guardrailed):
      1) build per-chain polymer sequences (protein+NA)
      2) map ref chains -> target chains by best alignment score
      3) for each mapped chain pair, build anchor atom pairs from aligned indices
      4) Superimposer on all anchor atoms, apply to target

    Returns: (target_structure_aligned, rmsd, residue_map)
      residue_map: {(ref_chain, ref_resseq, ref_icode, kind) -> (tgt_chain, tgt_resseq, tgt_icode, kind)}
    """
    ref_prof = _chain_polymer_profile(ref_structure)
    tgt_prof = _chain_polymer_profile(target_structure)

    if not ref_prof or not tgt_prof:
        if gui:
            _log(logger,"⚠ No polymer chains detected for sequence-aware alignment.\n")
        return None, None, {}

    # ---- Guardrails for huge complexes (ribosome) ----
    ref_total = sum(len(v.get("res_list", [])) for v in ref_prof.values())
    tgt_total = sum(len(v.get("res_list", [])) for v in tgt_prof.values())
    if (ref_total > max_total_polymer_res) or (tgt_total > max_total_polymer_res) \
            or (len(ref_prof) > max_chain_count) or (len(tgt_prof) > max_chain_count):
        if gui:
            _log(logger, "⚠ Seq-aware alignment skipped (system too large) → will use SEG-aware fallback.\n")
        return "SKIP_LARGE", None, {}



    chain_map = _best_chain_match(ref_prof, tgt_prof, min_len=min_chain_len)
    if not chain_map:
        if gui:
            _log(logger,"⚠ Could not map chains by sequence; alignment skipped.\n")
        return None, None, {}

    ref_atoms = []
    tgt_atoms = []
    residue_map = {}

    for rc, tc in chain_map.items():
        rs = ref_prof[rc]["seq"]
        ts = tgt_prof[tc]["seq"]
        pairs = _alignment_index_map(rs, ts)
        if not pairs:
            continue

        ref_res_list = ref_prof[rc]["res_list"]
        tgt_res_list = tgt_prof[tc]["res_list"]

        for i_ref, i_tgt in pairs:
            rres = ref_res_list[i_ref]
            tres = tgt_res_list[i_tgt]

            rk = _res_kind(rres)
            tk = _res_kind(tres)
            if rk is None or tk is None or rk != tk:
                continue

            ra = _anchor_atom(rres)
            ta = _anchor_atom(tres)
            if ra is None or ta is None:
                continue

            ref_atoms.append(ra)
            tgt_atoms.append(ta)

            rresseq = rres.id[1]
            ricode = (rres.id[2].strip() or None)
            tresseq = tres.id[1]
            ticode = (tres.id[2].strip() or None)

            residue_map[(rc, rresseq, ricode, rk)] = (tc, tresseq, ticode, rk)

    if len(ref_atoms) < max(3, int(min_anchor_atoms)):
        if gui:
            _log(logger,f"⚠ Not enough anchor atoms for alignment (n={len(ref_atoms)}). Skipping.\n")
        return None, None, residue_map

    sup = Superimposer()
    sup.set_atoms(ref_atoms, tgt_atoms)
    sup.apply(list(target_structure.get_atoms()))
    rmsd = float(sup.rms)

    if gui:
        _log(logger,
            f"📌 Seq-aware alignment: chains matched={len(chain_map)}, "
            f"anchor_atoms={len(ref_atoms)}, RMSD={rmsd:.3f}\n"
        )

    return target_structure, round(rmsd, 3), residue_map


def _build_seg_profiles_from_rcm(pdb_data):
    """
    Returns:
      prof[(chain, seg)] = {
         "seq": str,
         "res_meta": [ (resnum, icode, global_index), ... ]  # order preserved
      }
    """
    rcm = (pdb_data or {}).get("residue_chain_map", {}) or {}
    prof = {}

    def _one_letter(resn3):
        # protein+NA için basit map (senin projede zaten benzeri var; yoksa minimal bırak)
        aa = {
            "ALA":"A","CYS":"C","ASP":"D","GLU":"E","PHE":"F","GLY":"G","HIS":"H","ILE":"I","LYS":"K",
            "LEU":"L","MET":"M","ASN":"N","PRO":"P","GLN":"Q","ARG":"R","SER":"S","THR":"T","VAL":"V",
            "TRP":"W","TYR":"Y"
        }
        na = {"A":"A","U":"U","G":"G","C":"C","DA":"A","DT":"T","DG":"G","DC":"C"}
        r = (resn3 or "").strip().upper()
        return aa.get(r) or na.get(r) or "X"

    for ch, lst in rcm.items():
        ch = str(ch).strip()
        for r in (lst or []):
            gi = r.get("index")
            rn = r.get("residue_num")
            ic = (r.get("icode") or None)
            resn = r.get("residue_name")

            if gi is None or rn is None:
                continue
            try:
                gi = int(gi); rn = int(rn)
            except Exception:
                continue

            segs = r.get("all_segnames") or []
            segs = [str(s).strip() for s in segs if str(s).strip()]
            if not segs:
                s0 = r.get("segname")
                if s0 and str(s0).strip():
                    segs = [str(s0).strip()]
            if not segs:
                segs = [None]

            for seg in segs:
                key = (ch, seg)
                if key not in prof:
                    prof[key] = {"seq": [], "res_meta": []}
                prof[key]["seq"].append(_one_letter(resn))
                prof[key]["res_meta"].append((rn, (ic.strip() or None) if isinstance(ic,str) else ic, gi))

    # finalize seq strings
    for k in list(prof.keys()):
        prof[k]["seq"] = "".join(prof[k]["seq"])
    return prof


def _kmer_set(s, k=3):
    s = s or ""
    if len(s) < k:
        return set()
    return {s[i:i+k] for i in range(len(s)-k+1)}


def _best_seg_match(ref_seg_seq, tgt_seg_profiles, chain, topn=3, k=3):
    """
    tgt_seg_profiles: dict[(chain, seg)] -> {"seq":..., ...}
    Return best target seg for the given chain.
    """
    ref_k = _kmer_set(ref_seg_seq, k=k)
    if not ref_k:
        return None

    # 1) fast rank by Jaccard
    scored = []
    for (ch, seg), e in tgt_seg_profiles.items():
        if ch != chain:
            continue
        tk = _kmer_set(e["seq"], k=k)
        if not tk:
            continue
        inter = len(ref_k & tk)
        union = len(ref_k | tk)
        j = inter / union if union else 0.0
        scored.append((j, seg))

    scored.sort(reverse=True, key=lambda x: x[0])
    cand = [seg for _, seg in scored[:max(1, topn)]]
    if not cand:
        return None

    # 2) refine using real alignment only on candidates
    from Bio.Align import PairwiseAligner
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -0.5
    # mümkünse tek alignment ile sınırla (patlamayı azaltır)
    try:
        aligner.max_number_of_alignments = 1
    except Exception:
        pass

    best = (float("-inf"), None)
    for seg in cand:
        ts = tgt_seg_profiles[(chain, seg)]["seq"]
        alns = aligner.align(ref_seg_seq, ts)


        aln0 = next(iter(alns), None)
        if aln0 is None:
            continue

        sc = float(aln0.score)
        if sc > best[0]:
            best = (sc, seg)

    return best[1]


def _map_ref_res_to_target_index_large(ref_res, ref_data, tgt_data):
    """
    Returns target global_index (int) or None.
    """
    rch = str(ref_res.get("chain","")).strip()
    try:
        rrn = int(ref_res.get("residue_num"))
    except Exception:
        return None
    ric = (str(ref_res.get("icode")).strip() or None) if ref_res.get("icode") is not None else None

    # ref seg: kullanıcı girdisi varsa onu al; yoksa ref rcm'den bul
    ref_seg = ref_res.get("segname")
    ref_seg = str(ref_seg).strip() if ref_seg else None
    if ref_seg is None:
        # ref rcm'den (chain,resnum,icode) -> segname bul
        # senin already-existing _build_target_meta_lookup benzeri bir lookup burada da kullanılabilir
        rcm = (ref_data or {}).get("residue_chain_map", {}) or {}
        found = None
        for r in (rcm.get(rch) or []):
            if int(r.get("residue_num", -1)) != rrn:
                continue
            ic = r.get("icode") or None
            if ric is not None and (ic != ric):
                continue
            found = r
            break
        if found:
            # primary seg
            ref_seg = (found.get("segname") or None)
            ref_seg = str(ref_seg).strip() if ref_seg else None

    # seg profilleri
    ref_prof = _build_seg_profiles_from_rcm(ref_data)
    tgt_prof = _build_seg_profiles_from_rcm(tgt_data)

    if (rch, ref_seg) not in ref_prof:
        return None

    ref_seq = ref_prof[(rch, ref_seg)]["seq"]

    # target seg bul
    tgt_seg = _best_seg_match(ref_seq, tgt_prof, chain=rch, topn=3, k=3)
    if tgt_seg is None or (rch, tgt_seg) not in tgt_prof:
        return None

    # segment içi alignment index map
    pairs = _alignment_index_map(ref_seq, tgt_prof[(rch, tgt_seg)]["seq"])
    if not pairs:
        return None

    # ref segment içinde rrn'nin indexini bul
    ref_meta = ref_prof[(rch, ref_seg)]["res_meta"]  # [(rn,icode,gi), ...]
    tgt_meta = tgt_prof[(rch, tgt_seg)]["res_meta"]

    # ref position -> find i_ref
    i_ref = None
    for i, (rn, ic, _gi) in enumerate(ref_meta):
        if rn != rrn:
            continue
        if ric is not None and ic != ric:
            continue
        i_ref = i
        break
    if i_ref is None:
        return None

    # aligned mapping: find i_tgt that corresponds to i_ref
    # pairs: [(i_ref_pos, i_tgt_pos), ...]
    i_tgt = None
    for a, b in pairs:
        if a == i_ref:
            i_tgt = b
            break
    if i_tgt is None:
        return None

    # target global index
    _rn2, _ic2, gi2 = tgt_meta[i_tgt]
    return int(gi2) if gi2 is not None else None


def map_ref_residue_to_target_by_alignment(ref_res_rec, ref_structure, target_structure,
                                          residue_map, gui=None, fallback_distance=True,logger=None):
    """
    ref_res_rec: {'chain':..., 'residue_num':..., 'segname': optional, 'icode': optional}
    residue_map: output of align_structures_
    Returns: Bio.PDB.Residue or None
    """
    rchain = str(ref_res_rec.get("chain", "")).strip()
    try:
        rnum = int(ref_res_rec.get("residue_num"))
    except Exception:
        return None
    ric = ref_res_rec.get("icode")
    ric = (str(ric).strip() or None) if ric is not None else None

    # Determine kind from reference structure residue itself (more robust)
    ref_residue = None
    model = next(ref_structure.get_models())
    if rchain in model:
        chain = model[rchain]
        # find residue by resseq + optional icode
        for res in chain:
            if not _is_polymer_residue(res):
                continue
            if res.id[1] != rnum:
                continue
            if ric is not None:
                if (res.id[2].strip() or None) != ric:
                    continue
            ref_residue = res
            break

    if ref_residue is None:
        if gui:
            _log(logger, f"⚠ Reference residue not found in ref structure: {rchain}:{rnum}\n")
        return None

    kind = _res_kind(ref_residue)
    if kind is None:
        return None

    # 1) direct alignment-map lookup
    key = (rchain, rnum, (ref_residue.id[2].strip() or None), kind)
    if key in residue_map:
        tchain, tnum, ticode, _ = residue_map[key]
        tmodel = next(target_structure.get_models())
        if tchain in tmodel:
            tchain_obj = tmodel[tchain]
            for res in tchain_obj:
                if not _is_polymer_residue(res):
                    continue
                if res.id[1] != tnum:
                    continue
                if ticode is not None and (res.id[2].strip() or None) != ticode:
                    continue
                return res

    # 2) fallback: nearest residue of same kind in mapped target chain (if any)
    if not fallback_distance:
        return None

    # If ref chain mapped to some target chain in residue_map, restrict search
    mapped_tchain = None
    # pick any mapping with same ref chain & kind to infer the mapped chain
    for (rc, _, _, rk), (tc, _, _, tk) in residue_map.items():
        if rc == rchain and rk == kind and tk == kind:
            mapped_tchain = tc
            break

    # use improved closest with constraints
    return find_closest_residue(
        target_structure,
        ref_residue,
        restrict_chain=mapped_tchain,
        restrict_kind=kind
    )


def find_closest_residue(target_structure, ref_residue,
                                     restrict_chain=None, restrict_kind=None):
    def _center(res):
        a = _anchor_atom(res)
        if a is not None:
            return a.coord
        coords = [at.coord for at in res.get_atoms()]
        return np.mean(coords, axis=0) if coords else None

    ref_c = _center(ref_residue)
    if ref_c is None:
        return None

    tmodel = next(target_structure.get_models())
    chains = [tmodel[restrict_chain]] if (restrict_chain and restrict_chain in tmodel) else list(tmodel)

    best = None
    best_d = float("inf")

    for ch in chains:
        for res in ch:
            if not _is_polymer_residue(res):
                continue
            if restrict_kind and _res_kind(res) != restrict_kind:
                continue
            c = _center(res)
            if c is None:
                continue
            d = float(np.linalg.norm(ref_c - c))
            if d < best_d:
                best_d = d
                best = res
    return best


def process_residue_info_and_alignments(jobname, pdb_info_dict,
                                        reference_pdb_path,
                                        source_residues, sink_residues, gui, logger=None):
    import os

    ref_structure = get_structure_any("ref", reference_pdb_path)
    ref_basename = os.path.basename(reference_pdb_path)

    def _find_ref_data(pdb_info_dict, ref_basename):
        for _pid, _d in (pdb_info_dict or {}).items():
            fp = (_d or {}).get("file_path")
            if fp and os.path.basename(fp) == ref_basename:
                return _pid, _d
        ref_stem = os.path.splitext(ref_basename)[0]
        for _pid, _d in (pdb_info_dict or {}).items():
            fp = (_d or {}).get("file_path")
            if fp and os.path.splitext(os.path.basename(fp))[0] == ref_stem:
                return _pid, _d
        return None, None

    ref_pdb_id, ref_data = _find_ref_data(pdb_info_dict, ref_basename)
    result_dict = {}

    def _norm_seg(seg):
        return str(seg).strip() if seg else None

    def _norm_icode(ic):
        return str(ic).strip() if ic else None

    def _build_target_meta_lookup(data):
        """
        Build:
          idx_to_meta: global_index -> metadata (chain/resnum/resname/segname/all_segnames/icode)
          seg_lookup : (chain,resnum,icode)->segname (best-effort from residue_chain_map)
          atom_serial_to_index: optional
        """
        rcm = (data or {}).get("residue_chain_map", {}) or {}
        idx_to_meta = {}
        seg_lookup = {}
        atom_serial_to_index = {}

        for ch_key, lst in rcm.items():
            for r in (lst or []):
                ch = _real_chain_from_residue(r, ch_key)
                gi = r.get("index")
                rn = r.get("residue_num")
                if gi is None or rn is None:
                    continue
                try:
                    gi = int(gi)
                    rn = int(rn)
                except Exception:
                    continue

                idx_to_meta[gi] = {
                    "chain": ch,
                    "residue_num": rn,
                    "residue_name": (r.get("residue_name") or "UNK"),
                    "segname": r.get("segname"),
                    "all_segnames": r.get("all_segnames") or [],
                    "icode": (r.get("icode") or None),
                }

                sg = r.get("segname")
                ic = r.get("icode") or None
                if sg:
                    seg_lookup[(ch, rn, ic)] = str(sg).strip()

                fa = r.get("first_atom_serial")
                ca = r.get("ca_atom_serial")
                if ca is not None:
                    try:
                        atom_serial_to_index[int(ca)] = gi
                    except Exception:
                        pass
                if fa is not None:
                    try:
                        atom_serial_to_index[int(fa)] = gi
                    except Exception:
                        pass

        return idx_to_meta, seg_lookup, atom_serial_to_index

    def _build_seg_ranges(data):
        """
        (chain, segname) -> (min_resnum, max_resnum)
        """
        out = {}
        rcm = (data or {}).get("residue_chain_map", {}) or {}

        for ch_key, lst in rcm.items():
            for r in lst:
                ch = _real_chain_from_residue(r, ch_key)
                rn = r.get("residue_num")
                sg = r.get("segname")
                if rn is None:
                    continue
                try:
                    rn = int(rn)
                except Exception:
                    continue
                sg = _primary_seg_from_residue(r)
                key = (ch, sg)
                if key not in out:
                    out[key] = [rn, rn]
                else:
                    out[key][0] = min(out[key][0], rn)
                    out[key][1] = max(out[key][1], rn)

        return {k: tuple(v) for k, v in out.items()}

    for pdb_id, data in (pdb_info_dict or {}).items():
        target_pdb_path = (data or {}).get("file_path")
        if not target_pdb_path:
            continue
        if os.path.basename(target_pdb_path) == ref_basename:
            continue

        idx_map = _build_global_index_map(data)
        rcm = (data or {}).get("residue_chain_map", {}) or {}
        known_chains = {
            _real_chain_from_residue(r, ch_key)
            for ch_key, residues in rcm.items()
            for r in (residues or [])
        }
        seg_ranges = _build_seg_ranges(data)

        matches = {'source_matches': [], 'sink_matches': []}

        def _norm_chain(ch):
            if ch is None:
                return None
            ch = str(ch).strip()
            if ch in known_chains:
                return ch
            if len(ch) > 1:
                if ch[0] in known_chains:
                    return ch[0]
                if ch[-1] in known_chains:
                    return ch[-1]
            return ch

        def _find_target_seg_by_range(chain, rn):
            for (ch0, sg0), (lo, hi) in seg_ranges.items():
                if ch0 == chain and lo <= rn <= hi:
                    return sg0
            return None

        idx_to_meta, seg_lookup, atom_serial_to_index = _build_target_meta_lookup(data)

        def _direct_match_one(ref_res):
            ch = _norm_chain(ref_res.get("chain"))
            rn = ref_res.get("residue_num")
            if ch is None or rn is None:
                return None
            try:
                rn = int(rn)
            except Exception:
                return None

            ref_seg = _norm_seg(ref_res.get("segname"))  # ref’te seg olabilir/olmayabilir
            ref_ic = _norm_icode(ref_res.get("icode"))

            # Range tabanlı seg tespiti: olabilir de olmayabilir de
            target_seg_by_range = _find_target_seg_by_range(ch, rn)

            # Seg adayları:
            # 1) ref seg (varsa)
            # 2) range seg (varsa)
            # 3) None (segname yoksa “normal” yol)
            seg_candidates = []
            if ref_seg is not None:
                seg_candidates.append(ref_seg)
            if target_seg_by_range is not None and target_seg_by_range not in seg_candidates:
                seg_candidates.append(target_seg_by_range)
            seg_candidates.append(None)

            # icode adayları:
            # ref_ic varsa önce onu dene, sonra None
            ic_candidates = []
            if ref_ic is not None:
                ic_candidates.append(ref_ic)
            ic_candidates.append(None)

            # Index çöz: seg-aware + fallback
            gi = None
            chosen_seg = None
            chosen_ic = None

            for sg_try in seg_candidates:
                for ic_try in ic_candidates:
                    gi = idx_map.get((sg_try, ch, rn, ic_try))
                    if gi is not None:
                        chosen_seg = sg_try
                        chosen_ic = ic_try
                        break
                if gi is not None:
                    break

            if gi is None:
                return None

            # Meta (hedefin gerçek residue adı/seg’i buradan alınmalı)
            meta = idx_to_meta.get(gi, {}) or {}

            tgt_resname = meta.get("residue_name")
            if not tgt_resname or str(tgt_resname).strip() == "":
                tgt_resname = "UNK"

            ref_resname = ref_res.get("residue_name")
            if not ref_resname or str(ref_resname).strip() == "":
                ref_resname = tgt_resname

            # Target segname: öncelik meta’dan; yoksa seçilen seg; yoksa range
            target_seg = (
                    _norm_seg(meta.get("segname"))
                    or _norm_seg((meta.get("all_segnames") or [None])[0])
                    or chosen_seg
                    or target_seg_by_range
            )

            out = {
                "ref_chain": ref_res.get("chain"),
                "ref_residue_num": rn,
                "ref_residue_name": ref_resname,
                "ref_segname": ref_seg,

                "target_chain": meta.get("chain", ch),
                "target_residue_num": meta.get("residue_num", rn),
                "target_residue_name": tgt_resname,
                "target_segname": target_seg,

                "target_index": gi,
                "rmsd": None,

                # debug: range ile bulunan seg + gerçekten index’i çözerken kullanılan seg/icode
                "target_segname_by_range": target_seg_by_range,
                "target_segname_used_for_index": chosen_seg,
                "target_icode_used_for_index": chosen_ic,
            }

            if ref_ic is not None:
                out["ref_icode"] = ref_ic
            if meta.get("icode"):
                out["target_icode"] = _norm_icode(meta.get("icode"))

            return out

        for kind, residue_list in [('source_matches', source_residues),
                                   ('sink_matches',   sink_residues)]:
            for ref_res in residue_list or []:
                m = _direct_match_one(ref_res)
                if m:
                    matches[kind].append(m)

        result_dict[pdb_id] = matches

    return result_dict

def get_atom_segid(atom):
    g = getattr(atom, "get_segid", None)
    if callable(g):
        try:
            s = g()
            if isinstance(s, str) and s.strip():
                return s.strip()
        except Exception:
            pass
    s = getattr(atom, "segid", None)
    if isinstance(s, str) and s.strip():
        return s.strip()
    return None


def write_results_to_excel(jobname, results, reference_residues):
    """
    Writes alignment results to an Excel file with two sheets:
    - Reference Residues
    - Aligned Matches
    """
    import xlsxwriter
    job_dir = _resolve_job_dir(jobname)  # ✅
    job_label = os.path.basename(os.path.normpath(job_dir))  # ✅
    output_file = os.path.join(job_dir, f"{job_label}_alignment_results.xlsx")  # ✅
    workbook = xlsxwriter.Workbook(output_file)

    # === Sheet 1: Reference Residues ===
    ref_sheet = workbook.add_worksheet("Reference Residues")
    ref_headers = ["Residue Type", "Chain", "Segname", "Residue Num", "Residue Name", "Index"]
    for col, header in enumerate(ref_headers):
        ref_sheet.write(0, col, header)

    if reference_residues:
        for row, res in enumerate(reference_residues, start=1):
            ref_sheet.write(row, 0, res.get('type', ''))
            ref_sheet.write(row, 1, res.get('chain', ''))
            ref_sheet.write(row, 2, res.get('segname', ''))      # 🔹 segname
            ref_sheet.write(row, 3, res.get('residue_num', ''))
            ref_sheet.write(row, 4, res.get('residue_name', ''))
            ref_sheet.write(row, 5, res.get('index', ''))

    # === Sheet 2: Aligned Matches ===
    align_sheet = workbook.add_worksheet("Aligned Matches")
    align_headers = [
        "PDB File",
        "Residue Type",
        "Ref Chain",
        "Ref Segname",
        "Ref Residue Num",
        "Ref Residue Name",
        "Target Chain",
        "Target Segname",
        "Target Residue Num",
        "Target Residue Name",
        "Target Index",
    ]
    for col, header in enumerate(align_headers):
        align_sheet.write(0, col, header)

    row = 1
    for pdb_id, match_data in results.items():
        # Sources
        for match in match_data.get('source_matches', []):
            align_sheet.write(row, 0, pdb_id)
            align_sheet.write(row, 1, "Source")
            align_sheet.write(row, 2, match.get('ref_chain', ''))
            align_sheet.write(row, 3, match.get('ref_segname', ''))   # 🔹
            align_sheet.write(row, 4, match.get('ref_residue_num', ''))
            align_sheet.write(row, 5, match.get('ref_residue_name', ''))
            align_sheet.write(row, 6, match.get('target_chain', ''))
            align_sheet.write(row, 7, match.get('target_segname', ''))  # 🔹
            align_sheet.write(row, 8, match.get('target_residue_num', ''))
            align_sheet.write(row, 9, match.get('target_residue_name', ''))
            align_sheet.write(row,10, match.get('target_index', ''))
            row += 1

        # Sinks
        for match in match_data.get('sink_matches', []):
            align_sheet.write(row, 0, pdb_id)
            align_sheet.write(row, 1, "Sink")
            align_sheet.write(row, 2, match.get('ref_chain', ''))
            align_sheet.write(row, 3, match.get('ref_segname', ''))
            align_sheet.write(row, 4, match.get('ref_residue_num', ''))
            align_sheet.write(row, 5, match.get('ref_residue_name', ''))
            align_sheet.write(row, 6, match.get('target_chain', ''))
            align_sheet.write(row, 7, match.get('target_segname', ''))
            align_sheet.write(row, 8, match.get('target_residue_num', ''))
            align_sheet.write(row, 9, match.get('target_residue_name', ''))
            align_sheet.write(row,10, match.get('target_index', ''))
            row += 1

    workbook.close()
    print(f"✅ Results saved to {output_file}")


def run_residue_mapping(jobname, pdb_info_dict, reference_pdb_path, source_residues, sink_residues, gui,logger=None):
    """
    Maps residue indices/numbers of each PDB to a common reference and writes results.

    Key fix (ribosome/segname-safe):
    - Reference seeding does NOT rely on searching the Bio.PDB structure by chain/resnum,
      because ribosome PDBs can use "chain IDs" differently (e.g., DA) and segname carries
      the biological subunit identity.
    - Instead, we seed the reference source/sink indices directly from
      pdb_info_dict[ref_id]['residue_chain_map'] (segname-aware).
    """

    # Ensure reference PDB is present in pdb_info_dict and get its key
    ref_id = ensure_reference_in_dict(jobname, pdb_info_dict, reference_pdb_path, gui, logger=logger)


    # Parse reference structure (still used by downstream alignment/mapping code)
    parser = PDBParser(QUIET=True)
    ref_structure = parser.get_structure(ref_id, pdb_info_dict[ref_id]["file_path"])

    # -------------------------------------------------------------------------
    # --- NEW: robust ref seeding via residue_chain_map (segname-aware) ---
    # -------------------------------------------------------------------------
    if not getattr(gui, "reference_residues", None):
        ref_data = pdb_info_dict.get(ref_id, {}) or {}
        rcm = ref_data.get("residue_chain_map", {}) or {}

        # Build lookup maps from residue_chain_map
        idxmap_simple = {}  # (chain, resnum) -> global index
        idxmap_seg = {}     # (segname, chain, resnum) -> global index
        namemap = {}        # (global index) -> residue_name (for Excel)

        for ch, lst in rcm.items():
            ch = str(ch).strip()
            for r in (lst or []):
                gi = r.get("index")
                rn = r.get("residue_num")
                if gi is None or rn is None:
                    continue

                try:
                    gi_i = int(gi)
                    rn_i = int(rn)
                except Exception:
                    continue

                idxmap_simple[(ch, rn_i)] = gi_i
                namemap[gi_i] = r.get("residue_name", "UNK")

                # Prefer all_segnames if present (more correct for ribosome)
                all_segs = r.get("all_segnames") or []
                if all_segs:
                    for sg in all_segs:
                        if sg:
                            idxmap_seg[(str(sg).strip(), ch, rn_i)] = gi_i
                else:
                    sg = r.get("segname")
                    if sg:
                        idxmap_seg[(str(sg).strip(), ch, rn_i)] = gi_i

        gui.reference_residues = []

        def _push(ref_rec, label):
            ch_in = ref_rec.get("chain")
            rn_in = ref_rec.get("residue_num")
            sg_in = ref_rec.get("segname", None)

            if ch_in is None or rn_in is None:
                _log(logger,f"⚠ Reference residue missing chain/residue_num: {ref_rec}\n")
                return

            ch = str(ch_in).strip()
            try:
                rn = int(rn_in)
            except Exception:
                _log(logger,f"⚠ Reference residue residue_num not int-convertible: {ref_rec}\n")
                return

            sg = str(sg_in).strip() if sg_in else None

            gi = None
            if sg:
                gi = idxmap_seg.get((sg, ch, rn))
            if gi is None:
                gi = idxmap_simple.get((ch, rn))

            if gi is None:
                _log(logger,
                    "⚠ Reference residue not found in residue_chain_map: "
                    f"{(sg + ':') if sg else ''}{ch}:{rn}\n"
                )
                return

            gui.reference_residues.append({
                "type": label,
                "segname": sg_in,  # keep original (may preserve user’s exact formatting)
                "chain": ch_in,
                "residue_num": rn,
                "residue_name": namemap.get(int(gi), "UNK"),
                "index": int(gi),
            })

        for s in (source_residues or []):
            _push(s, "Source")
        for t in (sink_residues or []):
            _push(t, "Sink")
    # --- end NEW block ---
    # -------------------------------------------------------------------------

    # Seed reference's own residue_dict from gui.reference_residues
    src_list, snk_list = [], []
    for r in (gui.reference_residues or []):
        item = {
            "chain": r.get("chain"),
            "residue_num": r.get("residue_num"),
            "index": r.get("index"),
        }
        if r.get("segname"):
            item["segname"] = r.get("segname")

        if r.get("type") == "Source":
            src_list.append(item)
        elif r.get("type") == "Sink":
            snk_list.append(item)

    pdb_info_dict[ref_id]["residue_dict"] = {
        "source_residues": src_list,
        "sink_residues": snk_list
    }

    # Do alignments + mapping (this should map ref residues to each target PDB)
    pdb_residue_dict = process_residue_info_and_alignments(
        jobname, pdb_info_dict, reference_pdb_path, source_residues, sink_residues, gui
    )

    # Write back per-PDB mapped indices
    for pdb_id, match_dict in (pdb_residue_dict or {}).items():
        source_list = []
        for m in (match_dict.get("source_matches", []) or []):
            item = {
                "chain": m.get("target_chain"),
                "residue_num": m.get("target_residue_num"),
                "index": m.get("target_index"),
            }
            if m.get("target_segname"):
                item["segname"] = m.get("target_segname")
            source_list.append(item)

        sink_list = []
        for m in (match_dict.get("sink_matches", []) or []):
            item = {
                "chain": m.get("target_chain"),
                "residue_num": m.get("target_residue_num"),
                "index": m.get("target_index"),
            }
            if m.get("target_segname"):
                item["segname"] = m.get("target_segname")
            sink_list.append(item)

        if pdb_id in pdb_info_dict:
            pdb_info_dict[pdb_id]["residue_dict"] = {
                "source_residues": source_list,
                "sink_residues": sink_list
            }

    # Excel output + logs
    if pdb_residue_dict:
        write_results_to_excel(jobname, pdb_residue_dict, gui.reference_residues)
        _log(logger,"✅ Mapping results saved to Excel.\n")
    else:
        _log(logger,"⚠ Mapping completed, but no matches were found.\n")

    return pdb_residue_dict

def _clean_seg(seg):
    if seg in (None, "", " ", "NOSEG"):
        return None
    s = str(seg).strip()
    return s if s else None


def _clean_chain(chain):
    if chain in (None, "", " "):
        return ""
    return str(chain).strip()


def _clean_icode(icode):
    if icode in (None, "", " "):
        return None
    s = str(icode).strip()
    return s if s else None


def _real_chain_from_residue(r, fallback_ch=None):
    ch = r.get("chain") if isinstance(r, dict) else None
    if ch not in (None, "", " "):
        return str(ch).strip()
    return str(fallback_ch).strip() if fallback_ch is not None else ""


def _primary_seg_from_residue(r):
    all_segs = r.get("all_segnames") or []
    for sg in all_segs:
        sg = _clean_seg(sg)
        if sg:
            return sg
    return _clean_seg(r.get("segname"))


def _all_segs_from_residue(r):
    all_segs = r.get("all_segnames") or []
    segs = [_clean_seg(s) for s in all_segs]
    segs = [s for s in segs if s]

    if not segs:
        sg = _primary_seg_from_residue(r)
        if sg:
            segs = [sg]

    return segs or [None]

def _build_global_index_map(pdb_data):
    out = {}
    rcm = (pdb_data or {}).get("residue_chain_map", {}) or {}

    simple_seen, simple_bad = {}, set()
    strict_noic_seen, strict_noic_bad = {}, set()

    for ch_key, residues in rcm.items():

        for r in (residues or []):
            ch = _real_chain_from_residue(r, ch_key)

        for r in (residues or []):
            gi = r.get("index")
            rn = r.get("residue_num")
            ic = r.get("icode", None)

            if gi is None or rn is None:
                continue
            try:
                gi = int(gi)
            except Exception:
                continue

            s = str(rn).strip()
            digits = "".join(c for c in s if c.isdigit())
            if not digits:
                continue
            rn_i = int(digits)

            ic = ic if ic not in ("", " ") else None
            if ic is None:
                tail = "".join(c for c in s if c.isalpha()).strip()
                ic = tail or None
            ic = (str(ic).strip() if ic else None)

            # seg listesi: all_segnames varsa hepsini kullan
            segs = _all_segs_from_residue(r)

            # ---- STRICT: (seg, ch, rn, ic) her zaman yazılabilir
            # ---- STRICT-NOIC: (seg, ch, rn, None) sadece unambiguous ise yazılacak
            for sg in segs:
                out[(sg, ch, rn_i, ic)] = gi

                k_noic = (sg, ch, rn_i, None)
                if k_noic in strict_noic_seen and strict_noic_seen[k_noic] != gi:
                    strict_noic_bad.add(k_noic)
                else:
                    strict_noic_seen.setdefault(k_noic, gi)

            # ---- SIMPLE (chain-only) ----
            k_simple = (ch, rn_i, ic)
            k_simple_noic = (ch, rn_i, None)

            if k_simple in simple_seen and simple_seen[k_simple] != gi:
                simple_bad.add(k_simple)
            else:
                simple_seen.setdefault(k_simple, gi)

            if k_simple_noic in simple_seen and simple_seen[k_simple_noic] != gi:
                simple_bad.add(k_simple_noic)
            else:
                simple_seen.setdefault(k_simple_noic, gi)

    # strict_noic only if unambiguous
    for k, gi in strict_noic_seen.items():
        out[k] = None if k in strict_noic_bad else gi

    # simple only if unambiguous
    for k, gi in simple_seen.items():
        out[k] = None if k in simple_bad else gi

    return out


def resolve_residue_to_global_index(res, global_index_map):
    """
    Resolve a residue token/dict into a global index using the ribosome-safe map.

    Tries STRICT (seg,chain,rn,icode) first.
    Falls back to:
      - (seg,chain,rn,None)  (ignore icode but keep seg)
      - (chain,rn,icode)     ONLY if it exists (i.e., unique in structure)
      - (chain,rn,None)      ONLY if it exists (i.e., unique in structure)

    This prevents wrong mapping in ribosomes.
    """
    # If res is dict-like from your GUI internal structures
    if isinstance(res, dict):
        seg = res.get("segname", None)
        ch  = res.get("chain", None)
        rn_raw = res.get("residue_num", None)
        ic = res.get("icode", None)
        token_like = {"segname": seg, "chain": ch, "residue_num": rn_raw, "icode": ic}
    else:
        token_like = res

    # parse token robustly (your existing parser)
    seg, ch, rn, ic = flex_parse_residue_token(token_like, strict=False, default_seg="")

    seg = str(seg).strip() if seg not in (None, "", " ") else None
    ch  = (str(ch).strip() if ch else "")
    try:
        rn = int(rn) if rn is not None else None
    except Exception:
        rn = None
    ic = (str(ic).strip() if ic not in (None, "", " ") else None)

    if not ch or rn is None:
        return None

    # STRICT first
    k1 = (seg, ch, rn, ic)
    if k1 in global_index_map:
        return global_index_map[k1]

    # ignore icode but KEEP seg
    k2 = (seg, ch, rn, None)
    if k2 in global_index_map:
        return global_index_map[k2]

    # chain-only fallback ONLY if present (meaning unique)
    k3 = (ch, rn, ic)
    if k3 in global_index_map:
        return global_index_map[k3]

    k4 = (ch, rn, None)
    if k4 in global_index_map:
        return global_index_map[k4]

    return None


def run_adj_matrix(jobname, rcutt, pdb_info_dict, gui):
    """
    Calculates adj and edgeweight matrices for all PDB structures in pdb_info_dict.
    Saves results into each PDB's job subfolder and stores them back into pdb_info_dict.
    """
    try:
        job_dir = _resolve_job_dir(jobname)

        for pdb_id, pdb_data in (pdb_info_dict or {}).items():

            if str(pdb_id).strip() == "__ENSEMBLE__":
                continue

            if 'residue_chain_map' not in (pdb_data or {}):
                gui.log_output(f"⚠ [Warning] No loaded data found for {pdb_id}, skipping...\n")
                continue

            # ✅ Calculate matrices
            adj, ew, node_index_map = calculate_adj_and_edgeweight_matrix(pdb_data, rcutt)

            # ✅ Store back into dict
            pdb_data['adj_matrix'] = adj
            pdb_data['edgeweight_matrix'] = ew
            pdb_data['node_index_map'] = node_index_map

            # ✅ Create output folder
            pdb_folder = os.path.join(job_dir, pdb_id)
            os.makedirs(pdb_folder, exist_ok=True)

            # ✅ Save to files
            adj_matrix_file = os.path.join(pdb_folder, f"{pdb_id}_adj_matrix.txt")
            edgeweight_matrix_file = os.path.join(pdb_folder, f"{pdb_id}_edgeweight_matrix.txt")

            np.savetxt(adj_matrix_file, adj, fmt='%.6f')
            np.savetxt(edgeweight_matrix_file, ew, fmt='%.6f')

            gui.log_output(f"✅ adj & edgeweight matrices saved for {pdb_id}.\n")

    except Exception as e:
        gui.log_output(f"❌ Error calculating adj matrices: {e}\n")


def calculate_yens_k_shortest_paths(pdb_data, source_idx, sink_idx, k, gui, logger=None):
    import networkx as nx
    from itertools import islice
    import numpy as np

    G = nx.Graph()
    adj = pdb_data['adj_matrix']
    edgeweight = pdb_data.get('edgeweight_matrix')

    if edgeweight is None:
        _log(logger,"⚠ edgeweight_matrix not found; falling back to unit weights.\n")
        edgeweight = np.where(adj != 0, 1.0, 0.0)

    if edgeweight.shape != adj.shape:
        _log(logger,
            f"⚠ edgeweight shape {edgeweight.shape} != adj shape {adj.shape}; "
            f"using unit weights.\n"
        )
        edgeweight = np.where(adj != 0, 1.0, 0.0)

    num_nodes = len(adj)
    _log(logger,
        f"📌 calculate_yens_k_shortest_paths: source={source_idx}, "
        f"sink={sink_idx}, k={k}\n"
    )

    # düğümleri ekle
    for i in range(num_nodes):
        G.add_node(i)

    # kenarları ekle (adj != 0)
    rows, cols = np.where(
        (adj != 0) & (np.arange(num_nodes)[:, None] != np.arange(num_nodes))
    )
    for i, j in zip(rows, cols):
        G.add_edge(i, j, weight=float(edgeweight[i][j]))

    # hızlı özet
    _log(logger,
        f"   🔧 Graph summary: nodes={G.number_of_nodes()}, "
        f"edges={G.number_of_edges()}\n"
    )

    components = list(nx.connected_components(G))

    # source / sink graph’ta mı?
    if source_idx not in G.nodes or sink_idx not in G.nodes:
        _log(logger,
            f"⚠ Warning: source {source_idx} or target {sink_idx} "
            f"not found in graph nodes.\n"
        )
        return [], []

    # hangi component içindeler?
    comp_src = comp_snk = None
    for ci, comp in enumerate(components):
        if source_idx in comp:
            comp_src = ci
        if sink_idx in comp:
            comp_snk = ci


    if comp_src is not None and comp_snk is not None and comp_src != comp_snk:
        _log(logger,
            f"⚠ source ({source_idx}) and sink ({sink_idx}) are in "
            f"different components → no path possible.\n"
        )
        return [], []

    # degree bilgisi
    deg_s = G.degree[source_idx]
    deg_t = G.degree[sink_idx]


    # ✅ K-paths hesapla
    try:
        _log(logger, "⏳ Calculating paths…\n")
        paths = list(
            islice(
                nx.shortest_simple_paths(G, source_idx, sink_idx, weight='weight'),
                k
            )
        )
        costs = [nx.path_weight(G, path, weight='weight') for path in paths[:k]]
        _log(logger,
            f"   ✅ Found {len(paths)} paths (requested k={k}).\n"
        )
    except nx.NetworkXNoPath:
        _log(logger,
            f"⚠ No path found for pair {source_idx} → {sink_idx} "
            f"(but nodes are in same graph).\n"
        )
        return [], []

    return paths[:k], costs[:k]


def calculate_shortest_paths(jobname, k, pdb_info_dict, gui,logger=None):
    import numpy as np

    _log(logger,f"🔍 Calculation started - Job: {jobname}, k={k}\n")
    _log(logger,f"🔍  {len(pdb_info_dict)} PDB found in current job.\n")
    paths_dict = {}
    total_paths = 0

    for pdb_id, pdb_data in pdb_info_dict.items():
        res_dict = pdb_data.get('residue_dict', {}) or {}
        src_list = res_dict.get('source_residues') or []
        snk_list = res_dict.get('sink_residues') or []

        _log(logger,
            f"\n📁 [{pdb_id}] residue_dict summary: "
            f"{len(src_list)} sources, {len(snk_list)} sinks.\n"
        )

        # ✅ Önce kaynak/hedef listesi var mı kontrol et
        if not src_list or not snk_list:
            _log(logger,
                f"⚠ {pdb_id}: source/sink list is empty. "
                f"Run alignment or use 'Skip alignment' to seed indices.\n"
            )
            continue

        # adjacency & edgeweight kontrolü
        adj = pdb_data.get('adj_matrix')
        ew = pdb_data.get('edgeweight_matrix')

        if adj is None or ew is None:
            _log(logger,
                f"⚠ {pdb_id}: adj_matrix or edgeweight_matrix missing, skipping…\n"
            )
            continue

        if adj.shape != ew.shape:
            _log(logger,
                f"⚠ {pdb_id}: adj shape {adj.shape} != edgeweight shape {ew.shape}, "
                f"paths will not be calculated for this structure.\n"
            )
            continue

        nnz = int(np.count_nonzero(adj))
        _log(logger,
            f"   🔬 adj_matrix shape={adj.shape}, non-zero entries={nnz}\n"
        )

        paths_dict[pdb_id] = {}
        per_pdb_paths = 0

        # kaynaklar
        for source in src_list:
            s_idx = source.get('index')
            s_chain = source.get('chain')
            s_resn = source.get('residue_num')
            s_seg = source.get('segname')

            if s_idx is None:
                _log(logger,
                    f"   ⚠ Source missing index → "
                    f"{(s_seg + ':' if s_seg else '')}{s_chain}:{s_resn} (skipping)\n"
                )
                continue

            # hedefler
            for sink in snk_list:
                t_idx = sink.get('index')
                t_chain = sink.get('chain')
                t_resn = sink.get('residue_num')
                t_seg = sink.get('segname')

                if t_idx is None:
                    _log(logger,
                        f"   ⚠ Sink missing index → "
                        f"{(t_seg + ':' if t_seg else '')}{t_chain}:{t_resn} (skipping)\n"
                    )
                    continue

                _log(logger,
                    f"   ➜ Pair: "
                    f"{(s_seg + ':' if s_seg else '')}{s_chain}:{s_resn}[{s_idx}] "
                    f"→ {(t_seg + ':' if t_seg else '')}{t_chain}:{t_resn}[{t_idx}]\n"
                )

                paths, costs = calculate_yens_k_shortest_paths(
                    pdb_data, s_idx, t_idx, k, gui, logger=None
                )

                if not paths:
                    _log(logger,
                        f"   ⚠ 0 path returned for "
                        f"{s_idx} → {t_idx} (see logs above).\n"
                    )
                    continue

                key = f"{s_idx} -> {t_idx}"
                paths_dict[pdb_id][key] = {'paths': paths, 'costs': costs}
                found = len(paths)
                per_pdb_paths += found
                total_paths += found
                _log(logger,
                    f"   ✅ Stored {found} paths for pair {key}.\n"
                )

        _log(logger,
            f"📊 [{pdb_id}] finished: {per_pdb_paths} paths stored "
            f"for {len(paths_dict[pdb_id])} source–sink pairs.\n"
        )

    _log(logger,
        f"\n✅ Global summary: total {total_paths} paths were calculated "
        f"across all structures.\n"
    )

    gui.paths_dict_2 = paths_dict
    gui.pdb_info_dict = pdb_info_dict
    return paths_dict


def save_paths_to_excel(jobname, paths_dict_2, pdb_info_dict, gui=None,logger=None):

    per_pdb_files = []

    # --- k'yi infer et (tüm pair'lerde genelde aynıdır) ---
    def _infer_k(pd2):
        m = 0
        for _pair_dict in pd2.values():
            for _pdata in _pair_dict.values():
                m = max(m, len(_pdata.get("paths", [])))
        return m

    def _split_seg_chain_res(token: str):
        """
        STRICT token:
          SEG:CHAIN:123
          SEG:CHAIN:123A
        Returns: (seg, chain, resseq_str, icode_str_or_empty)
        """
        if token is None:
            return ("", "?", "?", "")

        seg, ch, rn, ic = flex_parse_residue_token(token, strict=True, default_seg="")
        rn_str = str(int(rn)) if rn is not None else "?"
        ic_str = (str(ic) if ic else "")
        return (str(seg), str(ch), rn_str, ic_str)

    k_infer = _infer_k(paths_dict_2)

    # --- NORMALİZASYONU TEK SEFERDE HESAPLA (0–1 aralığında) ---
    all_normalized_frequencies = compute_all_normalized_frequencies(
        paths_dict_2,
        pdb_info_dict=pdb_info_dict,
        k=k_infer
    )

    # ---- PER-PDB DOSYALAR ----
    for pdb_key, pair_dict in paths_dict_2.items():
        pdb_base = _base_only(pdb_key)
        job_dir  = _resolve_job_dir(jobname)
        pdb_dir  = os.path.join(job_dir, pdb_base)
        os.makedirs(pdb_dir, exist_ok=True)
        file_pdb = os.path.join(pdb_dir, f"{pdb_base}_paths_and_frequencies.xlsx")
        wb = xlsxwriter.Workbook(file_pdb)

        # --- Sheet: Paths ---
        ws_paths = wb.add_worksheet("Paths")
        headers = ["PDB ID","Source Chain","Source Residue","Sink Chain","Sink Residue",
                   "Path No","Path","Cost"]
        for c, h in enumerate(headers):
            ws_paths.write(0, c, h)

        row_p = 1
        for _, pdata in pair_dict.items():
            paths = pdata.get('paths', []) or []
            costs = pdata.get('costs', []) or []
            for i, (path, cost) in enumerate(zip(paths, costs)):
                if not path:
                    continue

                # Token formatı 'SEG:CHAIN:RES' veya 'CHAIN:RES' olabilir
                src_seg, src_ch, src_res, src_ic = flex_parse_residue_token(pdata['paths'][0][0])
                sink_seg, sink_ch, sink_res, sink_ic = flex_parse_residue_token(pdata['paths'][0][-1])

                ws_paths.write(row_p, 0, pdb_base)
                ws_paths.write(row_p, 1, src_ch)
                ws_paths.write(row_p, 2, src_res)
                ws_paths.write(row_p, 3, sink_ch)
                ws_paths.write(row_p, 4, sink_res)
                ws_paths.write_number(row_p, 5, i + 1)
                ws_paths.write(row_p, 6, " → ".join(path))
                try:
                    ws_paths.write_number(row_p, 7, float(cost))
                except (TypeError, ValueError):
                    ws_paths.write(row_p, 7, cost)
                row_p += 1

        # --- Sheet: Frequencies (ham sayımlar, per-PDB) ---
        ws_freq = wb.add_worksheet("Frequencies")

        # Bu PDB'deki tüm iç düğümler (source/sink hariç)
        all_residues = sorted(
            {
                rc
                for pdata in pair_dict.values()
                for path in (pdata.get('paths', []) or [])
                for rc in path[1:-1]
            },
            key=_sort_residue_token_key
        )

        # Başlıklar: 3 satır (SEG / CHAIN / RES)
        # İlk 5 kolon: [PDB ID, src_ch, src_res, sink_ch, sink_res] (bunları da yazıyoruz)
        ws_freq.write(2, 0, "PDB ID")
        ws_freq.write(2, 1, "Source Chain")
        ws_freq.write(2, 2, "Source Residue")
        ws_freq.write(2, 3, "Sink Chain")
        ws_freq.write(2, 4, "Sink Residue")

        for col, rc in enumerate(all_residues, start=5):
            seg, ch, rn, ic = _split_seg_chain_res(rc)
            ws_freq.write(0, col, seg)  # SEG
            ws_freq.write(1, col, ch)   # CHAIN
            ws_freq.write(2, col, rn)   # RES

        total_counts = {rc: 0 for rc in all_residues}
        row_f = 3
        for _, pdata in pair_dict.items():
            freq = {rc: 0 for rc in all_residues}

            for path in (pdata.get('paths', []) or []):
                for rc in path[1:-1]:
                    if rc in freq:
                        freq[rc] += 1
                        total_counts[rc] += 1

            if pdata.get('paths'):
                src_seg, src_ch, src_res, src_ic = flex_parse_residue_token(pdata['paths'][0][0])
                sink_seg, sink_ch, sink_res, sink_ic = flex_parse_residue_token(pdata['paths'][0][-1])
                ws_freq.write(row_f, 1, src_ch)
                ws_freq.write(row_f, 2, src_res)
                ws_freq.write(row_f, 3, sink_ch)
                ws_freq.write(row_f, 4, sink_res)

            ws_freq.write(row_f, 0, pdb_base)
            for col, rc in enumerate(all_residues, start=5):
                ws_freq.write_number(row_f, col, freq[rc])
            row_f += 1

        # TOTAL (ham)
        ws_freq.write(row_f, 0, "TOTAL")
        for col, rc in enumerate(all_residues, start=5):
            ws_freq.write_number(row_f, col, total_counts[rc])

        wb.close()
        per_pdb_files.append(file_pdb)
        if gui:
            _log(logger,f"📄 Saved per-PDB Excel: {file_pdb}\n")

    # ---- OVERALL JOB-LEVEL ----
    job_dir = _resolve_job_dir(jobname)
    job_label = os.path.basename(os.path.normpath(job_dir))
    overall_file = os.path.join(job_dir, f"{job_label}_frequencies.xlsx")

    wb2 = xlsxwriter.Workbook(overall_file)
    try:
        # ========== 1) SUMMARY SHEET ==========
        ws_sum = wb2.add_worksheet("Summary")
        ws_sum.write(0, 0, "Metric")
        ws_sum.write(0, 1, "Value")

        num_pdbs = len(paths_dict_2)

        global_sources = set()
        global_sinks   = set()
        total_paths_global = 0
        num_pairs_global = 0

        for _pdb_key, pair_dict in paths_dict_2.items():
            num_pairs_global += len(pair_dict)
            for _pair_key, pdata in pair_dict.items():
                paths = pdata.get("paths", []) or []
                total_paths_global += len(paths)
                for path in paths:
                    if len(path) >= 2:
                        global_sources.add(path[0])
                        global_sinks.add(path[-1])

        ws_sum.write(1, 0, "#PDB structures")
        ws_sum.write_number(1, 1, num_pdbs)

        ws_sum.write(2, 0, "#Unique source residues")
        ws_sum.write_number(2, 1, len(global_sources))

        ws_sum.write(3, 0, "#Unique sink residues")
        ws_sum.write_number(3, 1, len(global_sinks))

        ws_sum.write(4, 0, "#Total paths (all PDBs)")
        ws_sum.write_number(4, 1, total_paths_global)

        ws_sum.write(5, 0, "k (paths per source–sink pair)")
        ws_sum.write_number(5, 1, int(k_infer))

        ws_sum.write(6, 0, "#Source–sink pairs (all PDBs)")
        ws_sum.write_number(6, 1, int(num_pairs_global))

        # ========== 2) PATH COUNTS (PER PDB) SHEET ==========
        from collections import defaultdict
        ws_counts = wb2.add_worksheet("Path Counts (Per PDB)")

        ws_counts.write(0, 0, "PDB ID")
        ws_counts.write(0, 1, "SEG")
        ws_counts.write(0, 2, "Chain")
        ws_counts.write(0, 3, "Residue")
        ws_counts.write(0, 4, "Residue Token")
        ws_counts.write(0, 5, "#Paths (this PDB)")

        row = 1
        for pdb_key, pair_dict in paths_dict_2.items():
            pdb_base = _base_only(pdb_key)
            per_pdb_counts = defaultdict(int)

            for pdata in pair_dict.values():
                for path in (pdata.get("paths", []) or []):
                    for rc in set(path[1:-1]):
                        per_pdb_counts[rc] += 1

            for rc in sorted(per_pdb_counts.keys(), key=_sort_residue_token_key):
                seg, ch, rn, ic = _split_seg_chain_res(rc)
                ws_counts.write(row, 0, pdb_base)
                ws_counts.write(row, 1, seg)
                ws_counts.write(row, 2, ch)
                ws_counts.write(row, 3, rn)
                ws_counts.write(row, 4, rc)
                ws_counts.write_number(row, 5, per_pdb_counts[rc])
                row += 1

            row += 1  # boş satır

        # ========== 3) PERCENT FREQUENCIES SHEET ==========
        ws_pct = wb2.add_worksheet("Percent Frequencies")

        # Tüm yapılar için global residue listesi (iç düğümler)
        all_residues_global = sorted(
            {
                rc
                for _pair_dict in paths_dict_2.values()
                for _pdata in _pair_dict.values()
                for path in (_pdata.get("paths", []) or [])
                for rc in path[1:-1]
            },
            key=_sort_residue_token_key
        )

        # Başlıklar: 3 satır (SEG / CHAIN / RES)
        ws_pct.write(0, 0, "PDB ID")
        ws_pct.write(1, 0, "")
        ws_pct.write(2, 0, "")

        for col, rc in enumerate(all_residues_global, start=1):
            seg, ch, rn, ic = _split_seg_chain_res(rc)
            ws_pct.write(0, col, seg)  # SEG
            ws_pct.write(1, col, ch)   # CHAIN
            ws_pct.write(2, col, rn)   # RES

        # Veri satırları
        row_p = 3
        for pdb_base_key, norm_map in all_normalized_frequencies.items():
            ws_pct.write(row_p, 0, pdb_base_key)
            for col, rc in enumerate(all_residues_global, start=1):
                v = float(norm_map.get(rc, 0.0))  # 0–1
                ws_pct.write_number(row_p, col, v)
            row_p += 1

    finally:
        wb2.close()

    if gui:
        _log(logger,f"📗 Saved (overall): {overall_file}\n")

    return per_pdb_files, overall_file, all_normalized_frequencies


# ============================================================
# PATH SIMILARITY (NEW LOGIC) - FUNCTIONS
# ============================================================
# ============================================================
# CO-OCCURRENCE BACKBONE (HOCANIN İSTEDİĞİ) - FUNCTIONS
# ============================================================

import os
import re

def _safe_int(x):
    try:
        return int(x)
    except Exception:
        return None

def run_cooccurrence_backbone_for_one_structure(
    pdb_key,
    paths_dict_2,
    pdb_info_dict,
    out_dir,
    logger=None,
    selected_pairs=None,
    strict: bool = False,
    save_counts_png: bool = False,
    do_kmeans: bool = False,
    kmeans_k: int = 4,
    write_diagnostics: bool = True,
):
    """
    Backbone (co-occurrence) for ONE structure:
      - Each path -> N-length binary vector x_p
      - C = sum_p x_p x_p^T = M^T M  (N x N)
      - For visualization: keep ONLY nodes that actually appear in selected paths
        => C_used = C[used_idx, used_idx] (m x m)

    Outputs:
      - percent heatmap
      - optional count heatmap
      - long-format Excel with pairwise values
      - optional KMeans txt
      - diagnostics JSON
    """
    import os
    import re
    import json
    import numpy as np
    import pandas as pd

    os.makedirs(out_dir, exist_ok=True)

    def _log_local(msg: str):
        try:
            if logger is None:
                return
            if hasattr(logger, "log_output"):
                logger.log_output(msg)
            else:
                print(msg)
        except Exception:
            pass

    def _safe_int(x):
        try:
            return int(x)
        except Exception:
            return None

    def _split_token_any(s: str):
        s = (s or "").strip().replace(";", ",")
        s = re.sub(r"\s+", "", s)
        s = s.replace(",", ":")
        parts = [p for p in s.split(":") if p != ""]

        if len(parts) < 2:
            return ("", "", None, None)

        if len(parts) == 2:
            seg = ""
            ch = parts[0]
            rn_raw = parts[1]
        else:
            seg = ":".join(parts[:-2])
            ch = parts[-2]
            rn_raw = parts[-1]

        ch = str(ch).strip().upper()

        digits = "".join([c for c in str(rn_raw) if c.isdigit()])
        if not digits:
            return (seg.strip(), ch, None, None)
        rn_int = int(digits)

        tail = "".join([c for c in str(rn_raw) if c.isalpha()])
        ic = tail.strip() if tail else None

        return (seg.strip(), ch, rn_int, ic)

    pdb_data = (pdb_info_dict or {}).get(pdb_key) or (pdb_info_dict or {}).get(str(pdb_key)) or {}
    if not isinstance(pdb_data, dict) or not pdb_data:
        _log_local(f"⚠ Backbone: pdb_data not found for {pdb_key}\n")
        return []

    adj = pdb_data.get("adj_matrix", None)
    if adj is None:
        _log_local(f"⚠ Backbone: adj_matrix missing for {pdb_key}\n")
        return []

    n_adj = int(adj.shape[0])

    pair_dict = (paths_dict_2 or {}).get(pdb_key, {}) or {}
    if not isinstance(pair_dict, dict) or not pair_dict:
        _log_local(f"⚠ Backbone: no pairs for {pdb_key}\n")
        return []

    rcm = pdb_data.get("residue_chain_map", {}) or {}

    uid_to_idx = {}
    uid_to_idx_noseg = {}
    chainrnic_to_idx = {}
    chainrn_to_idx = {}
    idx_to_label = {}

    max_meta_idx = -1

    for ch_key, residues in rcm.items():
        for r in (residues or []):
            chU = _real_chain_from_residue(r, ch_key).upper()
        for r in (residues or []):
            gi = _safe_int(r.get("index", None))
            if gi is None:
                continue
            if gi > max_meta_idx:
                max_meta_idx = gi

            rn_raw = r.get("residue_num", None)
            digits = "".join([c for c in str(rn_raw) if c.isdigit()])
            if not digits:
                continue
            rn_i = int(digits)

            ic = r.get("icode", None)
            ic = str(ic).strip() if ic not in (None, "", " ") else None

            seg = ""
            all_segs = r.get("all_segnames") or []
            if all_segs:
                for sg in all_segs:
                    if sg is None:
                        continue
                    sg = str(sg).strip()
                    if sg:
                        seg = sg
                        break
            if not seg:
                seg0 = r.get("segname", None)
                seg = str(seg0).strip() if seg0 not in (None, "", " ") else ""

            seg = str(seg).strip()

            uid_to_idx[(seg, chU, rn_i, ic)] = gi
            uid_to_idx[(seg, chU, rn_i, None)] = uid_to_idx.get((seg, chU, rn_i, None), gi)
            uid_to_idx_noseg[("", chU, rn_i, ic)] = gi
            uid_to_idx_noseg[("", chU, rn_i, None)] = uid_to_idx_noseg.get(("", chU, rn_i, None), gi)
            chainrnic_to_idx[(chU, rn_i, ic)] = gi
            chainrnic_to_idx[(chU, rn_i, None)] = chainrnic_to_idx.get((chU, rn_i, None), gi)
            chainrn_to_idx[(chU, rn_i)] = gi

            aa3 = str(r.get("residue_name", "UNK")).strip().upper()

            lab = _format_plot_residue_name(
                chain=chU,
                resnum=rn_i,
                aa3=aa3,
                segname=seg,
                icode=ic,
            )

            idx_to_label[gi] = lab

    n_nodes = max(n_adj, (max_meta_idx + 1) if max_meta_idx >= 0 else n_adj)

    if selected_pairs:
        sel = set(selected_pairs)
        keys_iter = [k for k in pair_dict.keys() if k in sel]
    else:
        keys_iter = list(pair_dict.keys())

    all_paths = []
    for pk in keys_iter:
        pdata = pair_dict.get(pk, {}) or {}
        for p in (pdata.get("paths", []) or []):
            if p:
                all_paths.append(p)

    if not all_paths:
        _log_local(f"⚠ Backbone: no paths after filtering for {pdb_key}\n")
        return []

    seen_zero = False
    seen_n = False
    scan_lim = 5000
    scanned = 0
    for p in all_paths:
        for x in p:
            if scanned >= scan_lim:
                break
            scanned += 1
            gi = _safe_int(x) if not isinstance(x, (tuple, dict, list)) else None
            if gi is None:
                continue
            if gi == 0:
                seen_zero = True
            if gi == n_nodes:
                seen_n = True
        if scanned >= scan_lim:
            break
    one_based_hint = (not seen_zero) and seen_n

    unmapped_examples = []
    oor_examples = []

    def _node_to_idx(node):
        if isinstance(node, dict):
            seg = str(node.get("segname") or node.get("seg") or "").strip()
            ch = str(node.get("chain") or node.get("chain_id") or node.get("chainID") or "").strip().upper()
            rn = node.get("residue_num") if "residue_num" in node else node.get("resid")
            rn_i = _safe_int(rn) if rn is not None else None
            ic = node.get("icode") or None
            ic = str(ic).strip() if ic not in (None, "", " ") else None

            if not ch or rn_i is None:
                return None

            gi = uid_to_idx.get((seg, ch, rn_i, ic))
            if gi is None:
                gi = uid_to_idx.get((seg, ch, rn_i, None))
            if gi is None:
                gi = uid_to_idx_noseg.get(("", ch, rn_i, ic))
            if gi is None:
                gi = uid_to_idx_noseg.get(("", ch, rn_i, None))
            if gi is None:
                gi = chainrnic_to_idx.get((ch, rn_i, ic))
            if gi is None:
                gi = chainrnic_to_idx.get((ch, rn_i, None))
            if gi is None:
                gi = chainrn_to_idx.get((ch, rn_i))
            if gi is None:
                return None

            gi = int(gi)
            return gi if 0 <= gi < n_nodes else None

        if isinstance(node, (tuple, list)) and len(node) >= 2:
            try:
                ch = str(node[0]).strip().upper()
                rn_i = _safe_int(node[1])
                ic = None
                if len(node) >= 3 and node[2] not in (None, "", " "):
                    ic = str(node[2]).strip()
                if ch and rn_i is not None:
                    gi = chainrnic_to_idx.get((ch, rn_i, ic))
                    if gi is None:
                        gi = chainrnic_to_idx.get((ch, rn_i, None))
                    if gi is None:
                        gi = chainrn_to_idx.get((ch, rn_i))
                    if gi is None:
                        return None
                    gi = int(gi)
                    return gi if 0 <= gi < n_nodes else None
            except Exception:
                return None

        if isinstance(node, str):
            s = node.strip()

            gi = _safe_int(s)
            if gi is not None:
                if 0 <= gi < n_nodes:
                    return gi
                if one_based_hint and 1 <= gi <= n_nodes:
                    gi2 = gi - 1
                    return gi2 if 0 <= gi2 < n_nodes else None
                return None

            seg, ch, rn_i, ic = _split_token_any(s)
            if ch and rn_i is not None:
                gi = uid_to_idx.get((seg, ch, rn_i, ic))
                if gi is None:
                    gi = uid_to_idx.get((seg, ch, rn_i, None))
                if gi is None:
                    gi = uid_to_idx_noseg.get(("", ch, rn_i, ic))
                if gi is None:
                    gi = uid_to_idx_noseg.get(("", ch, rn_i, None))
                if gi is None:
                    gi = chainrnic_to_idx.get((ch, rn_i, ic))
                if gi is None:
                    gi = chainrnic_to_idx.get((ch, rn_i, None))
                if gi is None:
                    gi = chainrn_to_idx.get((ch, rn_i))
                if gi is None:
                    return None
                gi = int(gi)
                return gi if 0 <= gi < n_nodes else None

        gi = _safe_int(node)
        if gi is not None:
            if 0 <= gi < n_nodes:
                return gi
            if one_based_hint and 1 <= gi <= n_nodes:
                gi2 = gi - 1
                return gi2 if 0 <= gi2 < n_nodes else None

        return None

    idx_paths = []
    skipped_all_unmapped = 0
    total_nodes_seen = 0
    total_nodes_mapped = 0

    for p in all_paths:
        nodes = set()
        for x in p:
            total_nodes_seen += 1
            gi = _node_to_idx(x)
            if gi is None:
                if len(unmapped_examples) < 20:
                    unmapped_examples.append(str(x))
                continue
            total_nodes_mapped += 1
            if 0 <= gi < n_nodes:
                nodes.add(int(gi))
            else:
                if len(oor_examples) < 20:
                    oor_examples.append(str(gi))
                if strict:
                    raise ValueError(f"Node index out of range: {gi} (n_nodes={n_nodes})")

        if nodes:
            idx_paths.append(sorted(nodes))
        else:
            skipped_all_unmapped += 1

    K = len(idx_paths)
    pdb_base = _base_only(pdb_key)

    if K == 0:
        _log_local(
            f"⚠ Backbone: all paths unmapped for {pdb_key} | "
            f"nodes_seen={total_nodes_seen} mapped={total_nodes_mapped} "
            f"(one_based_hint={one_based_hint})\n"
        )
        if write_diagnostics:
            try:
                diag = {
                    "pdb_key": str(pdb_key),
                    "pdb_base": pdb_base,
                    "n_adj": n_adj,
                    "n_nodes": n_nodes,
                    "max_meta_idx": max_meta_idx,
                    "one_based_hint": bool(one_based_hint),
                    "paths_total": int(len(all_paths)),
                    "paths_used": 0,
                    "skipped_all_unmapped": int(skipped_all_unmapped),
                    "nodes_seen": int(total_nodes_seen),
                    "nodes_mapped": int(total_nodes_mapped),
                    "unmapped_examples": unmapped_examples,
                    "out_of_range_examples": oor_examples,
                }
                out_json = os.path.join(out_dir, f"BACKBONE__DIAG__{pdb_base}.json")
                with open(out_json, "w", encoding="utf-8") as f:
                    json.dump(diag, f, indent=2)
            except Exception:
                pass
        return []

    M = np.zeros((K, n_nodes), dtype=np.uint8)
    for i, nodes in enumerate(idx_paths):
        M[i, nodes] = 1

    C = (M.T @ M).astype(np.float32)

    K_total = float(K)
    C_percent = (100.0 * C / K_total).astype(np.float32) if K_total > 0 else np.zeros_like(C, dtype=np.float32)

    used_idx = sorted(set(int(j) for nodes in idx_paths for j in nodes))
    m = len(used_idx)

    if m > 0:
        C_plot = C[np.ix_(used_idx, used_idx)]
        C_percent_plot = C_percent[np.ix_(used_idx, used_idx)]
    else:
        C_plot = C
        C_percent_plot = C_percent
        used_idx = list(range(C.shape[0]))
        m = len(used_idx)

    labels = [idx_to_label.get(gi, str(gi)) for gi in used_idx]

    tick_pos = np.arange(m)
    tick_lab = labels

    if m <= 60:
        fs = 10
    elif m <= 120:
        fs = 7
    else:
        fs = 5
    rot = 90

    w = min(26.0, max(12.0, 0.28 * m))
    h = min(22.0, max(10.0, 0.28 * m))

    outs = []

    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    def _masked_zero(A):
        A = np.asarray(A, dtype=float).copy()
        np.fill_diagonal(A, np.nan)
        return np.ma.masked_invalid(np.ma.masked_where(A <= 0, A))

    cmap_main = plt.get_cmap("PuRd").copy()
    cmap_main.set_bad(color="white")

    out_png = os.path.join(out_dir, f"BACKBONE__PERCENT__{pdb_base}__K{K}__m{m}.png")
    fig = plt.figure(figsize=(w, h), dpi=350)
    ax = fig.add_subplot(111)

    im = ax.imshow(
        _masked_zero(C_percent_plot),
        interpolation="nearest",
        aspect="equal",
        cmap=cmap_main,
        vmin=0,
        vmax=100
    )

    ax.plot([-0.5, m - 0.5], [-0.5, m - 0.5], color="black", linewidth=0.6, alpha=0.8)

    ax.set_title(
        f"{pdb_base} | Backbone (percent, max=100) | K={K} | used={m} | "
        f"mapped={total_nodes_mapped}/{total_nodes_seen}"
    )
    ax.set_xlabel("Residue", fontsize=13)
    ax.set_ylabel("Residue", fontsize=13)

    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_lab, rotation=rot, fontsize=fs)
    ax.set_yticks(tick_pos)
    ax.set_yticklabels(tick_lab, fontsize=fs)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Percent")

    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)
    outs.append(out_png)

    if save_counts_png:
        out_png2 = os.path.join(out_dir, f"BACKBONE__COUNT__{pdb_base}__K{K}__m{m}.png")
        fig = plt.figure(figsize=(w, h), dpi=350)
        ax = fig.add_subplot(111)

        im = ax.imshow(_masked_zero(C_plot), interpolation="nearest", aspect="equal", cmap=cmap_main)
        ax.plot([-0.5, m - 0.5], [-0.5, m - 0.5], color="black", linewidth=0.6, alpha=0.8)

        ax.set_title(f"{pdb_base} | Backbone (% of paths) | K={K} | used={m}")
        ax.set_xlabel("Residue", fontsize=13)
        ax.set_ylabel("Residue", fontsize=13)

        ax.set_xticks(tick_pos)
        ax.set_xticklabels(tick_lab, rotation=rot, fontsize=fs)
        ax.set_yticks(tick_pos)
        ax.set_yticklabels(tick_lab, fontsize=fs)

        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Co-occurrence (% of paths)")

        fig.tight_layout()
        fig.savefig(out_png2, bbox_inches="tight")
        plt.close(fig)
        outs.append(out_png2)

    out_xlsx = os.path.join(out_dir, f"BACKBONE__PAIRS__{pdb_base}__K{K}__m{m}.xlsx")

    pair_rows = []
    for a, gi in enumerate(used_idx):
        for b, gj in enumerate(used_idx):
            if a == b:
                continue
            count_val = float(C_plot[a, b])
            percent_val = float(C_percent_plot[a, b])

            pair_rows.append({
                "i_index": int(gi),
                "j_index": int(gj),
                "i_label": idx_to_label.get(gi, str(gi)),
                "j_label": idx_to_label.get(gj, str(gj)),
                "count": count_val,
                "percent": percent_val,
            })

    df_pairs = pd.DataFrame(pair_rows)
    df_pairs_nonzero = df_pairs[df_pairs["count"] > 0].copy()

    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as writer:
        df_pairs_nonzero.to_excel(writer, sheet_name="pairs_long_format", index=False)

        df_count = pd.DataFrame(C_plot, index=labels, columns=labels)
        df_percent = pd.DataFrame(C_percent_plot, index=labels, columns=labels)

        df_count.to_excel(writer, sheet_name="count_matrix")
        df_percent.to_excel(writer, sheet_name="percent_matrix")

    outs.append(out_xlsx)

    if do_kmeans:
        try:
            from sklearn.cluster import KMeans
            X = C_percent
            km = KMeans(n_clusters=int(kmeans_k), n_init=10, random_state=0)
            labels_km = km.fit_predict(X)

            out_txt = os.path.join(out_dir, f"BACKBONE__KMEANS__{pdb_base}__K{kmeans_k}.txt")
            with open(out_txt, "w", encoding="utf-8") as f:
                for i, lab in enumerate(labels_km):
                    f.write(f"{i}\t{lab}\n")
            outs.append(out_txt)
        except Exception as e:
            _log_local(f"⚠ Backbone: KMeans failed: {e}\n")

    if write_diagnostics:
        try:
            diag = {
                "pdb_key": str(pdb_key),
                "pdb_base": pdb_base,
                "n_adj": int(n_adj),
                "n_nodes": int(n_nodes),
                "max_meta_idx": int(max_meta_idx),
                "one_based_hint": bool(one_based_hint),
                "paths_total": int(len(all_paths)),
                "paths_used": int(K),
                "skipped_all_unmapped": int(skipped_all_unmapped),
                "nodes_seen": int(total_nodes_seen),
                "nodes_mapped": int(total_nodes_mapped),
                "used_idx_count": int(len(used_idx)),
                "used_labels_preview": labels[:20],
                "tick_count": int(len(tick_pos)),
                "excel_pairs_rows_nonzero": int(len(df_pairs_nonzero)),
                "unmapped_examples": unmapped_examples,
                "out_of_range_examples": oor_examples,
                "outputs": outs,
            }
            out_json = os.path.join(out_dir, f"BACKBONE__DIAG__{pdb_base}.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(diag, f, indent=2)
            outs.append(out_json)
        except Exception:
            pass

    _log_local(
        f"Backbone {pdb_base}:\n"
        f"  paths_total={len(all_paths)} paths_used={K} skipped_all_unmapped={skipped_all_unmapped}\n"
        f"  nodes_seen={total_nodes_seen} nodes_mapped={total_nodes_mapped} one_based_hint={one_based_hint}\n"
        f"  N(adj)={n_adj}  N(final)={n_nodes}  used(m)={m}\n"
        f"  out={out_png}\n"
    )

    return outs


def run_cooccurrence_backbone_ensemble(
    paths_dict_2,
    pdb_info_dict,
    out_dir,
    logger=None,
    selected_pdb_keys=None,
    selected_pairs=None,
    strict: bool = False,
    save_counts_png: bool = False,
    do_kmeans: bool = False,
    kmeans_k: int = 4,
    write_diagnostics: bool = True,
    generate_per_structure: bool = True,
):
    import os
    import copy

    def _log(msg: str):
        try:
            if logger is None:
                print(msg)
                return
            if hasattr(logger, "log_output"):
                logger.log_output(msg)
            else:
                print(msg)
        except Exception:
            pass

    os.makedirs(out_dir, exist_ok=True)
    per_struct_dir = os.path.join(out_dir, "per_structure")
    ens_dir = os.path.join(out_dir, "ensemble")
    os.makedirs(per_struct_dir, exist_ok=True)
    os.makedirs(ens_dir, exist_ok=True)

    if not isinstance(paths_dict_2, dict) or not paths_dict_2:
        _log("⚠ Backbone Ensemble: paths_dict_2 is empty.\n")
        return []

    all_pdb_keys = list(paths_dict_2.keys())

    if selected_pdb_keys is None or (
        isinstance(selected_pdb_keys, (list, tuple, set)) and len(selected_pdb_keys) == 0
    ):
        sel_pdb_keys = all_pdb_keys
        sel_mode = f"ALL ({len(sel_pdb_keys)})"
    else:
        sel_set = {str(x).strip() for x in selected_pdb_keys}
        sel_pdb_keys = [k for k in all_pdb_keys if str(k).strip() in sel_set]
        sel_mode = f"{len(sel_pdb_keys)}/{len(all_pdb_keys)}"

    if not sel_pdb_keys:
        _log("⚠ Backbone Ensemble: no pdb_keys selected (after filtering).\n")
        return []

    _log(f"🧩 Backbone Ensemble: selected structures = {sel_mode}\n")

    outs = []

    if generate_per_structure:
        for pdb_key in sel_pdb_keys:
            pdb_base = _base_only(pdb_key)
            out_one = os.path.join(per_struct_dir, pdb_base)
            os.makedirs(out_one, exist_ok=True)

            try:
                out_files = run_cooccurrence_backbone_for_one_structure(
                    pdb_key=pdb_key,
                    paths_dict_2=paths_dict_2,
                    pdb_info_dict=pdb_info_dict,
                    out_dir=out_one,
                    logger=logger,
                    selected_pairs=selected_pairs,
                    strict=strict,
                    save_counts_png=save_counts_png,
                    do_kmeans=do_kmeans,
                    kmeans_k=kmeans_k,
                    write_diagnostics=write_diagnostics,
                )
                if out_files:
                    outs.extend(out_files)
            except Exception as e:
                _log(f"⚠ Backbone per-structure failed for {pdb_key}: {e}\n")

    ENS_KEY = "__ENSEMBLE__"
    merged_pair_dict = {}

    for pdb_key in sel_pdb_keys:
        pair_dict = paths_dict_2.get(pdb_key, {}) or {}
        if not isinstance(pair_dict, dict):
            continue

        if selected_pairs:
            keep_pairs = set(selected_pairs)
            pair_iter = [k for k in pair_dict.keys() if k in keep_pairs]
        else:
            pair_iter = list(pair_dict.keys())

        for pair_key in pair_iter:
            pdata = pair_dict.get(pair_key, {}) or {}
            paths = pdata.get("paths", []) or []
            costs = pdata.get("costs", []) or []

            if not paths:
                continue

            if pair_key not in merged_pair_dict:
                merged_pair_dict[pair_key] = {"paths": [], "costs": []}

            merged_pair_dict[pair_key]["paths"].extend(copy.deepcopy(paths))
            if costs:
                merged_pair_dict[pair_key]["costs"].extend(copy.deepcopy(costs))

    if not merged_pair_dict:
        _log("⚠ Backbone Ensemble: merged_pair_dict is empty (no paths). Ensemble not generated.\n")
        return outs

    ref_key = sel_pdb_keys[0]
    ref_info = (pdb_info_dict or {}).get(ref_key, None)
    if not isinstance(ref_info, dict) or not ref_info:
        _log("⚠ Backbone Ensemble: cannot create ensemble pdb_info (missing reference pdb_info).\n")
        return outs

    ensemble_pdb_info_dict = dict(pdb_info_dict or {})
    ensemble_pdb_info_dict[ENS_KEY] = ref_info
    merged_paths_dict_2 = {ENS_KEY: merged_pair_dict}

    _log(
        f"🧬 Backbone Ensemble: building ENSEMBLE from {len(sel_pdb_keys)} structures "
        f"(ref index-space={ref_key}) | pairs={len(merged_pair_dict)}\n"
    )

    try:
        out_files_ens = run_cooccurrence_backbone_for_one_structure(
            pdb_key=ENS_KEY,
            paths_dict_2=merged_paths_dict_2,
            pdb_info_dict=ensemble_pdb_info_dict,
            out_dir=ens_dir,
            logger=logger,
            selected_pairs=None,
            strict=strict,
            save_counts_png=save_counts_png,
            do_kmeans=do_kmeans,
            kmeans_k=kmeans_k,
            write_diagnostics=write_diagnostics,
        )
        if out_files_ens:
            outs.extend(out_files_ens)
            _log("✅ Backbone Ensemble: ENSEMBLE outputs saved.\n")
        else:
            _log("⚠ Backbone Ensemble: ENSEMBLE produced no outputs.\n")
    except Exception as e:
        _log(f"❌ Backbone Ensemble failed: {e}\n")

    return outs

def _cosine_similarity_rows_binary(M):
    import numpy as np
    X = np.asarray(M, dtype=np.float32)
    row_norm = np.linalg.norm(X, axis=1)
    row_norm[row_norm == 0] = 1.0
    S = (X @ X.T) / (row_norm[:, None] * row_norm[None, :])
    S = np.clip(S, 0.0, 1.0)
    return S.astype(np.float32)


def _connected_components_from_threshold(S, threshold=0.70):
    """
    Graph-based clustering on a similarity matrix.

    Parameters
    ----------
    S : np.ndarray
        (K x K) similarity matrix in [0,1]
    threshold : float
        Similarity cutoff. Paths with similarity >= threshold are connected.

    Returns
    -------
    clusters : list[list[int]]
        Sorted clusters, each cluster is a sorted list of path indices.
    """
    import numpy as np
    import networkx as nx

    S = np.asarray(S, dtype=np.float64)
    if S.ndim != 2 or S.shape[0] != S.shape[1]:
        raise ValueError("S must be a square similarity matrix.")

    K = int(S.shape[0])
    if K == 0:
        return []
    if K == 1:
        return [[0]]

    G = nx.Graph()
    G.add_nodes_from(range(K))

    for i in range(K):
        for j in range(i + 1, K):
            if float(S[i, j]) >= float(threshold):
                G.add_edge(i, j, weight=float(S[i, j]))

    clusters = [sorted(list(c)) for c in nx.connected_components(G)]
    clusters.sort(key=lambda x: (-len(x), x[0] if x else 10**9))
    return clusters


def _cluster_medoid_cost_weighted(S, members, path_costs):
    import numpy as np

    if not members:
        return None
    if len(members) == 1:
        return int(members[0])

    sub = S[np.ix_(members, members)]
    mean_sim = np.mean(sub, axis=1)

    scores = []
    for i, m in enumerate(members):
        cost = path_costs[m]

        if cost is None or cost <= 0:
            score = mean_sim[i]
        else:
            score = mean_sim[i] / float(cost)

        scores.append(score)

    best_local = int(np.argmax(scores))
    return int(members[best_local])


def _order_paths_by_clusters(clusters):
    order = []
    bounds = []
    start = 0
    for members in clusters:
        members_sorted = sorted(members)
        order.extend(members_sorted)
        end = start + len(members_sorted)
        bounds.append((start, end))
        start = end
    return order, bounds


def _draw_path_order_similarity_heatmap(
    S,
    out_png,
    pdb_base,
    K,
    similarity_threshold,
):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    K_plot = int(S.shape[0])

    fig_w = min(14.0, max(7.5, 0.045 * K_plot + 4.5))
    fig_h = min(13.0, max(6.8, 0.045 * K_plot + 4.0))

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=500)
    ax = fig.add_subplot(111)

    im = ax.imshow(
        S,
        interpolation="nearest",
        aspect="auto",
        cmap="viridis",
        vmin=0,
        vmax=1,
    )

    ax.set_title(
        f"Path similarity matrix ({pdb_base})",
        fontsize=14,
        fontweight="bold",
        pad=10,
    )
    ax.set_xlabel("Path index", fontsize=11, fontweight="bold")
    ax.set_ylabel("Path index", fontsize=11, fontweight="bold")

    # Sparse ticks only
    step = max(1, K_plot // 20)
    ticks = np.arange(0, K_plot, step)

    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t + 1) for t in ticks], rotation=90, fontsize=8)

    ax.set_yticks(ticks)
    ax.set_yticklabels([str(t + 1) for t in ticks], fontsize=8)

    for spine in ax.spines.values():
        spine.set_linewidth(1.3)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cbar.set_label("Cosine similarity", fontsize=10, fontweight="bold")
    cbar.ax.tick_params(labelsize=9)

    fig.text(
        0.015, 0.01,
        f"K = {K} paths | threshold = {similarity_threshold:.2f}",
        fontsize=9
    )

    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def _draw_cluster_size_plot(
    clusters,
    out_png,
    pdb_base,
    K,
    similarity_threshold,
):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    xs = np.arange(1, len(clusters) + 1)
    ys = np.array([len(c) for c in clusters], dtype=float)

    fig = plt.figure(figsize=(10.5, 5.8), dpi=500)
    ax = fig.add_subplot(111)

    if len(ys) > 0 and float(np.max(ys)) > float(np.min(ys)):
        norm = plt.Normalize(vmin=float(np.min(ys)), vmax=float(np.max(ys)))
        colors = cm.cividis(norm(ys))
    else:
        colors = ["#355C7D"] * len(xs)

    ax.bar(xs, ys, color=colors, edgecolor="black", linewidth=0.7, width=0.82)

    ax.set_xlabel("Cluster ID", fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of paths", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Distribution of path families ({pdb_base})",
        fontsize=14,
        fontweight="bold",
        pad=10,
    )

    ax.set_xticks(xs)
    ax.set_xticklabels([f"C{i}" for i in xs], rotation=90, fontsize=9)
    ax.tick_params(axis="y", labelsize=10)

    for spine in ax.spines.values():
        spine.set_linewidth(1.3)

    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.45)
    ax.set_axisbelow(True)

    fig.text(
        0.015, 0.01,
        f"K = {K} paths | threshold = {similarity_threshold:.2f}",
        fontsize=9
    )

    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def _draw_representative_path_summary(
    cluster_rows,
    out_png,
    pdb_base,
    top_n=5,
):
    import textwrap
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    def _fmt_num(x, ndigits=3):
        try:
            if x is None or x == "":
                return ""
            return f"{float(x):.{ndigits}f}"
        except Exception:
            return str(x)

    rows = cluster_rows[:max(1, int(top_n))]
    n = len(rows)

    fig_h = max(4.2, 1.28 * n + 1.2)
    fig = plt.figure(figsize=(15.5, fig_h), dpi=500)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n + 0.42)
    ax.axis("off")

    # Title
    ax.text(
        0.01, n + 0.23,
        f"Representative pathways of major communication families ({pdb_base})",
        fontsize=13.0,
        fontweight="bold",
        va="top",
        ha="left",
    )

    # Column headers
    ax.text(0.03, n + 0.01, "Cluster", fontsize=10, fontweight="bold", va="top")
    ax.text(0.16, n + 0.01, "Path metrics", fontsize=10, fontweight="bold", va="top")
    ax.text(0.30, n + 0.01, "Representative pathway", fontsize=10, fontweight="bold", va="top")

    for i, row in enumerate(rows):
        y0 = n - i - 0.76
        card_h = 0.56

        # subtle highlight for first 3
        if i < 3:
            facecolor = "#F7F9FB"
            accent = "#4C78A8"
        else:
            facecolor = "#FAFAFA"
            accent = "#B8B8B8"

        # main card
        patch = FancyBboxPatch(
            (0.01, y0),
            0.98,
            card_h,
            boxstyle="round,pad=0.008,rounding_size=0.012",
            facecolor=facecolor,
            edgecolor="black",
            linewidth=0.55,
        )
        ax.add_patch(patch)

        # left accent bar
        ax.add_patch(Rectangle((0.012, y0), 0.008, card_h, facecolor=accent, edgecolor="none"))

        cluster_id = row.get("cluster_id", "")
        cluster_size = row.get("cluster_size", "")
        rep_cost = _fmt_num(row.get("representative_cost", ""), ndigits=3)
        rep_eff = _fmt_num(row.get("representative_efficiency", ""), ndigits=2)


        # left block
        left_text = (
            f"Cluster {cluster_id}\n"
            f"paths = {cluster_size}\n"
        )
        ax.text(
            0.03, y0 + card_h / 2,
            left_text,
            fontsize=9.2,
            fontweight="bold",
            va="center",
            ha="left",
            linespacing=1.22,
        )

        # middle block
        mid_text = (
            f"cost = {rep_cost}\n"
            f"efficiency = {rep_eff}"
        )
        ax.text(
            0.16, y0 + card_h / 2,
            mid_text,
            fontsize=9.1,
            va="center",
            ha="left",
            linespacing=1.30,
        )

        # right block: path
        path_text = str(row.get("representative_path_nodes", "")).strip()
        if not path_text:
            path_text = "(no path)"

        ax.text(
            0.27, y0 + card_h / 2,
            path_text,
            fontsize=9.5,
            va="center",
            ha="left",
            linespacing=1.22,
            wrap=True,
        )

    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def run_path_similarity_for_one_structure(
    pdb_key,
    paths_dict_2,
    pdb_info_dict,
    out_dir,
    logger=None,
    selected_pairs=None,
    strict: bool = False,
    similarity_threshold: float = 0.70,
    write_diagnostics: bool = True,
):
    """
    Path similarity for ONE structure.

    Correct logic
    -------------
    1) Collect paths for selected pairs
    2) If paths are already global node indices, DO NOT remap them
    3) Build binary incidence matrix from per-path unique node sets
    4) Compute cosine similarity
    5) Cluster with threshold graph connected components
    6) Choose representative from REAL calculated paths
    7) Write representative/display path using convert_paths_to_residues(...)
       so labels match Path Explorer and other outputs
    """

    import os
    import re
    import json
    import math
    import numpy as np
    import pandas as pd

    os.makedirs(out_dir, exist_ok=True)

    def _log_local(msg: str):
        try:
            if logger is None:
                print(msg)
            elif hasattr(logger, "log_output"):
                logger.log_output(msg)
            else:
                print(msg)
        except Exception:
            pass

    def _safe_int(x):
        try:
            return int(x)
        except Exception:
            return None

    def _safe_float(x):
        try:
            val = float(x)
            if math.isfinite(val):
                return val
            return None
        except Exception:
            return None

    def _split_token_any(s: str):
        s = (s or "").strip().replace(";", ",")
        s = re.sub(r"\s+", "", s)
        s = s.replace(",", ":")
        parts = [p for p in s.split(":") if p != ""]
        if len(parts) < 2:
            return ("", "", None, None)

        if len(parts) == 2:
            seg = ""
            ch = parts[0]
            rn_raw = parts[1]
        else:
            seg = ":".join(parts[:-2])
            ch = parts[-2]
            rn_raw = parts[-1]

        ch = str(ch).strip().upper()

        digits = "".join([c for c in str(rn_raw) if c.isdigit()])
        if not digits:
            return (seg.strip(), ch, None, None)
        rn_int = int(digits)

        tail = "".join([c for c in str(rn_raw) if c.isalpha()])
        ic = tail.strip() if tail else None

        return (seg.strip(), ch, rn_int, ic)

    def _extract_path_and_cost_from_entry(entry, fallback_cost=None):
        cost_keys = [
            "cost", "path_cost", "total_cost", "weight", "distance",
            "length_cost", "cum_cost", "score"
        ]
        path_keys = ["path", "nodes", "residues", "node_path", "route"]

        if isinstance(entry, dict):
            path_obj = None
            for k in path_keys:
                if k in entry and entry.get(k) is not None:
                    path_obj = entry.get(k)
                    break
            if path_obj is None:
                return None, fallback_cost

            cost_val = None
            for ck in cost_keys:
                if ck in entry:
                    cost_val = _safe_float(entry.get(ck))
                    if cost_val is not None:
                        break
            if cost_val is None:
                cost_val = fallback_cost
            return path_obj, cost_val

        return entry, fallback_cost

    def _get_parallel_cost_lists(pdata):
        if not isinstance(pdata, dict):
            return None
        candidate_keys = [
            "costs", "path_costs", "total_costs", "weights",
            "distances", "scores"
        ]
        for ck in candidate_keys:
            vals = pdata.get(ck, None)
            if isinstance(vals, (list, tuple)):
                return list(vals)
        return None

    def _find_edgeweight_matrix(pdb_data_local):
        candidate_keys = [
            "edgeweight_matrix",
            "edge_weight_matrix",
            "weight_matrix",
            "weights_matrix",
            "distance_matrix",
            "cost_matrix",
            "edge_weights",
        ]
        for ck in candidate_keys:
            W = pdb_data_local.get(ck, None)
            if W is not None:
                return W
        return None

    def _compute_cost_from_index_seq(index_seq, W):
        if W is None:
            return None
        if not isinstance(index_seq, (list, tuple)) or len(index_seq) < 2:
            return None

        total = 0.0
        used_any = False

        try:
            nW0 = int(W.shape[0])
            nW1 = int(W.shape[1]) if len(W.shape) > 1 else int(W.shape[0])
        except Exception:
            return None

        for a, b in zip(index_seq[:-1], index_seq[1:]):
            ia = _safe_int(a)
            ib = _safe_int(b)
            if ia is None or ib is None:
                continue
            if not (0 <= ia < nW0 and 0 <= ib < nW1):
                continue
            try:
                w = _safe_float(W[ia, ib])
            except Exception:
                w = None
            if w is None:
                continue
            total += float(w)
            used_any = True

        return total if used_any else None

    def _ensure_global_index_to_residue_local(pdb_data_local):
        """
        Needed because convert_paths_to_residues(...) relies on this reverse map.
        """
        g2r = pdb_data_local.get("global_index_to_residue", None)
        if isinstance(g2r, dict) and g2r:
            return g2r

        rcm = pdb_data_local.get("residue_chain_map", {}) or {}
        rev = {}

        for ch_key, residues in rcm.items():
            for r in (residues or []):
                ch = _real_chain_from_residue(r, ch_key)

                gi = _safe_int(r.get("index", None))
                if gi is None:
                    continue

                rn_raw = r.get("residue_num", None)
                digits = "".join(c for c in str(rn_raw) if c.isdigit())
                if not digits:
                    continue
                rn_i = int(digits)

                ic = r.get("icode", None)
                ic = str(ic).strip() if ic not in (None, "", " ") else None

                seg = _primary_seg_from_residue(r) or ""

                rev[int(gi)] = {
                    "segname": seg,
                    "chain": ch,
                    "residue_num": rn_i,
                    "icode": ic,
                    "residue_name": str(r.get("residue_name", "UNK")).strip().upper(),
                }

        pdb_data_local["global_index_to_residue"] = rev
        return rev

    def _build_token_to_index_lookup(pdb_data_local):
        """
        Needed only if input paths are token-based, not integer-based.
        """
        rcm = pdb_data_local.get("residue_chain_map", {}) or {}

        uid_to_idx = {}
        uid_to_idx_noseg = {}
        chainrnic_to_idx = {}
        chainrn_to_idx = {}

        max_meta_idx_local = -1

        if isinstance(rcm, dict):
            for ch_key, residues in rcm.items():
                if isinstance(residues, list):
                    for r in (residues or []):
                        chU = _real_chain_from_residue(r, ch_key).upper()

                        gi = _safe_int(r.get("index", None))
                        if gi is None:
                            continue

                        max_meta_idx_local = max(max_meta_idx_local, gi)

                        rn_raw = r.get("residue_num", None)
                        digits = "".join([c for c in str(rn_raw) if c.isdigit()])
                        if not digits:
                            continue
                        rn_i = int(digits)

                        ic = r.get("icode", None)
                        ic = str(ic).strip() if ic not in (None, "", " ") else None

                        seg = _primary_seg_from_residue(r) or ""

                        uid_to_idx[(seg, chU, rn_i, ic)] = gi
                        uid_to_idx[(seg, chU, rn_i, None)] = uid_to_idx.get((seg, chU, rn_i, None), gi)
                        uid_to_idx_noseg[("", chU, rn_i, ic)] = gi
                        uid_to_idx_noseg[("", chU, rn_i, None)] = uid_to_idx_noseg.get(("", chU, rn_i, None), gi)
                        chainrnic_to_idx[(chU, rn_i, ic)] = gi
                        chainrnic_to_idx[(chU, rn_i, None)] = chainrnic_to_idx.get((chU, rn_i, None), gi)
                        chainrn_to_idx[(chU, rn_i)] = gi

        return uid_to_idx, uid_to_idx_noseg, chainrnic_to_idx, chainrn_to_idx, max_meta_idx_local

    def _token_node_to_idx(node, uid_to_idx, uid_to_idx_noseg, chainrnic_to_idx, chainrn_to_idx, n_nodes):
        if isinstance(node, dict):
            seg = str(node.get("segname") or node.get("seg") or "").strip()
            ch = str(node.get("chain") or node.get("chain_id") or node.get("chainID") or "").strip().upper()
            rn = node.get("residue_num") if "residue_num" in node else node.get("resid")
            rn_i = _safe_int(rn) if rn is not None else None
            ic = node.get("icode") or None
            ic = str(ic).strip() if ic not in (None, "", " ") else None
            if not ch or rn_i is None:
                return None

            gi = uid_to_idx.get((seg, ch, rn_i, ic))
            if gi is None:
                gi = uid_to_idx.get((seg, ch, rn_i, None))
            if gi is None:
                gi = uid_to_idx_noseg.get(("", ch, rn_i, ic))
            if gi is None:
                gi = uid_to_idx_noseg.get(("", ch, rn_i, None))
            if gi is None:
                gi = chainrnic_to_idx.get((ch, rn_i, ic))
            if gi is None:
                gi = chainrnic_to_idx.get((ch, rn_i, None))
            if gi is None:
                gi = chainrn_to_idx.get((ch, rn_i))
            if gi is None:
                return None

            gi = int(gi)
            return gi if 0 <= gi < n_nodes else None

        if isinstance(node, (tuple, list)) and len(node) >= 2:
            try:
                ch = str(node[0]).strip().upper()
                rn_i = _safe_int(node[1])
                ic = None
                if len(node) >= 3 and node[2] not in (None, "", " "):
                    ic = str(node[2]).strip()
                if ch and rn_i is not None:
                    gi = chainrnic_to_idx.get((ch, rn_i, ic))
                    if gi is None:
                        gi = chainrnic_to_idx.get((ch, rn_i, None))
                    if gi is None:
                        gi = chainrn_to_idx.get((ch, rn_i))
                    if gi is None:
                        return None
                    gi = int(gi)
                    return gi if 0 <= gi < n_nodes else None
            except Exception:
                return None

        if isinstance(node, str):
            s = node.strip()
            seg, ch, rn_i, ic = _split_token_any(s)
            if ch and rn_i is not None:
                gi = uid_to_idx.get((seg, ch, rn_i, ic))
                if gi is None:
                    gi = uid_to_idx.get((seg, ch, rn_i, None))
                if gi is None:
                    gi = uid_to_idx_noseg.get(("", ch, rn_i, ic))
                if gi is None:
                    gi = uid_to_idx_noseg.get(("", ch, rn_i, None))
                if gi is None:
                    gi = chainrnic_to_idx.get((ch, rn_i, ic))
                if gi is None:
                    gi = chainrnic_to_idx.get((ch, rn_i, None))
                if gi is None:
                    gi = chainrn_to_idx.get((ch, rn_i))
                if gi is None:
                    return None
                gi = int(gi)
                return gi if 0 <= gi < n_nodes else None

        return None

    def _convert_index_path_to_tokens(index_path, pdb_data_local):
        """
        Pretty display labels for path output.

        Output examples
        ---------------
        Protein residue: Cys123(A)
        Nucleotide:      A658(C)
        """

        def _pretty_label(meta):
            if not isinstance(meta, dict):
                return None

            resn = str(meta.get("residue_name", "UNK")).strip()
            ch = str(meta.get("chain", "")).strip()
            rn = meta.get("residue_num", None)
            ic = meta.get("icode", None)
            ic_txt = str(ic).strip() if ic not in (None, "", " ") else ""

            if not ch or rn is None:
                return None

            rn_txt = f"{int(rn)}{ic_txt}"

            # --- nucleotide vs amino-acid formatting ---
            # nucleotides -> A658(C)
            nuc_set = {
                "A", "U", "G", "C", "T", "I",
                "DA", "DT", "DG", "DC", "DI"
            }

            if resn.upper() in nuc_set:
                # DNA two-letter names can still be printed compactly
                if resn.upper().startswith("D") and len(resn) == 2:
                    base = resn.upper()[1]
                else:
                    base = resn.upper()
                return f"{base}{rn_txt}({ch})"

            # amino acids -> Cys123(A)
            aa_title = resn.capitalize()
            return f"{aa_title}{rn_txt}({ch})"

        g2r_local = pdb_data_local.get("global_index_to_residue", {}) or {}

        pretty = []
        for gi in index_path:
            meta = g2r_local.get(int(gi), None)
            if not meta:
                pretty.append(str(gi))
                continue

            lbl = _pretty_label(meta)
            pretty.append(lbl if lbl else str(gi))

        return pretty

    # ---------------- validate inputs ----------------
    if not isinstance(paths_dict_2, dict) or pdb_key not in paths_dict_2:
        _log_local(f"⚠ PathSimilarity: pdb_key not found in paths_dict_2: {pdb_key}\n")
        return []

    if not isinstance(pdb_info_dict, dict) or pdb_key not in pdb_info_dict:
        _log_local(f"⚠ PathSimilarity: pdb_key not found in pdb_info_dict: {pdb_key}\n")
        return []

    pdb_data = (pdb_info_dict or {}).get(pdb_key) or (pdb_info_dict or {}).get(str(pdb_key)) or {}
    if not isinstance(pdb_data, dict) or not pdb_data:
        _log_local(f"⚠ PathSimilarity: pdb_data not found for {pdb_key}\n")
        return []

    adj = pdb_data.get("adj_matrix", None)
    if adj is None:
        _log_local(f"⚠ PathSimilarity: adj_matrix missing for {pdb_key}\n")
        return []

    try:
        n_adj = int(adj.shape[0])
    except Exception:
        _log_local(f"⚠ PathSimilarity: invalid adj_matrix for {pdb_key}\n")
        return []

    W = _find_edgeweight_matrix(pdb_data)

    pair_dict = (paths_dict_2 or {}).get(pdb_key, {}) or {}
    if not isinstance(pair_dict, dict) or not pair_dict:
        _log_local(f"⚠ PathSimilarity: no pairs for {pdb_key}\n")
        return []

    # ensure reverse dict exists for convert_paths_to_residues(...)
    _ensure_global_index_to_residue_local(pdb_data)

    uid_to_idx, uid_to_idx_noseg, chainrnic_to_idx, chainrn_to_idx, max_meta_idx = _build_token_to_index_lookup(pdb_data)
    n_nodes = max(n_adj, (max_meta_idx + 1) if max_meta_idx >= 0 else n_adj)

    # ---------------- collect selected paths ----------------
    if selected_pairs:
        sel = set(selected_pairs)
        keys_iter = [k for k in pair_dict.keys() if k in sel]
    else:
        keys_iter = list(pair_dict.keys())

    all_path_records = []

    for pk in keys_iter:
        pdata = pair_dict.get(pk, {}) or {}
        paths = (pdata.get("paths", []) or [])
        parallel_costs = _get_parallel_cost_lists(pdata)

        for j, entry in enumerate(paths):
            fallback_cost = None
            if parallel_costs is not None and j < len(parallel_costs):
                fallback_cost = _safe_float(parallel_costs[j])

            path_obj, cost_obj = _extract_path_and_cost_from_entry(entry, fallback_cost=fallback_cost)
            if path_obj:
                all_path_records.append({
                    "pair_key": str(pk),
                    "raw_path": list(path_obj),
                    "raw_cost": cost_obj,
                    "source_entry_index_0based": j,
                })

    if not all_path_records:
        _log_local(f"⚠ PathSimilarity: no paths after filtering for {pdb_key}\n")
        return []

    # ---------------- build real paths ----------------
    idx_paths = []              # unique nodes for incidence matrix only
    real_index_paths = []       # REAL path order in index space
    real_token_paths = []       # REAL displayed path via convert_paths_to_residues
    path_rows_meta = []
    path_costs = []
    path_efficiencies = []

    skipped_all_unmapped = 0
    total_nodes_seen = 0
    total_nodes_mapped = 0
    unmapped_examples = []
    oor_examples = []

    for rec in all_path_records:
        raw_path = rec["raw_path"]
        raw_cost = rec["raw_cost"]

        is_all_indices = True
        tmp_index_path = []

        for x in raw_path:
            total_nodes_seen += 1
            gi = _safe_int(x)

            if gi is None:
                is_all_indices = False
                break

            if not (0 <= gi < n_nodes):
                is_all_indices = False
                break

            tmp_index_path.append(int(gi))

        if is_all_indices:
            index_path = tmp_index_path
            total_nodes_mapped += len(index_path)
        else:
            index_path = []
            for x in raw_path:
                gi = _token_node_to_idx(
                    x,
                    uid_to_idx=uid_to_idx,
                    uid_to_idx_noseg=uid_to_idx_noseg,
                    chainrnic_to_idx=chainrnic_to_idx,
                    chainrn_to_idx=chainrn_to_idx,
                    n_nodes=n_nodes,
                )
                if gi is None:
                    if len(unmapped_examples) < 20:
                        unmapped_examples.append(str(x))
                    continue

                if not (0 <= gi < n_nodes):
                    if len(oor_examples) < 20:
                        oor_examples.append(str(gi))
                    if strict:
                        raise ValueError(f"Node index out of range: {gi} (n_nodes={n_nodes})")
                    continue

                index_path.append(int(gi))
                total_nodes_mapped += 1

        if not index_path:
            skipped_all_unmapped += 1
            continue

        # display path from SAME conversion pipeline as other outputs
        token_path = _convert_index_path_to_tokens(index_path, pdb_data)

        # similarity incidence from unique node presence
        seen_local = set()
        nodes_seen_in_order = []
        for gi in index_path:
            if gi not in seen_local:
                nodes_seen_in_order.append(int(gi))
                seen_local.add(int(gi))

        final_cost = _safe_float(raw_cost)
        if final_cost is None:
            final_cost = _compute_cost_from_index_seq(index_path, W)

        final_eff = None
        if final_cost is not None and final_cost > 0:
            final_eff = 1.0 / float(final_cost)

        idx_paths.append(nodes_seen_in_order)
        real_index_paths.append(index_path)
        real_token_paths.append(token_path)
        path_costs.append(final_cost)
        path_efficiencies.append(final_eff)
        path_rows_meta.append({
            "path_index_1based": len(idx_paths),
            "pair_key": rec["pair_key"],
            "source_entry_index_0based": rec["source_entry_index_0based"],
        })

    K = len(idx_paths)
    if K == 0:
        _log_local(f"⚠ PathSimilarity: no valid mapped paths for {pdb_key}\n")
        return []

    M = np.zeros((K, n_nodes), dtype=np.uint8)
    for i, nodes in enumerate(idx_paths):
        M[i, nodes] = 1

    # ---------------- similarity + clustering ----------------
    S = _cosine_similarity_rows_binary(M)
    np.fill_diagonal(S, 1.0)

    clusters = _connected_components_from_threshold(
        S,
        threshold=similarity_threshold
    )
    pdb_base = _base_only(pdb_key) if "_base_only" in globals() else str(pdb_key).replace(os.sep, "_")
    outs = []

    # ---------------- cluster/path membership maps ----------------
    path_to_cluster = {}
    representative_indices = set()

    for cid, members in enumerate(clusters, start=1):
        for m in members:
            path_to_cluster[int(m)] = int(cid)
        rep_idx = _cluster_medoid_cost_weighted(S, members, path_costs)
        if rep_idx is not None:
            representative_indices.add(int(rep_idx))

    # ---------------- cluster summary ----------------
    cluster_rows = []
    for cid, members in enumerate(clusters, start=1):
        rep_idx = _cluster_medoid_cost_weighted(S, members, path_costs)
        rep_tokens = real_token_paths[rep_idx] if rep_idx is not None else []

        if len(members) > 1:
            sub = S[np.ix_(members, members)]
            iu = np.triu_indices_from(sub, k=1)
            vals = sub[iu]
            mean_within = float(np.mean(vals)) if len(vals) > 0 else 1.0
            min_within = float(np.min(vals)) if len(vals) > 0 else 1.0
            max_within = float(np.max(vals)) if len(vals) > 0 else 1.0
        else:
            mean_within = 1.0
            min_within = 1.0
            max_within = 1.0

        member_pairs = sorted(set(path_rows_meta[m]["pair_key"] for m in members if 0 <= m < len(path_rows_meta)))

        cluster_cost_vals = [path_costs[m] for m in members if 0 <= m < len(path_costs) and path_costs[m] is not None]
        cluster_eff_vals = [path_efficiencies[m] for m in members if 0 <= m < len(path_efficiencies) and path_efficiencies[m] is not None]

        rep_cost = path_costs[rep_idx] if (rep_idx is not None and 0 <= rep_idx < len(path_costs)) else None
        rep_eff = path_efficiencies[rep_idx] if (rep_idx is not None and 0 <= rep_idx < len(path_efficiencies)) else None

        cluster_rows.append({
            "cluster_id": cid,
            "cluster_size": len(members),
            "representative_rule": "cost_weighted_medoid_by_mean_cosine_similarity",
            "representative_path_index_1based": (rep_idx + 1) if rep_idx is not None else None,
            "representative_pair": path_rows_meta[rep_idx]["pair_key"] if rep_idx is not None else "",
            "representative_path_nodes": " -> ".join(rep_tokens),
            "representative_cost": round(rep_cost, 6) if rep_cost is not None else None,
            "representative_efficiency": round(rep_eff, 6) if rep_eff is not None else None,
            "mean_within_similarity": round(mean_within, 6),
            "min_within_similarity": round(min_within, 6),
            "max_within_similarity": round(max_within, 6),
            "min_cost_in_cluster": round(float(np.min(cluster_cost_vals)), 6) if cluster_cost_vals else None,
            "mean_cost_in_cluster": round(float(np.mean(cluster_cost_vals)), 6) if cluster_cost_vals else None,
            "max_cost_in_cluster": round(float(np.max(cluster_cost_vals)), 6) if cluster_cost_vals else None,
            "min_efficiency_in_cluster": round(float(np.min(cluster_eff_vals)), 6) if cluster_eff_vals else None,
            "mean_efficiency_in_cluster": round(float(np.mean(cluster_eff_vals)), 6) if cluster_eff_vals else None,
            "max_efficiency_in_cluster": round(float(np.max(cluster_eff_vals)), 6) if cluster_eff_vals else None,
            "member_pairs": "; ".join(member_pairs),
            "member_path_indices_1based": ",".join(str(int(x) + 1) for x in members),
        })

    # ---------------- path table ----------------
    path_rows = []
    for i, token_path in enumerate(real_token_paths, start=1):
        cost_i = path_costs[i - 1] if (i - 1) < len(path_costs) else None
        eff_i = path_efficiencies[i - 1] if (i - 1) < len(path_efficiencies) else None
        path_rows.append({
            "path_index_1based": i,
            "pair_key": path_rows_meta[i - 1]["pair_key"],
            "source_entry_index_0based": path_rows_meta[i - 1]["source_entry_index_0based"],
            "cluster_id": path_to_cluster.get(i - 1, None),
            "is_representative": "yes" if (i - 1) in representative_indices else "no",
            "node_count_unique_for_similarity": len(idx_paths[i - 1]),
            "node_count_real_path": len(real_index_paths[i - 1]),
            "path_cost": round(cost_i, 6) if cost_i is not None else None,
            "path_efficiency": round(eff_i, 6) if eff_i is not None else None,
            "nodes": " -> ".join(token_path),
        })

    # ---------------- outputs ----------------
    out_png_ordered = os.path.join(
        out_dir,
        f"PATHSIM__{pdb_base}__K{K}__thr{similarity_threshold:.2f}.png"
    )
    _draw_path_order_similarity_heatmap(
        S=S,
        out_png=out_png_ordered,
        pdb_base=pdb_base,
        K=K,
        similarity_threshold=similarity_threshold,
    )
    outs.append(out_png_ordered)

    out_bar = os.path.join(
        out_dir,
        f"PATHSIM__CLUSTER_SIZES__{pdb_base}__K{K}__thr{similarity_threshold:.2f}.png"
    )
    _draw_cluster_size_plot(
        clusters=clusters,
        out_png=out_bar,
        pdb_base=pdb_base,
        K=K,
        similarity_threshold=similarity_threshold,
    )
    outs.append(out_bar)

    out_repr = os.path.join(
        out_dir,
        f"PATHSIM__REPRESENTATIVE_PATHS__{pdb_base}__K{K}__thr{similarity_threshold:.2f}.png"
    )
    _draw_representative_path_summary(
        cluster_rows=cluster_rows,
        out_png=out_repr,
        pdb_base=pdb_base,
        top_n=5,
    )
    outs.append(out_repr)

    out_xlsx = os.path.join(
        out_dir,
        f"PATHSIM__SUMMARY__{pdb_base}__K{K}__thr{similarity_threshold:.2f}.xlsx"
    )

    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as writer:
        pd.DataFrame(cluster_rows).to_excel(writer, sheet_name="cluster_summary", index=False)

        sim_df = pd.DataFrame(
            S,
            index=[f"path_{i+1}" for i in range(K)],
            columns=[f"path_{i+1}" for i in range(K)],
        )
        sim_df.to_excel(writer, sheet_name="similarity_matrix")

        pd.DataFrame(path_rows).to_excel(writer, sheet_name="path_nodes", index=False)

    outs.append(out_xlsx)

    # diagnostics
    if write_diagnostics:
        try:
            diag = {
                "pdb_key": str(pdb_key),
                "pdb_base": pdb_base,
                "paths_total": int(len(all_path_records)),
                "paths_used": int(K),
                "nodes_seen": int(total_nodes_seen),
                "nodes_mapped": int(total_nodes_mapped),
                "clustering_method": "threshold_graph_connected_components",
                "similarity_threshold": float(similarity_threshold),
                "n_clusters": int(len(clusters)),
                "cluster_sizes": [int(len(c)) for c in clusters],
                "cost_source_priority": [
                    "path_entry_cost_field",
                    "pdata_parallel_cost_list",
                    "edgeweight_matrix_from_index_sequence",
                ],
                "edgeweight_matrix_found": bool(W is not None),
                "unmapped_examples": unmapped_examples,
                "out_of_range_examples": oor_examples,
                "skipped_all_unmapped": int(skipped_all_unmapped),
                "path_input_policy": "use_global_indices_directly_if_already_present",
                "display_label_policy": "convert_paths_to_residues",
                "outputs": outs,
            }
            out_json = os.path.join(
                out_dir,
                f"PATHSIM__DIAG__{pdb_base}__thr{similarity_threshold:.2f}.json"
            )
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(diag, f, indent=2)
            outs.append(out_json)
        except Exception:
            pass

    _log_local(
        f"PathSimilarity {pdb_base}:\n"
        f"  paths_total={len(all_path_records)} paths_used={K} skipped_all_unmapped={skipped_all_unmapped}\n"
        f"  nodes_seen={total_nodes_seen} nodes_mapped={total_nodes_mapped}\n"
        f"  threshold={similarity_threshold:.2f} clusters={len(clusters)}\n"
        f"  edgeweight_matrix_found={bool(W is not None)}\n"
        f"  out={out_png_ordered}\n"
    )

    return outs


def run_path_similarity_ensemble(
    paths_dict_2,
    pdb_info_dict,
    out_dir,
    logger=None,
    selected_pdb_keys=None,
    selected_pairs=None,
    strict: bool = False,
    similarity_threshold: float = 0.70,
    write_diagnostics: bool = True,
):
    """
    Runs path similarity for:
      1) each selected structure (per_structure/)
      2) pooled ENSEMBLE across selected structures (ensemble/)

    Notes
    -----
    - If selected_pdb_keys is None or empty, all structures are used.
    - Ensemble uses the first selected structure as reference index-space,
      matching the same strategy used in the backbone ensemble workflow.
    """

    import os

    def _log(msg: str):
        try:
            if logger is None:
                print(msg)
            elif hasattr(logger, "log_output"):
                logger.log_output(msg)
            else:
                print(msg)
        except Exception:
            pass

    os.makedirs(out_dir, exist_ok=True)
    per_struct_dir = os.path.join(out_dir, "per_structure")
    ens_dir = os.path.join(out_dir, "ensemble")
    os.makedirs(per_struct_dir, exist_ok=True)
    os.makedirs(ens_dir, exist_ok=True)

    if not isinstance(paths_dict_2, dict) or not paths_dict_2:
        _log("⚠ Path Similarity Ensemble: paths_dict_2 is empty.\n")
        return []

    all_pdb_keys = list(paths_dict_2.keys())

    if selected_pdb_keys is None or (
        isinstance(selected_pdb_keys, (list, tuple, set)) and len(selected_pdb_keys) == 0
    ):
        sel_pdb_keys = all_pdb_keys
        sel_mode = "ALL"
    else:
        sel_set = set(str(x).strip() for x in selected_pdb_keys)
        sel_pdb_keys = [k for k in all_pdb_keys if str(k).strip() in sel_set]
        sel_mode = f"{len(sel_pdb_keys)}/{len(all_pdb_keys)}"

    if not sel_pdb_keys:
        _log("⚠ Path Similarity Ensemble: no pdb_keys selected after filtering.\n")
        return []

    _log(f"🧩 Path Similarity Ensemble: selected structures = {sel_mode}\n")

    outs = []

    # 1) per-structure
    for pdb_key in sel_pdb_keys:
        pdb_base = _base_only(pdb_key) if "_base_only" in globals() else str(pdb_key).replace(os.sep, "_")
        out_one = os.path.join(per_struct_dir, pdb_base)
        os.makedirs(out_one, exist_ok=True)

        try:
            out_files = run_path_similarity_for_one_structure(
                pdb_key=pdb_key,
                paths_dict_2=paths_dict_2,
                pdb_info_dict=pdb_info_dict,
                out_dir=out_one,
                logger=logger,
                selected_pairs=selected_pairs,
                strict=strict,
                similarity_threshold=similarity_threshold,
                write_diagnostics=write_diagnostics,
            )
            if out_files:
                outs.extend(out_files)
        except Exception as e:
            _log(f"⚠ Path Similarity per-structure failed for {pdb_key}: {e}\n")

    # 2) pooled ensemble
    ENS_KEY = "__ENSEMBLE__"
    merged_pair_dict = {}

    for pdb_key in sel_pdb_keys:
        pair_dict = paths_dict_2.get(pdb_key, {}) or {}
        if not isinstance(pair_dict, dict):
            continue

        if selected_pairs:
            keep_pairs = set(selected_pairs)
            pair_iter = [k for k in pair_dict.keys() if k in keep_pairs]
        else:
            pair_iter = list(pair_dict.keys())

        for pair_key in pair_iter:
            pdata = pair_dict.get(pair_key, {}) or {}
            paths = pdata.get("paths", []) or []
            if not paths:
                continue

            if pair_key not in merged_pair_dict:
                merged_pair_dict[pair_key] = {"paths": []}

            merged_pair_dict[pair_key]["paths"].extend(paths)

    if not merged_pair_dict:
        _log("⚠ Path Similarity Ensemble: merged_pair_dict is empty. Ensemble not generated.\n")
        return outs

    ref_key = sel_pdb_keys[0]

    if ENS_KEY not in (pdb_info_dict or {}):
        if isinstance(pdb_info_dict, dict) and ref_key in pdb_info_dict:
            pdb_info_dict[ENS_KEY] = pdb_info_dict[ref_key]
        else:
            _log("⚠ Path Similarity Ensemble: missing reference pdb_info for ensemble.\n")
            return outs

    merged_paths_dict_2 = {ENS_KEY: merged_pair_dict}

    _log(
        f"🧬 Path Similarity Ensemble: building ENSEMBLE from {len(sel_pdb_keys)} structures "
        f"(ref index-space={ref_key}) | pairs={len(merged_pair_dict)}\n"
    )

    try:
        out_files_ens = run_path_similarity_for_one_structure(
            pdb_key=ENS_KEY,
            paths_dict_2=merged_paths_dict_2,
            pdb_info_dict=pdb_info_dict,
            out_dir=ens_dir,
            logger=logger,
            selected_pairs=None,
            strict=strict,
            similarity_threshold=similarity_threshold,
            write_diagnostics=write_diagnostics,
        )
        if out_files_ens:
            outs.extend(out_files_ens)
            _log("✅ Path Similarity Ensemble: ENSEMBLE outputs saved.\n")
        else:
            _log("⚠ Path Similarity Ensemble: ENSEMBLE produced no outputs.\n")
    except Exception as e:
        _log(f"❌ Path Similarity Ensemble failed: {e}\n")

    return outs


#####



def _ensure_global_index_to_residue(pdb_data: dict) -> dict:
    if not pdb_data:
        return {}

    if "global_index_to_residue" in pdb_data and pdb_data["global_index_to_residue"]:
        return pdb_data["global_index_to_residue"]

    rev = {}
    rcm = pdb_data.get("residue_chain_map", {}) or {}

    for ch, residues in rcm.items():
        ch = str(ch).strip()
        for r in residues:
            gi = r.get("index")
            if gi is None:
                continue

            rn_raw = str(r.get("residue_num", "")).strip()
            digits = "".join(c for c in rn_raw if c.isdigit())
            if not digits:
                continue
            rn = int(digits)

            # ICODE
            ic = r.get("icode")
            if not ic:
                tail = "".join(c for c in rn_raw if c.isalpha())
                ic = tail or None
            ic = ic.strip() if ic else None

            # ✅ FIX: segname'i önce all_segnames'ten al (ribozom-safe)
            seg = None
            all_segs = r.get("all_segnames") or []
            if all_segs:
                for sg in all_segs:
                    if sg is None:
                        continue
                    sg = str(sg).strip()
                    if sg:
                        seg = sg
                        break

            if seg is None:
                seg0 = r.get("segname")
                seg0 = str(seg0).strip() if seg0 not in (None, "", " ") else None
                seg = seg0

            rev[int(gi)] = {
                "segname": seg,
                "chain": ch,
                "residue_num": rn,
                "icode": ic,
                "residue_name": str(r.get("residue_name", "UNK")).strip().upper(),
            }

    pdb_data["global_index_to_residue"] = rev
    return rev


def convert_paths_to_residues(paths_or_paths_dict, pdb_data_or_pdb_info_dict):
    """
    Converts path node indices (global indices) to STRICT residue tokens: "SEG:CHAIN:RESNUM[ICODE]"

    Supports TWO input shapes:

    (A) Single-PDB mode:
        paths_or_paths_dict = list[list[int]]
        pdb_data_or_pdb_info_dict = pdb_data (dict)

    (B) Whole-job mode (what your GUI currently passes):
        paths_or_paths_dict = paths_dict  (dict[pdb_key -> dict[pair_key -> {"paths":..., "costs":...}]])
        pdb_data_or_pdb_info_dict = pdb_info_dict (dict[pdb_key -> pdb_data])
        Returns: same schema as paths_dict but with paths converted to token lists.
    """
    # -------- Mode (B): full paths_dict --------
    if isinstance(paths_or_paths_dict, dict) and any(isinstance(v, dict) for v in paths_or_paths_dict.values()):
        paths_dict = paths_or_paths_dict or {}
        pdb_info_dict = pdb_data_or_pdb_info_dict or {}

        def _pdb_lookup(key: str):
            key0 = str(key)
            key_base = _base_only(key0)

            if key0 in pdb_info_dict:
                return pdb_info_dict[key0]
            if key_base in pdb_info_dict:
                return pdb_info_dict[key_base]

            try:
                kb = _base_key(key0)
                if kb in pdb_info_dict:
                    return pdb_info_dict[kb]
            except Exception:
                pass

            return {}

        out = {}
        for pdb_key, pairs in (paths_dict or {}).items():
            pdb_data = _pdb_lookup(pdb_key)
            rev = _ensure_global_index_to_residue(pdb_data)

            out_pairs = {}
            for pair_key, pdata in (pairs or {}).items():
                raw_paths = (pdata or {}).get("paths", []) or []
                raw_costs = (pdata or {}).get("costs", []) or []

                converted_paths = []
                for p in raw_paths:
                    converted = []
                    for node in (p or []):
                        try:
                            gi = int(node)
                        except Exception:
                            raise ValueError(f"Path node is not an int-like global index: {node}")

                        r = rev.get(gi)
                        if not r:
                            raise KeyError(f"No reverse mapping for global index={gi} (pdb={pdb_key})")

                        seg = r.get("segname", None)
                        ch  = r.get("chain", None)
                        rn  = r.get("residue_num", None)
                        ic  = r.get("icode", None)

                        if not (ch and rn is not None):
                            raise KeyError(f"Incomplete reverse residue fields for global index={gi}: {r}")

                        ic_part = (str(ic).strip() if ic else "")
                        seg_u = (str(seg).strip() if seg not in (None, "", " ", "NOSEG") else None)
                        ch_u = str(ch).strip()

                        if seg_u:
                            token = f"{seg_u}:{ch_u}:{int(rn)}{ic_part}"
                        else:
                            token = f"{ch_u}:{int(rn)}{ic_part}"

                        converted.append(token)

                    converted_paths.append(converted)

                out_pairs[pair_key] = {
                    **(pdata or {}),
                    "paths": converted_paths,
                    "costs": raw_costs,
                }

            out[pdb_key] = out_pairs

        return out

    # -------- Mode (A): single PDB list-of-paths --------
    pdb_data = pdb_data_or_pdb_info_dict or {}
    rev = _ensure_global_index_to_residue(pdb_data)

    out = []
    for p in (paths_or_paths_dict or []):
        converted = []
        for node in (p or []):
            try:
                gi = int(node)
            except Exception:
                raise ValueError(f"Path node is not an int-like global index: {node}")

            r = rev.get(gi)
            if not r:
                raise KeyError(f"No reverse mapping for global index={gi}")

            seg = r.get("segname", None)
            ch  = r.get("chain", None)
            rn  = r.get("residue_num", None)
            ic  = r.get("icode", None)

            if not (ch and rn is not None):
                raise KeyError(f"Incomplete reverse residue fields for global index={gi}: {r}")

            ic_part = (str(ic) if ic else "")
            if seg:  # ribosome / segmented structures
                token = f"{seg}:{ch}:{int(rn)}{ic_part}"
            else:  # typical proteins (no segname)
                token = f"{ch}:{int(rn)}{ic_part}"
            converted.append(token)
        out.append(converted)

    return out


def color_match_key_strict(segname, chain, resseq, icode=None):
    """
    Strict color key.
    """
    if not segname or not chain or resseq is None:
        return None
    try:
        resseq = int(resseq)
    except Exception:
        return None
    icode = icode if (icode not in ("", " ")) else None
    segname = segname.strip()
    chain = str(chain).strip()
    return (segname, chain, resseq, icode)


def is_same_residue_strict(res_a, res_b):
    """
    res_* can be dict or token string.
    STRICT comparison by (seg, chain, residue number, insertion code).
    """
    try:
        seg_a, ch_a, rn_a, ic_a = flex_parse_residue_token(res_a, strict=True, default_seg="")
        seg_b, ch_b, rn_b, ic_b = flex_parse_residue_token(res_b, strict=True, default_seg="")
    except Exception:
        return False

    seg_a = seg_a or ""
    seg_b = seg_b or ""

    ic_a = ic_a or None
    ic_b = ic_b or None

    return (
        seg_a == seg_b and
        ch_a == ch_b and
        rn_a == rn_b and
        ic_a == ic_b
    )


_AUDIO_READY = False
_AUDIO_FAILED = False

def _ensure_audio():
    global _AUDIO_READY, _AUDIO_FAILED

    if _AUDIO_READY:
        return True
    if _AUDIO_FAILED:
        return False

    try:
        if not pygame.get_init():
            pygame.init()

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

        _AUDIO_READY = True
        return True
    except Exception:
        _AUDIO_FAILED = True
        return False

def play_midi(path: str) -> bool:
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    if not _ensure_audio():
        raise RuntimeError("Audio system could not be initialized on this system.")

    try:
        pygame.mixer.music.stop()
    except Exception:
        pass

    try:
        pygame.mixer.music.unload()
    except Exception:
        pass

    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    return True

def stop_midi() -> None:
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass


DEFAULT_PROP_SEMITONE_OFFSETS = {
    "hydrophobicity": {"hydrophobic": 0,  "hydrophilic": 5},           # +4th
    "charge":         {"positive": 7,     "negative": -3, "neutral": 0},# +5th / -m3
    "aromaticity":    {"aromatic": 2,     "nonaromatic": 0},           # +M2
    "polarity":       {"nonpolar": 0, "polar": 4},  # +M3
}

NOTE_OFFSETS = {"C":0,"C#":1,"D":2,"D#":3,"E":4,
                "F":5,"F#":6,"G":7,"G#":8,"A":9,"A#":10,"B":11}

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

AMINO_ACIDS = [
    ("ALA","A","Alanine"), ("ARG","R","Arginine"), ("ASN","N","Asparagine"),
    ("ASP","D","Aspartic acid"), ("CYS","C","Cysteine"), ("GLN","Q","Glutamine"),
    ("GLU","E","Glutamic acid"), ("GLY","G","Glycine"), ("HIS","H","Histidine"),
    ("ILE","I","Isoleucine"), ("LEU","L","Leucine"), ("LYS","K","Lysine"),
    ("MET","M","Methionine"), ("PHE","F","Phenylalanine"), ("PRO","P","Proline"),
    ("SER","S","Serine"), ("THR","T","Threonine"), ("TRP","W","Tryptophan"),
    ("TYR","Y","Tyrosine"), ("VAL","V","Valine")
]

PROP_COLORS = {
    "hydrophobicity": {
        "hydrophobic":  "#4A7C59",   # muted deep green (pastel)
        "hydrophilic":  "#64A6BD",   # muted light teal
    },
    "charge": {
        "positive": "#EBA370",    # soft muted orange
        "negative": "#C76D7E",    # muted rose-red
        "neutral":  "#DFE2E6",
    },
    "aromaticity": {
        "aromatic":    "#6E5A89",  # muted purple-navy
        "nonaromatic": "#D1D1D1",
    },
    "polarity": {
        "polar": "#4F7CAC",  # muted blue
        "nonpolar":  "#7A6A58",  # muted warm gray/brown
    },
}

FREQSCORE_COLORS = {
    0:  "#F7F7F7",
    1:  "#E3EEF9",
    2:  "#C8DBF2",
    3:  "#AAC8EB",
    4:  "#8BB4E1",
    5:  "#6CA1D6",
    6:  "#4D8ECC",
    7:  "#3C7AB8",
    8:  "#2D699F",
    9:  "#1F5786",
    10: "#0F466E",
}

NUCLEOTIDES = [
    ("DA","A","Deoxyadenosine"),   # DNA FAdenine
    ("DT","T","Deoxythymidine"),   # DNA Thymine
    ("DG","G","Deoxyguanosine"),   # DNA Guanine
    ("DC","C","Deoxycytidine"),    # DNA Cytosine
    ("A","A","Adenosine"),         # RNA Adenine
    ("U","U","Uridine"),           # RNA Uracil
    ("G","G","Guanosine"),         # RNA Guanine
    ("C","C","Cytidine"),          # RNA Cytosine
]

ALL_RESIDUES = AMINO_ACIDS + NUCLEOTIDES

GROUPS = {
    "hydrophobicity": {
        "hydrophobic": {"ALA","VAL","LEU","ILE","MET","PHE","TRP","PRO","CYS"},
        "hydrophilic": {"SER","THR","ASN","GLN","TYR","GLY","T","A","U","G","C"},
    },
    "charge": {
        "positive": {"LYS","ARG","HIS"},
        "negative": {"ASP","GLU"},
        "neutral":  {"ALA","VAL","LEU","ILE","MET","PHE","TRP","PRO","CYS","SER","THR","ASN","GLN","TYR","GLY","T","A","U","G","C"},
    },
    "aromaticity": {
        "aromatic":    {"PHE","TYR","TRP","HIS","T","A","U","G","C"},
        "nonaromatic": {"ALA","VAL","LEU","ILE","MET","PRO","CYS","SER","THR","ASN","GLN","LYS","ARG","ASP","GLU","GLY"},
    },
    "polarity": {
        "polar": {
            "SER", "THR", "ASN", "GLN", "TYR", "CYS",
            "HIS", "LYS", "ARG", "ASP", "GLU", "GLY",
            "T", "A", "U", "G", "C"
        },
        "nonpolar": {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "PRO"},
    },
}

def aa3_to_group(aa3: str, dimension: str) -> str | None:
    dim = GROUPS.get(dimension, {})
    for group_name, members in dim.items():
        if aa3 in members:
            return group_name
    return None


def get_triad_presets() -> dict[str, list[int]]:
    return {
        "Major (I)":        [0,4,7],
        "Minor (i)":        [0,3,7],
        "Diminished (dim)": [0,3,6],
        "Augmented (aug)":  [0,4,8],
        "Suspended (sus2)": [0,2,7],
        "Suspended (sus4)": [0,5,7],
        "Open Fifth":       [0,7,12],
        "Lydian-ish":       [0,4,6],
        "Phrygian-ish":     [0,1,7],
    }


def note_to_midi(note_with_oct: str) -> int:
    m = re.match(r"^([A-G]#?)(\d+)$", note_with_oct.upper())
    if not m:
        raise ValueError(f"Invalid note format: {note_with_oct}")
    note, octave = m.groups()
    octave = int(octave)
    return 12 * (octave + 1) + NOTE_OFFSETS[note]


def midi_to_note(m: int) -> str:
    sem = m % 12
    octv = (m // 12) - 1
    return f"{NOTE_NAMES[sem]}{octv}"


def apply_transpose_clamp(midi_no: int, transpose: int, clamp_low: int, clamp_high: int) -> int:
    new_note = midi_no + transpose
    lo = (clamp_low + 1) * 12
    hi = (clamp_high + 1) * 12 + 11
    return max(lo, min(hi, new_note))


def _midi_to_note_name(m: int) -> str:
    # MIDI 60 = C4 varsayımı
    n = NOTE_NAMES[m % 12]
    octv = (m // 12) - 1
    return f"{n}{octv}"


def _property_root(dim: str, grp: str, base_oct: int) -> str:
    # Base kök C<oct>, sınıfa göre yarım ses kaydır
    base = note_to_midi(f"C{int(base_oct)}")
    semi = DEFAULT_PROP_SEMITONE_OFFSETS.get(dim, {}).get(grp, 0)
    m = base + int(semi)
    return _midi_to_note_name(m)


def build_default_aa_mapping(scale_name: str, base_octave: int) -> dict[str, str]:
    scales = {
        "Chromatic (C)": ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"],
        "Major (C)":     ["C","D","E","F","G","A","B"],
        "Minor (A)":     ["A","B","C","D","E","F","G"],
    }
    notes = scales.get(scale_name, scales["Chromatic (C)"])
    mapping = {}
    i = 0
    for aa3, _, _ in ALL_RESIDUES:
        note = notes[i % len(notes)]
        octv = base_octave + (i // len(notes))
        mapping[aa3] = f"{note}{octv}"
        i += 1
    return mapping


def aa_mapping_to_residue_mapping(
    jobname,
    paths_dict_2,
    aa_map,
    pdb_info_dict,
    dimension: str | None = None,
    default_class: str = "C4",
    gui=None,
    logger=None
):
    """
    Map each residue token in paths_dict_2 to a 1-letter (veya sınıf) kodu.

    Beklenen token formatları örnek:
        - "C:1492"
        - "EB:C:1492"

    Mantık:
        1) Her PDB için residue_chain_map'ten şu key'leri üretir:
             - "C:1492"
             - "EB:C:1492"   (segname varsa)
        2) Path token’ı için önce tam eşleşme denenir,
           olmazsa sadeleştirilmiş "CHAIN:resnum" denenir.
        3) Eğer dimension verilirse: aa3_to_group(AA3, dimension) kullanılır.
           Aksi halde: aa_map[AA3] kullanılır.
    """
    residue_map = {}
    total_tokens = 0
    unknown_tokens = 0
    unknown_resnames = set()

    aa_map = aa_map or {}  # safe

    for pdb_key, pairs in (paths_dict_2 or {}).items():
        canon = _base_key(pdb_key)
        pdb_data = (pdb_info_dict or {}).get(canon, {}) or {}
        rcm = pdb_data.get('residue_chain_map', {}) or {}

        # ── 1) PDB içinden token -> AA3 haritasını kur ─────────────────────
        res2aa3 = {}

        for ch, residues in rcm.items():
            for r in (residues or []):
                resnum = r.get('residue_num')
                resname = (r.get('residue_name', 'UNK') or 'UNK')
                seg = r.get('segname')

                # digits only, ama residue_num normalde zaten int
                try:
                    digits = "".join(c for c in str(resnum) if c.isdigit())
                    if not digits:
                        continue
                    rn_int = int(digits)
                except Exception:
                    continue

                # normalize resname for matching
                resname = str(resname).strip().upper()

                real_ch = _real_chain_from_residue(r, ch)
                simple_key = f"{real_ch}:{rn_int}"
                res2aa3[simple_key] = resname

                if seg:
                    seg = str(seg).strip()
                    if seg:
                        seg_key = f"{seg}:{simple_key}"
                        res2aa3[seg_key] = resname

        # ── 2) Path token’larını sınıfa çevir ─────────────────────────────
        for _, pdata in (pairs or {}).items():
            for path in ((pdata or {}).get("paths") or []):
                for token in (path or []):
                    total_tokens += 1

                    tok_str = str(token).strip()
                    aa3 = res2aa3.get(tok_str)

                    # b) bulunamadıysa, sadeleştirerek dene
                    if aa3 is None:
                        parts = tok_str.split(":")
                        if len(parts) == 2:
                            chain_id, resid = parts
                            segname = None
                        elif len(parts) >= 3:
                            segname = ":".join(parts[:-2]) if len(parts) > 3 else parts[0]
                            chain_id = parts[-2]
                            resid = parts[-1]
                        else:
                            chain_id = None
                            resid = None
                            segname = None

                        rn_int = None
                        if resid is not None:
                            digits = "".join(c for c in str(resid) if c.isdigit())
                            if digits:
                                try:
                                    rn_int = int(digits)
                                except ValueError:
                                    rn_int = None

                        if chain_id is not None and rn_int is not None:
                            simple_key = f"{str(chain_id).strip()}:{rn_int}"
                            if segname:
                                segname = str(segname).strip()
                                if segname:
                                    seg_key = f"{segname}:{simple_key}"
                                    aa3 = res2aa3.get(seg_key)
                            if aa3 is None:
                                aa3 = res2aa3.get(simple_key)

                    if aa3 is None:
                        aa3 = "UNK"

                    if aa3 == "UNK":
                        unknown_tokens += 1

                    # ---- FINAL CLASSIFICATION ----
                    if dimension:
                        cls = aa3_to_group(aa3, dimension)
                        if cls is None:
                            unknown_resnames.add(aa3)
                            cls = default_class
                    else:
                        if aa3 not in aa_map:
                            unknown_resnames.add(aa3)
                        cls = aa_map.get(aa3, default_class)

                    # IMPORTANT: store by string token to avoid type mismatch
                    residue_map[tok_str] = cls

    if gui:
        _log(
            logger,
            f"✅ Residue mapping created ({len(residue_map)} residues). "
            f"Total tokens seen: {total_tokens}, unknown tokens: {unknown_tokens}.\n"
        )
        if unknown_resnames:
            _log(
                logger,
                "ℹ️ Residue 3-letter codes not in mapping (default applied):\n"
                "   " + ", ".join(sorted(unknown_resnames)) + "\n"
            )

    return residue_map



def triad_from_root(root_note: str, triad_name: str) -> list[str]:
    """root 'C4' gibi; preset aralıklara göre akor notalarını döndür."""
    intervals = get_triad_presets().get(triad_name, [0])
    # root'u MIDI'ye çevir, aralık ekle, geri string’e çevir
    root_midi = note_to_midi(root_note)
    notes = []
    for iv in intervals:
        m = root_midi + iv
        notes.append(midi_to_note(m))
    return notes


from collections import Counter


def compute_all_normalized_frequencies(paths_dict_2, pdb_info_dict=None, k=None):
    """
    Computes per-PDB normalized presence frequencies for internal residues.

    Output:
      { "<pdb_base>": { "<token>": 0..100 }, ... }
    """
    def _base_only(name):
        s = str(name).strip()
        s = os.path.basename(s)
        if "." in s:
            s = s.rsplit(".", 1)[0]
        return s

    out = {}

    for pdb_key, pairs in (paths_dict_2 or {}).items():
        pdb_base = _base_only(pdb_key)

        presence = Counter()
        total_paths = 0

        for _pair_key, pdata in (pairs or {}).items():
            paths = (pdata or {}).get("paths", []) or []
            for path in paths:
                if not path or len(path) < 2:
                    continue

                total_paths += 1
                internal = set(path[1:-1])  # presence per path
                for tok in internal:
                    presence[tok] += 1

        if total_paths > 0:
            # ✅ yüzdeye çevir (0–100)
            norm_map = {tok: (presence[tok] / float(total_paths)) * 100.0 for tok in presence}
        else:
            norm_map = {}

        out[pdb_base] = norm_map

    return out


def _norm01(d: dict) -> dict:
    if not d: return {}
    vmax = max(d.values())
    if vmax <= 0: return {k: 0.0 for k in d}
    return {k: (float(v)/vmax) for k,v in d.items()}


def _resolve_pdbkey_for_freq(freq_all: dict, pdb_key: str):
    try_keys = [pdb_key, _base_key(pdb_key), _base_only(pdb_key)]
    for k in try_keys:
        if k in freq_all:
            return k
    return None


def _resolve_freq_map(
    freq_all: dict,
    pdb_key: str,
    pair_key=None,
    path_idx=None,
    scope: str = "per_pdb",
):
    """
    Returns a token->weight map depending on scope.

    Scopes
    -------
    per_pdb  : returns base["pdb_pct"] if present (Excel normalized, percent-like values).
    per_pair : returns pairs[pair_key]["pair_pct"] if present (pair-local normalization).
    per_path : returns pairs[pair_key]["paths"][path_idx] (path-local map; values cast to float).
               This map is typically 0/1 (presence), but we keep numeric casting generic.

    Fallback behavior
    -----------------
    If requested scope cannot be resolved (missing keys, invalid indices, etc.),
    returns a best-effort normalized PDB map derived from base items whose keys look like "A:123".
    """
    if not isinstance(freq_all, dict) or not freq_all:
        return {}

    resolved_pdb_key = _resolve_pdbkey_for_freq(freq_all, pdb_key)
    if resolved_pdb_key is None:
        return {}

    base = freq_all.get(resolved_pdb_key) or {}
    if not isinstance(base, dict) or not base:
        return {}

    # Keys like "A:123" (or similar) directly under base
    norm_pdb_map = {
        k: v for k, v in base.items()
        if isinstance(k, str) and ":" in k
    }

    pairs = base.get("pairs") or {}
    if not isinstance(pairs, dict):
        pairs = {}

    scope = (scope or "per_pdb").strip().lower()

    if scope == "per_pdb":
        pdb_pct = base.get("pdb_pct") or {}
        return pdb_pct if isinstance(pdb_pct, dict) else {}

    if scope == "per_pair":
        if pair_key in pairs and isinstance(pairs.get(pair_key), dict):
            pair_pct = pairs[pair_key].get("pair_pct") or {}
            return pair_pct if isinstance(pair_pct, dict) else {}
        return norm_pdb_map

    if scope == "per_path":
        if pair_key in pairs and isinstance(pairs.get(pair_key), dict):
            paths = pairs[pair_key].get("paths") or {}
            if isinstance(paths, dict) and path_idx in paths and isinstance(paths.get(path_idx), dict):
                out = {}
                for tok, v in paths[path_idx].items():
                    try:
                        out[tok] = float(v)
                    except Exception:
                        # If v isn't numeric, treat as "present" if truthy
                        out[tok] = 1.0 if v else 0.0
                return out
        return norm_pdb_map

    # Unknown scope: fallback to normalized PDB map
    return norm_pdb_map

def build_property_matrix_for_pdb(
    pdb_key,
    freq_map,
    pdb_info_dict,
    dimensions=("hydrophobicity", "charge", "aromaticity", "polarity"),
    freq_threshold=0.0,
):
    import math
    import pandas as pd

    def _digits_only_local(n):
        try:
            s = "".join(c for c in str(n) if c.isdigit())
            return int(s) if s else None
        except Exception:
            return None

    def _norm_chain(ch, known_chains):
        s = "" if ch is None else str(ch).strip().upper()
        if not s:
            return None
        if s in known_chains:
            return s
        if len(s) > 1:
            if s[0] in known_chains:
                return s[0]
            if s[-1] in known_chains:
                return s[-1]
        return s

    def _norm_seg(x):
        s = "" if x is None else str(x).strip()
        return s.upper()

    def _norm_icode(x):
        s = "" if x is None else str(x).strip()
        return s if s else None

    canon = _base_key(pdb_key)
    pdb_data = pdb_info_dict.get(canon, {}) or {}
    rcm = pdb_data.get("residue_chain_map", {}) or {}
    known_chains = {
        _real_chain_from_residue(r, ch_key).upper()
        for ch_key, residues in rcm.items()
        for r in (residues or [])
    }
    # ------------------------------------------------------------------
    # 1) residue_chain_map -> metadata index
    #    segname mismatch olabileceği için hem segli hem segsiz key tut
    # ------------------------------------------------------------------
    meta_index = {}

    for ch_key, residues in rcm.items():
        ch_u = _real_chain_from_residue(r, ch_key).upper()

        for r in (residues or []):
            rn_digits = _digits_only_local(r.get("residue_num", r.get("resSeq", "")))
            if rn_digits is None:
                continue

            aa3 = str(r.get("residue_name", r.get("resname", "UNK"))).upper()[:3]

            seg = r.get("segname", "")
            seg_u = _norm_seg(seg)

            ic = (
                r.get("icode", None)
                if "icode" in r
                else r.get("iCode", None)
                if "iCode" in r
                else r.get("insertion_code", None)
            )
            ic_u = _norm_icode(ic)

            rec_meta = {
                "Chain": ch_u,
                "Segname": ("" if seg is None else str(seg)),
                "ResidueNum": rn_digits,
                "AA3": aa3,
            }

            # primary: segsiz lookup
            meta_index[("", ch_u, rn_digits, ic_u)] = rec_meta
            # secondary: segli lookup
            meta_index[(seg_u, ch_u, rn_digits, ic_u)] = rec_meta

    # ------------------------------------------------------------------
    # 2) freq_map tokens -> rows
    #    Artık rcm'den değil, doğrudan freq_map'ten başlıyoruz
    # ------------------------------------------------------------------
    rows = []

    for token, f in (freq_map or {}).items():
        seg, ch, rn, ic = flex_parse_residue_token(token, strict=False, default_seg="")

        rn_digits = _digits_only_local(rn)
        ch_u = _norm_chain(ch, known_chains)

        if not ch_u or rn_digits is None:
            continue

        seg_u = _norm_seg(seg)
        ic_u = _norm_icode(ic)

        try:
            freq = float(f)
        except Exception:
            continue

        freq = max(0.0, min(freq, 100.0))
        if freq < freq_threshold:
            continue

        # metadata lookup: önce segsiz, sonra segli fallback
        meta = meta_index.get(("", ch_u, rn_digits, ic_u))
        if meta is None and ic_u is not None:
            meta = meta_index.get(("", ch_u, rn_digits, None))
        if meta is None:
            meta = meta_index.get((seg_u, ch_u, rn_digits, ic_u))
        if meta is None and ic_u is not None:
            meta = meta_index.get((seg_u, ch_u, rn_digits, None))

        aa3 = meta["AA3"] if meta is not None else "UNK"
        seg_out = meta["Segname"] if meta is not None else ("" if seg is None else str(seg))

        freq_score = 0 if freq <= 0.0 else min(10, math.ceil(freq / 10.0))

        token_parts = []
        if seg_u:
            token_parts.append(seg_u)
        token_parts.extend([ch_u, str(rn_digits)])
        if ic_u:
            token_parts.append(ic_u)
        token_str = ":".join(token_parts)

        row = {
            "PDB": canon,
            "Chain": ch_u,
            "Segname": seg_out,
            "ResidueNum": rn_digits,
            "Token": token_str,
            "AA3": aa3,
            "Frequency(%)": freq,
            "FreqScore": freq_score,
        }

        for dim in dimensions:
            row[dim] = aa3_to_group(aa3, dim) or ""

        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        if "Segname" in df.columns:
            df = df.sort_values(["Segname", "Chain", "ResidueNum"]).reset_index(drop=True)
        else:
            df = df.sort_values(["Chain", "ResidueNum"]).reset_index(drop=True)
        df["OrderIndex"] = df.index + 1

    return df

def _add_property_legend(ax, ncols=4):
    fig = ax.figure
    handles = [
        Patch(facecolor=PROP_COLORS["hydrophobicity"]["hydrophobic"], edgecolor='none', label="Hydrophobic"),
        Patch(facecolor=PROP_COLORS["hydrophobicity"]["hydrophilic"], edgecolor='none', label="Hydrophilic"),
        Patch(facecolor=PROP_COLORS["charge"]["positive"], edgecolor='none', label="Positive"),
        Patch(facecolor=PROP_COLORS["charge"]["negative"], edgecolor='none', label="Negative"),
        Patch(facecolor=PROP_COLORS["charge"]["neutral"], edgecolor='none', label="Neutral"),
        Patch(facecolor=PROP_COLORS["aromaticity"]["aromatic"], edgecolor='none', label="Aromatic"),
        Patch(facecolor=PROP_COLORS["aromaticity"]["nonaromatic"], edgecolor='none', label="Non-aromatic"),
        Patch(facecolor=PROP_COLORS["polarity"]["polar"], edgecolor='none', label="Polar"),
        Patch(facecolor=PROP_COLORS["polarity"]["nonpolar"], edgecolor='none', label="Nonpolar"),
        Patch(facecolor=FREQSCORE_COLORS[1], edgecolor='none', label="FreqScore (1–10)"),
        Patch(facecolor="#FFFFFF", edgecolor='none', label="Below threshold / no path"),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncols=ncols,
        bbox_to_anchor=(0.5, 0.01),
        frameon=False,
        fontsize=12,
        columnspacing=1.4,
        handlelength=1.4,
    )


def plot_property_tracks_single(df, dimensions, out_png, min_score=0):
    """
    Tek bir PDB için property track çizimi.
    Legend artık figürün en altında düzgün oturur, x-ekseni alta kaydırıldı.
    """

    if df is None or df.empty:
        return

    df = df.copy()

    if "Token" not in df.columns and {"Chain", "ResidueNum"}.issubset(df.columns):
        df["Token"] = df["Chain"].astype(str) + ":" + df["ResidueNum"].astype(int).astype(str)

    df = df.sort_values(["Chain", "ResidueNum"]).reset_index(drop=True)

    tokens = list(df["Token"])
    # --- NEW: cooc-style x labels (Token + AA3) ---
    aa3_list = list(df["AA3"]) if "AA3" in df.columns else [""] * len(tokens)
    x_labels = [
        _format_residue_label_cooc(t, aa3=a, style="cooc+seg")  # seg varsa ekler
        for t, a in zip(tokens, aa3_list)
    ]


    n_cols = len(tokens)

    dims_full = ["FreqScore"] + list(dimensions)
    n_rows = len(dims_full)

    # Figür boyutunu kontrollü bir şekilde aç
    width  = max(6.0, n_cols * 0.28)
    height = max(3.6, n_rows * 0.75)

    fig = plt.figure(figsize=(width, height))

    # Ana ekseni üstte bırakıp altta boşluk açıyoruz
    ax = fig.add_axes([0.10, 0.30, 0.88, 0.68])   # left, bottom, width, height

    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)

    # X eksenini aşağı alıyoruz
    ax.set_xticks([i + 0.5 for i in range(n_cols)])
    ax.set_xticklabels(x_labels, rotation=90, fontsize=16)

    ax.set_yticks([])

    # Hücreleri çiz
    for row_idx, dim in enumerate(dims_full):

        ax.text(-0.5, row_idx + 0.5, dim,
                va="center", ha="right", fontsize=11)

        for i, r in df.iterrows():
            sc = int(r.get("FreqScore", 0))

            if sc < min_score:
                color = "#FFFFFF"
            else:
                if dim == "FreqScore":
                    color = FREQSCORE_COLORS.get(sc, "#EEEEEE")
                else:
                    grp = r.get(dim, "")
                    color = PROP_COLORS.get(dim, {}).get(grp, "#ECEFF1")

            ax.add_patch(Rectangle((i, row_idx), 1, 1,
                                   facecolor=color, edgecolor="white", linewidth=0.5))

            if dim == "FreqScore" and sc >= min_score:
                ax.text(i + 0.5, row_idx + 0.5, str(sc),
                        ha="center", va="center", fontsize=10,
                        color="white" if sc >= 6 else "black")

    # X eksenini düzgün yaz
    if "PDB" in df.columns:
        ax.set_xlabel(f"Residues — {df['PDB'].iloc[0]}", fontsize=14)
    else:
        ax.set_xlabel("Residues", fontsize=14)


    _add_property_legend(ax)
    fig.subplots_adjust(
        left=0.10,
        right=0.99,
        top=0.98,
        bottom=0.25  # single için legend'e biraz daha yer
    )
    # Artık tight_layout kullanmıyoruz; legend zaten aşağıda sabit.
    fig.savefig(out_png, dpi=300)
    plt.close(fig)

def _format_plot_residue_name(chain, resnum, aa3="", segname="", icode=None):
    """
    Figure labels only.
    Protein examples:
        ARG134(A)
        ARG134(A,EB)
    Nucleotide examples:
        C151(A)
        C151(A,EB)
    """
    ch = (str(chain).strip().upper() if chain is not None else "")
    seg = (str(segname).strip() if segname not in (None, "", " ") else "")
    ic  = (str(icode).strip() if icode not in (None, "", " ") else "")
    aa3_u = (str(aa3).strip().upper() if aa3 not in (None, "", " ") else "UNK")

    try:
        rn = int(resnum)
        rn_s = str(rn)
    except Exception:
        rn_s = str(resnum).strip()

    # insertion code varsa residue numarasına ekle
    rn_s = f"{rn_s}{ic}" if ic else rn_s

    core = f"{aa3_u}{rn_s}"

    if seg:
        return f"{core}({ch},{seg})"
    return f"{core}({ch})"

def _format_residue_label_cooc(token: str, aa3: str = "", style: str = "cooc", **_kwargs) -> str:
    seg, ch, rn, ic = flex_parse_residue_token(token, strict=False, default_seg="")

    seg = (seg or "").strip()
    ch  = (ch or "").strip().upper()
    rn  = rn if isinstance(rn, int) else ""
    ic  = None if ic in (None, "", " ") else str(ic).strip()

    aa3_u = (aa3 or "").strip().upper()

    return _format_plot_residue_name(
        chain=ch,
        resnum=rn,
        aa3=aa3_u,
        segname=seg,
        icode=ic,
    )

def plot_property_tracks_multi(
    df_all,
    dimensions,
    out_png,
    min_score=0,
    reference_pdb=None,
    pdb_info_dict=None,
    drop_all_missing: bool = True,
    drop_all_below: bool = True,
    x_label_style: str = "cooc",
    max_xticks: int = 60,
):
    """
    Multi-PDB property tracks plot with a COMMON aligned x-axis.

    Behavior:
      - Common x-axis is aligned by (Chain, ResidueNum, ICode), NOT by full Token.
      - Segment name differences across structures do not create separate columns.
      - Display labels are segname-free for a cleaner aligned visualization.
      - Values are read directly from df_all rows (no secondary remapping logic).
      - All x-labels are shown; no skipping.
    """
    import os
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    if df_all is None or df_all.empty:
        return
    if pdb_info_dict is None:
        pdb_info_dict = {}

    try:
        min_score_i = int(min_score)
    except Exception:
        min_score_i = 0

    df = df_all.copy()
    if "PDB" not in df.columns:
        return

    # Fallback only; do not overwrite if already present
    if "Token" not in df.columns and {"Chain", "ResidueNum"}.issubset(df.columns):
        def _mk_token(row):
            ch = str(row["Chain"]).strip()
            rn = str(int(row["ResidueNum"]))
            seg = ""
            if "Segname" in df.columns:
                v = row.get("Segname", "")
                if v is not None and str(v).strip():
                    seg = str(v).strip()
            return f"{seg}:{ch}:{rn}" if seg else f"{ch}:{rn}"
        df["Token"] = df.apply(_mk_token, axis=1)

    pdb_list = list(df["PDB"].dropna().unique())
    if not pdb_list:
        return

    def _sort_df_for_plot(df_p):
        if "OrderIndex" in df_p.columns:
            return df_p.sort_values(["OrderIndex"]).reset_index(drop=True)
        elif "Segname" in df_p.columns:
            return df_p.sort_values(["Segname", "Chain", "ResidueNum"]).reset_index(drop=True)
        else:
            return df_p.sort_values(["Chain", "ResidueNum"]).reset_index(drop=True)

    def _axis_key_from_token(tok):
        seg, ch, rn, ic = flex_parse_residue_token(tok, strict=False, default_seg="")
        ch = (ch or "").strip().upper()

        if not isinstance(rn, int):
            try:
                s = "".join(c for c in str(rn) if c.isdigit())
                rn = int(s) if s else None
            except Exception:
                rn = None

        ic = None if ic in (None, "", " ") else str(ic).strip()
        return (ch, rn, ic)

    def _display_label_from_key_and_rec(k, rec=None):
        ch, rn, ic = k

        aa3 = ""
        seg = ""

        if rec is not None:
            aa3 = str(rec.get("AA3", "")).strip().upper()
            seg = str(rec.get("Segname", "")).strip()

        return _format_plot_residue_name(
            chain=ch,
            resnum=rn,
            aa3=aa3,
            segname=seg,
            icode=ic,
        )

    def _axis_sort_key(k, chain_priority=None):
        ch, rn, ic = k
        if rn is None:
            rn = 10**9
        ic_s = "" if ic is None else str(ic)

        if chain_priority is None:
            chain_rank = 999
        else:
            chain_rank = chain_priority.get(ch, 999)

        return (chain_rank, ch, rn, ic_s)

    # Reference chain order
    ref_pdb = reference_pdb if (reference_pdb in pdb_list) else pdb_list[0]
    df_ref = df[df["PDB"] == ref_pdb].copy()
    df_ref = _sort_df_for_plot(df_ref)

    ref_chains = []
    if "Chain" in df_ref.columns:
        for ch in df_ref["Chain"].astype(str):
            ch = ch.strip().upper()
            if ch and ch not in ref_chains:
                ref_chains.append(ch)
    chain_priority = {ch: i for i, ch in enumerate(ref_chains)}

    # ------------------------------------------------------------------
    # Build global aligned axis by (chain, residue, icode)
    # ------------------------------------------------------------------
    key_to_label = {}
    all_keys = set()

    for _, rec in df.iterrows():
        tok = rec.get("Token", "")
        if not tok:
            continue

        try:
            sc = int(rec.get("FreqScore", 0))
        except Exception:
            sc = 0

        if drop_all_below and min_score_i > 0 and sc < min_score_i:
            continue

        k = _axis_key_from_token(tok)
        if k[1] is None:
            continue

        all_keys.add(k)

        # Prefer reference label if available later; initialize once if missing
        if k not in key_to_label:
            key_to_label[k] = _display_label_from_key_and_rec(k, rec)

    # If reference exists, refresh labels from reference rows first
    for _, rec in df_ref.iterrows():
        tok = rec.get("Token", "")
        if not tok:
            continue

        try:
            sc = int(rec.get("FreqScore", 0))
        except Exception:
            sc = 0

        if drop_all_below and min_score_i > 0 and sc < min_score_i:
            continue

        k = _axis_key_from_token(tok)
        if k[1] is None:
            continue

        key_to_label[k] = _display_label_from_key_and_rec(k, rec)

    axis_keys = sorted(all_keys, key=lambda k: _axis_sort_key(k, chain_priority))

    if not axis_keys:
        return

    # ------------------------------------------------------------------
    # Per-PDB lookup by aligned key (chain, residue, icode)
    # Keep first record in correct table order
    # ------------------------------------------------------------------
    per_pdb_lookup = {}
    plot_pdbs = []

    for pdb in pdb_list:
        df_p = df[df["PDB"] == pdb].copy()
        df_p = _sort_df_for_plot(df_p)

        if drop_all_below and min_score_i > 0:
            df_p = df_p[df_p["FreqScore"] >= min_score_i].copy()

        lut = {}
        for rec in df_p.to_dict(orient="records"):
            tok = rec.get("Token", "")
            if not tok:
                continue

            k = _axis_key_from_token(tok)
            if k[1] is None:
                continue

            if k not in lut:
                lut[k] = rec

        if (not drop_all_missing) or len(lut) > 0:
            per_pdb_lookup[pdb] = lut
            plot_pdbs.append(pdb)

    if not plot_pdbs:
        return

    # Remove columns absent in all plotted PDBs
    if drop_all_missing:
        axis_keys = [
            k for k in axis_keys
            if any(k in per_pdb_lookup.get(pdb, {}) for pdb in plot_pdbs)
        ]

    if not axis_keys:
        return

    x_labels = [key_to_label.get(k, f"{k[0]}:{k[1]}{'' if k[2] is None else k[2]}") for k in axis_keys]

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    dims_full = ["FreqScore"] + list(dimensions)

    n_rows_per_pdb = len(dims_full)
    n_rows = len(plot_pdbs) * n_rows_per_pdb
    n_cols = len(axis_keys)

    width = max(12.0, min(40.0, n_cols * 0.32))
    height = max(4.5, n_rows * 0.75)

    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)
    ax.set_yticks([])

    # Show every x label
    xtick_pos = [i + 0.5 for i in range(n_cols)]
    xtick_lab = x_labels
    ax.set_xticks(xtick_pos)
    ax.set_xticklabels(xtick_lab, rotation=90, fontsize=14)
    ax.tick_params(axis="x", pad=2)

    # ------------------------------------------------------------------
    # Draw blocks
    # ------------------------------------------------------------------
    row_base = 0
    for pdb in plot_pdbs:
        lut = per_pdb_lookup.get(pdb, {})

        if row_base > 0:
            ax.axhline(row_base, color="#CFD8DC", linewidth=0.6)

        for dim_idx, dim in enumerate(dims_full):
            global_row = row_base + dim_idx

            ax.text(
                -0.5,
                global_row + 0.5,
                f"{pdb} | {dim}",
                va="center",
                ha="right",
                fontsize=10,
            )

            for j, k in enumerate(axis_keys):
                rec = lut.get(k)

                try:
                    sc = int(rec.get("FreqScore", 0)) if rec is not None else 0
                except Exception:
                    sc = 0

                if min_score_i > 0 and sc < min_score_i:
                    color = "#FFFFFF"
                else:
                    if rec is None:
                        color = "#FFFFFF"
                    elif dim == "FreqScore":
                        color = FREQSCORE_COLORS.get(sc, "#EEEEEE")
                    else:
                        grp = rec.get(dim, "")
                        color = PROP_COLORS.get(dim, {}).get(grp, "#ECEFF1")

                ax.add_patch(
                    Rectangle(
                        (j, global_row), 1, 1,
                        facecolor=color,
                        edgecolor="white",
                        linewidth=0.4
                    )
                )

                if dim == "FreqScore" and (min_score_i <= 0 or sc >= min_score_i) and sc > 0:
                    ax.text(
                        j + 0.5,
                        global_row + 0.5,
                        str(sc),
                        ha="center",
                        va="center",
                        fontsize=10,
                        color="white" if sc >= 6 else "black",
                    )

        row_base += n_rows_per_pdb

    ax.set_xlabel("Residues", fontsize=14)

    _add_property_legend(ax)

    fig.subplots_adjust(left=0.10, right=0.99, top=0.98, bottom=0.28)
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _token_key_for_alignment(token, pdb_key=None, pdb_id=None, pdb_info_dict=None, **kwargs):
    """
    Alignment key used to match residues across structures.
    Uses (chain, resseq, icode) primarily; segname is NOT required to match
    because ribosome segnames can differ across files (MC vs DC).
    """
    if pdb_key is None:
        pdb_key = pdb_id
    seg, ch, rn, ic = flex_parse_residue_token(token, strict=False, default_seg="")
    ch = (ch or "").strip()
    rn = rn if isinstance(rn, int) else None
    ic = ic if ic not in ("", " ") else None
    return (ch, rn, ic)


def _build_row_lookup_by_key(df_pdb):
    """
    Build lookup dict from a per-PDB property DataFrame.
    If duplicates exist for same (chain, rn, ic), the first encountered is kept.
    """
    lut = {}
    if df_pdb is None or df_pdb.empty:
        return lut

    # Ensure Token exists
    if "Token" not in df_pdb.columns and {"Chain", "ResidueNum"}.issubset(df_pdb.columns):
        df_pdb = df_pdb.copy()
        df_pdb["Token"] = df_pdb["Chain"].astype(str) + ":" + df_pdb["ResidueNum"].astype(int).astype(str)

    for rec in df_pdb.to_dict(orient="records"):
        k = _token_key_for_alignment(rec.get("Token"))
        if k not in lut:
            lut[k] = rec
    return lut


def export_property_excel_aligned(df_all, out_xlsx, reference_pdb=None):
    """
    Writes a detailed Excel for property tracks with alignment.

    Sheets:
      1) Raw           : original concatenated df_all (same as old exporter)
      2) ResidueMap    : reference tokens + per-PDB matched token + present flag
      3) ALL_Aligned   : property table aligned to reference order (x-axis = reference)

    Missing residues in a PDB:
      - keep the row (because reference defines the axis)
      - Present=0
      - Frequency=0, FreqScore=0
      - AA3 and property dimensions filled from reference row (stable / comparable)
    """
    import pandas as pd

    if df_all is None or df_all.empty:
        return

    df_all = df_all.copy()

    # Determine dimensions present in df_all
    base_known = {
        "PDB","OrderIndex","Chain","Segname","ResidueNum","AA3","Token","Frequency(%)","FreqScore"
    }
    dims = [c for c in df_all.columns if c not in base_known]

    # Choose reference PDB
    pdbs = list(df_all["PDB"].dropna().unique())
    if not pdbs:
        return
    ref_pdb = reference_pdb if (reference_pdb in pdbs) else pdbs[0]

    df_ref = df_all[df_all["PDB"] == ref_pdb].copy()
    if df_ref.empty:
        ref_pdb = pdbs[0]
        df_ref = df_all[df_all["PDB"] == ref_pdb].copy()

    # Reference order: if OrderIndex exists, use it; else Chain/ResidueNum
    if "OrderIndex" in df_ref.columns:
        df_ref = df_ref.sort_values(["OrderIndex"]).reset_index(drop=True)
    else:
        df_ref = df_ref.sort_values(["Chain","ResidueNum"]).reset_index(drop=True)

    # Build per-PDB lookups
    per_pdb_lookup = {}
    for pdb in pdbs:
        df_p = df_all[df_all["PDB"] == pdb].copy()
        per_pdb_lookup[pdb] = _build_row_lookup_by_key(df_p)

    # -----------------------
    # Sheet: ResidueMap
    # -----------------------
    map_rows = []
    for rec_ref in df_ref.to_dict(orient="records"):
        ref_token = rec_ref.get("Token")
        k = _token_key_for_alignment(ref_token)

        row = {
            "RefPDB": ref_pdb,
            "RefToken": ref_token,
            "RefChain": rec_ref.get("Chain"),
            "RefSegname": rec_ref.get("Segname"),
            "RefResidueNum": rec_ref.get("ResidueNum"),
            "RefAA3": rec_ref.get("AA3"),
        }

        for pdb in pdbs:
            hit = per_pdb_lookup[pdb].get(k)
            row[f"{pdb}__Token"] = (hit.get("Token") if hit else "")
            row[f"{pdb}__Present"] = (1 if hit else 0)

        map_rows.append(row)

    df_map = pd.DataFrame(map_rows)

    # -----------------------
    # Sheet: ALL_Aligned
    # -----------------------
    aligned_rows = []
    for rec_ref in df_ref.to_dict(orient="records"):
        ref_token = rec_ref.get("Token")
        k = _token_key_for_alignment(ref_token)

        base = {
            "RefToken": ref_token,
            "RefChain": rec_ref.get("Chain"),
            "RefSegname": rec_ref.get("Segname"),
            "RefResidueNum": rec_ref.get("ResidueNum"),
            "RefAA3": rec_ref.get("AA3"),
        }
        # Keep reference property dims too (useful for comparing)
        for d in dims:
            base[f"Ref__{d}"] = rec_ref.get(d, "")

        for pdb in pdbs:
            hit = per_pdb_lookup[pdb].get(k)

            if hit:
                base[f"{pdb}__Present"] = 1
                base[f"{pdb}__Token"] = hit.get("Token","")
                base[f"{pdb}__AA3"] = hit.get("AA3","")
                base[f"{pdb}__Frequency(%)"] = hit.get("Frequency(%)", 0)
                base[f"{pdb}__FreqScore"] = hit.get("FreqScore", 0)
                for d in dims:
                    base[f"{pdb}__{d}"] = hit.get(d, "")
            else:
                # Missing residue in this structure -> fill from reference (stable axis)
                base[f"{pdb}__Present"] = 0
                base[f"{pdb}__Token"] = ""   # explicitly missing
                base[f"{pdb}__AA3"] = rec_ref.get("AA3","")
                base[f"{pdb}__Frequency(%)"] = 0
                base[f"{pdb}__FreqScore"] = 0
                for d in dims:
                    base[f"{pdb}__{d}"] = rec_ref.get(d, "")

        aligned_rows.append(base)

    df_aligned = pd.DataFrame(aligned_rows)

    # -----------------------
    # Write Excel
    # -----------------------
    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as writer:
        # Raw (original)
        df_all.to_excel(writer, sheet_name="Raw", index=False)

        # Mapping
        df_map.to_excel(writer, sheet_name="ResidueMap", index=False)

        # Aligned table
        df_aligned.to_excel(writer, sheet_name="ALL_Aligned", index=False)

@dataclass
class MusicOptions:
    # Output structure
    rep_res_freq: str = "per_pdb"           # per_path | per_pair | per_pdb

    # NEW: play order / alignment mode
    align_mode: str = "aligned"           # "aligned" | "legacy"

    # Mapping
    mapping_mode: str = "aa"              # aa | property | single
    chord_mode: str = "single"            # single | triad
    aa_triad_name: str = "Major (I)"
    default_scale_name: str = "Chromatic (C)"
    default_base_octave: int = 4

    # Property mapping
    property_dimension: str = "hydrophobicity"
    property_base_octave: int = 4
    property_triads: dict = None          # {dimension: {class: triad_name}}

    # Single-AA focus
    single_aa_code: str = "K"
    single_triad_name: str = "Major (I)"
    single_base_octave: int = 4
    single_others_policy: str = "rest"    # rest | skip

    # Instrument & dynamics
    program: int = 0
    velocity_mode: str = "by_frequency"   # constant | by_frequency
    velocity_constant: int = 90
    velocity_min: int = 30                # NEW: by_frequency alt sınır
    velocity_max: int = 110               # NEW: by_frequency üst sınır
    freq_scope: str = "per_pdb"           # per_path | per_pair | per_pdb

    # Pitch
    transpose: int = 0
    clamp_low: int = 3
    clamp_high: int = 6

    # Rhythm
    tempo_bpm: int = 120
    note_beats: float = 1.0
    rest_beats: float = 0.25


def _pick_velocity(options: MusicOptions, freq_val: float = 0.0) -> int:

    mode = getattr(options, "velocity_mode", "by_frequency")
    if mode == "constant":
        return max(1, min(127, int(getattr(options, "velocity_constant", 90))))

    # by_frequency
    vmin = max(1, int(getattr(options, "velocity_min", 30)))
    vmax = max(vmin, int(getattr(options, "velocity_max", 110)))
    x = max(0.0, min(1.0, float(freq_val)))

    v = int(round(vmin + x * (vmax - vmin)))
    return max(1, min(127, v))


def generate_audio(jobname, paths_dict_2, residue_note_map,
                   options: MusicOptions,
                   all_normalized_frequencies=None,
                   gui=None,
                   pdb_info_dict=None,logger=None):

    import os, re
    from collections import Counter
    from midiutil import MIDIFile


    if pdb_info_dict is None:
        pdb_info_dict = {}


    return_event_log = bool(getattr(options, "return_event_log", False))


    tempo_bpm = int(getattr(options, "tempo_bpm", 120) or 120)
    note_beats = float(getattr(options, "note_beats", 1.0) or 1.0)
    rest_beats = float(getattr(options, "rest_beats", 0.25) or 0.25)
    sec_per_beat = 60.0 / max(1, tempo_bpm)


    program = int(getattr(options, "program", 0) or 0)
    transpose = int(getattr(options, "transpose", 0) or 0)
    clamp_lo = int(getattr(options, "clamp_low", 3) or 3)
    clamp_hi = int(getattr(options, "clamp_high", 6) or 6)

    policy  = (getattr(options, "rep_res_freq", "per_pdb") or "per_pdb").lower()
    vel_mode = (getattr(options, "velocity_mode", "constant") or "constant").lower()

    written = []
    event_logs = {}

    def _safe_fname(s: str) -> str:
        return re.sub(r'[^A-Za-z0-9._-]+', '_', str(s)).strip('_')

    def _token_sort_key(token):
        seg, ch, rn, ic = flex_parse_residue_token(token, strict=True,default_seg="")
        return (seg or "", ch or "", int(rn) if rn is not None else 10 ** 9, ic or "")

    def _unique_sorted_tokens_from_paths(list_of_paths):

        uniq_keys = set()

        for p in list_of_paths or []:
            for t in p or []:
                try:
                    seg, ch, rn, ic = flex_parse_residue_token(t, strict=True, default_seg="")
                except Exception:
                    continue

                if not ch or rn is None:
                    continue

                seg = (seg or "").strip()
                ch = str(ch).strip().upper()
                rn = int(rn)
                ic = (str(ic).strip() if ic else None)

                uniq_keys.add((seg, ch, rn, ic))

        # Convert back to canonical token strings
        uniq_tokens = []
        for seg, ch, rn, ic in uniq_keys:
            tok = f"{ch}:{rn}" + (f":{ic}" if ic else "")
            if seg:
                tok = f"{seg}:{tok}"
            uniq_tokens.append(tok)

        return sorted(uniq_tokens, key=_token_sort_key)

    from collections import Counter

    def _count_map_from_paths(list_of_paths):
        """
        Count residue appearances across multiple paths.
        STRICT counting by (seg, chain, rn, icode).
        Returns: dict { "SEG:CHAIN:RN[:ICODE]" : count }
        """
        cnt = Counter()

        for p in list_of_paths or []:
            for t in p or []:
                try:
                    seg, ch, rn, ic = flex_parse_residue_token(t, strict=True, default_seg="")
                except Exception:
                    continue

                if not ch or rn is None:
                    continue

                seg = (seg or "").strip()
                ch = str(ch).strip().upper()
                rn = int(rn)
                ic = (str(ic).strip() if ic else None)

                key = f"{ch}:{rn}" + (f":{ic}" if ic else "")
                if seg:
                    key = f"{seg}:{key}"
                cnt[key] += 1

        return dict(cnt)

    def _norm01(d: dict) -> dict:
        if not d:
            return {}
        vmax = max(float(v) for v in d.values())
        if vmax <= 0:
            return {k: 0.0 for k in d}
        return {k: (float(v)/vmax) for k, v in d.items()}

    def aa3_for_token(token: str, pdb_key: str) -> str | None:

        canon = os.path.splitext(os.path.basename(pdb_key))[0]
        pdb_data = (pdb_info_dict or {}).get(canon, {}) or {}
        if not pdb_data:
            pdb_data = (pdb_info_dict or {}).get(pdb_key, {}) or {}
        rcm = pdb_data.get("residue_chain_map", {}) or {}

        # Build STRICT token -> aa3 map (SEG:CHAIN:RES[icode])
        res2aa3 = {}

        for ch, residues in rcm.items():
            ch = str(ch).strip()

            for r in (residues or []):
                resnum = r.get("residue_num")
                if resnum is None:
                    continue

                digits = "".join(c for c in str(resnum) if c.isdigit())
                if not digits:
                    continue
                rn = int(digits)

                aa3 = str(r.get("residue_name", "UNK")).upper()[:3]

                seg = str(r.get("segname") or "").strip()

                ic = r.get("icode", None)
                ic = ic if ic not in ("", " ") else None
                ic_suffix = str(ic) if ic else ""

                strict_key = f"{seg}:{ch}:{rn}{ic_suffix}"
                res2aa3[strict_key] = aa3
                # ALSO store seg-less key so CHAIN:RES lookups work when seg is missing
                segless_key = f"{ch}:{rn}{ic_suffix}"
                # do not overwrite a previously stored non-UNK if any
                if segless_key not in res2aa3 or res2aa3.get(segless_key) in (None, "UNK"):
                    res2aa3[segless_key] = aa3

        def _norm_resnum(x):
            if x is None:
                return None
            digits = "".join(c for c in str(x) if c.isdigit())
            if not digits:
                return None
            return int(digits)

        # ---- normalize incoming token to candidate keys ----
        candidates = []

        # dict token
        if isinstance(token, dict):
            ch = str(token.get("chain", "")).strip()
            rn = _norm_resnum(token.get("residue_num"))
            seg = token.get("segname", None)
            if ch and rn is not None:
                candidates.append(f"{ch}:{rn}")
                if seg:
                    candidates.append(f"{str(seg).strip()}:{ch}:{rn}")

        # tuple/list token
        elif isinstance(token, (tuple, list)):
            if len(token) == 2:
                ch = str(token[0]).strip()
                rn = _norm_resnum(token[1])
                if ch and rn is not None:
                    candidates.append(f"{ch}:{rn}")
            elif len(token) >= 3:
                seg = str(token[0]).strip()
                ch = str(token[1]).strip()
                rn = _norm_resnum(token[2])
                if ch and rn is not None:
                    candidates.append(f"{ch}:{rn}")
                    if seg:
                        candidates.append(f"{seg}:{ch}:{rn}")

        # string token
        else:
            s = str(token).strip()
            if s:
                # try direct first (it might already be "SEG:CHAIN:RES")
                candidates.append(s)

                # also parse with your robust splitter
                seg, ch, rn_raw, ic = flex_parse_residue_token(s, strict=False, default_seg="")
                rn = _norm_resnum(rn_raw)
                ch = str(ch).strip()
                ic = (str(ic).strip() if ic not in (None, "", " ") else None)
                ic_suffix = str(ic) if ic else ""
                seg = (str(seg).strip() if seg else "")

                if ch and rn is not None:
                    candidates.append(f"{ch}:{rn}{ic_suffix}")  # seg-less
                    candidates.append(f"{seg}:{ch}:{rn}{ic_suffix}")  # strict

                    if seg:
                        candidates.append(f"{str(seg).strip()}:{ch}:{rn}")

        # lookup in priority order
        for key in candidates:
            aa3 = res2aa3.get(key)
            if aa3 and aa3 != "UNK":
                return aa3

        # last-resort: if key exists but was UNK, return UNK
        for key in candidates:
            aa3 = res2aa3.get(key)
            if aa3:
                return aa3

        return None

    def property_group_root(dimension: str, group: str, base_octave: int) -> str:
        return _property_root(dimension, group, base_octave)

    NOSEG = ""

    def canonical_residue_token(seg, chain, resseq, icode=None):
        """
        Canonical token policy:
          - If seg is missing / NOSEG -> return SEG-LESS token: "CHAIN:RES[icode]"
          - If seg exists            -> return strict token:   "SEG:CHAIN:RES[icode]"
        This is critical so segname-less proteins do NOT get polluted with "NOSEG:".
        """
        chain = (chain or "").strip()
        if not chain:
            raise ValueError("Empty chain in token")

        resseq = int(resseq)

        ic = (str(icode).strip() if icode not in (None, "", " ") else "")
        ic_suffix = f"{ic}" if ic else ""

        seg_s = (str(seg).strip() if seg not in (None, "", " ") else "")
        if (not seg_s) or (seg_s.upper() == NOSEG):
            return f"{chain}:{resseq}{ic_suffix}"

        return f"{seg_s}:{chain}:{resseq}{ic_suffix}"

    def canonicalize_any_token(token, default_seg=""):
        seg, ch, rn, ic = flex_parse_residue_token(
            token, strict=False, default_seg=default_seg
        )
        if not ch or rn is None:
            return None
        return canonical_residue_token(seg, ch, rn, ic)

    def notes_for_token(token: str, pdb_key: str):
        """
        Return (note_list, group_label_or_None, mode_tag)
        mode_tag: 'aa' | 'property' | 'single'
        """
        mode = (getattr(options, "mapping_mode", "aa") or "aa").lower()

        # ---------- AA MODE ----------
        if mode == "aa":
            skey = canonicalize_any_token(token)
            if not skey:
                return [], None, "aa"

            root = residue_note_map.get(skey)
            if not root:
                return [], None, "aa"

            if (getattr(options, "chord_mode", "single") or "single") == "single":
                return [root], None, "aa"

            tri_name = getattr(options, "aa_triad_name", "Major (I)") or "Major (I)"
            return triad_from_root(root, tri_name), None, "aa"

        # ---------- PROPERTY MODE ----------
        if mode == "property":
            aa3 = aa3_for_token(token, pdb_key)
            if not aa3:
                return [], None, "property"

            dim = getattr(options, "property_dimension", "hydrophobicity")
            grp = aa3_to_group(aa3, dim)
            if not grp:
                return [], None, "property"

            base_oct = int(getattr(options, "property_base_octave", 4))
            root = property_group_root(dim, grp, base_oct)

            tri_map = (getattr(options, "property_triads", {}) or {})
            tri_name = (tri_map.get(dim, {}) or {}).get(grp) or "Major (I)"
            return triad_from_root(root, tri_name), grp, "property"

        # ---------- SINGLE AA MODE ----------
        if mode == "single":
            aa3 = aa3_for_token(token, pdb_key)
            if not aa3:
                return [], None, "single"

            want = (getattr(options, "single_aa_code", "K") or "K").upper()
            aa1 = None
            for trip, one, _ in ALL_RESIDUES:
                if trip == aa3:
                    aa1 = one
                    break

            if aa1 == want:
                root = f"C{int(getattr(options, 'single_base_octave', 4))}"
                tri_name = getattr(options, "single_triad_name", "Major (I)") or "Major (I)"
                return triad_from_root(root, tri_name), None, "single"

            return (
                [], None, "single"
            ) if (getattr(options, "single_others_policy", "rest") == "skip") \
                else (["REST"], None, "single")

        return [], None, mode

    # Velocity hesaplayıcı
    def _vel(freq_val: float) -> int:
        try:
            return int(_pick_velocity(options, freq_val))
        except Exception:
            if vel_mode == "constant":
                return max(1, min(127, int(getattr(options, "velocity_constant", 90))))
            vmin = max(1, int(getattr(options, "velocity_min", 30)))
            vmax = max(vmin, int(getattr(options, "velocity_max", 110)))
            x = max(0.0, min(1.0, float(freq_val)))
            return max(1, min(127, int(round(vmin + x * (vmax - vmin)))))

    def normalize_token_for_audio(token, default_seg=""):
        """
        Returns:
          strict_key : 'SEG:CHAIN:RES[icode]'  (SEG always present; NOSEG if missing)
          display    : 'CHAIN:RES[icode]' if seg==NOSEG else strict_key

        This function must ALWAYS return exactly 2 values.
        """
        seg, ch, rn, ic = flex_parse_residue_token(token, strict=False, default_seg=default_seg)

        seg = (str(seg).strip().upper() if seg else "")
        ch = (str(ch).strip().upper() if ch else "")

        try:
            rn = int(rn) if rn is not None else None
        except Exception:
            rn = None

        ic = (str(ic).strip() if ic not in (None, "", " ") else None)
        ic_suffix = str(ic) if ic else ""

        # If chain/resnum missing, return safe display and None strict_key
        if (not ch) or (rn is None):
            return None, str(token)

        strict_key = f"{seg}:{ch}:{rn}{ic_suffix}"
        display = f"{ch}:{rn}{ic_suffix}" if seg == default_seg else strict_key
        return strict_key, display

    # Nota yazıcı + event kaydı
    def _emit_token_list(mid, track, start_t_beats, token_list, pdb_key, freq_map_or_none, out_path, meta):
        t = float(start_t_beats)
        events = event_logs.setdefault(out_path, [])
        for token in token_list:
            notes, grp, tag = notes_for_token(token, pdb_key)
            if not notes or notes == ["REST"]:
                t += (note_beats + rest_beats)
                continue

            if freq_map_or_none is None:
                fval = 0.0
            else:
                skey, disp = normalize_token_for_audio(token, default_seg="")
                fval = float(
                    freq_map_or_none.get(token, None) or
                    (freq_map_or_none.get(disp, None) if disp else None) or
                    (freq_map_or_none.get(skey, None) if skey else None) or
                    0.0
                )

            vel = _vel(fval)

            written_midi = []
            for n in notes:
                try:
                    midi_no = apply_transpose_clamp(note_to_midi(n), transpose, clamp_lo, clamp_hi)
                except Exception:
                    continue
                mid.addNote(
                    int(track),
                    0,
                    int(midi_no),
                    float(t),
                    float(note_beats),
                    int(vel),
                )
                written_midi.append(midi_no)

            if return_event_log and written_midi:
                note_names = [midi_to_note(m) for m in written_midi]
                note_str = "+".join(note_names) if len(note_names) > 1 else note_names[0]
                events.append({
                    "token": skey or token,
                    "token_display":disp,
                    "group": grp,
                    "mode": tag,
                    "velocity": vel,
                    "note": note_str,
                    "residue": disp,
                    "start_beat": t,
                    "end_beat": t + note_beats,
                    "start_sec": t * sec_per_beat,
                    "end_sec": (t + note_beats) * sec_per_beat,
                    "meta": meta,
                    "path_index": meta.get("path_index"),
                })
            t += (note_beats + rest_beats)
        return t


    out_dir = os.path.join(jobname, "music")
    os.makedirs(out_dir, exist_ok=True)


    from datetime import datetime
    run_label = getattr(options, "run_label", None)
    if run_label:
        base_label = re.sub(r'[^A-Za-z0-9._-]+', '_', str(run_label)).strip('_')
        if not base_label:
            base_label = "run"
    else:
        base_label = "run"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(out_dir, f"{base_label}_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)


    settings_path = os.path.join(run_dir, "settings.txt")
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write("MUSIKALL music generation settings\n")
            f.write(f"job_folder = {jobname}\n")
            f.write(f"run_folder = {run_dir}\n")
            f.write(f"policy (rep_res_freq) = {policy}\n")
            f.write(f"velocity_mode = {vel_mode}\n")
            f.write(f"tempo_bpm = {tempo_bpm}\n")
            f.write(f"note_beats = {note_beats}\n")
            f.write(f"rest_beats = {rest_beats}\n")
            f.write(f"program = {program}\n")
            f.write(f"transpose = {transpose}\n")
            f.write(f"clamp_low = {clamp_lo}\n")
            f.write(f"clamp_high = {clamp_hi}\n")

            try:
                opt_dict = getattr(options, "__dict__", None) or {}
                for k, v in opt_dict.items():
                    if k in {
                        "tempo_bpm", "note_beats", "rest_beats", "program",
                        "transpose", "clamp_low", "clamp_high",
                        "rep_res_freq", "velocity_mode",
                        "return_event_log", "run_label"
                    }:
                        continue
                    f.write(f"{k} = {v}\n")
            except Exception:
                pass
    except Exception as e:
        if gui:
            _log(logger,f"⚠ Could not write music settings.txt: {e}\n")

    if gui:
        _log(logger,f"🎵 Music run folder: {run_dir}\n")



    if policy == "per_path":
        for pdb_key, pairs in paths_dict_2.items():
            pdb_base = _base_only(pdb_key)
            for pair_key, pdata in pairs.items():
                paths = list(pdata.get("paths", []))
                for idx, path in enumerate(paths, start=1):
                    token_list = []
                    for t in path:
                        ct = canonicalize_any_token(t)
                        if ct:
                            token_list.append(ct)
                    freq_map = None
                    if vel_mode == "by_frequency":
                        freq_map = _norm01(_count_map_from_paths([path])) or None

                    mid = MIDIFile(1); tr = 0
                    mid.addTempo(tr, 0, tempo_bpm)
                    mid.addProgramChange(tr, 0, 0, program)

                    outp = os.path.join(run_dir, f"{pdb_base}_{_safe_fname(pair_key)}_path{idx}.mid")
                    _emit_token_list(
                        mid, tr, 0.0, token_list, pdb_key, freq_map, outp,
                        meta={"scope": "per_path", "pdb": pdb_key, "pair": pair_key, "path_index": idx}
                    )
                    with open(outp, "wb") as fh:
                        mid.writeFile(fh)
                    written.append(outp)
                    if gui: _log(logger,f"🎵 Wrote {outp}\n")
        return (written, event_logs) if return_event_log else written

    if policy == "per_pair":
        for pdb_key, pairs in paths_dict_2.items():
            pdb_base = _base_only(pdb_key)
            for pair_key, pdata in pairs.items():
                paths = list(pdata.get("paths", []))
                if not paths:
                    continue
                token_list = _unique_sorted_tokens_from_paths(paths)
                freq_map = None
                if vel_mode == "by_frequency":
                    freq_map = _norm01(_count_map_from_paths(paths)) or None

                mid = MIDIFile(1); tr = 0
                mid.addTempo(tr, 0, tempo_bpm)
                mid.addProgramChange(tr, 0, 0, program)

                outp = os.path.join(run_dir, f"{pdb_base}_{_safe_fname(pair_key)}.mid")
                _emit_token_list(
                    mid, tr, 0.0, token_list, pdb_key, freq_map, outp,
                    meta={"scope": "per_pair", "pdb": pdb_key, "pair": pair_key}
                )
                with open(outp, "wb") as fh:
                    mid.writeFile(fh)
                written.append(outp)
                if gui: _log(logger,f"🎵 Wrote {outp}\n")
        return (written, event_logs) if return_event_log else written

    # per_pdb (default)
    for pdb_key, pairs in paths_dict_2.items():
        pdb_base = _base_only(pdb_key)
        all_paths = []
        for _pair_key, pdata in pairs.items():
            all_paths.extend(list(pdata.get("paths", [])))
        if not all_paths:
            continue

        token_list = _unique_sorted_tokens_from_paths(all_paths)
        freq_map = None
        if vel_mode == "by_frequency":
            freq_map = _norm01(_count_map_from_paths(all_paths)) or None

        mid = MIDIFile(1); tr = 0
        mid.addTempo(tr, 0, tempo_bpm)
        mid.addProgramChange(tr, 0, 0, program)

        outp = os.path.join(run_dir, f"{pdb_base}.mid")
        _emit_token_list(
            mid, tr, 0.0, token_list, pdb_key, freq_map, outp,
            meta={"scope": "per_pdb", "pdb": pdb_key}
        )
        with open(outp, "wb") as fh:
            mid.writeFile(fh)
        written.append(outp)
        if gui: _log(logger,f"🎵 Wrote {outp}\n")

    return (written, event_logs) if return_event_log else written


pr_generate_audio = generate_audio

def _set_b_all(atom, b):

    b = float(b)
    if hasattr(atom, "is_disordered") and atom.is_disordered():
        # tüm altloc varyantlarına yaz
        for alt in atom.child_dict.values():
            alt.set_bfactor(b)
    else:
        atom.set_bfactor(b)

def save_colored_pdbs(jobname, all_normalized_frequencies, pdb_info_dict, logger=None, paths_dict_2=None):
    import os
    from collections import Counter

    def _logx(msg):
        try:
            _log(logger, msg)
        except Exception:
            try:
                if logger and hasattr(logger, "log_output"):
                    logger.log_output(msg)
            except Exception:
                pass

    _logx("🎨 Saving colored PDBs: per-PDB normalized + per-PDB TOTAL + GLOBAL TOTAL...\n")

    # --- job dir: accept name OR absolute path ---
    if isinstance(jobname, str) and os.path.isdir(jobname):
        job_dir = jobname
    else:
        job_dir, _ = _job_dir_and_label(jobname)

    pdb_dir = os.path.join(job_dir, "pdb_files")
    if not os.path.isdir(pdb_dir):
        _logx(f"❌ PDB folder not found: {pdb_dir}\n")
        return

    all_freqs = all_normalized_frequencies or {}
    pdb_info_dict = pdb_info_dict or {}

    # ----------------------------
    # Helpers (case-robust)
    # ----------------------------
    def _base_variants(x):
        """
        Case-robust variants for matching:
          - raw
          - lower/upper
          - split('.')[0] variants
        """
        try:
            b = _base_only(x)
        except Exception:
            b = str(x)

        b = str(b).strip()
        out = set()
        if not b:
            return out

        out.add(b)
        out.add(b.lower())
        out.add(b.upper())

        b0 = b.split(".")[0]
        out.add(b0)
        out.add(b0.lower())
        out.add(b0.upper())
        return out

    def _pick_first_match(base_variants, mapping_dict):
        """Return mapping_dict[key] for the first key found in mapping_dict."""
        for bv in base_variants:
            if bv in mapping_dict:
                return mapping_dict[bv]
        return None

    # --- canonical map for frequencies: base -> real key in all_freqs ---
    freq_key_by_base = {}
    for k in all_freqs.keys():
        try:
            for b in _base_variants(k):
                if b and b not in freq_key_by_base:
                    freq_key_by_base[b] = k
        except Exception:
            pass

    # --- canonical map for pdb_info_dict: base -> pdb_data ---
    pdbdata_by_base = {}
    for k, v in pdb_info_dict.items():
        try:
            for b in _base_variants(k):
                if b and b not in pdbdata_by_base:
                    pdbdata_by_base[b] = v
        except Exception:
            pass

    def _idx2tok_for_base(pdb_base_canon):
        """Return node_index_map for this pdb_base (canonical), if available."""
        pdb_data = pdbdata_by_base.get(pdb_base_canon) or {}
        nim = pdb_data.get("node_index_map") or {}
        return nim if isinstance(nim, dict) else {}

    def _node_to_token(pdb_base_canon, node):
        """
        Convert node into token string.
        Accepts:
          - token-like strings containing ":" -> returned as-is
          - index-like int/"123" -> mapped via node_index_map
        """
        if node is None:
            return None

        s = str(node).strip()
        if ":" in s:
            return s

        try:
            idx = int(s)
        except Exception:
            return None

        nim = _idx2tok_for_base(pdb_base_canon)
        tok = nim.get(idx)
        if tok:
            return str(tok).strip()
        return None

    def _parse_token_any(tok):
        """
        Returns: (seg_u, ch_u, rn:int, ic:str|None)
        Accepts:
          - "C:1492"
          - "EB:C:1492"
          - "NOSEG:C:1492A"
        """
        try:
            seg, ch, rn, ic = flex_parse_residue_token(tok, strict=False, default_seg="NOSEG")
            if ch and rn is not None:
                ic = (str(ic).strip() if ic not in (None, "", " ") else None)
                return (str(seg or "NOSEG").strip().upper(),
                        str(ch).strip().upper(),
                        int(rn),
                        ic)
        except Exception:
            pass

        s = str(tok).strip()
        parts = s.split(":")
        seg = "NOSEG"
        ch = None
        res_part = None

        if len(parts) == 2:
            ch, res_part = parts
        elif len(parts) >= 3:
            seg = ":".join(parts[:-2]) if len(parts) > 3 else parts[0]
            ch = parts[-2]
            res_part = parts[-1]
        else:
            return (None, None, None, None)

        if not ch or res_part is None:
            return (None, None, None, None)

        digits = "".join(c for c in res_part if c.isdigit())
        if not digits:
            return (None, None, None, None)
        rn = int(digits)

        tail_alpha = "".join(c for c in res_part if c.isalpha()).strip()
        ic = tail_alpha or None

        return (str(seg or "NOSEG").strip().upper(), str(ch).strip().upper(), rn, ic)

    def _build_maps_from_token_values(token_values_dict):
        """
        token_values_dict: {token(str): float}
        token can be 'A:123' or 'SEG:A:123A'
        """
        strict_map = {}
        simple_map = {}
        for tok, v in (token_values_dict or {}).items():
            if not isinstance(v, (int, float)):
                continue
            seg, ch, rn, ic = _parse_token_any(tok)
            if not ch or rn is None:
                continue

            ic_suffix = f"{ic}" if ic else ""
            seg_u = (seg or "NOSEG").strip().upper()
            ch_u = ch.strip().upper()

            strict_k = f"{seg_u}:{ch_u}:{int(rn)}{ic_suffix}"
            simple_k = f"{ch_u}:{int(rn)}{ic_suffix}"

            strict_map[strict_k] = float(v)
            if simple_k not in simple_map:
                simple_map[simple_k] = float(v)

        return strict_map, simple_map

    def _write_colored_pdb(in_pdb_path, out_pdb_path, strict_map, simple_map):
        """Write B-factor colored PDB (0..100)."""
        # detect if this PDB uses SEGID field
        has_segid = False
        with open(in_pdb_path, "r", encoding="utf-8", errors="ignore") as fchk:
            for line in fchk:
                if (line.startswith("ATOM") or line.startswith("HETATM")) and len(line) >= 76:
                    if line[72:76].strip():
                        has_segid = True
                        break

        with open(in_pdb_path, "r", encoding="utf-8", errors="ignore") as fin, \
             open(out_pdb_path, "w", encoding="utf-8") as fout:

            for line in fin:
                if not (line.startswith("ATOM") or line.startswith("HETATM")):
                    fout.write(line)
                    continue
                if len(line) < 66:
                    fout.write(line)
                    continue

                chain_id = (line[21].strip() or "").upper()
                resseq_str = line[22:26].strip()
                icode = (line[26].strip() or None)
                seg = (line[72:76].strip() if len(line) >= 76 else "")
                seg_u = (seg.strip().upper() if seg.strip() else "NOSEG")

                digits = "".join(c for c in resseq_str if c.isdigit())
                if not digits or not chain_id:
                    fout.write(line)
                    continue
                rn = int(digits)

                ic_suffix = f"{icode}" if icode else ""
                k_strict = f"{seg_u}:{chain_id}:{rn}{ic_suffix}"
                k_simple = f"{chain_id}:{rn}{ic_suffix}"

                bval = strict_map.get(k_strict)
                if bval is None and (not has_segid):
                    bval = simple_map.get(k_simple)
                if bval is None:
                    bval = 0.0

                # clamp 0–100
                if bval < 0:
                    bval = 0.0
                elif bval > 100:
                    bval = 100.0

                newline = line[:60] + f"{float(bval):6.2f}" + line[66:]
                fout.write(newline)

    def _rescale_0_100(values_dict):
        """Rescale dict values to 0..100 by max (keeps keys)."""
        if not values_dict:
            return {}
        vmax = max(values_dict.values()) if values_dict else 0.0
        if vmax <= 0:
            return {k: 0.0 for k in values_dict.keys()}
        return {k: (float(v) / float(vmax)) * 100.0 for k, v in values_dict.items()}

    # ----------------------------
    # list pdb files
    # ----------------------------
    pdb_files = [f for f in sorted(os.listdir(pdb_dir)) if f.lower().endswith(".pdb")]
    if not pdb_files:
        _logx(f"❌ No .pdb files found in: {pdb_dir}\n")
        return

    # global accumulator across PDBs
    global_total_counts = Counter()

    for fname in pdb_files:
        pdb_base_raw = _base_only(fname)               # e.g., "2RH1" (for folder/filename)
        pdb_base_canon = _base_key(pdb_base_raw)       # e.g., "2rh1" (for lookups)
        pdb_base_variants = _base_variants(pdb_base_raw) | _base_variants(pdb_base_canon)

        in_pdb = os.path.join(pdb_dir, fname)

        # output dir per PDB (your existing behavior: one folder per structure)
        out_dir = os.path.join(job_dir, pdb_base_raw)
        os.makedirs(out_dir, exist_ok=True)

        # -------------------------------
        # (A) PER-PDB NORMALIZED (0..100)
        # -------------------------------
        freq_key = _pick_first_match(pdb_base_variants, freq_key_by_base)
        nm_full = all_freqs.get(freq_key) if freq_key is not None else None

        if not nm_full:
            _logx(f"⚠️ No normalized frequencies for {fname} (base '{pdb_base_raw}'). Skipping per-PDB normalized.\n")
        else:
            token_vals_norm = {}
            for k, v in nm_full.items():
                if not isinstance(v, (int, float)):
                    continue
                tok = _node_to_token(pdb_base_canon, k)
                if not tok:
                    continue
                token_vals_norm[tok] = float(v)  # already 0..100

            if token_vals_norm:
                strict_map, simple_map = _build_maps_from_token_values(token_vals_norm)
                out_norm = os.path.join(out_dir, f"{pdb_base_raw}_colored.pdb")
                _write_colored_pdb(in_pdb, out_norm, strict_map, simple_map)
                _logx(f"✅ Per-PDB normalized colored: {out_norm}\n")
            else:
                _logx(f"⚠️ Normalized map exists but no usable tokens for {fname}. Skipping per-PDB normalized.\n")

        # -------------------------------
        # (B) PER-PDB TOTAL from paths_dict_2
        # -------------------------------
        if not paths_dict_2:
            _logx(f"⚠️ paths_dict_2 not provided -> per-PDB total not computed for {fname}.\n")
            continue

        pairs = None
        for k, v in (paths_dict_2 or {}).items():
            try:
                kb = _base_only(k)
                if kb in pdb_base_variants or kb.split(".")[0] in pdb_base_variants:
                    pairs = v
                    break
            except Exception:
                continue

        if not pairs:
            _logx(f"⚠️ No paths found for {fname} (base '{pdb_base_raw}'). Skipping per-PDB total.\n")
            continue

        # count internal nodes across all paths
        presence = Counter()
        for _pair_key, pdata in (pairs or {}).items():
            paths = (pdata or {}).get("paths", []) or []
            for path in paths:
                if not path or len(path) < 2:
                    continue
                internal = set(path[1:-1])
                for node in internal:
                    tok = _node_to_token(pdb_base_canon, node)
                    if tok:
                        presence[tok] += 1

        if not presence:
            _logx(f"⚠️ Total presence empty for {fname}. Skipping per-PDB total.\n")
            continue

        # accumulate global raw counts
        global_total_counts.update(presence)

        # scale within this PDB to 0..100 for coloring
        presence_scaled = _rescale_0_100(dict(presence))
        strict_tot, simple_tot = _build_maps_from_token_values(presence_scaled)

        out_total = os.path.join(out_dir, f"{pdb_base_raw}_total_colored.pdb")
        _write_colored_pdb(in_pdb, out_total, strict_tot, simple_tot)
        _logx(f"✅ Per-PDB TOTAL colored: {out_total}\n")

    # -------------------------------
    # (C) GLOBAL TOTAL across all PDBs -> color reference PDB in job root
    # -------------------------------
    if paths_dict_2 and global_total_counts:
        ref_fname = pdb_files[0]
        ref_base_raw = _base_only(ref_fname)
        ref_path = os.path.join(pdb_dir, ref_fname)

        global_scaled = _rescale_0_100(dict(global_total_counts))
        g_strict, g_simple = _build_maps_from_token_values(global_scaled)

        out_global = os.path.join(job_dir, f"GLOBAL_TOTAL__{ref_base_raw}__colored.pdb")
        _write_colored_pdb(ref_path, out_global, g_strict, g_simple)
        _logx(f"✅ GLOBAL TOTAL colored: {out_global}\n")

    _logx("🎨 Finished saving colored PDBs.\n")

def build_3d_html(pdbstr, start_residues=None, end_residues=None):
    import json
    import os

    js_path = _resource_path_local("3Dmol-min.js")
    if not os.path.exists(js_path):
        raise FileNotFoundError(f"3Dmol-min.js not found: {js_path}")

    with open(js_path, "r", encoding="utf-8", errors="ignore") as fh:
        js_code = fh.read()

    start_residues = start_residues or []
    end_residues = end_residues or []

    pdb_json = json.dumps(pdbstr)
    start_json = json.dumps(start_residues)
    end_json = json.dumps(end_residues)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>3D Viewer</title>
<style>
    html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: white;
    }}
    #viewer {{
        width: 100%;
        height: 100vh;
    }}
</style>
<script>
{js_code}
</script>
</head>
<body>
<div id="viewer"></div>

<script>
(function() {{
    const pdbText = {pdb_json};
    const startResidues = {start_json};
    const endResidues = {end_json};

    const viewer = $3Dmol.createViewer("viewer", {{
        backgroundColor: "white"
    }});

    viewer.addModel(pdbText, "pdb");

    viewer.setStyle({{}}, {{
        cartoon: {{
            colorscheme: {{
                prop: "b",
                gradient: "roygb",
                min: 0.0,
                max: 100.0
            }},
            tubes: true,
            arrows: true
        }}
    }});

    function markResidues(resList, color, label) {{
        for (const item of resList) {{
            const ch = String(item[0]).trim();
            const rn = String(item[1]).trim();
            if (!ch || !rn) continue;

            const sel = {{chain: ch, resi: rn}};

            viewer.addStyle(sel, {{
                sphere: {{
                    color: color,
                    radius: 1.8
                }}
            }});

            viewer.addLabel(label + " " + ch + ":" + rn, {{
                fontColor: "white",
                backgroundColor: "black",
                backgroundOpacity: 0.85,
                fontSize: 16,
                inFront: true
            }}, sel);
        }}
    }}

    markResidues(startResidues, "#00FFFF", "Start");
    markResidues(endResidues, "#FF00FF", "End");

    viewer.zoomTo();
    viewer.center();
    viewer.zoom(1.05);
    viewer.render();
}})();
</script>
</body>
</html>
"""
    return html

def extract_residue_nodes_and_coords(structure_file):
    from Bio.PDB import PDBParser, MMCIFParser

    fmt = "mmcif" if structure_file.lower().endswith(".cif") else "pdb"

    if fmt == "pdb":
        structure = PDBParser(QUIET=True).get_structure("s", structure_file)
    else:
        structure = MMCIFParser(QUIET=True).get_structure("s", structure_file)

    nodes = []
    coords = {}
    resnames = {}
    seen = set()

    for model in structure:
        for chain in model:
            ch = str(chain.id).strip()

            for res in chain:
                if res.id[0] != " ":
                    continue

                resseq = int(res.id[1])
                icode = (res.id[2] or "").strip()
                rn = f"{resseq}{icode}" if icode else f"{resseq}"
                key = f"{ch}:{rn}"

                if key in seen:
                    continue
                seen.add(key)

                atom = None
                if res.has_id("CA"):
                    atom = res["CA"]
                elif res.has_id("P"):
                    atom = res["P"]

                if atom is not None:
                    coord = [float(x) for x in atom.coord]
                else:
                    atoms = [a.coord for a in res.get_atoms()]
                    if not atoms:
                        continue
                    n = len(atoms)
                    coord = [
                        float(sum(a[0] for a in atoms) / n),
                        float(sum(a[1] for a in atoms) / n),
                        float(sum(a[2] for a in atoms) / n),
                    ]

                nodes.append([ch, rn])
                coords[key] = coord
                resnames[key] = str(res.get_resname()).strip()

    return nodes, coords, resnames

def build_3d_html_colored(
    structure_file,
    start_residues=None,
    end_residues=None,
    freq_map=None,
    graph_nodes=None,
    graph_edges=None
):
    import json
    import os

    if not os.path.exists(structure_file):
        raise FileNotFoundError(structure_file)

    js_path = _resource_path_local("3Dmol-min.js")
    if not os.path.exists(js_path):
        raise FileNotFoundError(f"3Dmol-min.js not found: {js_path}")

    with open(js_path, "r", encoding="utf-8", errors="ignore") as fh:
        js_code = fh.read()

    with open(structure_file, "r", encoding="utf-8", errors="ignore") as fh:
        model_text = fh.read()

    fmt = "mmcif" if structure_file.lower().endswith(".cif") else "pdb"

    start_residues = start_residues or []
    end_residues = end_residues or []
    freq_map = freq_map or {}
    graph_nodes = graph_nodes or []
    graph_edges = graph_edges or []

    # ---------------------------------------------------------
    # ONE NODE PER RESIDUE / NUCLEOTIDE
    # Representative atom:
    #   protein -> CA
    #   nucleotide -> P
    # fallback -> centroid of residue atoms
    # ---------------------------------------------------------
    node_coords = {}
    residue_names = {}

    try:
        if fmt == "pdb":
            from Bio.PDB import PDBParser
            structure = PDBParser(QUIET=True).get_structure("s", structure_file)
        else:
            from Bio.PDB import MMCIFParser
            structure = MMCIFParser(QUIET=True).get_structure("s", structure_file)

        seen = set()

        for model in structure:
            for chain in model:
                ch = str(chain.id).strip()

                for res in chain:
                    if res.id[0] != " ":
                        continue

                    resseq = int(res.id[1])
                    icode = (res.id[2] or "").strip()
                    rn = f"{resseq}{icode}" if icode else f"{resseq}"
                    key = f"{ch}:{rn}"

                    if key in seen:
                        continue
                    seen.add(key)

                    atom = None
                    if res.has_id("CA"):
                        atom = res["CA"]
                    elif res.has_id("P"):
                        atom = res["P"]

                    if atom is not None:
                        coord = [float(x) for x in atom.coord]
                    else:
                        coords = [a.coord for a in res.get_atoms()]
                        if not coords:
                            continue
                        n = len(coords)
                        coord = [
                            float(sum(c[0] for c in coords) / n),
                            float(sum(c[1] for c in coords) / n),
                            float(sum(c[2] for c in coords) / n),
                        ]

                    node_coords[key] = coord
                    residue_names[key] = str(res.get_resname()).strip()
    except Exception:
        pass

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Interactive 3D Structure Viewer</title>

<style>
html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    font-family: Arial, sans-serif;
    background: #ffffff;
}}

#viewer {{
    position: absolute;
    left: 0;
    top: 0;
    right: 280px;
    bottom: 0;
}}

#panel {{
    position: absolute;
    top: 0;
    right: 0;
    width: 280px;
    height: 100%;
    box-sizing: border-box;
    background: #fafafa;
    border-left: 1px solid #d0d0d0;
    padding: 14px;
    overflow-y: auto;
}}

.panel-title {{
    font-weight: bold;
    font-size: 15px;
    margin-bottom: 8px;
}}

.legend-wrap {{
    display: flex;
    align-items: stretch;
    gap: 10px;
    margin-bottom: 16px;
}}

.legend-bar {{
    width: 26px;
    height: 220px;
    border: 1px solid #999;
    background: linear-gradient(
    to top,
    #0d0887 0%,
    #5c01a6 20%,
    #9c179e 40%,
    #cc4778 60%,
    #ed7953 75%,
    #fdb42f 90%,
    #f0f921 100%
    );
}}

.legend-labels {{
    height: 220px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    font-size: 12px;
}}

.badge {{
    display: inline-block;
    padding: 4px 9px;
    margin: 3px 0;
    border-radius: 12px;
    font-size: 12px;
    color: white;
}}

.badge-start {{ background: #00bcd4; }}
.badge-end   {{ background: #d81b60; }}
.badge-edge  {{ background: #D3D3D3; }}

.section {{
    margin-bottom: 16px;
}}

#hoverinfo {{
    font-size: 12px;
    line-height: 1.45;
    background: white;
    border: 1px solid #dddddd;
    border-radius: 6px;
    padding: 10px;
    min-height: 110px;
    white-space: pre-line;
}}

.ctrl-row {{
    margin: 6px 0;
    font-size: 12px;
}}
</style>

<script>
{js_code}
</script>
</head>

<body>
<div id="viewer"></div>

<div id="panel">
    <div class="section">
        <div class="panel-title">Frequency Scale (%)</div>
        <div class="legend-wrap">
            <div class="legend-bar"></div>
            <div class="legend-labels">
                <div>100</div>
                <div>75</div>
                <div>50</div>
                <div>25</div>
                <div>0 </div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="panel-title">Layers</div>
        <div class="ctrl-row">
            <label><input type="checkbox" id="chkCartoon" checked onchange="updateVisibility()"> Cartoon</label>
        </div>
        <div class="ctrl-row">
            <label><input type="checkbox" id="chkNodes" checked onchange="updateVisibility()"> Graph Nodes</label>
        </div>
        <div class="ctrl-row">
            <label><input type="checkbox" id="chkEdges" checked onchange="updateVisibility()"> Graph Edges</label>
        </div>
        <div class="ctrl-row">
            <label><input type="checkbox" id="chkStartEnd" checked onchange="updateVisibility()"> Start / End</label>
        </div>
    </div>

    <div class="section">
        <div class="panel-title">Hover Info</div>
        <div id="hoverinfo">Move the mouse over a node or residue.</div>
    </div>
</div>

<script>
const MODEL_TEXT  = {json.dumps(model_text)};
const MODEL_FMT   = {json.dumps(fmt)};
const START_RES   = {json.dumps(start_residues)};
const END_RES     = {json.dumps(end_residues)};
const FREQ_MAP    = {json.dumps(freq_map)};
const GRAPH_NODES = {json.dumps(graph_nodes)};
const GRAPH_EDGES = {json.dumps(graph_edges)};
const NODE_COORDS = {json.dumps(node_coords)};
const RESN_MAP    = {json.dumps(residue_names)};

const hoverBox = document.getElementById("hoverinfo");

let viewer = null;

function normKey(chain, resi) {{
    return String(chain).trim() + ":" + String(resi).trim();
}}

function getFreq(chain, resi) {{
    const key = normKey(chain, resi);
    const v = FREQ_MAP[key];
    if (v === undefined || v === null || isNaN(Number(v))) return 0;
    return Number(v);
}}

function getResn(chain, resi, fallback) {{
    const key = normKey(chain, resi);
    return RESN_MAP[key] || fallback || "N/A";
}}

function getCoord(chain, resi) {{
    return NODE_COORDS[normKey(chain, resi)] || null;
}}

function colorFromFreq(v) {{
    const t = Math.max(0, Math.min(100, Number(v))) / 100.0;

    const colors = [
        [13, 8, 135],
        [75, 3, 161],
        [125, 3, 168],
        [168, 34, 150],
        [203, 70, 121],
        [229, 107, 93],
        [248, 148, 65],
        [253, 195, 40],
        [240, 249, 33]
    ];

    const n = colors.length - 1;
    const x = t * n;
    const i = Math.floor(x);
    const f = x - i;

    const c1 = colors[i];
    const c2 = colors[Math.min(i + 1, n)];

    const r = Math.round(c1[0] + (c2[0] - c1[0]) * f);
    const g = Math.round(c1[1] + (c2[1] - c1[1]) * f);
    const b = Math.round(c1[2] + (c2[2] - c1[2]) * f);

    return "rgb(" + r + "," + g + "," + b + ")";
}}

function scaleFromFreq(v) {{
    const x = Math.max(0, Math.min(100, Number(v))) / 100.0;
    return 0.3 + Math.pow(x, 1.5) * 5;
}}

function radiusFromFreq(v) {{
    if (v === null) return 0.03;
    const f = Math.max(0, Math.min(100, Number(v)));
    return 0.015 + (f / 100.0) * 0.1;
}}

function labelText(atom) {{
    const freq = getFreq(atom.chain, atom.resi);
    const freqText = (freq === null) ? "0" : freq.toFixed(2) + "%";

    return (
        "Chain: " + (atom.chain || "N/A") + "\\n" +
        "Residue No: " + (atom.resi || "N/A") + "\\n" +
        "Residue Name: " + getResn(atom.chain, atom.resi, atom.resn) + "\\n" +
        "Atom: " + (atom.atom || atom.elem || "N/A") + "\\n" +
        "Frequency: " + freqText
    );
}}

function updateHoverPanel(text) {{
    hoverBox.innerText = text;
}}

function addStartEndMarkers(list, color, label) {{
    for (const item of list) {{
        const ch = String(item[0]).trim();
        const rn = String(item[1]).trim();
        if (!ch || !rn) continue;

        const coord = getCoord(ch, rn);
        if (!coord) continue;

        viewer.addSphere({{
            center: {{ x: coord[0], y: coord[1], z: coord[2] }},
            radius: 0.22,
            color: color,
            alpha: 0.85
        }});

        viewer.addLabel(label + " " + ch + ":" + rn, {{
            position: {{ x: coord[0], y: coord[1], z: coord[2] }},
            fontColor: "white",
            backgroundColor: "black",
            backgroundOpacity: 0.75,
            fontSize: 11,
            inFront: true
        }});
    }}
}}

function rebuildScene() {{
    viewer.clear();

    const showCartoon  = document.getElementById("chkCartoon").checked;
    const showNodes    = document.getElementById("chkNodes").checked;
    const showEdges    = document.getElementById("chkEdges").checked;
    const showStartEnd = document.getElementById("chkStartEnd").checked;

    viewer.addModel(MODEL_TEXT, MODEL_FMT);

    if (showCartoon) {{
        viewer.setStyle({{}}, {{
            cartoon: {{
                color: "#b5b5b5",
                opacity: 0.55
            }}
        }});
    }}

    if (showNodes) {{
        for (const item of GRAPH_NODES) {{
            const ch = String(item[0]).trim();
            const rn = String(item[1]).trim();
            if (!ch || !rn) continue;

            const coord = getCoord(ch, rn);
            if (!coord) continue;

            const freq  = getFreq(ch, rn);
            const color = colorFromFreq(freq);
            const scale = scaleFromFreq(freq);

            viewer.addSphere({{
                center: {{ x: coord[0], y: coord[1], z: coord[2] }},
                radius: scale,
                color: color,
                alpha: 0.85
            }});
        }}
    }}


    if (showStartEnd) {{
        addStartEndMarkers(START_RES, "#00bcd4", "Start");
        addStartEndMarkers(END_RES,   "#d81b60", "End");
    }}

    if (showEdges) {{
        for (const e of GRAPH_EDGES) {{
            const a = e[0];
            const b = e[1];

            const ch1 = String(a[0]).trim();
            const rn1 = String(a[1]).trim();
            const ch2 = String(b[0]).trim();
            const rn2 = String(b[1]).trim();

            if (!ch1 || !ch2 || !rn1 || !rn2) continue;

            const c1 = getCoord(ch1, rn1);
            const c2 = getCoord(ch2, rn2);
            if (!c1 || !c2) continue;

            const f1 = getFreq(ch1, rn1);
            const f2 = getFreq(ch2, rn2);
            const favg = (f1 === null && f2 === null)
                ? null
                : (((f1 || 0) + (f2 || 0)) / ((f1 !== null && f2 !== null) ? 2.0 : 1.0));

            viewer.addCylinder({{
                start: {{ x: c1[0], y: c1[1], z: c1[2] }},
                end:   {{ x: c2[0], y: c2[1], z: c2[2] }},
                radius: radiusFromFreq(favg),
                color: "#D3D3D3",
                dashed: false,
                fromCap: 1,
                toCap: 1
            }});
        }}
    }}

    let nodeSet = new Set(
        GRAPH_NODES.map(x => String(x[0]).trim() + ":" + String(x[1]).trim())
    );

    viewer.setHoverable({{}}, true,
        function(atom, viewer) {{
            const key = normKey(atom.chain, atom.resi);
            if (!nodeSet.has(key)) return;

            const txt = labelText(atom);
            updateHoverPanel(txt);

            const ff = getFreq(atom.chain, atom.resi);
            const freqText = (ff === null) ? "N/A" : ff.toFixed(2) + "%";

            if (!atom._hoverLabel) {{
                atom._hoverLabel = viewer.addLabel(
                    (atom.chain || "?") + ":" + (atom.resi || "?") +
                    " | " + getResn(atom.chain, atom.resi, atom.resn) +
                    " | f=" + freqText,
                    {{
                        position: atom,
                        backgroundColor: "black",
                        fontColor: "white",
                        fontSize: 12,
                        backgroundOpacity: 0.82,
                        inFront: true
                    }}
                );
            }}
        }},
        function(atom, viewer) {{
            const key = normKey(atom.chain, atom.resi);
            if (!nodeSet.has(key)) return;

            updateHoverPanel("Move the mouse over a node or residue.");

            if (atom._hoverLabel) {{
                viewer.removeLabel(atom._hoverLabel);
                atom._hoverLabel = null;
            }}
        }}
    );

    viewer.zoomTo();
    viewer.center();
    viewer.rotate(90, "y");
    viewer.zoom(1.15);
    viewer.render();
}}

function updateVisibility() {{
    rebuildScene();
}}

viewer = $3Dmol.createViewer("viewer", {{
    backgroundColor: "white"
}});

rebuildScene();
</script>
</body>
</html>
"""
    return html

#####


# -----------------------------
# JSON helpers
# -----------------------------
def _json_dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _json_load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _job_root_from_jobname(jobname):
    # You already have _resolve_job_dir(jobname) in your codebase
    # Keep using that to avoid breaking existing layout.
    return _resolve_job_dir(jobname)


JOB_SCHEMA_VERSION = 1

def save_job_snapshot(jobname, gui, also_save_run=False, run_label=None):
    """
    Saves job_state + key dicts into the job folder ONLY when this function is called.

    Important:
    - This function is intended for manual Save Job.
    - Do NOT call this from autosave_job if you do not want automatic JSON/cache output.
    - Excel/PNG/PDB outputs are not affected by this function.
    """
    job_dir = _job_root_from_jobname(jobname)
    os.makedirs(job_dir, exist_ok=True)

    results_dir = os.path.join(job_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    # --- Manifest
    manifest_path = os.path.join(job_dir, "job_manifest.json")
    manifest = _json_load(manifest_path, default=None)

    if not manifest:
        manifest = {
            "schema_version": JOB_SCHEMA_VERSION,
            "jobname": jobname,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

    manifest["last_saved_at"] = datetime.now().isoformat(timespec="seconds")
    _json_dump(manifest_path, manifest)

    # --- State
    state = collect_job_state_from_gui(gui, jobname)
    _json_dump(os.path.join(job_dir, "job_state.json"), state)

    # --- Big dicts
    if getattr(gui, "pdb_info_dict", None):
        safe_pdb_info = _sanitize_pdb_info_dict(gui.pdb_info_dict)
        _json_dump(os.path.join(results_dir, "pdb_info_dict.json"), safe_pdb_info)

    if getattr(gui, "paths_dict_2", None):
        _json_dump(os.path.join(results_dir, "paths_dict_2.json"), gui.paths_dict_2)

    if getattr(gui, "all_normalized_frequencies", None):
        _json_dump(
            os.path.join(results_dir, "normalized_frequencies.json"),
            gui.all_normalized_frequencies
        )

    # --- Optional run snapshot, only if explicitly requested
    if also_save_run:
        save_run_snapshot(jobname, gui, run_label=run_label)

    return job_dir

def list_runs(jobname):
    job_dir = _job_root_from_jobname(jobname)
    runs_dir = os.path.join(job_dir, "runs")
    if not os.path.isdir(runs_dir):
        return []

    out = []
    for run_id in sorted(os.listdir(runs_dir)):
        cfg = os.path.join(runs_dir, run_id, "run_config.json")
        if os.path.exists(cfg):
            out.append((run_id, cfg))
    return out


def save_run_snapshot(jobname, gui, run_label=None):
    """
    Creates a run folder and stores run_config + results dicts (JSON-safe).
    Enables: open old job and regenerate music / recompute with same workspace.
    """
    import os
    from datetime import datetime

    job_dir = _job_root_from_jobname(jobname)
    run_id = _now_run_id()

    if run_label:
        run_label = "".join(c for c in str(run_label) if c.isalnum() or c in ("-", "_"))[:40]
        run_id = f"{run_id}_{run_label}"

    run_dir = os.path.join(job_dir, "runs", run_id)
    os.makedirs(run_dir, exist_ok=True)

    # run_config: keep it small and safe
    inputs = {}
    try:
        st = collect_job_state_from_gui(gui, jobname)
        inputs = (st or {}).get("inputs", {}) or {}
    except Exception:
        inputs = {}

    run_config = {
        "run_id": run_id,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": _json_safe(inputs),
        "stage": getattr(gui, "last_completed_stage", None),
    }
    _json_dump(os.path.join(run_dir, "run_config.json"), run_config)

    # paths_dict_2
    if getattr(gui, "paths_dict_2", None):
        _json_dump(
            os.path.join(run_dir, "paths_dict_2.json"),
            _json_safe(gui.paths_dict_2, max_depth=18)  # paths can be nested
        )

    # normalized frequencies
    if getattr(gui, "all_normalized_frequencies", None):
        _json_dump(
            os.path.join(run_dir, "normalized_frequencies.json"),
            _json_safe(gui.all_normalized_frequencies, max_depth=18)
        )

    return run_dir


def load_job_snapshot(job_dir, gui):
    """
    Loads job_state + dicts into GUI instance.
    Restores workspace so user can continue (does not auto-run computations).
    """
    import os

    state = _json_load(os.path.join(job_dir, "job_state.json"), default=None)
    if not state:
        raise FileNotFoundError(f"No job_state.json in: {job_dir}")

    # Ensure gui.state exists
    if not hasattr(gui, "state") or not isinstance(getattr(gui, "state", None), dict):
        gui.state = {}

    # Restore main dicts
    pdb_info = _json_load(os.path.join(job_dir, "results", "pdb_info_dict.json"), default=None)
    paths2   = _json_load(os.path.join(job_dir, "results", "paths_dict_2.json"), default=None)
    freqs    = _json_load(os.path.join(job_dir, "results", "normalized_frequencies.json"), default=None)

    if pdb_info is not None:
        gui.pdb_info_dict = pdb_info
    if paths2 is not None:
        gui.paths_dict_2 = paths2
    if freqs is not None:
        gui.all_normalized_frequencies = freqs

    # Stage restore
    gui.last_completed_stage = state.get("stage")

    # Restore lightweight inputs
    inputs = state.get("inputs", {}) or {}
    if isinstance(inputs, dict):
        gui.state.update(inputs)

    # remember jobname
    gui.state["jobname"] = state.get("jobname") or gui.state.get("jobname") or os.path.basename(job_dir)

    return state


def _is_biopython_structure_obj(x):
    # Avoid importing Bio.PDB here (keeps this helper light and safe)
    t = type(x)
    mod = getattr(t, "__module__", "") or ""
    name = getattr(t, "__name__", "") or ""
    # Covers Structure/Model/Chain/Residue/Atom and related Biopython classes
    return mod.startswith("Bio.PDB") or name in {"Structure", "Model", "Chain", "Residue", "Atom"}


def _json_safe(obj, *, max_depth=12, _depth=0, drop_keys=None):
    """
    Recursively convert an object into JSON-serializable data.

    - Keeps basic JSON types
    - Converts pathlib.Path -> str
    - Converts numpy arrays -> list (WARNING: can be large; drop instead if needed)
    - Converts numpy scalar -> python scalar
    - Converts Bio.PDB objects -> marker string
    - Dict keys -> str
    - Supports drop_keys at any dict level
    """
    if drop_keys is None:
        drop_keys = set()

    if _depth > max_depth:
        return "<max_depth_reached>"

    # basic JSON types
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # pathlib
    try:
        from pathlib import Path
        if isinstance(obj, Path):
            return str(obj)
    except Exception:
        pass

    # numpy
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            # Option A: keep (can be huge)
            return obj.tolist()
            # Option B: drop huge matrices
            # return "<ndarray_dropped>"
        if isinstance(obj, (np.integer, np.floating, np.bool_)):
            return obj.item()
    except Exception:
        pass

    # Biopython objects (Structure/Atom/Residue/...)
    if _is_biopython_structure_obj(obj):
        return f"<Bio.PDB:{type(obj).__name__}>"

    # dict
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            ks = k if isinstance(k, str) else str(k)
            if ks in drop_keys:
                continue
            out[ks] = _json_safe(v, max_depth=max_depth, _depth=_depth + 1, drop_keys=drop_keys)
        return out

    # list/tuple/set
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(x, max_depth=max_depth, _depth=_depth + 1, drop_keys=drop_keys) for x in obj]

    # fallback
    try:
        return str(obj)
    except Exception:
        return f"<unserializable:{type(obj).__name__}>"


def _sanitize_pdb_info_dict(pdb_info_dict):
    """
    Returns a JSON-safe copy of pdb_info_dict:
    - Drops heavy/non-serializable fields (structure, graphs, matrices, kdtrees, caches)
    - Keeps file paths, chain lists, residue maps, etc.
    """
    if not isinstance(pdb_info_dict, dict):
        return _json_safe(pdb_info_dict)

    drop_keys = {
        # Biopython / runtime objects
        "structure", "biopython_structure", "parsed_structure",
        "model_obj", "chain_obj", "residue_obj", "atom_obj",

        # Graph / caches / heavy arrays
        "graph", "G", "nx_graph", "networkx_graph",
        "adj_matrix", "edgeweight_matrix", "distance_matrix",
        "kd_tree", "kdtree", "coords_cache", "atom_cache",
        "neighbor_cache", "contact_cache",
    }

    cleaned = {}
    for pdb_key, info in pdb_info_dict.items():
        if isinstance(info, dict):
            c = {}
            for k, v in info.items():
                if k in drop_keys:
                 continue
                 c[k] = v
            cleaned[pdb_key] = c
        else:
            cleaned[pdb_key] = info


    return _json_safe(cleaned, drop_keys=drop_keys)


def collect_job_state_from_gui(gui, jobname):

    if not hasattr(gui, "state") or not isinstance(getattr(gui, "state", None), dict):
        gui.state = {}

    stage = getattr(gui, "last_completed_stage", None)


    if stage is None:
        stage = gui.state.get("last_completed_stage")


    if stage is None:
        stage = "unknown"

    state = {
        "schema_version": 1,
        "jobname": jobname,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "stage": stage,
        "inputs": gui.state.copy(),
        "has": {
            "pdb_info_dict": bool(getattr(gui, "pdb_info_dict", None)),
            "paths_dict_2": bool(getattr(gui, "paths_dict_2", None)),
            "all_normalized_frequencies": bool(getattr(gui, "all_normalized_frequencies", None)),
        }
    }
    return state


def compute_global_normalized_frequencies(paths_dict_2, internal_only=True):
    """
    Compute GLOBAL/TOTAL percent frequencies (0..100) across ALL conformers in paths_dict_2.
    Uses presence-per-path (not per-step). Optional internal_only excludes endpoints.
    """
    from collections import Counter

    presence = Counter()
    total_paths = 0

    for _pdb_key, pair_dict in (paths_dict_2 or {}).items():
        for _pair_key, pdata in (pair_dict or {}).items():
            paths = (pdata or {}).get("paths", []) or []
            for p in paths:
                if not p or len(p) < 2:
                    continue
                total_paths += 1
                nodes = p[1:-1] if (internal_only and len(p) > 2) else p
                for tok in set(nodes):  # presence per path
                    presence[tok] += 1

    if total_paths <= 0:
        return {}

    return {tok: (presence[tok] / float(total_paths)) * 100.0 for tok in presence}


def save_global_total_colored_reference_pdb(jobname, paths_dict_2, reference_pdb=None, logger=None):
    """
    1) Computes GLOBAL/TOTAL % map across ALL conformers (paths_dict_2).
    2) Colors ONE reference PDB by writing GLOBAL % into B-factor.
    3) Saves outputs directly under job folder for cross-job comparison.
       - <job_dir>/GLOBAL_TOTAL__<refbase>__colored.pdb
       - <job_dir>/GLOBAL_TOTAL__frequencies.json
    """
    import os, json


    if isinstance(jobname, str) and os.path.isdir(jobname):
        job_dir = jobname
    else:
        job_dir, _ = _job_dir_and_label(jobname)

    pdb_dir = os.path.join(job_dir, "pdb_files")

    if not os.path.isdir(pdb_dir):
        _log(logger, f"⚠️ GLOBAL TOTAL: pdb_files not found: {pdb_dir}\n")
        return None

    if reference_pdb is None:
        cand = [f for f in sorted(os.listdir(pdb_dir)) if f.lower().endswith(".pdb")]
        if not cand:
            _log(logger, "⚠️ GLOBAL TOTAL: no .pdb files found in pdb_files.\n")
            return None
        reference_pdb = os.path.join(pdb_dir, cand[0])
    else:
        # allow passing just filename
        if not os.path.isabs(reference_pdb):
            reference_pdb = os.path.join(pdb_dir, reference_pdb)
        if not os.path.isfile(reference_pdb):
            _log(logger, f"⚠️ GLOBAL TOTAL: reference PDB not found: {reference_pdb}\n")
            return None

    # --- compute global map ---
    global_map = compute_global_normalized_frequencies(paths_dict_2, internal_only=True)
    if not global_map:
        _log(logger, "⚠️ GLOBAL TOTAL: global frequency map is empty (no paths?).\n")
        return None

    # --- reuse the SAME parsing/patching logic as save_colored_pdbs ---
    def _parse_token_any(tok):
        try:
            seg, ch, rn, ic = flex_parse_residue_token(tok, strict=False, default_seg="NOSEG")
            if ch and rn is not None:
                ic = (str(ic).strip() if ic not in (None, "", " ") else None)
                return (str(seg or "NOSEG").strip().upper(),
                        str(ch).strip().upper(),
                        int(rn),
                        ic)
        except Exception:
            return (None, None, None, None)

    strict_map = {}
    simple_map = {}
    for tok, v in global_map.items():
        if not isinstance(v, (int, float)):
            continue
        seg_u, ch_u, rn, ic = _parse_token_any(tok)
        if not ch_u or rn is None:
            continue
        ic_suffix = f"{ic}" if ic else ""
        strict_k = f"{seg_u}:{ch_u}:{int(rn)}{ic_suffix}"
        simple_k = f"{ch_u}:{int(rn)}{ic_suffix}"
        strict_map[strict_k] = float(v)
        if simple_k not in simple_map:
            simple_map[simple_k] = float(v)

    if not strict_map and not simple_map:
        _log(logger, "⚠️ GLOBAL TOTAL: no valid residue tokens after parsing.\n")
        return None

    # detect segid usage in reference PDB
    has_segid = False
    with open(reference_pdb, "r", encoding="utf-8", errors="ignore") as fchk:
        for line in fchk:
            if (line.startswith("ATOM") or line.startswith("HETATM")) and len(line) >= 76:
                if line[72:76].strip():
                    has_segid = True
                    break

    refbase = _base_only(os.path.basename(reference_pdb))
    out_pdb = os.path.join(job_dir, f"GLOBAL_TOTAL__{refbase}__colored.pdb")

    with open(reference_pdb, "r", encoding="utf-8", errors="ignore") as fin, \
         open(out_pdb, "w", encoding="utf-8") as fout:
        for line in fin:
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                fout.write(line)
                continue
            if len(line) < 66:
                fout.write(line)
                continue

            chain_id = (line[21].strip() or "").upper()
            resseq_str = line[22:26].strip()
            icode = (line[26].strip() or None)
            seg = (line[72:76].strip() if len(line) >= 76 else "")
            seg_u = (seg.strip().upper() if seg.strip() else "NOSEG")

            digits = "".join(c for c in resseq_str if c.isdigit())
            if not digits or not chain_id:
                fout.write(line)
                continue
            rn = int(digits)

            ic_suffix = f"{icode}" if icode else ""

            # try multiple strict keys + always allow simple fallback
            k_strict1 = f"{seg_u}:{chain_id}:{rn}{ic_suffix}"  # segid from file
            k_strict2 = f"NOSEG:{chain_id}:{rn}{ic_suffix}"  # token may be NOSEG
            k_simple = f"{chain_id}:{rn}{ic_suffix}"  # chain-only fallback

            bval = strict_map.get(k_strict1)
            if bval is None:
                bval = strict_map.get(k_strict2)
            if bval is None:
                bval = simple_map.get(k_simple)
            if bval is None:
                bval = 0.0

            fout.write(line[:60] + f"{float(bval):6.2f}" + line[66:])

    _log(logger, f"✅ GLOBAL TOTAL colored PDB written: {out_pdb}\n")

    # also save map for cross-job comparisons
    out_json = os.path.join(job_dir, "GLOBAL_TOTAL__frequencies.json")
    try:
        with open(out_json, "w", encoding="utf-8") as jf:
            json.dump(global_map, jf, ensure_ascii=False, indent=2)
        _log(logger, f"✅ GLOBAL TOTAL map saved: {out_json}\n")
    except Exception as e:
        _log(logger, f"⚠️ GLOBAL TOTAL map could not be saved: {e}\n")

    return out_pdb
