import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os, threading, subprocess, json, pickle, shutil, tempfile, re, sys, ctypes, webbrowser
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
from pathlib import Path
import re
import time
from tkinter import ttk, messagebox



# Heavy scientific dependencies are loaded after the Welcome window is visible.
# This keeps startup responsive while preserving the same analysis functions.
_BACKEND_READY = False
_BACKEND_ERROR = None

def _load_analysis_backend():
    global _BACKEND_READY, _BACKEND_ERROR
    global PDBParser, MIDIFile, np
    global create_job_folder, load_pdb_files, run_adj_matrix, parse_residue_input
    global run_residue_mapping, calculate_shortest_paths, save_colored_pdbs
    global build_3d_html, extract_start_end_residues_safe, play_midi, stop_midi
    global note_to_midi, apply_transpose_clamp, get_triad_presets, MusicOptions
    global run_cooccurrence_backbone_for_one_structure, run_cooccurrence_backbone_ensemble
    global run_path_similarity_for_one_structure, run_path_similarity_ensemble
    global NOTE_NAMES, ALL_RESIDUES, build_default_aa_mapping
    global aa_mapping_to_residue_mapping, pr_generate_audio
    try:
        import numpy as _np
        from Bio.PDB import PDBParser as _PDBParser
        from midiutil import MIDIFile as _MIDIFile
        import MUSIKALL_functions1 as _mf

        np = _np
        PDBParser = _PDBParser
        MIDIFile = _MIDIFile
        create_job_folder = _mf.create_job_folder
        load_pdb_files = _mf.load_pdb_files
        run_adj_matrix = _mf.run_adj_matrix
        parse_residue_input = _mf.parse_residue_input
        run_residue_mapping = _mf.run_residue_mapping
        calculate_shortest_paths = _mf.calculate_shortest_paths
        save_colored_pdbs = _mf.save_colored_pdbs
        build_3d_html = _mf.build_3d_html
        extract_start_end_residues_safe = _mf.extract_start_end_residues_safe
        play_midi = _mf.play_midi
        stop_midi = _mf.stop_midi
        note_to_midi = _mf.note_to_midi
        apply_transpose_clamp = _mf.apply_transpose_clamp
        get_triad_presets = _mf.get_triad_presets
        MusicOptions = _mf.MusicOptions
        run_cooccurrence_backbone_for_one_structure = _mf.run_cooccurrence_backbone_for_one_structure
        run_cooccurrence_backbone_ensemble = _mf.run_cooccurrence_backbone_ensemble
        run_path_similarity_for_one_structure = _mf.run_path_similarity_for_one_structure
        run_path_similarity_ensemble = _mf.run_path_similarity_ensemble
        NOTE_NAMES = _mf.NOTE_NAMES
        ALL_RESIDUES = _mf.ALL_RESIDUES
        build_default_aa_mapping = _mf.build_default_aa_mapping
        aa_mapping_to_residue_mapping = _mf.aa_mapping_to_residue_mapping
        pr_generate_audio = _mf.generate_audio
        _BACKEND_READY = True
    except Exception as exc:
        _BACKEND_ERROR = exc




def _unique_filename(path):
    """
    Return a non-conflicting output filename.
    base.png -> base.png if available; otherwise base_2.png, base_3.png, etc.
    """
    import os
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while True:
        candidate = f"{base}_{i}{ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1


import os, sys

def _resource_path(rel: str) -> str:
    """
    Resolve resource paths for both PyInstaller builds and normal Python execution.
    Never rely on the current working directory.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS                       # ...\MUSIKALL\_internal
    else:
        base = os.path.dirname(os.path.abspath(__file__))  # Directory containing MUSIKALL_gui1.py
    return os.path.join(base, rel)


def _set_windows_appid(appid: str = "MUSIKALL.App"):
    """Set the Windows application ID for consistent taskbar and Alt+Tab branding."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
    except Exception:
        pass


# --- THEMES / PALETTES  ---
palettes = {
    "aqua": {  # airy, neutral, modern
        "bg": "#F7FAFC",
        "surface": "#FFFFFF",
        "muted": "#E0F2FE",
        "text": "#1E293B",
        "subtext": "#475569",
        "accent": "#0EA5E9",
        "accent_fg": "#FFFFFF",
        "border": "#BAE6FD",
        "focus": "#38BDF8"
    },
    "lilac": {  # pastel, soft, scientific/creative
        "bg": "#FAF5FF",
        "surface": "#FFFFFF",
        "muted": "#E9D5FF",
        "text": "#312E81",
        "subtext": "#5B21B6",
        "accent": "#8B5CF6",
        "accent_fg": "#FFFFFF",
        "border": "#DDD6FE",
        "focus": "#A78BFA"
    },
    "sunset": {  # warm, energetic, high-visibility
        "bg": "#FFF7ED",
        "surface": "#FFFFFF",
        "muted": "#FED7AA",
        "text": "#431407",
        "subtext": "#9A3412",
        "accent": "#F97316",
        "accent_fg": "#FFFFFF",
        "border": "#FDBA74",
        "focus": "#FB923C"
    },
    "forest": {  # natural, biology-friendly
        "bg": "#F0FDF4",
        "surface": "#FFFFFF",
        "muted": "#DCFCE7",
        "text": "#064E3B",
        "subtext": "#166534",
        "accent": "#22C55E",
        "accent_fg": "#FFFFFF",
        "border": "#BBF7D0",
        "focus": "#4ADE80"
    },
    "slate": {  # professional, neutral, institutional
        "bg": "#F8FAFC",
        "surface": "#FFFFFF",
        "muted": "#E2E8F0",
        "text": "#0F172A",
        "subtext": "#475569",
        "accent": "#64748B",
        "accent_fg": "#FFFFFF",
        "border": "#CBD5E1",
        "focus": "#94A3B8"
    },
    "dark": {  # dark, polished, modern
        "bg": "#111827",
        "surface": "#1F2937",
        "muted": "#374151",
        "text": "#F9FAFB",
        "subtext": "#9CA3AF",
        "accent": "#3B82F6",
        "accent_fg": "#FFFFFF",
        "border": "#4B5563",
        "focus": "#60A5FA"
    }
}

# --- Simple Tooltip helper for Tkinter ---
class Tooltip:
    def __init__(self, widget, text, delay=350):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._id = None
        self.tip = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._unschedule)
        widget.bind("<ButtonPress>", self._unschedule)

    def _schedule(self, _):
        self._unschedule(None)
        self._id = self.widget.after(self.delay, self._show)

    def _unschedule(self, _):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        self._hide()

    def _show(self):
        if self.tip or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") if self.widget.winfo_ismapped() else (0,0,0,0)
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify="left",
                         relief="solid", borderwidth=1,
                         bg="#ffffe0", fg="#333", font=("Arial", 10), padx=6, pady=4)
        label.pack()

    def _hide(self):
        if self.tip:
            self.tip.destroy()
            self.tip = None

class MUSIKALL_GUI(tk.Tk):

    def build_interactive_cache(self, force=False):
        import os
        import threading

        if self._interactive_cache_building:
            return

        if self._interactive_cache_ready and not force:
            return

        def worker():
            self._interactive_cache_building = True

            try:
                from MUSIKALL_functions1 import (
                    build_3d_html_colored,
                    extract_start_end_residues_safe,
                    extract_residue_nodes_and_coords,
                    _resolve_job_dir,
                )

                def _viewer_key_from_token(token):
                    if token is None:
                        return None

                    try:
                        parts = [
                            p.strip()
                            for p in str(token).split(":")
                            if p.strip() != ""
                        ]

                        if len(parts) == 2:
                            seg = ""
                            ch = parts[0]
                            rn = parts[1]

                        elif len(parts) >= 3:
                            seg = ":".join(parts[:-2]).strip()
                            ch = parts[-2]
                            rn = parts[-1]

                        else:
                            return None

                        ch = str(ch).strip().upper()
                        rn = str(rn).strip()

                        if not ch or not rn:
                            return None

                        return (
                            f"{seg}:{ch}:{rn}"
                            if seg
                            else f"{ch}:{rn}"
                        )

                    except Exception:
                        return None

                jobname = self.jobname_entry.get().strip()

                if not jobname:
                    return

                if not getattr(self, "paths_dict_2", None):
                    return

                if not getattr(self, "pdb_info_dict", None):
                    return

                job_dir = _resolve_job_dir(jobname)
                cache = {}

                for pdb_key in sorted(self.paths_dict_2.keys()):

                    try:
                        pdb_data = self.pdb_info_dict.get(pdb_key, {}) or {}

                        orig_path = pdb_data.get("file_path")
                        if not orig_path:
                            continue

                        pdb_base = os.path.splitext(
                            os.path.basename(orig_path)
                        )[0]

                        colored_pdb = os.path.join(
                            job_dir,
                            pdb_base,
                            f"{pdb_base}_colored.pdb"
                        )

                        colored_cif = os.path.join(
                            job_dir,
                            pdb_base,
                            f"{pdb_base}_colored.cif"
                        )

                        if os.path.exists(colored_pdb):
                            colored_path = colored_pdb

                        elif os.path.exists(colored_cif):
                            colored_path = colored_cif

                        else:
                            continue

                        start_residues, end_residues = (
                            extract_start_end_residues_safe(
                                self.paths_dict_2,
                                pdb_key
                            )
                        )

                        _nodes, node_coords, residue_names = (
                            extract_residue_nodes_and_coords(
                                colored_path
                            )
                        )

                        structure_key_set = set(node_coords.keys())

                        adj = pdb_data.get("adj_matrix")
                        node_index_map = (
                                pdb_data.get("node_index_map", {}) or {}
                        )

                        graph_nodes = []
                        seen_graph_keys = set()
                        index_to_key = {}
                        all_edges = []

                        for idx, token in node_index_map.items():

                            vk = _viewer_key_from_token(token)

                            if vk is None:
                                continue

                            if vk not in structure_key_set:
                                continue

                            index_to_key[int(idx)] = vk

                            if vk not in seen_graph_keys:
                                seen_graph_keys.add(vk)

                                # SEGNAME-safe:
                                # EB:C:530 -> EB:C | 530
                                ch, rn = vk.rsplit(":", 1)

                                graph_nodes.append([ch, rn])

                        if adj is not None:

                            try:
                                n = adj.shape[0]

                                for i in range(n):
                                    for j in range(i + 1, n):

                                        try:
                                            if float(adj[i, j]) == 0.0:
                                                continue
                                        except Exception:
                                            continue

                                        akey = index_to_key.get(i)
                                        bkey = index_to_key.get(j)

                                        if (
                                                akey is None
                                                or bkey is None
                                                or akey == bkey
                                        ):
                                            continue

                                        # SEGNAME-safe
                                        ach, arn = akey.rsplit(":", 1)
                                        bch, brn = bkey.rsplit(":", 1)

                                        all_edges.append(
                                            [
                                                [ach, arn],
                                                [bch, brn]
                                            ]
                                        )

                            except Exception:
                                pass

                        freq_map = self._freq_map_for_pdb(pdb_key)

                        html = build_3d_html_colored(
                            colored_path,
                            start_residues=start_residues,
                            end_residues=end_residues,
                            freq_map=freq_map,
                            graph_nodes=graph_nodes,
                            graph_edges=all_edges,
                        )

                        html_path = os.path.join(
                            job_dir,
                            pdb_base,
                            f"{pdb_base}_interactive.html"
                        )

                        with open(
                                html_path,
                                "w",
                                encoding="utf-8"
                        ) as fh:
                            fh.write(html)

                        cache[pdb_key] = html_path

                    except Exception as e:
                        self.log_output(
                            f"⚠ interactive cache failed "
                            f"for {pdb_key}: {e}\n"
                        )

                self._interactive_cache = cache
                self._interactive_cache_ready = True

                self.log_output(
                    "✅ Interactive viewer cache prepared.\n"
                )

            finally:
                self._interactive_cache_building = False

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def _make_colorbar(self, parent_frame):

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib import cm
        from matplotlib import colors as mcolors

        fig = Figure(figsize=(0.6, 3.5), dpi=100)
        cax = fig.add_axes([0.25, 0.05, 0.5, 0.9])

        # fixed 0..1 range
        norm = mcolors.Normalize(vmin=0.0, vmax=1.0)
        sm = cm.ScalarMappable(cmap=cm.plasma, norm=norm)
        sm.set_array([])

        cb = fig.colorbar(sm, cax=cax, orientation='vertical',
                          ticks=[0.0, 0.25, 0.5, 0.75, 1.0])
        cb.set_label('Normalized Frequency (B-factor 0–1)', fontsize=8)

        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="y")

        # retain a reference if needed
        if not hasattr(self, "_embedded_canvases"):
            self._embedded_canvases = []
        self._embedded_canvases.append(canvas)

    def schedule_prewarm(self):
        self.after(500, lambda: threading.Thread(target=self._prewarm_3d, daemon=True).start())

    def _prewarm_3d(self):
        try:
            self._lazy_matplotlib()
            from matplotlib.figure import Figure
            fig = Figure(figsize=(6, 4), dpi=100)
            fig.canvas.draw()
            plt.close(fig)
        except Exception:
            pass

    def _lazy_matplotlib(self):
        import matplotlib
        # Tkinter ile en uyumlu backend
        matplotlib.use('TkAgg', force=True)
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        plt.rcParams['figure.max_open_warning'] = 0  # suppress excessive-open-figure warnings
        mpl.rcParams['agg.path.chunksize'] = 10000  # chunk long paths for large 3D drawings

        # Import only the required objects
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        # Do not call plt.figure here.
        self._mpl_ready = True

    def set_theme(self, palette="aqua"):
        P = palettes.get(palette, palettes["aqua"])
        self.current_palette = P
        self.current_theme = palette

        # Window background
        self.configure(bg=P["bg"])

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Checkbutton
        style.configure(
            "TCheckbutton",
            background=P["bg"],
            foreground=P["text"],
            font=("Arial", 10),
        )
        style.map(
            "TCheckbutton",
            background=[("active", P["muted"])],
            foreground=[("disabled", "#AAAAAA")]
        )

        self.recolor_raw_widgets()

        # General backgrounds
        style.configure("TFrame", background=P["bg"])
        style.configure("Card.TFrame", background=P["bg"])
        style.configure("Muted.TFrame", background=P["muted"])

        style.configure("TLabel", background=P["bg"], foreground=P["text"])
        style.configure("Sub.TLabel", background=P["bg"], foreground=P["subtext"])
        style.configure("SectionHint.TLabel", background=P["bg"], foreground=P["subtext"], font=("Segoe UI", 9))
        style.configure("FieldLabel.TLabel", background=P["bg"], foreground=P["text"], font=("Segoe UI", 9, "bold"))
        style.configure("Quiet.TButton", background=P["surface"], foreground=P["text"], padding=(9, 6))

        # LabelFrame section headers
        style.configure(
            "Card.TLabelframe",
            background=P["bg"],  # keep the background consistent with the active theme
            bordercolor=P["border"],
            relief="solid"
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=P["bg"],  # keep the title area consistent with the active theme
            foreground=P["text"],
            font=("Segoe UI", 10, "bold")
        )

        # Button
        style.configure("TButton",
                        background=P["surface"],
                        foreground=P["text"],
                        borderwidth=1,
                        padding=(10, 6))
        style.map("TButton",
                  background=[("active", P["muted"])],
                  relief=[("pressed", "sunken"), ("!pressed", "raised")])

        # Accent Button
        style.configure("Accent.TButton",
                        background=P["accent"],
                        foreground=P["accent_fg"],
                        borderwidth=0,
                        padding=(12, 8))
        style.map("Accent.TButton",
                  background=[("active", P["focus"])],
                  foreground=[("disabled", "#DDDDDD")])

        # Entry
        style.configure("TEntry",
                        fieldbackground=P["surface"],
                        foreground=P["text"],
                        bordercolor=P["border"])
        style.map("TEntry", bordercolor=[("focus", P["focus"])])

        # Combobox
        style.configure("TCombobox",
                        fieldbackground=P["surface"],
                        background=P["surface"],
                        foreground=P["text"])
        style.map("TCombobox", fieldbackground=[("readonly", P["surface"])])

        # Treeview
        style.configure("Treeview",
                        background=P["surface"],
                        fieldbackground=P["surface"],
                        foreground=P["text"],
                        bordercolor=P["border"])
        style.configure("Treeview.Heading",
                        background=P["muted"],
                        foreground=P["text"],
                        bordercolor=P["border"])

        # PanedWindow & Separator
        style.configure("TPanedwindow", background=P["bg"])
        style.configure("TSeparator", background=P["border"])

        # Text widget
        if hasattr(self, "output_text"):
            self.output_text.configure(bg=P["surface"], fg=P["text"], insertbackground=P["text"])

        # Label
        style.configure("TLabel",
                        background=P["bg"],
                        foreground=P["text"])
        style.configure("Card.TLabel",
                        background=P["bg"],
                        foreground=P["text"])
        try:
            for w in getattr(self, "_path_explorer_windows", []):
                if not (w and w.winfo_exists()):
                    continue
                w.configure(bg=P["bg"])
                # update nested raw Tk Label/Frame widgets as well
                for child in w.winfo_children():
                    try:
                        if isinstance(child, (tk.Label, tk.Frame)):
                            child.configure(bg=P["bg"], fg=P["text"])
                    except Exception:
                        pass
        except Exception:
            pass
        # Apply the theme to the main frames as well
        for attr in ("welcome_frame", "main_pw", "left_col", "right_col"):
            if hasattr(self, attr):
                frame = getattr(self, attr)
                if frame and frame.winfo_exists():
                    frame.configure(bg=P["bg"])

    def recolor_raw_widgets(self):
        P = self.current_palette

        # Apply the theme to all canvases
        for child in self.winfo_children():
            self._recolor_recursive(child, P)

        # Main window
        self.configure(bg=P["bg"])

        # Recolor the welcome frame when present
        if hasattr(self, "welcome_frame") and self.welcome_frame.winfo_exists():
            self.welcome_frame.configure(bg=P["bg"])
            for child in self.welcome_frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=P["bg"], fg=P["text"])
                elif isinstance(child, tk.Button):
                    child.configure(bg=P["accent"], fg=P["accent_fg"], activebackground=P["focus"])

        # Recolor the main PanedWindow when present
        if hasattr(self, "main_pw") and self.main_pw.winfo_exists():
            self.main_pw.configure(bg=P["bg"])

        # Recolor the left/right columns when present
        if hasattr(self, "left_col") and self.left_col.winfo_exists():
            self.left_col.configure(bg=P["bg"])
        if hasattr(self, "right_col") and self.right_col.winfo_exists():
            self.right_col.configure(bg=P["bg"])

    def _recolor_recursive(self, widget, P):
        if isinstance(widget, tk.Canvas):
            widget.configure(bg=P["surface"])
        elif isinstance(widget, tk.Text):
            widget.configure(bg=P["surface"], fg=P["text"], insertbackground=P["text"])
        elif isinstance(widget, tk.Label):
            widget.configure(bg=P["bg"], fg=P["text"])
        for child in widget.winfo_children():
            self._recolor_recursive(child, P)

    def _split_token(self, node: str) -> tuple[str, str, str]:
        """
        Convert "CHAIN:RES" or "SEG:CHAIN:RES" into (seg, chain, res).
        Returns an empty segment string when SEGNAME is absent.
        """
        if node is None:
            return ("", "", "")
        s = str(node).strip()
        parts = s.split(":")
        if len(parts) == 2:
            ch, rn = parts
            return ("", ch.strip().upper(), rn.strip())
        if len(parts) >= 3:
            seg = parts[0].strip()
            ch = parts[1].strip().upper()
            rn = parts[2].strip()
            return (seg, ch, rn)
        return ("", "", s)

    def __init__(self, *args, **kwargs):
        import os, sys

        def resource_path(relative_path):
            """Get absolute path to resource, works for dev and for PyInstaller EXE."""
            try:
                # Inside a PyInstaller executable
                base_path = sys._MEIPASS
            except Exception:
                # Normal Python execution
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        super().__init__(*args, **kwargs)
        self.title("MUSIKALL")
        self.geometry("1200x750")

        # --- Icon setup ---
        try:
            from ctypes import windll  # Windows only
            def _set_windows_appid(appid):
                try:
                    windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
                except Exception:
                    pass
        except ImportError:
            def _set_windows_appid(appid):
                pass

        def _resource_path(fname: str) -> str:
            """Resolve bundled resource files in both development and PyInstaller builds."""
            import sys, os
            if hasattr(sys, "_MEIPASS"):
                return os.path.join(sys._MEIPASS, fname)
            return os.path.join(os.path.abspath("."), fname)

        self.icon_image = Image.open(resource_path("icon.png"))
        from tkinter import PhotoImage
        self.iconphoto(False, PhotoImage(file=resource_path("icon.png")))

        # --- Icon setup ---
        _set_windows_appid("MUSIKALL.Prod")
        ico_path = _resource_path("icon.ico")
        png_path = _resource_path("icon.png")

        # 1) ICO is preferred on Windows
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        # 2) PNG fallback (Linux/macOS + Windows)
        try:
            if os.path.exists(png_path):
                # PIL-free fallback: use Tk PhotoImage directly
                import tkinter as tk
                _img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, _img)
                self._icon_ref = _img  # Keep a reference to prevent garbage collection
        except Exception:
            pass

        self.set_theme(palette="aqua")
        self.create_menu()
        self.show_welcome_screen()
        self._backend_ready = False
        self._backend_error = None
        self.after(75, self._start_backend_prewarm)
        self.state = {
            "jobname": None,
            "pdb_info_dict": None,
            "paths_dict": None,
            "paths_dict_2": None,
            "all_normalized_frequencies": None
        }
        self.all_normalized_frequencies = {}
        self._interactive_cache = {}
        self._interactive_cache_building = False
        self._interactive_cache_ready = False
        self._viewer_proc = None


    from PIL import Image, ImageTk

    def _start_backend_prewarm(self):
        """Load the scientific backend after the first window has been painted."""
        if getattr(self, "_backend_loading", False) or getattr(self, "_backend_ready", False):
            return
        self._backend_loading = True

        def worker():
            global _BACKEND_READY, _BACKEND_ERROR
            _load_analysis_backend()
            self.after(0, self._finish_backend_prewarm)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_backend_prewarm(self):
        self._backend_loading = False
        self._backend_ready = bool(_BACKEND_READY)
        self._backend_error = _BACKEND_ERROR
        if hasattr(self, "backend_status_label") and self.backend_status_label.winfo_exists():
            if self._backend_ready:
                self.backend_status_label.configure(text="Ready")
            else:
                self.backend_status_label.configure(text="Analysis engine could not be loaded")
        if hasattr(self, "start_button") and self.start_button.winfo_exists():
            self.start_button.configure(state=("normal" if self._backend_ready else "disabled"))

    def show_welcome_screen(self):
        """Shows the welcome screen with a Start button and an improved image display."""
        self.welcome_frame = tk.Frame(self, bg=self.current_palette["bg"])
        self.welcome_frame.pack(fill="both", expand=True)

        # Title
        tk.Label(
            self.welcome_frame,
            text="Welcome to MUSIKALL!",
            font=("Arial", 26, "bold"),
            bg=self.current_palette["bg"],
            fg=self.current_palette["text"]
        ).pack(pady=20)

        # Icon (PNG)
        img = Image.open(_resource_path("icon.png"))
        img = img.resize((100, 100), Image.LANCZOS) 
        self.logo_img = ImageTk.PhotoImage(img)  # keep a persistent image reference
        tk.Label(self.welcome_frame, image=self.logo_img, bg=self.current_palette["bg"]).pack(pady=10)

        # Subtitle
        tk.Label(
            self.welcome_frame,
            text="Transcribing allosteric communication pathways in protein structures to audio-visual",
            font=("Arial", 14),
            bg=self.current_palette["bg"],
            fg=self.current_palette["text"]
        ).pack(pady=10)

        # Start button
        self.start_button = ttk.Button(
            self.welcome_frame,
            text="Start",
            command=self.show_main_interface,
            style="Accent.TButton",
            state="disabled"
        )
        self.start_button.pack(pady=(12, 4))
        self.backend_status_label = ttk.Label(
            self.welcome_frame, text="Preparing analysis engine…", style="Sub.TLabel"
        )
        self.backend_status_label.pack(pady=(0, 8))


        # Additional image below the Start button
        img2 = Image.open(_resource_path("welcome.png"))
        img2 = img2.resize((720, 250), Image.LANCZOS) 
        self.welcome_img = ImageTk.PhotoImage(img2)
        tk.Label(self.welcome_frame, image=self.welcome_img, bg=self.current_palette["bg"]).pack(pady=10)


        # Copyright notice at the bottom of the window
        tk.Label(
            self.welcome_frame,
            text="© 2026 Kurkcuoglu Levitas Lab, Istanbul Technical University.  All rights reserved.",
            font=("Arial", 9, "italic"),
            bg=self.current_palette["bg"],
            fg=self.current_palette["text"]
        ).pack(side="bottom", pady=5)

    def create_menu(self):
        self.option_add("*Menu.font", ("Arial", 10, "bold"))
        menu_bar = tk.Menu(self)

        # Theme menu
        theme_menu = tk.Menu(menu_bar, tearoff=0)
        self.theme_var = tk.StringVar(value=getattr(self, "current_theme", "aqua"))
        for theme_name in palettes.keys():
            theme_menu.add_radiobutton(
                label=theme_name.capitalize(),
                variable=self.theme_var,
                value=theme_name,
                command=lambda tn=theme_name: self.set_theme(tn)
            )
        menu_bar.add_cascade(label="Theme", menu=theme_menu)

        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open Projects Folder", command=self.open_projects_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        menu_bar.add_cascade(label="File", menu=file_menu)

        # 📖 Help Menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="📗 Quick Start", command=self.open_quick_start)
        help_menu.add_command(label="📘 User Guide", command=self.open_user_guide)
        help_menu.add_command(label="ℹ Theory & Methods", command=self.open_theory_info)
        help_menu.add_command(label="🎧 Music Playground", command=self.open_music_playground)
        help_menu.add_separator()
        help_menu.add_command(label="🛠 Troubleshooting", command=self.open_troubleshooting)
        help_menu.add_command(label="ⓘ About MUSIKALL", command=self.open_about_musikall)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        # Additional menus
        cite_menu = tk.Menu(menu_bar, tearoff=0)
        cite_menu.add_command(label="How to Cite", command=self.show_cite)
        menu_bar.add_cascade(label="Cite", menu=cite_menu)

        Contact_menu = tk.Menu(menu_bar, tearoff=0)
        Contact_menu.add_command(label="Contact Us", command=self.show_Contact)
        menu_bar.add_cascade(label="Contact", menu=Contact_menu)

        self.config(menu=menu_bar)



    def open_projects_folder(self):
        """Open the MUSIKALL Projects directory in the operating-system file browser."""
        try:
            from MUSIKALL_functions1 import get_projects_root
            project_root = str(get_projects_root())
            os.makedirs(project_root, exist_ok=True)

            if sys.platform.startswith("win"):
                os.startfile(project_root)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", project_root])
            else:
                subprocess.Popen(["xdg-open", project_root])
        except Exception as e:
            messagebox.showerror("Open Projects Folder", f"Could not open the projects folder:\n{e}")


    def _open_help_document(self, title, subtitle, text, geometry="980x720", action_label=None, action_command=None):
        """Render a searchable, navigable, theme-aware Help workspace."""
        import tkinter.font as tkfont

        P = getattr(self, "current_palette", palettes["aqua"])
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry(geometry)
        win.minsize(860, 580)
        win.configure(bg=P["bg"])
        win.transient(self)

        outer = tk.Frame(win, bg=P["bg"])
        outer.pack(fill="both", expand=True)

        # ------------------------------------------------------------------
        # Header
        # ------------------------------------------------------------------
        header = tk.Frame(
            outer,
            bg=P["surface"],
            highlightthickness=1,
            highlightbackground=P["border"],
        )
        header.pack(fill="x", padx=18, pady=(18, 10))

        tk.Label(
            header,
            text=title,
            anchor="w",
            font=("Segoe UI", 20, "bold"),
            bg=P["surface"],
            fg=P["text"],
        ).pack(fill="x", padx=22, pady=(18, 2))

        tk.Label(
            header,
            text=subtitle,
            anchor="w",
            justify="left",
            font=("Segoe UI", 10),
            bg=P["surface"],
            fg=P["subtext"],
        ).pack(fill="x", padx=22, pady=(0, 12))

        # Help-page switcher + in-page search
        tools = tk.Frame(header, bg=P["surface"])
        tools.pack(fill="x", padx=22, pady=(0, 14))

        tk.Label(
            tools,
            text="Help page",
            font=("Segoe UI", 9, "bold"),
            bg=P["surface"],
            fg=P["subtext"],
        ).pack(side="left", padx=(0, 6))

        page_names = [
            "Quick Start",
            "User Guide",
            "Theory & Methods",
            "Music Playground",
            "Troubleshooting",
            "About MUSIKALL",
        ]
        title_to_page = {
            "MUSIKALL — Quick Start": "Quick Start",
            "MUSIKALL — User Guide": "User Guide",
            "MUSIKALL — Theory & Methods": "Theory & Methods",
            "MUSIKALL — Troubleshooting": "Troubleshooting",
            "About MUSIKALL": "About MUSIKALL",
            "MUSIKALL — About": "About MUSIKALL",
        }
        page_var = tk.StringVar(value=title_to_page.get(title, "Quick Start"))
        page_cb = ttk.Combobox(
            tools,
            textvariable=page_var,
            values=page_names,
            state="readonly",
            width=19,
        )
        page_cb.pack(side="left", padx=(0, 18))

        tk.Label(
            tools,
            text="Search this page",
            font=("Segoe UI", 9, "bold"),
            bg=P["surface"],
            fg=P["subtext"],
        ).pack(side="left", padx=(0, 6))

        search_var = tk.StringVar()
        search_entry = ttk.Entry(tools, textvariable=search_var, width=28)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        search_prev_btn = ttk.Button(tools, text="◀", width=3)
        search_prev_btn.pack(side="left", padx=(0, 3))
        search_next_btn = ttk.Button(tools, text="▶", width=3)
        search_next_btn.pack(side="left", padx=(0, 6))

        search_status = tk.Label(
            tools,
            text="",
            width=9,
            anchor="w",
            font=("Segoe UI", 9),
            bg=P["surface"],
            fg=P["subtext"],
        )
        search_status.pack(side="left")

        accent = tk.Frame(header, height=4, bg=P["accent"])
        accent.pack(fill="x")

        # ------------------------------------------------------------------
        # Resizable navigation/document split
        # ------------------------------------------------------------------
        body = tk.Frame(outer, bg=P["bg"])
        body.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        split = tk.PanedWindow(
            body,
            orient="horizontal",
            bg=P["bg"],
            sashrelief="raised",
            sashwidth=7,
            bd=0,
            showhandle=False,
        )
        split.pack(fill="both", expand=True)

        nav_card = tk.Frame(
            split,
            bg=P["surface"],
            highlightthickness=1,
            highlightbackground=P["border"],
        )
        doc_card = tk.Frame(
            split,
            bg=P["surface"],
            highlightthickness=1,
            highlightbackground=P["border"],
        )

        # The user can drag the sash to resize the Contents pane.
        split.add(nav_card, minsize=150, width=240)
        split.add(doc_card, minsize=420)

        tk.Label(
            nav_card,
            text="CONTENTS",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=P["surface"],
            fg=P["subtext"],
        ).pack(fill="x", padx=14, pady=(14, 6))

        tk.Label(
            nav_card,
            text="Drag the divider to resize",
            anchor="w",
            font=("Segoe UI", 8),
            bg=P["surface"],
            fg=P["subtext"],
        ).pack(fill="x", padx=14, pady=(0, 6))

        nav_wrap = tk.Frame(nav_card, bg=P["surface"])
        nav_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        nav_wrap.grid_rowconfigure(0, weight=1)
        nav_wrap.grid_columnconfigure(0, weight=1)

        nav = tk.Listbox(
            nav_wrap,
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 9),
            activestyle="none",
            bg=P["surface"],
            fg=P["text"],
            selectbackground=P["muted"],
            selectforeground=P["text"],
            exportselection=False,
        )
        nav.grid(row=0, column=0, sticky="nsew")

        nav_vscroll = ttk.Scrollbar(nav_wrap, orient="vertical", command=nav.yview)
        nav_vscroll.grid(row=0, column=1, sticky="ns")
        nav_hscroll = ttk.Scrollbar(nav_wrap, orient="horizontal", command=nav.xview)
        nav_hscroll.grid(row=1, column=0, sticky="ew")
        nav.configure(
            yscrollcommand=nav_vscroll.set,
            xscrollcommand=nav_hscroll.set,
        )

        doc_card.grid_rowconfigure(0, weight=1)
        doc_card.grid_columnconfigure(0, weight=1)

        txt = tk.Text(
            doc_card,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            padx=28,
            pady=22,
            bg=P["surface"],
            fg=P["text"],
            insertbackground=P["text"],
            font=("Segoe UI", 10),
            spacing1=2,
            spacing3=7,
            cursor="arrow",
        )
        txt.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(doc_card, orient="vertical", command=txt.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=scroll.set)

        normal_font = tkfont.Font(family="Segoe UI", size=10)
        h1_font = tkfont.Font(family="Segoe UI", size=17, weight="bold")
        h2_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        h3_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        code_font = tkfont.Font(family="Consolas", size=9)

        txt.tag_configure("h1", font=h1_font, foreground=P["text"], spacing1=8, spacing3=12)
        txt.tag_configure("h2", font=h2_font, foreground=P["accent"], spacing1=14, spacing3=7)
        txt.tag_configure("h3", font=h3_font, foreground=P["text"], spacing1=10, spacing3=5)
        txt.tag_configure("body", font=normal_font, foreground=P["text"], lmargin1=0, lmargin2=0)
        txt.tag_configure("bullet", font=normal_font, foreground=P["text"], lmargin1=14, lmargin2=30, spacing1=1, spacing3=3)
        txt.tag_configure("code", font=code_font, foreground=P["text"], background=P["muted"], lmargin1=18, lmargin2=18, rmargin=18, spacing1=5, spacing3=5)
        txt.tag_configure("inline", font=("Consolas", 9), foreground=P["text"], background=P["muted"])
        txt.tag_configure("bold", font=("Segoe UI", 10, "bold"), foreground=P["text"])
        txt.tag_configure("rule", foreground=P["border"], spacing1=8, spacing3=8)
        txt.tag_configure("search_hit", background=P["muted"], foreground=P["text"])
        txt.tag_configure("search_current", background=P["accent"], foreground=P["accent_fg"])

        anchors = []
        heading_counter = 0

        def insert_inline_markup(line, base_tag="body"):
            pattern = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")
            pos = 0
            for m in pattern.finditer(line):
                if m.start() > pos:
                    txt.insert("end", line[pos:m.start()], base_tag)
                token = m.group(0)
                if token.startswith("**"):
                    txt.insert("end", token[2:-2], "bold")
                else:
                    txt.insert("end", token[1:-1], "inline")
                pos = m.end()
            if pos < len(line):
                txt.insert("end", line[pos:], base_tag)

        for raw in text.strip().splitlines():
            line = raw.rstrip()
            stripped = line.strip()

            if not stripped:
                txt.insert("end", "\n", "body")
                continue

            if stripped.startswith("### "):
                label = stripped[4:].strip()
                mark = f"help_h_{heading_counter}"
                heading_counter += 1
                txt.mark_set(mark, "end")
                txt.insert("end", label + "\n", "h3")
                anchors.append((label, mark, 2))
                continue

            if stripped.startswith("## "):
                label = stripped[3:].strip()
                mark = f"help_h_{heading_counter}"
                heading_counter += 1
                txt.mark_set(mark, "end")
                txt.insert("end", label + "\n", "h2")
                anchors.append((label, mark, 1))
                continue

            if stripped.startswith("# "):
                label = stripped[2:].strip()
                mark = f"help_h_{heading_counter}"
                heading_counter += 1
                txt.mark_set(mark, "end")
                txt.insert("end", label + "\n", "h1")
                anchors.append((label, mark, 0))
                continue

            if stripped in ("---", "___"):
                txt.insert("end", "────────────────────────────────────────\n", "rule")
                continue

            if line.startswith("    "):
                txt.insert("end", stripped + "\n", "code")
                continue

            if stripped.startswith("- "):
                txt.insert("end", "• ", "bullet")
                insert_inline_markup(stripped[2:], "bullet")
                txt.insert("end", "\n", "bullet")
                continue

            insert_inline_markup(stripped, "body")
            txt.insert("end", "\n", "body")

        for label, mark, level in anchors:
            if level <= 1:
                nav.insert("end", ("  " if level else "") + label)

        nav_marks = [mark for _, mark, level in anchors if level <= 1]

        # ------------------------------------------------------------------
        # Contents navigation
        # ------------------------------------------------------------------
        def _scroll_to_nav_index(idx):
            if not (0 <= idx < len(nav_marks)):
                return
            mark = nav_marks[idx]

            def _do_scroll():
                try:
                    txt.yview(mark)
                except Exception:
                    try:
                        txt.see(mark)
                    except Exception:
                        pass

            win.after_idle(_do_scroll)

        def jump_to_heading(_event=None):
            sel = nav.curselection()
            if sel:
                _scroll_to_nav_index(int(sel[0]))

        def jump_to_heading_click(event):
            if nav.size() <= 0:
                return
            idx = int(nav.nearest(event.y))
            if 0 <= idx < nav.size():
                nav.selection_clear(0, "end")
                nav.selection_set(idx)
                nav.activate(idx)
                _scroll_to_nav_index(idx)

        nav.bind("<<ListboxSelect>>", jump_to_heading)
        nav.bind("<ButtonRelease-1>", jump_to_heading_click, add="+")
        nav.bind("<Return>", jump_to_heading)

        # ------------------------------------------------------------------
        # In-page search
        # ------------------------------------------------------------------
        search_matches = []
        search_pos = {"index": -1, "query": ""}

        def _clear_search_tags():
            txt.tag_remove("search_hit", "1.0", "end")
            txt.tag_remove("search_current", "1.0", "end")

        def _collect_search_matches(query):
            _clear_search_tags()
            search_matches.clear()
            search_pos["index"] = -1
            search_pos["query"] = query

            q = (query or "").strip()
            if not q:
                search_status.configure(text="")
                return

            start = "1.0"
            while True:
                found = txt.search(q, start, stopindex="end", nocase=True)
                if not found:
                    break
                end_idx = f"{found}+{len(q)}c"
                search_matches.append((found, end_idx))
                txt.tag_add("search_hit", found, end_idx)
                start = end_idx

            if search_matches:
                search_status.configure(text=f"{len(search_matches)} found")
            else:
                search_status.configure(text="No matches")

        def _show_search_match(index):
            if not search_matches:
                return
            index %= len(search_matches)
            search_pos["index"] = index
            txt.tag_remove("search_current", "1.0", "end")
            start_idx, end_idx = search_matches[index]
            txt.tag_add("search_current", start_idx, end_idx)
            txt.see(start_idx)
            search_status.configure(text=f"{index + 1}/{len(search_matches)}")

        def _ensure_search_matches():
            q = (search_var.get() or "").strip()
            if q != search_pos["query"]:
                _collect_search_matches(q)
            return bool(search_matches)

        def search_next(_event=None):
            if not _ensure_search_matches():
                return "break"
            _show_search_match(search_pos["index"] + 1)
            return "break"

        def search_previous(_event=None):
            if not _ensure_search_matches():
                return "break"
            if search_pos["index"] < 0:
                _show_search_match(len(search_matches) - 1)
            else:
                _show_search_match(search_pos["index"] - 1)
            return "break"

        def _search_changed(*_):
            _collect_search_matches(search_var.get())

        search_var.trace_add("write", _search_changed)
        search_next_btn.configure(command=search_next)
        search_prev_btn.configure(command=search_previous)
        search_entry.bind("<Return>", search_next)
        search_entry.bind("<Shift-Return>", search_previous)
        win.bind("<Control-f>", lambda _e: (search_entry.focus_set(), search_entry.selection_range(0, "end")))

        # ------------------------------------------------------------------
        # Help-page switching
        # ------------------------------------------------------------------
        def _switch_help_page(_event=None):
            choice = page_var.get()
            current = title_to_page.get(title)
            if choice == current:
                return

            dispatch = {
                "Quick Start": self.open_quick_start,
                "User Guide": self.open_user_guide,
                "Theory & Methods": self.open_theory_info,
                "Music Playground": self.open_music_playground,
                "Troubleshooting": self.open_troubleshooting,
                "About MUSIKALL": self.open_about_musikall,
            }
            callback = dispatch.get(choice)
            if callback is None:
                return
            win.destroy()
            callback()

        page_cb.bind("<<ComboboxSelected>>", _switch_help_page)

        txt.configure(state="disabled")

        # ------------------------------------------------------------------
        # Footer
        # ------------------------------------------------------------------
        footer = tk.Frame(outer, bg=P["bg"])
        footer.pack(fill="x", padx=18, pady=(0, 14))
        tk.Label(
            footer,
            text="Ctrl+F searches • Enter/Shift+Enter moves through matches • Drag the divider to resize Contents • Esc closes",
            font=("Segoe UI", 9),
            bg=P["bg"],
            fg=P["subtext"],
        ).pack(side="left")

        if action_label and action_command:
            ttk.Button(
                footer,
                text=action_label,
                command=action_command,
                style="Accent.TButton",
            ).pack(side="right")
        else:
            ttk.Button(footer, text="Close", command=win.destroy).pack(side="right")

        win.bind("<Escape>", lambda _e: win.destroy())
        win.focus_set()
        return win

    def open_quick_start(self):
        text = "\n# MUSIKALL — Quick Start\n\nUse this guide to complete a standard analysis from structures to network paths, visualization, and sonification.\n\n## 1. Create a job\n- Enter a **Job Name** and click **Create Job**.\n- MUSIKALL creates a dedicated job directory under `Documents/MUSIKALL Projects`.\n\n## 2. Upload structures\n- Click **Upload PDBs** and select one or more `.pdb` files.\n- Hydrogen atoms are removed from the copied PDB files before network construction.\n- For direct structural comparison, keep related conformers or conditions in the same job.\n\n## 3. Build the residue interaction network\n- Set the **Cutoff Value (Å)**.\n- Click **Calculate Adjacency Matrix**.\n- MUSIKALL builds a residue-level contact network and stores the adjacency and edge-cost matrices for each structure.\n\n## 4. Define the reference and endpoints\n- Select a **Reference PDB** when comparing multiple structures.\n- Enter **Source residues** and **Sink residues**.\n- Basic input: `CHAIN,RESNUM` or `CHAIN,START-END`.\n- SEGNAME-aware input: `SEGNAME:CHAIN,RESNUM` or `SEGNAME:CHAIN,START-END`.\n- Separate multiple selections with semicolons or new lines.\n\n## 5. Map residues or skip mapping\n- Leave **Skip alignment** unchecked when source/sink residues must be projected from the selected reference to other structures.\n- Use **Skip alignment** only when residue identifiers are already directly compatible across the structures being compared.\n\n## 6. Calculate K-shortest paths\n- Set **K** and click **Calculate Shortest Paths**.\n- MUSIKALL ranks simple source-to-sink paths by cumulative network edge cost.\n\n## 7. Explore and compare paths\nAfter KSP calculation, use:\n- **Path Explorer** to inspect individual routes and costs.\n- **Cooccurrence Backbone** to examine residues that repeatedly occur together across selected paths.\n- **Path Similarity** to compare path composition within a structure or across an ensemble.\n- **Property Tracks** to relate path-frequency scores to residue properties.\n\n## 8. Visualize\n- **Save PDBs** writes frequency information into structure files for external visualization.\n- **Show 3D Structures** opens the built-in 3D viewer.\n\n## 9. Generate audio\n- Configure mapping, harmony, instrument, rhythm, pitch range, and velocity in the music panel.\n- Click **Generate Audio** to create MIDI output under the job's music directory.\n\n## Reproducibility checklist\nFor a direct comparison, keep the following fixed unless the change is intentional:\n- input structure files,\n- cutoff value,\n- reference/mapping mode,\n- source and sink selections,\n- K value,\n- MUSIKALL software version.\n"
        self._open_help_document(
            "MUSIKALL — Quick Start",
            "A concise end-to-end workflow from structure upload to path analysis, visualization, and sonification.",
            text,
            geometry="980x720",
        )



    def open_user_guide(self):
        text = '\n# MUSIKALL — User Guide\n\nMUSIKALL provides a workflow for constructing residue interaction networks from biomolecular structures, calculating weighted K-shortest paths between selected residues, analyzing path ensembles, visualizing residue usage, and generating deterministic MIDI representations.\n\n## 1. Jobs and output organization\nA job is a self-contained analysis workspace. Input copies, matrices, path tables, plots, colored structures, diagnostics, and music outputs are written inside the job directory. Use separate or versioned jobs when changing core analysis parameters.\n\n## 2. Structure input and residue identity\n### PDB handling\nThe current upload workflow reads PDB files and removes hydrogen atoms from the copied inputs before contact analysis. Residue nodes are built from standard polymer `ATOM` records. In the PDB format, these records are not limited to proteins: standard amino-acid, RNA, and DNA residues are represented as polymer `ATOM` records. MUSIKALL therefore supports protein structures, nucleic-acid structures, and hybrid assemblies such as ribosomes. In the current implementation, `HETATM` records are not used to create RIN residue nodes.\n\n### Residue identity\nMUSIKALL preserves the identifiers needed to distinguish residues in ordinary proteins and large assemblies:\n- chain ID,\n- residue number,\n- optional insertion code,\n- optional SEGNAME.\n\nWhen SEGNAME is present, residue tokens can be represented as `SEGNAME:CHAIN:RESNUM`; otherwise `CHAIN:RESNUM` is used. This distinction is important when chain IDs and residue numbers are reused in large complexes.\n\n## 3. Residue interaction network construction\nEach residue is a graph node. Two residues are connected when at least one heavy-atom pair lies within the user-defined cutoff.\n\nFor residues i and j:\n- `Ni` = number of heavy atoms in residue i,\n- `Nj` = number of heavy atoms in residue j,\n- `Nij` = number of inter-residue heavy-atom pairs within the cutoff.\n\nThe implemented normalized contact strength is:\n\n    Aij = Nij / sqrt(Ni * Nj)\n\nFor every non-zero contact, the path-search edge cost is:\n\n    wij = 1 / (Aij + 1e-6)\n\nTherefore, stronger normalized contacts have lower graph cost and are favored by weighted shortest-path searches. The saved matrix files contain the adjacency values and corresponding edge costs.\n\n## 4. Reference structure, source/sink selection, and mapping\nSource and sink selections are defined with respect to the selected reference structure when mapping is used.\n\nAccepted input examples:\n- `A,150`\n- `A,150-153`\n- `A,150,155,160`\n- `PROT:A,150`\n- multiple selections separated by `;` or new lines.\n\n### Mapping mode\nWhen mapping is enabled, MUSIKALL first resolves the selected residues in the reference structure and then projects those endpoints to the other structures using the implemented residue-correspondence logic. Large systems receive SEGNAME-aware handling to reduce ambiguity.\n\n### Skip alignment\nUse **Skip alignment** only when the selected residue identifiers can be resolved directly and consistently in every structure. It is not a general replacement for residue correspondence when numbering differs.\n\n## 5. K-shortest paths\nMUSIKALL constructs an undirected weighted graph from non-zero adjacency entries and uses NetworkX `shortest_simple_paths` to obtain up to K simple paths between each source/sink pair.\n\nA path is ranked by cumulative edge cost:\n\n    Cost(P) = sum(wij) for all edges (i,j) in P\n\nHere, "shortest" means lowest cumulative **network cost**, not shortest geometric distance in angstroms.\n\n## 6. Path Explorer\nPath Explorer lists calculated paths, residue tokens, and path costs. It can filter by source/sink pair and by residue search text. Use it to inspect individual routes before interpreting aggregate statistics.\n\n## 7. Residue frequencies and exported path tables\nMUSIKALL counts residue usage across the calculated path ensemble and generates normalized frequency values used by downstream plots, structure coloring, and optional frequency-dependent MIDI velocity. Source and sink handling is kept separate from interior-node frequency summaries where implemented.\n\n## 8. Cooccurrence Backbone\nEach selected path is converted to a binary residue-use vector `xp`. Stacking these vectors gives matrix `M`, and the co-occurrence matrix is:\n\n    C = M^T M\n\n`C[i,j]` records how often residues i and j occur together in the selected path ensemble. For visualization, the implementation restricts the heatmap to residues that actually appear in the selected paths. Per-structure and ensemble modes are available, with percent/count outputs and diagnostics according to the selected options.\n\n## 9. Path Similarity\nPath Similarity compares binary residue-membership patterns between paths. The implementation supports per-structure and ensemble analyses and uses a user-set similarity threshold. Use this module to identify recurrent or compositionally similar routes; it is distinct from comparing path costs.\n\n## 10. Property Tracks\nProperty Tracks relate path-frequency scores to residue classifications. The current GUI supports:\n- hydrophobicity,\n- charge,\n- aromaticity,\n- polarity.\n\nA minimum FreqScore can be applied before plotting. Results can be exported to `property_tracks_all.xlsx`, visualized per structure, and combined across structures using the selected reference when available.\n\n## 11. Visualization\n### Saved structures\nMUSIKALL can write normalized residue-frequency information into the B-factor field of output PDB files for visualization. These values are analysis annotations; they should not be interpreted as experimental crystallographic B-factors.\n\n### Built-in 3D viewer\nThe built-in viewer displays structures together with graph nodes/edges, source/sink residues, and frequency information when available.\n\n## 12. Sonification\nSonification is a representation layer applied after structural/path analysis. It does not change the residue network or KSP calculations.\n\nThe current music module supports:\n- output grouping: `per_path`, `per_pair`, `per_pdb`,\n- mapping modes: amino-acid grid, property, or single-residue focus,\n- single-note or triad playback,\n- General MIDI instrument selection,\n- tempo, note/rest duration, transpose, and pitch clamping,\n- constant or frequency-dependent velocity.\n\nWhen velocity is frequency-dependent, normalized frequency values are mapped between the configured minimum and maximum MIDI velocities.\n\n## 13. Reproducibility and good practice\nFor direct comparisons between structures:\n- use the same cutoff,\n- use the same K,\n- document the same source/sink definition and reference structure,\n- keep mapping mode consistent,\n- preserve the exact structure files used,\n- record the MUSIKALL version/build.\n\n## 14. Common warnings\n- **No paths found:** source and sink may lie in disconnected graph components at the selected cutoff.\n- **Residue not found:** verify chain, residue number, insertion code, and SEGNAME where applicable.\n- **Empty path analyses:** confirm KSP results exist for the selected structure/pair.\n- **Unexpected cross-structure endpoints:** verify the selected reference and mapping mode.\n- **Viewer or MIDI issues:** use the dedicated Troubleshooting page under Help.\n'
        self._open_help_document(
            "MUSIKALL — User Guide",
            "Operational reference for inputs, residue identity, network construction, mapping, analyses, outputs, and reproducibility.",
            text,
            geometry="1080x780",
        )



    def open_theory_info(self):
        text = '# Structural Network and K-Shortest-Path Method\n\n## Residue interaction network\nMUSIKALL represents each polymer residue as a node in an undirected graph. Nodes can correspond to amino-acid residues or standard RNA/DNA nucleotides, allowing proteins, nucleic acids, and hybrid assemblies to be analyzed within the same residue-level network. Structural contacts are derived from heavy atoms within the user-defined cutoff distance.\n\nFor residues i and j:\n\n    Ni  = heavy-atom count of residue i\n    Nj  = heavy-atom count of residue j\n    Nij = number of i-j heavy-atom pairs within the cutoff\n\nThe implemented normalized contact strength is:\n\n    Aij = Nij / sqrt(Ni * Nj)\n\nThis normalization reduces the direct dependence of contact magnitude on residue size. If `Nij = 0`, no graph edge is created.\n\n## Edge cost\nWeighted path searches require lower cost for stronger contacts. MUSIKALL therefore uses:\n\n    wij = 1 / (Aij + epsilon)\n\nwith `epsilon = 1e-6` for numerical stability.\n\nThus:\n- larger normalized contact strength -> lower edge cost,\n- lower normalized contact strength -> higher edge cost.\n\n## Path cost and K-shortest paths\nFor a path P composed of graph edges:\n\n    Cost(P) = sum(wij)\n\nMUSIKALL uses NetworkX `shortest_simple_paths` to rank simple source-to-sink paths by this cumulative network cost. A simple path does not repeat nodes.\n\nThe resulting routes are best interpreted as low-cost candidate communication routes encoded by the selected structural contact network. They are network-derived hypotheses rather than direct measurements of dynamical signal transmission.\n\n## Residue usage and co-occurrence\nFor a set of K paths, residue usage summarizes how often individual nodes participate in the selected path ensemble.\n\nFor co-occurrence analysis, each path is represented by a binary vector `xp` indicating whether each residue is present. With path vectors stacked in matrix `M`:\n\n    C = M^T M\n\n`C[i,j]` is the number of selected paths in which residues i and j co-occur. Individual residue frequency is a first-order usage statistic; co-occurrence is a pairwise usage statistic.\n\n## Path similarity\nPath Similarity compares path-level binary residue-membership patterns. This measures compositional overlap between routes and is conceptually different from comparing their cumulative network costs.\n\n## Residue correspondence across structures\nCross-structure analyses require a consistent correspondence between biological residues. MUSIKALL uses chain/residue identifiers and, where required, insertion codes, SEGNAME information, and implemented sequence-aware projection logic. SEGNAME-aware handling is especially important in large assemblies where chain and residue numbering alone may be ambiguous.\n\n---\n\n# Sonification Method\n\nMUSIKALL sonification converts already calculated molecular/path information into deterministic MIDI events. Musical settings do not feed back into network construction or path calculation.\n\n## Residue identity to pitch\nIn amino-acid-grid mode, each residue type is assigned a root note and octave. A note name is converted to a MIDI pitch using the standard MIDI pitch-number convention.\n\n## Harmony\nWhen chord mode is `single`, only the root pitch is emitted. When chord mode is `triad`, the selected preset adds fixed semitone intervals to the root pitch.\n\n## Pitch shaping\nA global transpose can be applied. Resulting pitches are clamped to the selected lower and upper octave bounds to avoid values outside the desired register.\n\n## Temporal mapping\nTempo determines seconds per beat. `note_beats` determines event duration and `rest_beats` controls silence between successive events.\n\nIn `per_path` output, path order can be preserved as musical time. `per_pair` and `per_pdb` modes aggregate residues at broader analysis scopes according to the implemented ordering policy.\n\n## Dynamics\nTwo velocity modes are available:\n\n- `constant`: a fixed MIDI velocity is used.\n- `by_frequency`: normalized residue frequency `F` in [0,1] is mapped between configured velocity bounds:\n\n    velocity = vmin + F * (vmax - vmin)\n\nThe result is clamped to the MIDI velocity range.\n\n## Representation policies\n- `per_path`: one MIDI representation per calculated path.\n- `per_pair`: one representation per source-sink pair.\n- `per_pdb`: one representation per structure.\n\n## Interpretation\nSonification provides an additional representation of residue identity, ordering, path membership, and frequency. Musical pitch, harmony, rhythm, or loudness should not be interpreted as independent biochemical measurements unless explicitly defined by the selected mapping.'
        self._open_help_document(
            "MUSIKALL — Theory & Methods",
            "Scientific and mathematical basis of the structural-network, path-analysis, and deterministic sonification layers.",
            text,
            geometry="1040x760",
        )


    def open_music_playground(self):
        """Interactive preview workspace that mirrors the current music-generation rules."""
        import os
        import re
        import tempfile
        import tkinter as tk
        from collections import Counter
        from tkinter import ttk, messagebox

        try:
                        from MUSIKALL_functions1 import (
                ALL_RESIDUES,
                NOTE_NAMES,
                GROUPS,
                aa3_to_group,
                get_triad_presets,
                note_to_midi,
                midi_to_note,
                triad_from_root,
                apply_transpose_clamp,
                _property_root,
                _pick_velocity,
                flex_parse_residue_token,
            )
        except Exception as e:
            messagebox.showerror("Music Playground", f"Required music components could not be loaded:\n{e}")
            return

        # One-window rule: bring an existing playground to the front.
        old = getattr(self, "_music_playground_win", None)
        try:
            if old is not None and old.winfo_exists():
                old.deiconify()
                old.lift()
                old.focus_force()
                return
        except Exception:
            pass

        if not hasattr(self, "music_opts"):
            self.init_music_options()

        P = getattr(self, "current_palette", {}) or {}
        bg = P.get("bg", "#F7FAFC")
        surface = P.get("surface", "#FFFFFF")
        muted = P.get("muted", "#E0F2FE")
        text_c = P.get("text", "#1E293B")
        subtext = P.get("subtext", "#475569")
        accent = P.get("accent", "#0EA5E9")
        border = P.get("border", "#BAE6FD")

        win = tk.Toplevel(self)
        self._music_playground_win = win
        win.title("Music Playground")
        win.geometry("1160x800")
        win.minsize(940, 650)
        win.configure(bg=bg)

        style = ttk.Style(win)
        style.configure("MP.TFrame", background=bg)
        style.configure("MP.Surface.TFrame", background=surface)
        style.configure("MP.TLabel", background=bg, foreground=text_c)
        style.configure("MP.Surface.TLabel", background=surface, foreground=text_c)
        style.configure("MP.Sub.TLabel", background=surface, foreground=subtext)
        style.configure("MP.Header.TLabel", background=surface, foreground=text_c,
                        font=("Segoe UI", 17, "bold"))
        style.configure("MP.Section.TLabel", background=surface, foreground=text_c,
                        font=("Segoe UI", 11, "bold"))
        style.configure("MP.Card.TLabelframe", background=surface, bordercolor=border)
        style.configure("MP.Card.TLabelframe.Label", background=surface, foreground=text_c,
                        font=("Segoe UI", 10, "bold"))

        # ---------- Current UI option readers ----------
        def _get(var_name, fallback):
            obj = getattr(self, var_name, None)
            if obj is not None:
                try:
                    return obj.get()
                except Exception:
                    pass
            return fallback

        def _beats_from_label(lbl):
            return {
                "Whole (1/1)": 4.0,
                "Half (1/2)": 2.0,
                "Quarter (1/4)": 1.0,
                "Eighth (1/8)": 0.5,
                "Sixteenth (1/16)": 0.25,
            }.get(str(lbl), 1.0)

        def _snapshot_options():
            """Copy the currently visible music controls into a lightweight MusicOptions-like object."""
            from copy import copy
            opts = copy(self.music_opts)
            opts.rep_res_freq = str(_get("_rep_res_freq", getattr(opts, "rep_res_freq", "per_pdb")) or "per_pdb")
            opts.mapping_mode = str(_get("_mapping_mode", getattr(opts, "mapping_mode", "aa")) or "aa")
            opts.chord_mode = str(_get("_chord_mode", getattr(opts, "chord_mode", "single")) or "single")
            opts.aa_triad_name = str(_get("_aa_triad", getattr(opts, "aa_triad_name", "Major (I)")) or "Major (I)")
            opts.property_dimension = str(_get("_prop_dimension", getattr(opts, "property_dimension", "hydrophobicity")) or "hydrophobicity")
            opts.property_base_octave = int(_get("_prop_octave", getattr(opts, "property_base_octave", 4)) or 4)
            opts.single_aa_code = str(_get("_single_code", getattr(opts, "single_aa_code", "K")) or "K").strip().upper()[:1]
            opts.single_triad_name = str(_get("_single_triad", getattr(opts, "single_triad_name", "Major (I)")) or "Major (I)")
            opts.single_base_octave = int(_get("_single_octave", getattr(opts, "single_base_octave", 4)) or 4)
            opts.single_others_policy = str(_get("_single_others", getattr(opts, "single_others_policy", "rest")) or "rest")
            opts.program = int(_get("_program_var", getattr(opts, "program", 0)) or 0)
            opts.velocity_mode = str(_get("_vel_mode", getattr(opts, "velocity_mode", "by_frequency")) or "by_frequency")
            opts.velocity_constant = int(_get("_vel_const", getattr(opts, "velocity_constant", 90)) or 90)
            opts.velocity_min = int(_get("_velocity_min", getattr(opts, "velocity_min", 30)) or 30)
            opts.velocity_max = int(_get("_velocity_max", getattr(opts, "velocity_max", 110)) or 110)
            opts.transpose = int(_get("_transpose", getattr(opts, "transpose", 0)) or 0)
            opts.clamp_low = int(_get("_clamp_lo", getattr(opts, "clamp_low", 3)) or 3)
            opts.clamp_high = int(_get("_clamp_hi", getattr(opts, "clamp_high", 6)) or 6)
            opts.tempo_bpm = int(_get("_tempo_var", getattr(opts, "tempo_bpm", 120)) or 120)
            opts.note_beats = _beats_from_label(_get("_note_value", "Quarter (1/4)"))
            rr = float(_get("_rest_ratio", 0.25) or 0.0)
            opts.rest_beats = max(0.0, opts.note_beats * rr)

            # Use live property-triad controls when Advanced Options is currently open.
            tri_map = dict(getattr(opts, "property_triads", {}) or {})
            dim = opts.property_dimension
            live_vars = getattr(self, "_prop_triad_vars", {}) or {}
            if live_vars:
                tri_map[dim] = {
                    cls: (var.get() if hasattr(var, "get") else str(var))
                    for cls, var in live_vars.items()
                }
            opts.property_triads = tri_map
            return opts

        TRIADS = get_triad_presets()
        aa_by_one = {one: (aa3, fullname) for aa3, one, fullname in ALL_RESIDUES}
        aa_name = {aa3: (one, fullname) for aa3, one, fullname in ALL_RESIDUES}

        def _grid_root(aa3):
            wset = (getattr(self, "aa_widgets", {}) or {}).get(aa3)
            if not wset:
                return None
            try:
                note = (wset["note"].get() or "C").strip()
                octave = int((wset["oct"].get() or "4").strip())
                return f"{note}{octave}"
            except Exception:
                return None

        def _midi_notes(note_names, opts):
            out = []
            for n in note_names:
                if n == "REST":
                    continue
                try:
                    m = note_to_midi(n)
                    out.append(apply_transpose_clamp(m, opts.transpose, opts.clamp_low, opts.clamp_high))
                except Exception:
                    continue
            return out

        def _notes_for_aa3(aa3, opts):
            """Mirror generate_audio.notes_for_token, but operate on a known residue name."""
            mode = (opts.mapping_mode or "aa").lower()

            if mode == "aa":
                root = _grid_root(aa3)
                if not root:
                    return [], None, "No grid root"
                if (opts.chord_mode or "single").lower() == "single":
                    return [root], None, "AA identity"
                return triad_from_root(root, opts.aa_triad_name), None, "AA identity"

            if mode == "property":
                dim = opts.property_dimension
                group = aa3_to_group(aa3, dim)
                if not group:
                    return [], None, "No property class"
                root = _property_root(dim, group, opts.property_base_octave)
                tri_name = ((opts.property_triads or {}).get(dim, {}) or {}).get(group) or "Major (I)"
                return triad_from_root(root, tri_name), group, f"{dim}: {group}"

            if mode == "single":
                one = aa_name.get(aa3, (None, None))[0]
                if one == opts.single_aa_code:
                    root = f"C{opts.single_base_octave}"
                    return triad_from_root(root, opts.single_triad_name), None, "Target residue"
                if (opts.single_others_policy or "rest").lower() == "rest":
                    return ["REST"], None, "Rest"
                return [], None, "Skipped"

            return [], None, "Unknown mapping mode"

        def _resolve_aa3(token, pdb_key):
            """Resolve a path token to the residue name using current residue metadata."""
            try:
                seg, ch, rn, ic = flex_parse_residue_token(token, strict=False, default_seg="")
                ch = str(ch or "").strip()
                rn = int(rn)
                seg = str(seg or "").strip()
                ic = str(ic).strip() if ic not in (None, "", " ") else None
            except Exception:
                return None

            pdb_data = (getattr(self, "pdb_info_dict", {}) or {}).get(pdb_key, {}) or {}
            if not pdb_data:
                stem = os.path.splitext(os.path.basename(str(pdb_key)))[0].lower()
                pdb_data = (getattr(self, "pdb_info_dict", {}) or {}).get(stem, {}) or {}

            candidates = []
            for ch_key, residues in (pdb_data.get("residue_chain_map", {}) or {}).items():
                for r in residues or []:
                    rch = str(r.get("chain") or ch_key).strip()
                    try:
                        rrn = int(r.get("residue_num"))
                    except Exception:
                        continue
                    ric = r.get("icode")
                    ric = str(ric).strip() if ric not in (None, "", " ") else None
                    rseg = str(r.get("segname") or "").strip()
                    if rch != ch or rrn != rn:
                        continue
                    if ic is not None and ric != ic:
                        continue
                    if seg and rseg != seg:
                        continue
                    candidates.append(str(r.get("residue_name", "UNK")).strip().upper())
            uniq = [x for x in dict.fromkeys(candidates) if x and x != "UNK"]
            return uniq[0] if len(uniq) == 1 else (uniq[0] if seg and uniq else None)

        def _canonical(token):
            try:
                seg, ch, rn, ic = flex_parse_residue_token(token, strict=False, default_seg="")
                if not ch or rn is None:
                    return None
                base = f"{str(ch).strip().upper()}:{int(rn)}" + (str(ic).strip() if ic else "")
                return f"{str(seg).strip()}:{base}" if seg else base
            except Exception:
                return None

        def _sort_token(token):
            try:
                seg, ch, rn, ic = flex_parse_residue_token(token, strict=False, default_seg="")
                return (str(seg or ""), str(ch or ""), int(rn), str(ic or ""))
            except Exception:
                return ("", "", 10**9, str(token))

        def _unique_sorted(paths):
            s = set()
            for p in paths or []:
                for t in p or []:
                    ct = _canonical(t)
                    if ct:
                        s.add(ct)
            return sorted(s, key=_sort_token)

        def _freq_map(paths):
            cnt = Counter()
            for p in paths or []:
                for t in p or []:
                    ct = _canonical(t)
                    if ct:
                        cnt[ct] += 1
            if not cnt:
                return {}
            mx = max(cnt.values())
            return {k: v / mx for k, v in cnt.items()} if mx else {k: 0.0 for k in cnt}

        def _write_and_play(events, name="preview", opts_override=None):
            """Play preview events using current settings or an explicit preview option snapshot."""
            opts = opts_override if opts_override is not None else _snapshot_options()
            try:
                stop_midi()
            except Exception:
                pass

            mid = MIDIFile(1)
            tr = 0
            mid.addTempo(tr, 0, max(1, int(opts.tempo_bpm)))
            mid.addProgramChange(tr, 0, 0, max(0, min(127, int(opts.program))))
            t = 0.0
            for midi_notes, velocity in events:
                if midi_notes:
                    for m in midi_notes:
                        mid.addNote(tr, 0, int(m), t, float(opts.note_beats),
                                    max(1, min(127, int(velocity))))
                t += float(opts.note_beats) + float(opts.rest_beats)

            tmp = os.path.join(tempfile.gettempdir(),
                               f"musikall_{re.sub(r'[^A-Za-z0-9_-]+', '_', name)}.mid")
            with open(tmp, "wb") as fh:
                mid.writeFile(fh)
            play_midi(tmp)

        def _single_event_for_aa(aa3, freq=0.5):
            opts = _snapshot_options()
            names, _grp, _desc = _notes_for_aa3(aa3, opts)
            midi = _midi_notes(names, opts)
            vel = _pick_velocity(opts, freq)
            return [(midi if midi else None, vel)]

        # ---------- Header ----------
        header = tk.Frame(win, bg=surface, highlightthickness=1, highlightbackground=border)
        header.pack(fill="x", padx=14, pady=(14, 8))
        left_head = tk.Frame(header, bg=surface)
        left_head.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        tk.Label(left_head, text="Music Playground", bg=surface, fg=text_c,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(left_head,
                 text="Preview the same mapping, chord, dynamics, pitch-range, rhythm and grouping rules used by Generate Audio.",
                 bg=surface, fg=subtext, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))
        head_btns = ttk.Frame(header, style="MP.Surface.TFrame")
        head_btns.pack(side="right", padx=12, pady=12)
        ttk.Button(head_btns, text="Stop", command=stop_midi).pack(side="left", padx=4)

        # Live settings strip
        settings_var = tk.StringVar()
        settings_bar = tk.Label(win, textvariable=settings_var, bg=muted, fg=text_c,
                                anchor="w", padx=12, pady=7, font=("Segoe UI", 9))
        settings_bar.pack(fill="x", padx=14, pady=(0, 8))

        def _refresh_settings_label():
            o = _snapshot_options()
            settings_var.set(
                f"Mode: {o.mapping_mode}   |   Output: {o.rep_res_freq}   |   Program: {o.program}   |   "
                f"Tempo: {o.tempo_bpm} BPM   |   Note: {o.note_beats:g} beat(s)   |   Rest: {o.rest_beats:g}   |   "
                f"Velocity: {o.velocity_mode}   |   Transpose: {o.transpose:+d}   |   Clamp: {o.clamp_low}–{o.clamp_high}"
            )

        _refresh_settings_label()

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # ---------- Tab 1: Current mapping ----------
        tab_current = ttk.Frame(nb, style="MP.TFrame")
        nb.add(tab_current, text="Current Mapping")
        current_card = tk.Frame(tab_current, bg=surface, highlightthickness=1, highlightbackground=border)
        current_card.pack(fill="both", expand=True, padx=8, pady=8)

        current_top = tk.Frame(current_card, bg=surface)
        current_top.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(current_top, text="Residue preview", bg=surface, fg=text_c,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(current_top, text="Frequency preview", bg=surface, fg=subtext).pack(side="left", padx=(24, 6))
        freq_var = tk.DoubleVar(value=0.5)
        freq_scale = ttk.Scale(current_top, from_=0.0, to=1.0, variable=freq_var, length=180)
        freq_scale.pack(side="left")
        freq_label = tk.Label(current_top, text="0.50", bg=surface, fg=text_c, width=5)
        freq_label.pack(side="left", padx=(6, 0))
        freq_var.trace_add("write", lambda *_: freq_label.configure(text=f"{freq_var.get():.2f}"))
        ttk.Button(current_top, text="Refresh", command=lambda: _rebuild_residue_rows()).pack(side="right")

        table_wrap = tk.Frame(current_card, bg=surface)
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        columns = ("residue", "mapping", "output", "velocity")
        tree = ttk.Treeview(table_wrap, columns=columns, show="headings", height=18)
        tree.heading("residue", text="Residue")
        tree.heading("mapping", text="Mapping / class")
        tree.heading("output", text="Audible output")
        tree.heading("velocity", text="Velocity")
        tree.column("residue", width=210, anchor="w")
        tree.column("mapping", width=240, anchor="w")
        tree.column("output", width=300, anchor="w")
        tree.column("velocity", width=90, anchor="center")
        ysb = ttk.Scrollbar(table_wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")

        row_aa = {}

        def _rebuild_residue_rows():
            _refresh_settings_label()
            tree.delete(*tree.get_children())
            row_aa.clear()
            o = _snapshot_options()
            f = float(freq_var.get())
            vel = _pick_velocity(o, f)
            for aa3, aa1, fullname in ALL_RESIDUES:
                names, grp, desc = _notes_for_aa3(aa3, o)
                audible = "Rest" if names == ["REST"] else (" + ".join(midi_to_note(m) for m in _midi_notes(names, o)) if names else "Skipped / unavailable")
                mapping_desc = desc
                if o.mapping_mode == "aa":
                    mapping_desc = _grid_root(aa3) or "No grid root"
                    if o.chord_mode == "triad":
                        mapping_desc += f" · {o.aa_triad_name}"
                elif o.mapping_mode == "property" and grp:
                    mapping_desc = f"{o.property_dimension}: {grp}"
                elif o.mapping_mode == "single":
                    mapping_desc = "Target" if aa1 == o.single_aa_code else o.single_others_policy.capitalize()
                iid = tree.insert("", "end", values=(f"{aa3} ({aa1}) — {fullname}", mapping_desc, audible, vel))
                row_aa[iid] = aa3

        def _play_selected(_event=None):
            sel = tree.selection()
            if not sel:
                return
            aa3 = row_aa.get(sel[0])
            if aa3:
                _write_and_play(_single_event_for_aa(aa3, float(freq_var.get())), f"residue_{aa3}")

        tree.bind("<Double-1>", _play_selected)
        tree.bind("<Return>", _play_selected)
        row_buttons = ttk.Frame(current_card, style="MP.Surface.TFrame")
        row_buttons.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(row_buttons, text="Play selected residue", command=_play_selected).pack(side="left")
        tk.Label(row_buttons, text="Double-click a row to hear it.", bg=surface, fg=subtext).pack(side="left", padx=10)
        _rebuild_residue_rows()

        # ---------- Residue Grid library: all residue-identity sounds ----------
        tab_grid = ttk.Frame(nb, style="MP.TFrame")
        nb.add(tab_grid, text="Residue Grid")
        grid_card = tk.Frame(tab_grid, bg=surface, highlightthickness=1, highlightbackground=border)
        grid_card.pack(fill="both", expand=True, padx=8, pady=8)
        tk.Label(grid_card, text="Residue-identity mapping library", bg=surface, fg=text_c,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(14, 3))
        tk.Label(grid_card,
                 text="Audition every residue/nucleotide using its current residue-grid root. Choose single-note or any supported triad without changing the main music settings.",
                 bg=surface, fg=subtext, wraplength=980, justify="left").pack(anchor="w", padx=14)
        grid_ctl = tk.Frame(grid_card, bg=surface)
        grid_ctl.pack(fill="x", padx=14, pady=10)
        grid_mode = tk.StringVar(value="single")
        grid_triad = tk.StringVar(value="Major (I)")
        tk.Label(grid_ctl, text="Playback", bg=surface, fg=text_c).pack(side="left")
        ttk.Combobox(grid_ctl, textvariable=grid_mode, values=["single", "triad"], state="readonly", width=9).pack(side="left", padx=(6, 14))
        tk.Label(grid_ctl, text="Triad", bg=surface, fg=text_c).pack(side="left")
        ttk.Combobox(grid_ctl, textvariable=grid_triad, values=list(TRIADS.keys()), state="readonly", width=22).pack(side="left", padx=6)
        grid_body = tk.Frame(grid_card, bg=surface)
        grid_body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        grid_tree = ttk.Treeview(grid_body, columns=("residue","root","audible"), show="headings", height=16)
        for key, title, width in [("residue","Residue",260),("root","Current root",120),("audible","Audible output",360)]:
            grid_tree.heading(key, text=title); grid_tree.column(key, width=width, anchor="w")
        grid_sb = ttk.Scrollbar(grid_body, orient="vertical", command=grid_tree.yview)
        grid_tree.configure(yscrollcommand=grid_sb.set)
        grid_tree.pack(side="left", fill="both", expand=True); grid_sb.pack(side="right", fill="y")
        grid_row_aa = {}

        def _refresh_grid_library(*_):
            grid_tree.delete(*grid_tree.get_children()); grid_row_aa.clear()
            o = _snapshot_options()
            for aa3, aa1, fullname in ALL_RESIDUES:
                root = _grid_root(aa3)
                if root:
                    names = [root] if grid_mode.get() == "single" else triad_from_root(root, grid_triad.get())
                    audible = " + ".join(midi_to_note(m) for m in _midi_notes(names, o))
                else:
                    audible = "Unavailable"
                iid = grid_tree.insert("", "end", values=(f"{aa3} ({aa1}) — {fullname}", root or "—", audible))
                grid_row_aa[iid] = aa3

        def _play_grid_selected(_event=None):
            sel=grid_tree.selection()
            if not sel: return
            aa3=grid_row_aa.get(sel[0]); root=_grid_root(aa3) if aa3 else None
            if not root: return
            o=_snapshot_options(); names=[root] if grid_mode.get()=="single" else triad_from_root(root, grid_triad.get())
            _write_and_play([(_midi_notes(names,o), _pick_velocity(o,0.5))], f"grid_{aa3}")

        grid_mode.trace_add("write", _refresh_grid_library); grid_triad.trace_add("write", _refresh_grid_library)
        grid_tree.bind("<Double-1>", _play_grid_selected)
        ttk.Button(grid_card, text="Play selected residue", command=_play_grid_selected).pack(anchor="w", padx=14, pady=(0,12))
        _refresh_grid_library()

        # ---------- Property library: every dimension and class ----------
        tab_prop_music = ttk.Frame(nb, style="MP.TFrame")
        nb.add(tab_prop_music, text="Properties")
        prop_card = tk.Frame(tab_prop_music, bg=surface, highlightthickness=1, highlightbackground=border)
        prop_card.pack(fill="both", expand=True, padx=8, pady=8)
        tk.Label(prop_card, text="Property-mapping library", bg=surface, fg=text_c,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(14,3))
        tk.Label(prop_card,
                 text="Hear every class used by hydrophobicity, charge, aromaticity and polarity mapping. Roots are generated by the same property-root function used by Generate Audio.",
                 bg=surface, fg=subtext, wraplength=980, justify="left").pack(anchor="w", padx=14)
        prop_ctl = tk.Frame(prop_card, bg=surface); prop_ctl.pack(fill="x", padx=14, pady=10)
        prop_oct_lib = tk.IntVar(value=int(getattr(self.music_opts,"property_base_octave",4)))
        prop_triad_lib = tk.StringVar(value="Major (I)")
        tk.Label(prop_ctl,text="Base octave",bg=surface,fg=text_c).pack(side="left")
        ttk.Spinbox(prop_ctl,from_=0,to=9,textvariable=prop_oct_lib,width=5).pack(side="left",padx=(6,14))
        tk.Label(prop_ctl,text="Audition triad",bg=surface,fg=text_c).pack(side="left")
        ttk.Combobox(prop_ctl,textvariable=prop_triad_lib,values=list(TRIADS.keys()),state="readonly",width=22).pack(side="left",padx=6)
        prop_body=tk.Frame(prop_card,bg=surface); prop_body.pack(fill="both",expand=True,padx=14,pady=(0,10))
        prop_tree=ttk.Treeview(prop_body,columns=("dim","class","root","audible"),show="headings",height=14)
        for key,title,width in [("dim","Property",170),("class","Class",170),("root","Root",100),("audible","Audible output",340)]:
            prop_tree.heading(key,text=title); prop_tree.column(key,width=width,anchor="w")
        psb=ttk.Scrollbar(prop_body,orient="vertical",command=prop_tree.yview); prop_tree.configure(yscrollcommand=psb.set)
        prop_tree.pack(side="left",fill="both",expand=True); psb.pack(side="right",fill="y")
        prop_rows={}
        def _refresh_property_library(*_):
            prop_tree.delete(*prop_tree.get_children()); prop_rows.clear(); o=_snapshot_options()
            for dim, classes in GROUPS.items():
                for grp in classes.keys():
                    root=_property_root(dim,grp,int(prop_oct_lib.get()))
                    names=triad_from_root(root,prop_triad_lib.get()); audible=" + ".join(midi_to_note(m) for m in _midi_notes(names,o))
                    iid=prop_tree.insert("","end",values=(dim,grp,root,audible)); prop_rows[iid]=(dim,grp)
        def _play_property_selected(_event=None):
            sel=prop_tree.selection()
            if not sel:return
            dim,grp=prop_rows[sel[0]]; o=_snapshot_options(); root=_property_root(dim,grp,int(prop_oct_lib.get()))
            names=triad_from_root(root,prop_triad_lib.get()); _write_and_play([(_midi_notes(names,o),_pick_velocity(o,0.5))],f"property_{dim}_{grp}")
        def _play_all_property_classes():
            o=_snapshot_options(); events=[]
            for dim,classes in GROUPS.items():
                for grp in classes.keys():
                    root=_property_root(dim,grp,int(prop_oct_lib.get())); events.append((_midi_notes(triad_from_root(root,prop_triad_lib.get()),o),_pick_velocity(o,0.5)))
            _write_and_play(events,"all_property_classes")
        prop_oct_lib.trace_add("write",_refresh_property_library); prop_triad_lib.trace_add("write",_refresh_property_library)
        prop_tree.bind("<Double-1>",_play_property_selected)
        pb=ttk.Frame(prop_card,style="MP.Surface.TFrame"); pb.pack(fill="x",padx=14,pady=(0,12))
        ttk.Button(pb,text="Play selected class",command=_play_property_selected).pack(side="left")
        ttk.Button(pb,text="Play all property classes",command=_play_all_property_classes).pack(side="left",padx=6)
        _refresh_property_library()

        # ---------- Single-residue focus library ----------
        tab_single = ttk.Frame(nb, style="MP.TFrame")
        nb.add(tab_single, text="Single Residue")
        single_card=tk.Frame(tab_single,bg=surface,highlightthickness=1,highlightbackground=border)
        single_card.pack(fill="both",expand=True,padx=8,pady=8)
        tk.Label(single_card,text="Single-residue focus",bg=surface,fg=text_c,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=14,pady=(14,3))
        tk.Label(single_card,text="Choose any supported residue code and hear exactly how the target is rendered. Non-target residues can be previewed as rest or skip, matching the backend policy.",bg=surface,fg=subtext,wraplength=980,justify="left").pack(anchor="w",padx=14)
        sc=tk.Frame(single_card,bg=surface); sc.pack(fill="x",padx=14,pady=14)
        single_choices=[f"{one} — {aa3} — {fullname}" for aa3,one,fullname in ALL_RESIDUES]
        single_sel=tk.StringVar(value=single_choices[0]); single_triad_lib=tk.StringVar(value="Major (I)"); single_oct_lib=tk.IntVar(value=4); single_policy_lib=tk.StringVar(value="rest")
        for label,var,values,width in [("Residue",single_sel,single_choices,30),("Triad",single_triad_lib,list(TRIADS.keys()),22),("Others",single_policy_lib,["rest","skip"],8)]:
            tk.Label(sc,text=label,bg=surface,fg=text_c).pack(side="left",padx=(0,5)); ttk.Combobox(sc,textvariable=var,values=values,state="readonly",width=width).pack(side="left",padx=(0,12))
        tk.Label(sc,text="Octave",bg=surface,fg=text_c).pack(side="left"); ttk.Spinbox(sc,from_=0,to=9,textvariable=single_oct_lib,width=5).pack(side="left",padx=6)
        single_desc=tk.StringVar(); tk.Label(single_card,textvariable=single_desc,bg=muted,fg=text_c,anchor="w",padx=10,pady=8).pack(fill="x",padx=14,pady=(0,12))
        def _single_preview_notes():
            one=single_sel.get().split(" — ",1)[0].strip(); o=_snapshot_options(); root=f"C{int(single_oct_lib.get())}"; names=triad_from_root(root,single_triad_lib.get()); audible=" + ".join(midi_to_note(m) for m in _midi_notes(names,o)); single_desc.set(f"Target code: {one}   |   Root: {root}   |   Output: {audible}   |   Non-target policy: {single_policy_lib.get()}"); return o,names,one
        def _play_single_target():
            o,names,one=_single_preview_notes(); _write_and_play([(_midi_notes(names,o),_pick_velocity(o,0.5))],f"single_{one}")
        def _play_single_behavior():
            o,names,one=_single_preview_notes(); events=[(_midi_notes(names,o),_pick_velocity(o,0.5))]
            # REST creates a timed silent event; SKIP produces no event for the non-target residue.
            if single_policy_lib.get()=="rest": events.append((None,_pick_velocity(o,0.5)))
            _write_and_play(events,f"single_behavior_{one}")
        for v in (single_sel,single_triad_lib,single_oct_lib,single_policy_lib): v.trace_add("write",lambda *_:_single_preview_notes())
        sb=ttk.Frame(single_card,style="MP.Surface.TFrame"); sb.pack(fill="x",padx=14,pady=(0,14))
        ttk.Button(sb,text="Play target",command=_play_single_target).pack(side="left")
        ttk.Button(sb,text="Play target + non-target behavior",command=_play_single_behavior).pack(side="left",padx=6)
        _single_preview_notes()

        # ---------- Generated-output preview ----------
        tab_paths = ttk.Frame(nb, style="MP.TFrame")
        nb.add(tab_paths, text="Output Preview")
        path_card = tk.Frame(tab_paths, bg=surface, highlightthickness=1, highlightbackground=border)
        path_card.pack(fill="both", expand=True, padx=8, pady=8)
        tk.Label(path_card, text="Preview stored KSP data using the current output-grouping rule",
                 bg=surface, fg=text_c, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(14, 3))
        tk.Label(path_card,
                 text="per_path preserves path order; per_pair and per_pdb use unique residue tokens sorted deterministically, matching Generate Audio.",
                 bg=surface, fg=subtext, wraplength=980, justify="left").pack(anchor="w", padx=14)

        preview_info = tk.StringVar(value="")
        tk.Label(path_card, textvariable=preview_info, bg=muted, fg=text_c,
                 anchor="w", padx=10, pady=7).pack(fill="x", padx=14, pady=(12, 8))

        path_text = tk.Text(path_card, height=12, wrap="word", bg=surface, fg=text_c,
                            relief="flat", highlightthickness=1, highlightbackground=border,
                            font=("Consolas", 9), padx=10, pady=8)
        path_text.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        def _first_preview_dataset():
            pd2 = getattr(self, "paths_dict_2", {}) or {}
            for pdb_key, pairs in pd2.items():
                if not pairs:
                    continue
                o = _snapshot_options()
                policy = (o.rep_res_freq or "per_pdb").lower()
                if policy == "per_path":
                    for pair_key, pdata in pairs.items():
                        paths = list((pdata or {}).get("paths", []) or [])
                        if paths:
                            toks = [_canonical(t) for t in paths[0]]
                            toks = [t for t in toks if t]
                            return pdb_key, f"{pair_key} · path 1", toks, _freq_map([paths[0]])
                if policy == "per_pair":
                    for pair_key, pdata in pairs.items():
                        paths = list((pdata or {}).get("paths", []) or [])
                        if paths:
                            return pdb_key, pair_key, _unique_sorted(paths), _freq_map(paths)
                all_paths = []
                for pdata in pairs.values():
                    all_paths.extend(list((pdata or {}).get("paths", []) or []))
                if all_paths:
                    return pdb_key, "all stored pairs", _unique_sorted(all_paths), _freq_map(all_paths)
            return None

        def _build_path_preview(play=False):
            _refresh_settings_label()
            data = _first_preview_dataset()
            path_text.configure(state="normal")
            path_text.delete("1.0", "end")
            if not data:
                preview_info.set("No stored K-shortest paths are available yet.")
                path_text.insert("end", "Run K-shortest paths first to preview a real MUSIKALL output sequence.")
                path_text.configure(state="disabled")
                return

            pdb_key, label, tokens, fmap = data
            o = _snapshot_options()
            events = []
            display_lines = []
            for tok in tokens:
                aa3 = _resolve_aa3(tok, pdb_key)
                if not aa3:
                    display_lines.append(f"{tok:<24}  unresolved → silence/rest slot")
                    events.append((None, _pick_velocity(o, fmap.get(tok, 0.0))))
                    continue
                names, grp, desc = _notes_for_aa3(aa3, o)
                midi = _midi_notes(names, o)
                vel = _pick_velocity(o, fmap.get(tok, 0.0))
                note_disp = "REST" if names == ["REST"] else ("+".join(midi_to_note(m) for m in midi) if midi else "SKIP")
                display_lines.append(f"{tok:<24}  {aa3:<4}  {desc:<24}  {note_disp:<18}  vel={vel}")
                events.append((midi if midi else None, vel))

            preview_info.set(f"PDB: {pdb_key}   |   Scope: {o.rep_res_freq}   |   Selection: {label}   |   Events: {len(tokens)}")
            path_text.insert("end", "\n".join(display_lines))
            path_text.configure(state="disabled")
            if play and events:
                _write_and_play(events, "stored_output_preview")

        path_btns = ttk.Frame(path_card, style="MP.Surface.TFrame")
        path_btns.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(path_btns, text="Refresh preview", command=lambda: _build_path_preview(False)).pack(side="left")
        ttk.Button(path_btns, text="Play preview", command=lambda: _build_path_preview(True)).pack(side="left", padx=6)
        _build_path_preview(False)

        # ---------- Chord library ----------
        tab_chords = ttk.Frame(nb, style="MP.TFrame")
        nb.add(tab_chords, text="Chord Library")
        chord_card = tk.Frame(tab_chords, bg=surface, highlightthickness=1, highlightbackground=border)
        chord_card.pack(fill="both", expand=True, padx=8, pady=8)
        controls = tk.Frame(chord_card, bg=surface)
        controls.pack(fill="x", padx=14, pady=14)
        tk.Label(controls, text="Root", bg=surface, fg=text_c).pack(side="left")
        chord_root = tk.StringVar(value="C")
        ttk.Combobox(controls, textvariable=chord_root, values=NOTE_NAMES, state="readonly", width=6).pack(side="left", padx=(6, 14))
        tk.Label(controls, text="Octave", bg=surface, fg=text_c).pack(side="left")
        chord_oct = tk.IntVar(value=4)
        ttk.Spinbox(controls, from_=0, to=9, textvariable=chord_oct, width=5).pack(side="left", padx=6)
        tk.Label(controls, text="Transpose and clamp are applied exactly as in Generate Audio.", bg=surface, fg=subtext).pack(side="left", padx=16)

        chord_body = tk.Frame(chord_card, bg=surface)
        chord_body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        for i, (name, intervals) in enumerate(TRIADS.items()):
            row = tk.Frame(chord_body, bg=surface)
            row.grid(row=i, column=0, sticky="ew", pady=3)
            chord_body.grid_columnconfigure(0, weight=1)
            tk.Label(row, text=name, bg=surface, fg=text_c, width=24, anchor="w").pack(side="left")
            tk.Label(row, text="Intervals: " + ", ".join(str(x) for x in intervals), bg=surface, fg=subtext, width=24, anchor="w").pack(side="left")

            def _play_chord(nm=name):
                o = _snapshot_options()
                root = f"{chord_root.get()}{int(chord_oct.get())}"
                names = triad_from_root(root, nm)
                midi = _midi_notes(names, o)
                _write_and_play([(midi, _pick_velocity(o, 0.5))], f"chord_{nm}")

            ttk.Button(row, text="Play", command=_play_chord).pack(side="right")

        # ---------- Instrument & pitch library ----------
        tab_inst = ttk.Frame(nb, style="MP.TFrame")
        nb.add(tab_inst, text="Instrument & Pitch")
        inst_card=tk.Frame(tab_inst,bg=surface,highlightthickness=1,highlightbackground=border)
        inst_card.pack(fill="both",expand=True,padx=8,pady=8)
        tk.Label(inst_card,text="General MIDI instrument and pitch preview",bg=surface,fg=text_c,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=14,pady=(14,3))
        tk.Label(inst_card,text="MUSIKALL sends a General MIDI program number (0–127). The exact timbre depends on the synthesizer/soundfont installed on the computer.",bg=surface,fg=subtext,wraplength=980,justify="left").pack(anchor="w",padx=14)
        GM_NAMES = [
            "Acoustic Grand Piano","Bright Acoustic Piano","Electric Grand Piano","Honky-tonk Piano","Electric Piano 1","Electric Piano 2","Harpsichord","Clavinet",
            "Celesta","Glockenspiel","Music Box","Vibraphone","Marimba","Xylophone","Tubular Bells","Dulcimer",
            "Drawbar Organ","Percussive Organ","Rock Organ","Church Organ","Reed Organ","Accordion","Harmonica","Tango Accordion",
            "Acoustic Guitar (nylon)","Acoustic Guitar (steel)","Electric Guitar (jazz)","Electric Guitar (clean)","Electric Guitar (muted)","Overdriven Guitar","Distortion Guitar","Guitar Harmonics",
            "Acoustic Bass","Electric Bass (finger)","Electric Bass (pick)","Fretless Bass","Slap Bass 1","Slap Bass 2","Synth Bass 1","Synth Bass 2",
            "Violin","Viola","Cello","Contrabass","Tremolo Strings","Pizzicato Strings","Orchestral Harp","Timpani",
            "String Ensemble 1","String Ensemble 2","Synth Strings 1","Synth Strings 2","Choir Aahs","Voice Oohs","Synth Voice","Orchestra Hit",
            "Trumpet","Trombone","Tuba","Muted Trumpet","French Horn","Brass Section","Synth Brass 1","Synth Brass 2",
            "Soprano Sax","Alto Sax","Tenor Sax","Baritone Sax","Oboe","English Horn","Bassoon","Clarinet",
            "Piccolo","Flute","Recorder","Pan Flute","Blown Bottle","Shakuhachi","Whistle","Ocarina",
            "Lead 1 (square)","Lead 2 (sawtooth)","Lead 3 (calliope)","Lead 4 (chiff)","Lead 5 (charang)","Lead 6 (voice)","Lead 7 (fifths)","Lead 8 (bass + lead)",
            "Pad 1 (new age)","Pad 2 (warm)","Pad 3 (polysynth)","Pad 4 (choir)","Pad 5 (bowed)","Pad 6 (metallic)","Pad 7 (halo)","Pad 8 (sweep)",
            "FX 1 (rain)","FX 2 (soundtrack)","FX 3 (crystal)","FX 4 (atmosphere)","FX 5 (brightness)","FX 6 (goblins)","FX 7 (echoes)","FX 8 (sci-fi)",
            "Sitar","Banjo","Shamisen","Koto","Kalimba","Bag Pipe","Fiddle","Shanai",
            "Tinkle Bell","Agogo","Steel Drums","Woodblock","Taiko Drum","Melodic Tom","Synth Drum","Reverse Cymbal",
            "Guitar Fret Noise","Breath Noise","Seashore","Bird Tweet","Telephone Ring","Helicopter","Applause","Gunshot"]
        inst_ctl=tk.Frame(inst_card,bg=surface); inst_ctl.pack(fill="x",padx=14,pady=14)
        inst_choice=tk.StringVar(value=f"{int(getattr(self.music_opts,'program',0)):03d} — {GM_NAMES[int(getattr(self.music_opts,'program',0))%128]}")
        inst_values=[f"{i:03d} — {name}" for i,name in enumerate(GM_NAMES)]
        tk.Label(inst_ctl,text="Program",bg=surface,fg=text_c).pack(side="left"); ttk.Combobox(inst_ctl,textvariable=inst_choice,values=inst_values,state="readonly",width=36).pack(side="left",padx=(6,14))
        inst_note=tk.StringVar(value="C4"); tk.Label(inst_ctl,text="Sample note",bg=surface,fg=text_c).pack(side="left"); ttk.Combobox(inst_ctl,textvariable=inst_note,values=[f"{n}{o}" for o in range(1,8) for n in NOTE_NAMES],state="readonly",width=7).pack(side="left",padx=6)
        inst_info=tk.StringVar(); tk.Label(inst_card,textvariable=inst_info,bg=muted,fg=text_c,anchor="w",padx=10,pady=8).pack(fill="x",padx=14,pady=(0,12))
        def _play_instrument():
            o=_snapshot_options(); o.program=int(inst_choice.get().split(" — ",1)[0]); midi=_midi_notes([inst_note.get()],o); inst_info.set(f"Program {o.program}: {GM_NAMES[o.program]}   |   Input {inst_note.get()}   |   After transpose/clamp: {' + '.join(midi_to_note(m) for m in midi)}"); _write_and_play([(midi,_pick_velocity(o,0.5))],f"program_{o.program}")
        ttk.Button(inst_card,text="Play instrument sample",command=_play_instrument).pack(anchor="w",padx=14,pady=(0,14))
        _play_instrument()

        # ---------- Dynamics & rhythm ----------
        tab_dyn = ttk.Frame(nb, style="MP.TFrame")
        nb.add(tab_dyn, text="Dynamics & Rhythm")
        dyn_card = tk.Frame(tab_dyn, bg=surface, highlightthickness=1, highlightbackground=border)
        dyn_card.pack(fill="both", expand=True, padx=8, pady=8)
        tk.Label(dyn_card, text="Hear frequency → velocity and timing exactly as configured",
                 bg=surface, fg=text_c, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(14, 8))

        dyn_freq = tk.DoubleVar(value=0.0)
        dyn_value = tk.StringVar()
        dyn_row = tk.Frame(dyn_card, bg=surface)
        dyn_row.pack(fill="x", padx=14, pady=8)
        tk.Label(dyn_row, text="Normalized frequency", bg=surface, fg=text_c).pack(side="left")
        ttk.Scale(dyn_row, from_=0.0, to=1.0, variable=dyn_freq, length=300).pack(side="left", padx=12)
        tk.Label(dyn_row, textvariable=dyn_value, bg=surface, fg=text_c, font=("Consolas", 10)).pack(side="left")

        def _dyn_update(*_):
            o = _snapshot_options()
            dyn_value.set(f"f={dyn_freq.get():.2f}  →  velocity={_pick_velocity(o, dyn_freq.get())}")
        dyn_freq.trace_add("write", _dyn_update)
        _dyn_update()

        rhythm_notes = ["C4", "E4", "G4", "C5"]
        tk.Label(dyn_card,
                 text="The rhythm preview emits four notes. Note duration and inter-note rest use the current Advanced Music Options.",
                 bg=surface, fg=subtext, wraplength=900, justify="left").pack(anchor="w", padx=14, pady=(10, 8))

        def _play_dyn():
            o = _snapshot_options()
            vel = _pick_velocity(o, dyn_freq.get())
            events = []
            for n in rhythm_notes:
                midi = _midi_notes([n], o)
                events.append((midi, vel))
            _write_and_play(events, "dynamics_rhythm")

        ttk.Button(dyn_card, text="Play dynamics & rhythm preview", command=_play_dyn).pack(anchor="w", padx=14, pady=8)
        tk.Label(dyn_card,
                 text="Note: MIDI Program selects the instrument patch. The exact timbre heard depends on the MIDI synthesizer/soundfont available on the system.",
                 bg=surface, fg=subtext, wraplength=900, justify="left").pack(anchor="w", padx=14, pady=(8, 14))

        # Refresh on tab changes so the summary follows live Advanced controls.
        nb.bind("<<NotebookTabChanged>>", lambda _e: (_refresh_settings_label(), _dyn_update()))

        def _close_playground():
            try:
                stop_midi()
            except Exception:
                pass
            try:
                self._music_playground_win = None
            except Exception:
                pass
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", _close_playground)
        win.bind("<Escape>", lambda _e: _close_playground())
        win.bind("<Control-r>", lambda _e: (_rebuild_residue_rows(), _build_path_preview(False)))



    def open_troubleshooting(self):
        text = '\n# Troubleshooting\n\n## No path is found\n- Confirm that source and sink residues were resolved to valid graph indices.\n- Check whether source and sink are in the same connected component.\n- Verify that the same intended cutoff was used when building the network.\n\n## A residue cannot be found\n- Check chain ID and residue number.\n- For large assemblies, also verify SEGNAME and insertion code when applicable.\n- Confirm that the residue exists in the selected reference structure.\n\n## Cross-structure endpoints look wrong\n- Confirm the selected Reference PDB.\n- Do not use Skip alignment when numbering or residue identity differs between structures.\n- Inspect the alignment/mapping Excel output for the projected source and sink residues.\n\n## Path Explorer, Backbone, Similarity, or Property Tracks are empty\n- Run K-shortest paths first.\n- Confirm that the selected structure and source/sink pair actually have stored paths.\n- Check the session log for unmapped or missing residue tokens.\n\n## 3D viewer does not open\n- Confirm that the colored/interactive structure output exists.\n- Verify the PySide6/WebEngine installation used by the packaged build.\n- Check `MUSIKALL_sessionlog.txt` for viewer-generation errors.\n\n## MIDI playback or generation fails\n- Confirm that KSP results exist.\n- Verify the selected mapping and pitch settings.\n- Check that the output music directory is writable and inspect the session log for dependency or playback errors.\n\n## Results differ from a previous MUSIKALL run\nCompare the exact:\n- input structure files,\n- MUSIKALL build/version,\n- cutoff,\n- reference structure,\n- mapping/Skip alignment setting,\n- source and sink selections,\n- K value.\n\nA change in node identity, residue correspondence, network construction, or edge costs can change KSP results even when the GUI inputs appear similar.\n'
        self._open_help_document(
            "MUSIKALL — Troubleshooting",
            "Practical checks for common mapping, path, visualization, and audio problems.",
            text,
            geometry="980x720",
        )



    def open_about_musikall(self):
        text = '\n# About MUSIKALL\n\nMUSIKALL is a biomolecular network-analysis and sonification application developed by the Kurkcuoglu Levitas Lab at Istanbul Technical University.\n\nIts current workflow integrates:\n- residue interaction network construction from structure-derived heavy-atom contacts,\n- weighted K-shortest-path analysis,\n- residue-frequency and path-exploration outputs,\n- co-occurrence backbone analysis,\n- path similarity analysis,\n- biochemical property tracks,\n- structure visualization,\n- deterministic MIDI sonification.\n\nMUSIKALL is intended to support comparative, structure-based analysis of candidate communication routes and their residue-level organization. Network-derived routes and sonification outputs should be interpreted within the assumptions of the selected structural model and analysis parameters.\n\nFor reproducibility, report the MUSIKALL version/build together with the cutoff, K value, source/sink definitions, reference structure, and mapping mode used in the analysis.\n\nMUSIKALL is distributed under the MIT License. See the official repository for license and citation information.\n'
        self._open_help_document(
            "About MUSIKALL",
            "Software scope, analytical capabilities, interpretation, and reproducibility notes.",
            text,
            geometry="900x660",
        )



    def show_cite(self):
        """Show a compact citation window with a direct link to the official repository."""
        win = tk.Toplevel(self)
        win.title("How to Cite MUSIKALL")
        win.geometry("520x220")
        win.minsize(480, 200)
        win.transient(self)

        bg = getattr(self, "_theme_bg", "#f7f7f8")
        fg = getattr(self, "_theme_fg", "#1f2937")
        accent = getattr(self, "_theme_accent", "#5b6ee1")
        win.configure(bg=bg)

        frame = tk.Frame(win, bg=bg)
        frame.pack(fill="both", expand=True, padx=28, pady=24)

        tk.Label(
            frame,
            text="How to Cite MUSIKALL",
            font=("Segoe UI", 16, "bold"),
            bg=bg,
            fg=fg,
        ).pack(anchor="w")

        tk.Label(
            frame,
            text="Please use the citation information provided in the official MUSIKALL repository.",
            font=("Segoe UI", 10),
            bg=bg,
            fg=fg,
            justify="left",
            wraplength=440,
        ).pack(anchor="w", pady=(10, 14))

        url = "https://github.com/zeynepguneryilmaz/MUSIKALL"
        link = tk.Label(
            frame,
            text=url,
            font=("Segoe UI", 10, "underline"),
            bg=bg,
            fg=accent,
            cursor="hand2",
        )
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda _e: webbrowser.open(url))

        win.bind("<Escape>", lambda _e: win.destroy())

    def show_Contact(self):
        """Display contact information in a polished, theme-aware card."""
        P = getattr(self, "current_palette", palettes["aqua"])
        win = tk.Toplevel(self)
        win.title("Contact MUSIKALL")
        win.geometry("640x410")
        win.resizable(False, False)
        win.configure(bg=P["bg"])
        win.transient(self)

        card = tk.Frame(win, bg=P["surface"], highlightthickness=1, highlightbackground=P["border"])
        card.pack(fill="both", expand=True, padx=24, pady=24)

        tk.Label(card, text="Contact MUSIKALL", font=("Segoe UI", 20, "bold"),
                 bg=P["surface"], fg=P["text"], anchor="w").pack(fill="x", padx=26, pady=(24, 4))
        tk.Label(card, text="Kurkcuoglu Levitas Lab • Istanbul Technical University",
                 font=("Segoe UI", 10), bg=P["surface"], fg=P["subtext"], anchor="w").pack(fill="x", padx=26)

        tk.Frame(card, height=4, bg=P["accent"]).pack(fill="x", pady=(18, 20))

        tk.Label(card, text="Email", font=("Segoe UI", 9, "bold"),
                 bg=P["surface"], fg=P["subtext"], anchor="w").pack(fill="x", padx=26)

        email = "ozdezeynepg@gmail.com"
        email_box = tk.Entry(card, font=("Consolas", 11), relief="flat",
                             readonlybackground=P["muted"], fg=P["text"], justify="left")
        email_box.insert(0, email)
        email_box.config(state="readonly")
        email_box.pack(fill="x", padx=26, pady=(6, 18), ipady=8)

        tk.Label(card,
                 text="For questions about the software, analysis workflow, or reproducibility, include the MUSIKALL version/build and a concise description of the issue.",
                 wraplength=540, justify="left", font=("Segoe UI", 10),
                 bg=P["surface"], fg=P["text"], anchor="w").pack(fill="x", padx=26)

        buttons = tk.Frame(card, bg=P["surface"])
        buttons.pack(fill="x", padx=26, pady=(22, 24))

        def copy_email():
            self.clipboard_clear()
            self.clipboard_append(email)
            self.update()
            messagebox.showinfo("Copied", "Email address copied to the clipboard.")

        ttk.Button(buttons, text="Copy email", command=copy_email, style="Accent.TButton").pack(side="left")
        ttk.Button(buttons, text="Close", command=win.destroy).pack(side="right")
        win.bind("<Escape>", lambda _e: win.destroy())


    def _install_text_placeholder(self, widget, placeholder):
        """Show example text in a Text widget without treating it as user input."""
        normal_fg = self.current_palette.get("text", "#1E293B")
        placeholder_fg = self.current_palette.get("subtext", "#64748B")
        widget._musikall_placeholder = placeholder
        widget._musikall_has_placeholder = False

        def show_placeholder():
            if not widget.get("1.0", "end-1c").strip():
                widget.delete("1.0", "end")
                widget.insert("1.0", placeholder)
                widget.configure(fg=placeholder_fg)
                widget._musikall_has_placeholder = True

        def on_focus_in(_event=None):
            if getattr(widget, "_musikall_has_placeholder", False):
                widget.delete("1.0", "end")
                widget.configure(fg=normal_fg)
                widget._musikall_has_placeholder = False

        def on_focus_out(_event=None):
            if not widget.get("1.0", "end-1c").strip():
                show_placeholder()

        widget.bind("<FocusIn>", on_focus_in, add="+")
        widget.bind("<FocusOut>", on_focus_out, add="+")
        show_placeholder()

    @staticmethod
    def _text_input_value(widget):
        """Return Text-widget content while excluding the MUSIKALL placeholder."""
        if getattr(widget, "_musikall_has_placeholder", False):
            return ""
        return widget.get("1.0", "end-1c").strip()

    def show_main_interface(self):
        if not getattr(self, "_backend_ready", False):
            if getattr(self, "_backend_error", None):
                messagebox.showerror("MUSIKALL", f"Analysis engine could not be loaded:\n{self._backend_error}")
            return
        self.welcome_frame.destroy()

        # Main analysis workspace. Functionality and callback wiring are unchanged;
        # this layout only improves visual hierarchy and spacing.
        bg = getattr(self, "current_palette", {}).get("bg", "#FFFFFF")
        P = self.current_palette

        self.main_pw = tk.PanedWindow(
            self, orient="horizontal", bg=bg, sashrelief="flat", bd=0,
            sashwidth=8, sashpad=2
        )
        self.main_pw.pack(fill="both", expand=True, padx=16, pady=(12, 8))

        # Fixed analysis column. The compact layout keeps all current sections visible
        # without an additional scrollbar.
        self.left_col = tk.Frame(self.main_pw, bg=bg)
        self.right_col = tk.Frame(self.main_pw, width=360, bg=bg)
        self.main_pw.add(self.left_col, stretch="always", minsize=660)
        self.main_pw.add(self.right_col, minsize=330)

        # ---------- 1. Structure & Network ----------
        section1 = ttk.LabelFrame(
            self.left_col, text="1  Structure & Network",
            style="Card.TLabelframe", padding=(10, 6)
        )
        section1.pack(fill="x", padx=4, pady=(0, 4))
        section1.columnconfigure(1, weight=1)

        ttk.Label(
            section1,
            text="Create the analysis workspace, add PDB structures, and construct residue-level contact networks.",
            style="SectionHint.TLabel"
        ).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 5))

        ttk.Label(section1, text="Job name", style="FieldLabel.TLabel").grid(
            row=1, column=0, padx=(0, 10), pady=3, sticky="w"
        )
        self.jobname_entry = tk.Entry(section1, width=30)
        self.jobname_entry.grid(row=1, column=1, padx=(0, 10), pady=3, sticky="ew")
        ttk.Button(section1, text="Create Job", command=self.create_job, style="Accent.TButton").grid(
            row=1, column=2, padx=(0, 8), pady=3
        )
        ttk.Button(section1, text="Upload PDBs", command=self.upload_pdb_files).grid(
            row=1, column=3, padx=(0, 8), pady=3
        )
        ttk.Button(section1, text="⟲", width=2, command=self.reset_section1).grid(
            row=1, column=4, padx=(2, 0), pady=3
        )

        ttk.Label(section1, text="Contact cutoff", style="FieldLabel.TLabel").grid(
            row=3, column=0, padx=(0, 10), pady=3, sticky="w"
        )
        cutoff_wrap = ttk.Frame(section1)
        cutoff_wrap.grid(row=3, column=1, sticky="w", pady=3)
        self.cutoff_entry = tk.Entry(cutoff_wrap, width=8)
        self.cutoff_entry.pack(side="left")
        self.cutoff_entry.insert(0, "4.5")
        ttk.Label(cutoff_wrap, text="Å", style="Sub.TLabel").pack(side="left", padx=(5, 0))
        ttk.Button(
            section1, text="Calculate Adjacency Matrix",
            command=self.run_adj_matrix, style="Accent.TButton"
        ).grid(row=3, column=2, columnspan=2, padx=(0, 8), pady=3, sticky="w")

        # ---------- 2. K-Shortest Paths ----------
        section3 = ttk.LabelFrame(
            self.left_col, text="2  K-Shortest Paths",
            style="Card.TLabelframe", padding=(10, 6)
        )
        section3.pack(fill="x", padx=4, pady=(0, 4))
        section3.columnconfigure(0, weight=1)

        hdr = ttk.Frame(section3)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        hdr.columnconfigure(0, weight=1)
        ttk.Label(
            hdr,
            text="Define endpoints on a reference structure, map them when needed, and calculate alternative low-cost routes.",
            style="SectionHint.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(hdr, text="⟲", width=2, command=self.reset_section3).grid(row=0, column=1, sticky="e")

        inputs = ttk.Frame(section3)
        inputs.grid(row=1, column=0, sticky="ew")
        inputs.columnconfigure(1, weight=1)

        ttk.Label(inputs, text="Reference PDB", style="FieldLabel.TLabel").grid(
            row=0, column=0, padx=(0, 10), pady=3, sticky="w"
        )
        self.ref_pdb_entry = getattr(self, "ref_pdb_entry", tk.Entry(inputs, width=40))
        self.ref_pdb_entry.grid(row=0, column=1, padx=(0, 8), pady=3, sticky="ew")
        ttk.Button(inputs, text="Select", command=self.select_reference_pdb).grid(
            row=0, column=2, padx=(0, 10), pady=3
        )
        self.skip_alignment_var = getattr(self, "skip_alignment_var", tk.BooleanVar(value=False))
        ttk.Checkbutton(inputs, text="Skip alignment", variable=self.skip_alignment_var).grid(
            row=0, column=3, pady=3, sticky="w"
        )


        ttk.Label(inputs, text="Source residues", style="FieldLabel.TLabel").grid(
            row=2, column=0, padx=(0, 10), pady=3, sticky="nw"
        )
        self.source_res_entry = getattr(self, "source_res_entry", tk.Text(inputs, height=2, width=40))
        self.source_res_entry.configure(relief="solid", bd=1, padx=7, pady=3, wrap="word")
        self.source_res_entry.grid(row=2, column=1, padx=(0, 8), pady=3, sticky="ew")
        self._install_text_placeholder(
            self.source_res_entry,
            "Example: A,150-153; B,45  or  PROT:A,150-153"
        )
        info_btn_src = tk.Label(
            inputs, text="ⓘ", fg=self.current_palette["accent"],
            cursor="question_arrow", bg=self.current_palette["bg"], font=("Segoe UI", 10)
        )
        info_btn_src.grid(row=2, column=2, sticky="nw", padx=(0, 8), pady=(7, 0))
        Tooltip(
            info_btn_src,
            "Input format:\n"
            "- CHAIN,start-end or CHAIN,res1,res2,...\n"
            "  Example: DA,1047-1050 or DA,1047,1050,1100\n\n"
            "- With SEGNAME: SEGNAME:CHAIN,start-end\n"
            "  Example: MC:DA,1047-1050\n\n"
            "- Separate multiple entries with ';' or new lines."
        )

        ttk.Label(inputs, text="Sink residues", style="FieldLabel.TLabel").grid(
            row=3, column=0, padx=(0, 10), pady=3, sticky="nw"
        )
        self.sink_res_entry = getattr(self, "sink_res_entry", tk.Text(inputs, height=2, width=40))
        self.sink_res_entry.configure(relief="solid", bd=1, padx=7, pady=3, wrap="word")
        self.sink_res_entry.grid(row=3, column=1, padx=(0, 8), pady=3, sticky="ew")
        self._install_text_placeholder(
            self.sink_res_entry,
            "Example: A,268-270; B,113  or  RNA:C,1490-1493"
        )
        info_btn_sink = tk.Label(
            inputs, text="ⓘ", fg=self.current_palette["accent"],
            cursor="question_arrow", bg=self.current_palette["bg"], font=("Segoe UI", 10)
        )
        info_btn_sink.grid(row=3, column=2, sticky="nw", padx=(0, 8), pady=(7, 0))
        Tooltip(
            info_btn_sink,
            "Input format:\n"
            "- CHAIN,start-end or CHAIN,res1,res2,...\n"
            "  Example: DA,2000-2010 or DA,2000,2005,2010\n\n"
            "- With SEGNAME: SEGNAME:CHAIN,start-end\n"
            "  Example: MC:DA,2000-2010\n\n"
            "- Separate multiple entries with ';' or new lines."
        )

        actions = ttk.Frame(section3)
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure(1, weight=1)

        primary = ttk.Frame(actions)
        primary.grid(row=0, column=0, sticky="w")
        ttk.Label(primary, text="K", style="FieldLabel.TLabel").pack(side="left", padx=(0, 6))
        try:
            self.k_entry.destroy()
        except Exception:
            pass
        self.k_entry = tk.Spinbox(primary, from_=1, to=999, width=7)
        self.k_entry.delete(0, "end")
        self.k_entry.insert(0, "20")
        self.k_entry.pack(side="left", padx=(0, 10))
        _calc_cmd = getattr(self, "_on_ksp_calculate", None) or self.calculate_shortest_paths
        ttk.Button(
            primary, text="Calculate Shortest Paths",
            command=_calc_cmd, style="Accent.TButton"
        ).pack(side="left")

        analysis_tools = ttk.Frame(actions)
        analysis_tools.grid(row=0, column=1, sticky="e")
        ttk.Button(analysis_tools, text="Path Explorer", command=self.open_path_explorer).pack(side="left", padx=(6, 0))
        ttk.Button(analysis_tools, text="Cooccurrence Backbone", command=self.open_cooccurrence_backbone).pack(side="left", padx=(6, 0))
        ttk.Button(analysis_tools, text="Path Similarity", command=self.open_path_similarity).pack(side="left", padx=(6, 0))

        self.ksp_prog = getattr(self, "ksp_prog", ttk.Progressbar(section3, mode="indeterminate"))
        self.ksp_prog.grid(row=4, column=0, sticky="ew", pady=(5, 1))
        self.ksp_prog.grid_remove()
        self.ksp_status = getattr(self, "ksp_status", ttk.Label(section3, style="Sub.TLabel", text=""))
        self.ksp_status.grid(row=5, column=0, sticky="w", pady=(0, 2))

        # ---------- 3. Property Tracks ----------
        section_prop = ttk.LabelFrame(
            self.left_col, text="3  Property Tracks",
            style="Card.TLabelframe", padding=(10, 6)
        )
        section_prop.pack(fill="x", padx=4, pady=(0, 5))
        section_prop.columnconfigure(0, weight=1)

        ttk.Label(
            section_prop,
            text="Relate residue frequency scores to the selected physicochemical classifications.",
            style="SectionHint.TLabel"
        ).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 4))

        self.chk_hydro_var = tk.BooleanVar()
        self.chk_charge_var = tk.BooleanVar()
        self.chk_aroma_var = tk.BooleanVar()
        self.chk_polarity_var = tk.BooleanVar()

        props = ttk.Frame(section_prop)
        props.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(0, 4))
        for idx, (label, var) in enumerate([
            ("Hydrophobicity", self.chk_hydro_var),
            ("Charge", self.chk_charge_var),
            ("Aromaticity", self.chk_aroma_var),
            ("Polarity", self.chk_polarity_var),
        ]):
            ttk.Checkbutton(props, text=label, variable=var).pack(side="left", padx=(0 if idx == 0 else 14, 0))

        opts = ttk.Frame(section_prop)
        opts.grid(row=2, column=0, columnspan=5, sticky="ew")
        ttk.Label(opts, text="Minimum FreqScore", style="FieldLabel.TLabel").pack(side="left", padx=(0, 6))
        self.min_score_var = tk.IntVar(value=1)
        ttk.Spinbox(opts, from_=0, to=10, textvariable=self.min_score_var, width=5).pack(side="left", padx=(0, 16))
        self.only_figures_var = tk.BooleanVar()
        ttk.Checkbutton(
            opts, text="Only figures (use existing Excel)", variable=self.only_figures_var
        ).pack(side="left", padx=(0, 16))
        ttk.Button(
            opts, text="Generate Tracks", command=self._run_property_tracks,
            style="Accent.TButton"
        ).pack(side="right")

        # ---------- 4. Visualization ----------
        section5 = ttk.LabelFrame(
            self.left_col, text="4  Visualization",
            style="Card.TLabelframe", padding=(10, 6)
        )
        section5.pack(fill="x", padx=4, pady=(0, 4))
        section5.columnconfigure(0, weight=1)

        ttk.Label(
            section5,
            text="Export frequency-annotated structures or inspect them in the built-in interactive 3D viewer.",
            style="SectionHint.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        viz_actions = ttk.Frame(section5)
        viz_actions.grid(row=1, column=0, sticky="w")
        ttk.Button(
            viz_actions, text="Save PDBs", command=self.save_colored_pdbs,
            style="Accent.TButton"
        ).pack(side="left", padx=(0, 8))
        ttk.Button(viz_actions, text="Show 3D Structures", command=self.show_3d_structures).pack(side="left", padx=(0, 8))
        ttk.Button(viz_actions, text="⟲", width=2, command=self.reset_section5).pack(side="left")

        # ---------- Right: Sonification ----------
        self.build_music_sidebar(self.right_col)

        # ---------- Session log ----------
        log_card = ttk.LabelFrame(self, text="Session Log", style="Card.TLabelframe", padding=(6, 4))
        log_card.pack(fill="both", padx=16, pady=(0, 14))
        self.output_text = tk.Text(
            log_card, height=6, width=100, wrap="word", relief="flat", bd=0,
            font=("Consolas", 9), padx=11, pady=9,
            bg=P["surface"], fg=P["text"], insertbackground=P["text"]
        )
        log_scroll = ttk.Scrollbar(log_card, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y", padx=(0, 3), pady=3)
        self.output_text.pack(side="left", fill="both", expand=True, padx=(3, 0), pady=3)

    def _run_property_tracks(self):
        import os
        import pandas as pd
        from tkinter import messagebox

        from MUSIKALL_functions1 import (
            build_property_matrix_for_pdb,
            plot_property_tracks_single,
            plot_property_tracks_multi,
            export_property_excel_aligned,
            save_property_legend_png,
            _base_key
        )

        # -------------------------------------------------
        # 1) Selected property dimensions
        # -------------------------------------------------
        dims = []
        if self.chk_hydro_var.get():
            dims.append("hydrophobicity")
        if self.chk_charge_var.get():
            dims.append("charge")
        if self.chk_aroma_var.get():
            dims.append("aromaticity")
        if self.chk_polarity_var.get():
            dims.append("polarity")

        if not dims:
            self.log_output("⚠ Please select at least one property dimension.\n")
            return

        # -------------------------------------------------
        # 2) Resolve job directory
        # -------------------------------------------------
        job_dir = getattr(self, "current_job_folder", None)
        if not job_dir:
            jobname = getattr(self, "jobname", None)
            if not jobname:
                messagebox.showerror("Error", "Please create a job first in Section 1.")
                return
            job_dir = create_job_folder(jobname)
            self.current_job_folder = job_dir

        os.makedirs(job_dir, exist_ok=True)

        # -------------------------------------------------
        # 3) Parameters
        # -------------------------------------------------
        try:
            min_score = int(self.min_score_var.get())
        except Exception:
            min_score = 1

        only_figs = bool(self.only_figures_var.get())
        excel_path = os.path.join(job_dir, "property_tracks_all.xlsx")

        # -------------------------------------------------
        # 4) Build PDB list robustly
        # -------------------------------------------------
        all_norm = getattr(self, "all_normalized_frequencies", {}) or {}
        pdb_info_dict = getattr(self, "pdb_info_dict", {}) or {}

        pdb_list_from_freq = [_base_key(k) for k in all_norm.keys()]
        pdb_list_from_info = [_base_key(k) for k in pdb_info_dict.keys()]

        pdb_list = sorted(set(pdb_list_from_freq + pdb_list_from_info))

        if not pdb_list and not only_figs:
            self.log_output("⚠ No calculated frequency / PDB information was found yet.\n")
            return

        self.log_output(
            f"🧪 Running property tracks for {len(pdb_list)} structures "
            f"(dims={', '.join(dims)}, min_score={min_score}, only_figures={only_figs})\n"
        )

        # -------------------------------------------------
        # 5) Only-figures mode: load existing Excel
        # -------------------------------------------------
        if only_figs:
            if not os.path.exists(excel_path):
                self.log_output("⚠ 'Only figures' was selected, but property_tracks_all.xlsx could not be found.\n")
                return

            try:
                df_all = pd.read_excel(excel_path)
            except Exception as e:
                self.log_output(f"⚠ Existing Excel could not be read:\n   • {e}\n")
                return

            if df_all.empty:
                self.log_output("⚠ Existing property_tracks_all.xlsx is empty.\n")
                return

            self.log_output(f"📂 Existing Excel loaded:\n   • {excel_path}\n")

        # -------------------------------------------------
        # 6) Full build mode: calculate property tables
        # -------------------------------------------------
        else:
            all_dfs = []

            for pdb in pdb_list:
                try:
                    freq_map = self._freq_map_for_pdb(pdb)
                except Exception as e:
                    self.log_output(f"⚠ Frequency map could not be resolved for {pdb}: {e}\n")
                    freq_map = {}

                canon = _base_key(pdb)
                pdb_data = (pdb_info_dict.get(canon, {}) or {})
                rcm = pdb_data.get("residue_chain_map", {}) or {}

                n_chains = len(rcm) if isinstance(rcm, dict) else 0
                n_res = sum(len(v) for v in rcm.values()) if isinstance(rcm, dict) else 0
                freq_n = len(freq_map) if isinstance(freq_map, dict) else 0

                self.log_output(
                    f"[DEBUG] PropertyTracks | pdb={pdb} | canon={canon} | "
                    f"freq_map_n={freq_n} | chains={n_chains} | residues={n_res}\n"
                )

                if not rcm:
                    self.log_output(f"⚠ residue_chain_map missing for {pdb} (canon={canon}). Skipped.\n")
                    continue

                try:
                    df = build_property_matrix_for_pdb(
                        canon,
                        freq_map,
                        pdb_info_dict,
                        dimensions=dims
                    )
                except Exception as e:
                    self.log_output(f"⚠ Property matrix build failed for {pdb}: {e}\n")
                    continue

                self.log_output(f"[DEBUG] rows_returned={len(df)} for {canon}\n")

                if df is None or df.empty:
                    self.log_output(f"ℹ No property rows generated for {canon}.\n")
                    continue

                # Add the PDB column if it is missing
                if "PDB" not in df.columns:
                    df["PDB"] = canon

                all_dfs.append(df)

            if not all_dfs:
                self.log_output("⚠ No residue with a frequency was found.\n")
                self.log_output("⚠ Property tracks table could not be created because all per-PDB tables were empty.\n")
                return

            try:
                df_all = pd.concat(all_dfs, ignore_index=True)
            except Exception as e:
                self.log_output(f"⚠ Could not concatenate property tables: {e}\n")
                return

            if df_all.empty:
                self.log_output("⚠ Combined property dataframe is empty.\n")
                return

            try:
                ref_pdb_raw = self.ref_pdb_entry.get().strip() if hasattr(self, "ref_pdb_entry") else ""
                ref_pdb = _base_key(ref_pdb_raw) if ref_pdb_raw else None
            except Exception:
                ref_pdb = None

            try:
                export_property_excel_aligned(df_all, excel_path, reference_pdb=ref_pdb)
            except Exception as e:
                self.log_output(f"⚠ Property Excel export failed: {e}\n")
                return

            self.log_output(f"📁 Property table saved to:\n   • {excel_path}\n")

        # -------------------------------------------------
        # 7) Validate required columns before plotting
        # -------------------------------------------------
        required_cols = {"PDB", "FreqScore"}
        missing_cols = required_cols - set(df_all.columns)
        if missing_cols:
            self.log_output(
                f"⚠ Required columns are missing in property dataframe: {', '.join(sorted(missing_cols))}\n"
            )
            return

        # -------------------------------------------------
        # Shared legend: save once for all property-track figures
        # -------------------------------------------------
        legend_png = os.path.join(job_dir, "PROPERTY_TRACKS__LEGEND.png")

        try:
            save_property_legend_png(
                legend_png,
                dimensions=dims,
                ncols=4
            )
            self.log_output(
                f"🎨 Shared property-track legend saved:\n"
                f"   • {legend_png}\n"
            )
        except Exception as e:
            self.log_output(f"⚠ Property-track legend generation failed: {e}\n")

        # -------------------------------------------------
        # 8) Per-structure plots
        # -------------------------------------------------
        for pdb in sorted(df_all["PDB"].dropna().astype(str).unique()):
            df_p = df_all[df_all["PDB"].astype(str) == str(pdb)].copy()
            df_plot = df_p[df_p["FreqScore"] >= min_score].copy()

            if df_plot.empty:
                self.log_output(f"ℹ No residue with FreqScore >= {min_score} for {pdb}; figure was not drawn.\n")
                continue

            pdb_folder = os.path.join(job_dir, str(pdb))
            os.makedirs(pdb_folder, exist_ok=True)

            base_png = os.path.join(pdb_folder, f"{pdb}_property_tracks_score{min_score}.png")
            out_png = _unique_filename(base_png)

            try:
                plot_property_tracks_single(df_plot, dims, out_png)
                self.log_output(
                    f"📊 Property track figure saved for {pdb}:\n"
                    f"   • {out_png}\n"
                )
            except Exception as e:
                self.log_output(f"⚠ Figure generation failed for {pdb}: {e}\n")

        # -------------------------------------------------
        # 9) Combined plot across all structures
        # -------------------------------------------------
        df_filtered_all = df_all[df_all["FreqScore"] >= min_score].copy()

        if df_filtered_all.empty:
            self.log_output(
                f"ℹ No residues with FreqScore >= {min_score} were found in any structure; combined figure was not drawn.\n"
            )
            return

        try:
            ref_pdb_raw = self.ref_pdb_entry.get().strip() if hasattr(self, "ref_pdb_entry") else ""
            self.reference_pdb_key = _base_key(ref_pdb_raw) if ref_pdb_raw else None
        except Exception:
            self.reference_pdb_key = None

        base_png_all = os.path.join(job_dir, f"ALL_property_tracks_score{min_score}.png")
        out_png_all = _unique_filename(base_png_all)

        try:
            plot_property_tracks_multi(
                df_filtered_all,
                dims,
                out_png_all,
                min_score=min_score,
                reference_pdb=self.reference_pdb_key,
                pdb_info_dict=pdb_info_dict,
                drop_all_missing=True,
                drop_all_below=True,
                x_label_style="seg|chain|resid",
                max_xticks=60
            )

            self.log_output(
                f"🧩 All structures combined property track saved:\n"
                f"   • {out_png_all}\n"
            )
        except Exception as e:
            self.log_output(f"⚠ Combined property track figure generation failed: {e}\n")

    def reset_section1(self):
        self.jobname_entry.delete(0, tk.END)
        self.cutoff_entry.delete(0, tk.END)
        self.cutoff_entry.insert(0, "4.5")
        self.log_output("♻️ Section 1 reset.\n")

    def reset_section2(self):
        self.ref_pdb_entry.delete(0, tk.END)
        self.source_res_entry.delete("1.0", "end")
        self.sink_res_entry.delete("1.0", "end")
        self.skip_alignment_var.set(False)
        if hasattr(self, "reference_residues"): self.reference_residues = {}
        self.log_output("♻️ Section 2 reset.\n")

    def reset_section3(self):
        """Reset the complete K-shortest-path section without touching loaded structures or matrices.

        This deliberately invalidates all endpoint-dependent in-memory state so the
        next calculation can only use the newly entered reference/source/sink values.
        """
        # Visible KSP inputs
        self.ref_pdb_entry.delete(0, tk.END)

        for widget in (self.source_res_entry, self.sink_res_entry):
            widget.delete("1.0", "end")
            widget.configure(fg=self.current_palette.get("text", "#1E293B"))
            widget._musikall_has_placeholder = False
            placeholder = getattr(widget, "_musikall_placeholder", "")
            if placeholder:
                widget.insert("1.0", placeholder)
                widget.configure(fg=self.current_palette.get("subtext", "#64748B"))
                widget._musikall_has_placeholder = True

        self.skip_alignment_var.set(False)
        self.k_entry.delete(0, tk.END)
        self.k_entry.insert(0, "20")

        # Cancel any queued continuation from an older mapping request.
        self._pending_ksp = None

        # Clear reference/mapping state.
        self.reference_residues = []
        self.pdb_residue_dict = {}

        # Most importantly, remove previously resolved source/sink indices from
        # every loaded structure while preserving PDB data and adj/edge matrices.
        for _pdb_id, _pdata in (getattr(self, "pdb_info_dict", {}) or {}).items():
            if isinstance(_pdata, dict):
                _pdata["residue_dict"] = {
                    "source_residues": [],
                    "sink_residues": [],
                }

        # Clear all endpoint/path-derived products and caches.
        self.paths_dict = {}
        self.paths_dict_2 = {}
        self.all_normalized_frequencies = {}
        self.per_pdb_files = []
        self.overall_file = None
        self.results_files = ()

        # Invalidate the old mapping signature and endpoint-related session fields.
        if not hasattr(self, "state") or not isinstance(self.state, dict):
            self.state = {}
        for _key in (
            "mapping_signature",
            "reference_pdb",
            "source_residues_raw",
            "sink_residues_raw",
            "k",
            "per_pdb_files",
            "overall_file",
        ):
            self.state.pop(_key, None)

        self.log_output(
            "♻️ K-shortest-path section reset: reference, source/sink mapping, "
            "old paths, and frequency caches cleared. Loaded structures and "
            "adjacency matrices were preserved.\n"
        )

    import os, re, tkinter as tk
    from tkinter import ttk, messagebox

    # --- PATH EXPLORER ----------------------------------------------------------
    def open_path_explorer(self):
        """Open a window for browsing paths after K-shortest-path calculation."""
        if not getattr(self, "paths_dict_2", None):
            messagebox.showerror("Error", "Please calculate K shortest paths first.")
            return
        if not getattr(self, "pdb_info_dict", None):
            self.log_output("⚠ pdb_info_dict is missing  index→residue matching may fail.\n")

        import tkinter as tk
        from tkinter import ttk

        win = tk.Toplevel(self)
        win.title("Path Explorer")
        win.geometry("980x640")

        P = getattr(self, "current_palette", {"bg": "#ffffff", "text": "#000", "subtext": "#666"})
        try:
            win.configure(bg=P["bg"])
        except Exception:
            pass

        style = ttk.Style(win)
        style.configure("TFrame", background=P.get("bg", "#fff"))
        style.configure("TLabel", background=P.get("bg", "#fff"), foreground=P.get("text", "#000"))
        style.configure("Treeview", background=P.get("surface", "#fff"),
                        fieldbackground=P.get("surface", "#fff"), foreground=P.get("text", "#000"))
        style.configure("Treeview.Heading", background=P.get("muted", "#eaeaea"),
                        foreground=P.get("text", "#000"))

        info = tk.Label(
            win,
            text=("Tip: When 'Show All Paths' is unchecked, only the selected Source→Sink paths are listed.  "
                  "The Find box filters the LISTED rows.  "
                  "Search examples: A,123 | A 123 | A:123 | 123"),
            fg=P.get("subtext", "#555"), bg=P.get("bg", "#fff"),
            anchor="w", justify="left", wraplength=920
        )
        info.pack(fill="x", padx=10, pady=(8, 0))

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)

        for pdb_key in sorted(self.paths_dict_2.keys(), key=lambda s: str(s).lower()):
            try:
                self._build_path_explorer_tab(notebook, pdb_key, parent_win=win)
            except Exception as e:
                self.log_output(f"⚠️ Path explorer tab failed for {pdb_key}: {e}\n")

        self._path_explorer_windows = getattr(self, "_path_explorer_windows", [])
        self._path_explorer_windows.append(win)


    # ---------------- helpers ----------------

    def _canon_node(self, s: str) -> tuple[str, str]:
        """
        Matching identity for Path Explorer.

        CHAIN:RES       -> ("CHAIN", "RES")
        SEG:CHAIN:RES   -> ("SEG:CHAIN", "RES")
        CHAIN,RES       -> ("CHAIN", "RES")
        SEG:CHAIN,RES   -> ("SEG:CHAIN", "RES")
        """
        import re

        if not s:
            return ("", "")

        t = str(s).strip()
        t = t.replace(";", ",")
        t = re.sub(r"\s+", "", t)

        # GUI input/display form:
        # C,530
        # EB:C,530
        if "," in t:
            left, rn = t.rsplit(",", 1)
            return (left.upper(), rn)

        # Internal token:
        # C:530
        # EB:C:530
        if ":" in t:
            parts = [p for p in t.split(":") if p != ""]

            if len(parts) == 2:
                return (parts[0].upper(), parts[1])

            if len(parts) >= 3:
                segchain = ":".join(parts[:-1]).upper()
                rn = parts[-1]
                return (segchain, rn)

        return ("", t)

    def _node_matches(self, want: tuple[str, str], got: tuple[str, str]) -> bool:
        """Match residues when the chain is compatible and the residue identifier matches exactly or numerically."""
        wch, wrn = want
        gch, grn = got
        if wch and (wch != gch): return False
        if wrn == grn: return True
        wnum = "".join(filter(str.isdigit, wrn))
        gnum = "".join(filter(str.isdigit, grn))
        return (wnum != "" and wnum == gnum)

    def _canon_pdb_key(self, pdb_key):
        from MUSIKALL_functions1 import _base_only, _base_key

        if not isinstance(self.paths_dict_2, dict):
            return None

        target_base = _base_only(pdb_key)
        target_canon = _base_key(target_base)

        if pdb_key in self.paths_dict_2:
            return pdb_key

        for k in self.paths_dict_2.keys():
            kb = _base_only(k)
            if _base_key(kb) == target_canon:
                return k

        return None

    def _index_to_node_map(self, pdb_id):
        """
        Return mapping: graph_index -> residue token
        Token: 'CHAIN:RES' veya 'SEG:CHAIN:RES'.
        Priority: pdb_data['node_index_map'] (SEGNAME-aware and consistent with matrix indices)
        """
        pdb_data = getattr(self, "pdb_info_dict", {}).get(pdb_id, {}) or {}

        # 1) Preferred source: node_index_map generated by run_adj_matrix()
        nim = pdb_data.get("node_index_map")
        if isinstance(nim, dict) and len(nim) > 0:
            out = {}
            for k, v in nim.items():
                try:
                    out[int(k)] = str(v)
                except Exception:
                    # Skip keys that cannot be converted to integer indices
                    continue
            if out:
                return out

        # ---------------------------------------------------------------------
        # 2) Fallback: reconstruct tokens from residue_dict
        # ---------------------------------------------------------------------
        m = {}
        rd = (pdb_data or {}).get("residue_dict", {})

        def _put(r):
            try:
                idx = r.get("index")
                ch = str(r.get("chain") or "").strip().upper()
                rn = str(r.get("residue_num") or "").strip()
                ic = str(r.get("insertion_code") or "").strip()
                seg = str(r.get("segname") or "").strip()

                if idx is None or not rn:
                    return

                token = f"{ch}:{rn}{ic}"
                if seg:
                    token = f"{seg}:{token}"

                m[int(idx)] = token
            except Exception:
                pass

        for key in ("all_residues", "residues", "nodes"):
            arr = rd.get(key)
            if isinstance(arr, list):
                for r in arr:
                    _put(r)

        for key in ("source_residues", "sink_residues"):
            arr = rd.get(key)
            if isinstance(arr, list):
                for r in arr:
                    try:
                        idx = int(r.get("index"))
                    except Exception:
                        idx = None
                    if idx is not None and idx not in m:
                        _put(r)

        return m

    def _iter_paths_for_pdb(self, pdb_key):
        """
        Iterate over the output structure produced by calculate_shortest_paths().
        yield: (list[str], cost|None)
        """
        true_key = self._canon_pdb_key(pdb_key)
        root = (self.paths_dict_2.get(true_key) or {}) if true_key else {}

        pdb_id_for_map = true_key if true_key is not None else pdb_key
        idx2node = self._index_to_node_map(pdb_id_for_map)

        def _emit(paths, costs):
            paths = list(paths or [])
            costs = list(costs or [])
            for i, p in enumerate(paths):
                norm_p = []
                for node in (p or []):
                    if isinstance(node, (int, float)) or str(node).isdigit():
                        try:
                            norm_p.append(idx2node.get(int(node), str(node)))
                        except:
                            norm_p.append(str(node))
                    else:
                        norm_p.append(str(node))
                c = costs[i] if i < len(costs) else None
                yield norm_p, c

        # Schema: { "s -> t": {"paths":[...], "costs":[...]} , ... }
        if isinstance(root, dict):
            for bundle in root.values():
                if isinstance(bundle, dict) and "paths" in bundle:
                    yield from _emit(bundle.get("paths"), bundle.get("costs"))

    def _unique_residues_from_pdb_paths(self, pdb_key):
        seen, disp = set(), []
        for path, _ in self._iter_paths_for_pdb(pdb_key):
            for node in (path or []):
                if node in seen:
                    continue
                seen.add(node)

                seg, ch, rn = self._split_token(node)

                # Combobox display: "SEG,CHAIN,RES" when SEGNAME exists, otherwise "CHAIN,RES"
                if seg:
                    disp.append((seg, ch, rn))
                else:
                    disp.append(("", ch, rn))

        def _sort_key(x):
            seg, ch, rn = x
            try:
                num = int("".join(filter(str.isdigit, rn)) or 0)
            except Exception:
                num = 0
            return (seg, ch, num, rn)

        out = []
        for seg, ch, rn in sorted(disp, key=_sort_key):
            if seg:
                out.append(f"{seg},{ch},{rn}")
            else:
                out.append(f"{ch},{rn}" if ch else rn)
        return out

    def _index_matches_residue(self, pdb_id, idx, want_residue: tuple[str, str]) -> bool:
        rd = getattr(self, "pdb_info_dict", {}).get(pdb_id, {}).get("residue_dict", {})
        for key in ("all_residues", "residues", "nodes", "source_residues", "sink_residues"):
            arr = rd.get(key)
            if isinstance(arr, list):
                for r in arr:
                    try:
                        if int(r.get("index")) == int(idx):
                            ch = str(r.get("chain") or "").strip().upper()
                            rn = str(r.get("residue_num") or "").strip()
                            ic = str(r.get("insertion_code") or "").strip()
                            return self._node_matches(want_residue, (ch, rn + ic))
                    except:
                        pass
        return False

    def _paths_for_pair(self, pdb_key, src, sink, show_all=False):
        """
        show_all=True returns all paths; otherwise returns paths matching the selected source and sink endpoints.
        Returns: list[(path_str, cost)]
        """
        out = []
        want_src = self._canon_node(src)  # ('A','123') gibi (seg burada yok)
        want_sink = self._canon_node(sink)

        # Use the same PDB identifier as the iterator to preserve index consistency
        true_key = self._canon_pdb_key(pdb_key)
        pdb_id_for_map = true_key if true_key is not None else pdb_key

        got_any = False
        for path, cost in self._iter_paths_for_pdb(pdb_key):
            got_any = True
            if not path:
                continue

            if show_all:
                out.append((" \u2192 ".join(map(str, path)), cost))
                continue

            first = str(path[0])
            last = str(path[-1])

            # --- FIRST (source) match ---
            # Token ise: "CHAIN:RES" veya "SEG:CHAIN:RES"
            if ":" in first:
                seg1, ch1, rn1 = self._split_token(first)

                id1 = (
                    f"{seg1}:{ch1}".upper()
                    if seg1
                    else ch1.upper()
                )

                first_ok = self._node_matches(
                    want_src,
                    (id1, rn1)
                )
            else:
                # Index ise
                try:
                    first_ok = self._index_matches_residue(pdb_id_for_map, int(first), want_src)
                except Exception:
                    first_ok = False

            # --- LAST (sink) match ---
            if ":" in last:
                segN, chN, rnN = self._split_token(last)

                idN = (
                    f"{segN}:{chN}".upper()
                    if segN
                    else chN.upper()
                )

                last_ok = self._node_matches(
                    want_sink,
                    (idN, rnN)
                )
            else:
                try:
                    last_ok = self._index_matches_residue(pdb_id_for_map, int(last), want_sink)
                except Exception:
                    last_ok = False

            if first_ok and last_ok:
                out.append((" \u2192 ".join(map(str, path)), cost))

        if not got_any:
            self.log_output(f"⚠ No paths yielded for {pdb_key}. Check paths_dict_2 schema/keys.\n")

        return out

    def _open_frequency_tab(self, notebook, pdb_key):
        import os, tkinter as tk
        from tkinter import ttk

        # ---------- Local helpers (DO NOT rely on self.* here) ----------
        def _split_token(tok: str):
            """Returns (seg, ch, rn) robustly for 'CH:RES' or 'SEG:CH:RES'."""
            s = (tok or "").strip()
            parts = s.split(":")
            if len(parts) == 2:
                return ("", parts[0].strip(), parts[1].strip())
            if len(parts) >= 3:
                return (parts[0].strip(), parts[1].strip(), parts[2].strip())
            return ("", "?", s)

        def _norm_token(tok: str) -> str:
            """Standardize token to 'SEG:CH:RES' if seg exists, else 'CH:RES'."""
            seg, ch, rn = _split_token(tok)
            seg = (seg or "").strip()
            ch = (ch or "").strip()
            rn = (rn or "").strip()
            if ch in ("", "?") or rn in ("", "?"):
                return (tok or "").strip()
            return f"{seg}:{ch}:{rn}" if seg else f"{ch}:{rn}"

        def _base_only(x):
            return os.path.splitext(os.path.basename(str(x)))[0]

        def _coerce_float(x, default=None):
            try:
                return float(x)
            except Exception:
                return default

        def _extract_flat_freq_map(fm_raw):
            """
            Accepts:
              - flat: { "A:123": 0.42, ... } or { "SEG:A:123": 0.42, ... }
              - nested: { "pdb_pct": {...}, "pairs": {...}, ... }
              - alternative keys: "pct", "percent", "normalized", "freq"
            Returns flat dict: { token: float, ... }
            """
            if not isinstance(fm_raw, dict):
                return {}

            # already flat?
            if fm_raw and all(isinstance(k, str) for k in fm_raw.keys()) and any(
                    isinstance(v, (int, float, str)) for v in fm_raw.values()
            ):
                # could still be nested but looks flat; we'll attempt to parse values as float
                flat = {}
                for k, v in fm_raw.items():
                    fv = _coerce_float(v, None)
                    if fv is not None:
                        flat[_norm_token(k)] = fv
                # if we got meaningful floats, accept
                if flat:
                    return flat

            # nested candidates
            for key in ("pdb_pct", "pct", "percent", "normalized", "freq", "frequencies"):
                sub = fm_raw.get(key, None)
                if isinstance(sub, dict):
                    flat = {}
                    for k, v in sub.items():
                        fv = _coerce_float(v, None)
                        if fv is not None:
                            flat[_norm_token(k)] = fv
                    if flat:
                        return flat

            return {}

        def _detect_percent_scale(values):
            """
            Decide display scale:
              - if values mostly <= 1.0 -> treat as 0..1, display as percent (x100)
              - if values already like 0..100 -> keep
            """
            vals = [v for v in values if v is not None]
            if not vals:
                return ("raw", 1.0)

            vmax = max(vals)
            # Heuristic: if max <= 1.0001 -> normalized fraction
            if vmax <= 1.0001:
                return ("percent", 100.0)
            # If already percent-like (0..100+), do not scale
            return ("raw", 1.0)

        # ---------- Tab title ----------
        base = _base_only(pdb_key)
        tab_title = f"{base} • Frequencies"

        # Tab already exists -> select
        for tid in notebook.tabs():
            if notebook.tab(tid, "text") == tab_title:
                notebook.select(tid)
                return

        # ---------- Canon key resolution (match pdb_info_dict key) ----------
        canon = base
        try:
            from MUSIKALL_functions1 import _base_key
            canon = _base_key(base)
        except Exception:
            canon = base

        if canon not in (self.pdb_info_dict or {}):
            for k, pdata in (self.pdb_info_dict or {}).items():
                fp = (pdata or {}).get("file_path", "")
                if _base_only(fp).lower() == base.lower():
                    canon = k
                    break

        # ---------- Get freq map (robust to nested output) ----------
        fm_raw = self._freq_map_for_pdb(pdb_key)  # may be flat OR nested
        fm = _extract_flat_freq_map(fm_raw)  # 반드시 flat dict

        # ---------- Build tab ----------
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=tab_title)
        notebook.select(tab)

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Label(top, text="Chain").grid(row=0, column=0, sticky="w")
        chain_var = tk.StringVar(value="")

        # Collect chain values from pdb_info_dict and from fm keys
        rcm = (self.pdb_info_dict.get(canon, {}) or {}).get("residue_chain_map", {}) or {}
        chains_from_rcm = {str(ch).upper() for ch in rcm.keys()}

        chains_from_fm = set()
        for tok in fm.keys():
            seg, ch, rn = _split_token(tok)
            if ch and ch not in ("?", ""):
                chains_from_fm.add(ch.upper())

        chain_values = [""] + sorted(chains_from_rcm | chains_from_fm)

        ttk.Combobox(
            top, textvariable=chain_var, width=6, state="readonly",
            values=chain_values
        ).grid(row=0, column=1, padx=(4, 12))

        ttk.Label(top, text="Residue").grid(row=0, column=2, sticky="w")
        resid_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=resid_var, width=10).grid(row=0, column=3, padx=(4, 12))

        ttk.Label(top, text="Min").grid(row=0, column=4, sticky="w")
        min_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=min_var, width=8).grid(row=0, column=5, padx=(4, 12))

        ttk.Label(top, text="Max").grid(row=0, column=6, sticky="w")
        max_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=max_var, width=8).grid(row=0, column=7, padx=(4, 12))

        # Note
        note = ttk.Label(
            top,
            text=("Note: Frequencies count internal nodes of Source→Sink paths "
                  "(start/end excluded). Values are displayed as % if the map is 0–1."),
            foreground=getattr(self, "current_palette", {}).get("subtext", "#555"),
            wraplength=720, justify="left", anchor="w"
        )
        note.grid(row=1, column=0, columnspan=8, sticky="w", padx=4, pady=(6, 2))

        # ---------- Table + scrollbars ----------
        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        tv = ttk.Treeview(table_frame, columns=("#", "Residue", "Value"), show="headings", height=18)
        tv.heading("#", text="#")
        tv.column("#", width=60, anchor="center", stretch=False)
        tv.heading("Residue", text="Residue")
        tv.column("Residue", width=220, anchor="center", stretch=True)
        tv.heading("Value", text="Freq (%)")
        tv.column("Value", width=110, anchor="center", stretch=False)

        ysb = ttk.Scrollbar(table_frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=ysb.set)

        # (horizontal is optional here, but safe if tokens get long)
        xsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tv.xview)
        tv.configure(xscrollcommand=xsb.set)

        tv.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        try:
            tv.tag_configure("odd", background="#FFFFFF")
            tv.tag_configure("even", background="#FAFAFA")
        except Exception:
            pass

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        status = ttk.Label(bottom, text="", anchor="center", justify="center")
        status.pack(fill="x", expand=True)

        # ---------- Build initial items ----------
        items = [(tok, float(v)) for tok, v in fm.items()]  # already normalized tokens
        mode, scale = _detect_percent_scale([v for _, v in items])

        # If empty: show endpoints as 0.0 (optional) - keep your original behavior
        if not items:
            try:
                rdict = (self.pdb_info_dict.get(canon, {}) or {}).get("residue_dict", {}) or {}
                endpoints = set()
                for lst_key in ("source_residues", "sink_residues"):
                    for it in rdict.get(lst_key, []) or []:
                        ch = str(it.get("chain", "")).upper()
                        rn = it.get("residue_num")
                        if ch and rn is not None:
                            endpoints.add(f"{ch}:{int(rn)}")

                def _reslabel_sort_key(lbl: str):
                    ch, rn = (lbl.split(":", 1) + [""])[:2]
                    try:
                        num = int("".join(filter(str.isdigit, rn)) or 0)
                    except Exception:
                        num = 0
                    return (ch, num, lbl)

                items = [(lbl, 0.0) for lbl in sorted(endpoints, key=_reslabel_sort_key)]
                if items:
                    self.log_output("ℹ Frequency map empty — listing endpoints as 0.0.\n")
            except Exception as e:
                self.log_output(f"ℹ Frequency map empty — endpoints unavailable: {e}\n")

        # Sort descending by numeric value
        items.sort(key=lambda x: x[1], reverse=True)

        # Update value column label depending on scaling
        try:
            tv.heading("Value", text="Freq (%)" if mode == "percent" else "Freq")
        except Exception:
            pass

        def _refresh():
            tv.delete(*tv.get_children())

            ch_filter = (chain_var.get() or "").strip().upper()
            rn_q = (resid_var.get() or "").strip()

            vmin = _coerce_float(min_var.get(), None) if min_var.get() != "" else None
            vmax = _coerce_float(max_var.get(), None) if max_var.get() != "" else None

            rows = []
            for tok, f in items:
                seg_i, ch_i, rn_i = _split_token(tok)

                if ch_filter and (ch_i or "").upper() != ch_filter:
                    continue
                if rn_q and rn_q not in (rn_i or ""):
                    continue

                # apply min/max on the *raw* value (before percent scaling) to keep consistent behavior
                if vmin is not None and f < vmin:
                    continue
                if vmax is not None and f > vmax:
                    continue

                rows.append((tok, f))

            for i, (tok, f) in enumerate(rows, 1):
                disp = f * scale
                tv.insert(
                    "", "end",
                    values=(i, tok, f"{disp:.3f}"),
                    tags=("odd",) if i % 2 else ("even",)
                )

            status.config(
                text=f"{len(rows)} residues listed. "
                     f"{'(displayed as %)' if mode == 'percent' else ''}"
            )

        for w in (chain_var, resid_var, min_var, max_var):
            w.trace_add("write", lambda *_: _refresh())

        tab.bind_all(
            "<Return>",
            lambda e: _refresh() if tab == notebook.nametowidget(notebook.select()) else None
        )

        _refresh()

    def _freq_map_for_pdb(self, pdb_key):
        import os

        # ---- local safe base helpers (avoid NameError) ----
        def _base_only_local(p):
            return os.path.splitext(os.path.basename(str(p)))[0]

        # Try importing project canonicalizer; otherwise fall back safely
        try:
            from MUSIKALL_functions1 import _base_key
        except Exception:
            _base_key = lambda x: _base_only_local(x)

        # Build identifiers
        base = _base_only_local(pdb_key)
        canon = _base_key(base)  # IMPORTANT: canonicalize the base, not the full filename

        # ----------------------------------------------------
        # (1) Try cache: self.all_normalized_frequencies
        # ----------------------------------------------------
        all_norm = getattr(self, "all_normalized_frequencies", None)
        if isinstance(all_norm, dict) and all_norm:

            # Priority order: canon -> base -> raw string -> with extension variants
            key_candidates = [
                canon,
                f"{canon}.pdb",
                base,
                f"{base}.pdb",
                str(pdb_key),
            ]

            for k in key_candidates:
                v = all_norm.get(k)
                if isinstance(v, dict) and v:
                    return v

            # Fallback: match by base_only (case-insensitive)
            baseL = base.lower()
            for k, v in all_norm.items():
                if not isinstance(v, dict) or not v:
                    continue
                try:
                    kb = _base_only_local(k).lower()
                except Exception:
                    kb = str(k).lower()
                if kb == baseL:
                    return v

        # ----------------------------------------------------
        # (2) If no cache: compute on-demand from paths_dict_2
        # ----------------------------------------------------
        try:
            from MUSIKALL_functions1 import compute_all_normalized_frequencies
        except Exception:
            compute_all_normalized_frequencies = None

        if compute_all_normalized_frequencies is None:
            return {}

        pd2 = getattr(self, "paths_dict_2", None) or {}
        if not isinstance(pd2, dict) or not pd2:
            return {}

        # Infer k (same logic you had, but safe)
        k_infer = 0
        for _pair_dict in pd2.values():
            if not isinstance(_pair_dict, dict):
                continue
            for _pdata in _pair_dict.values():
                paths = ((_pdata or {}).get("paths", []) or [])
                if isinstance(paths, list):
                    k_infer = max(k_infer, len(paths))

        all_norm2 = compute_all_normalized_frequencies(
            pd2, pdb_info_dict=self.pdb_info_dict, k=k_infer
        )

        # Cache it
        self.all_normalized_frequencies = all_norm2

        # Try again with same priority
        if isinstance(all_norm2, dict) and all_norm2:
            key_candidates = [
                canon,
                f"{canon}.pdb",
                base,
                f"{base}.pdb",
                str(pdb_key),
            ]
            for k in key_candidates:
                v = all_norm2.get(k)
                if isinstance(v, dict) and v:
                    return v

            baseL = base.lower()
            for k, v in all_norm2.items():
                if not isinstance(v, dict) or not v:
                    continue
                try:
                    kb = _base_only_local(k).lower()
                except Exception:
                    kb = str(k).lower()
                if kb == baseL:
                    return v

        return {}

    # --- /PATH EXPLORER ---------------------------------------------------------

    def reset_section5(self):
        if hasattr(self, "results_files"): self.results_files = ()
        if hasattr(self, "all_normalized_frequencies"): self.all_normalized_frequencies = {}
        self.log_output("♻️ Section 5 reset.\n")

    def log_output(self, message):
        """Thread-safe output logging + mirror to a per-job log file."""

        # --- 1) Write to the GUI when output_text is available ---
        txt = getattr(self, "output_text", None)
        if txt is not None:
            try:
                # Append in a thread-safe manner
                def _append():
                    txt.insert("end", message)
                    txt.see("end")
                    # Uncomment to prevent direct keyboard editing
                    # txt.bind("<Key>", lambda e: "break")

                txt.after(0, _append)
            except Exception:
                # Fall back to the console if GUI logging fails
                print(message, end="")
        else:
            # Before the main interface is created (e.g., welcome screen)
            print(message, end="")

        # --- 2) Mirror the same message to MUSIKALL_sessionlog.txt in the job folder ---
        try:
            job_dir = getattr(self, "current_job_folder", None)

            # If the main interface is not ready, resolve job_dir from state/jobname
            if job_dir is None:
                jobname = None

                st = getattr(self, "state", None)
                if isinstance(st, dict):
                    jobname = st.get("jobname", None)

                if jobname is None:
                    jobname = getattr(self, "jobname", None)

                if jobname:
                    try:
                        from MUSIKALL_functions1 import _resolve_job_dir
                        job_dir = _resolve_job_dir(jobname)
                    except Exception:
                        job_dir = None

            if job_dir:
                log_path = os.path.join(job_dir, "MUSIKALL_sessionlog.txt")
                # Open in append mode
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(message)
        except Exception:
            # Ignore log-file errors so they do not disrupt the GUI
            pass

    def _endpoints_from_pdb_paths(self, pdb_key):
        sources, sinks = set(), set()
        for path, _ in self._iter_paths_for_pdb(pdb_key):
            if not path: continue
            first, last = str(path[0]), str(path[-1])
            sources.add(first)
            sinks.add(last)

        def _fmt(node: str) -> str:
            node = str(node).strip()

            parts = [p for p in node.split(":") if p != ""]

            if len(parts) == 2:
                ch, rn = parts
                return f"{ch},{rn}"

            if len(parts) >= 3:
                seg = ":".join(parts[:-2])
                ch = parts[-2]
                rn = parts[-1]
                return f"{seg}:{ch},{rn}"

            return node

        def _sort_key(s: str):
            if "," in s:
                ch, rn = s.split(",", 1)
                return (ch, int("".join(filter(str.isdigit, rn)) or 0), rn)
            return ("", int("".join(filter(str.isdigit, s)) or 0), s)

        return (sorted((_fmt(n) for n in sources), key=_sort_key),
                sorted((_fmt(n) for n in sinks), key=_sort_key))

    def _build_path_explorer_tab(self, notebook, pdb_key, parent_win=None):
        import os, re, tkinter as tk
        from tkinter import ttk

        tab = ttk.Frame(notebook)
        from MUSIKALL_functions1 import _base_only
        base = _base_only(pdb_key)
        notebook.add(tab, text=base)

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=8, pady=8)

        # --- Derive Source/Sink only from path endpoints ---
        src_list, sink_list = self._endpoints_from_pdb_paths(pdb_key)
        if not src_list or not sink_list:
            ttk.Label(top, text="No paths found for this PDB.", foreground="#c00").grid(row=0, column=0, sticky="w")
            return

        def to_key(s: str) -> str:
            s = (s or "").strip()
            if not s: return ""
            s = s.replace(";", ",")
            s = re.sub(r"\s+", "", s)
            if ":" in s: return s
            if "," in s:
                ch, rn = s.split(",", 1)
                return f"{ch}:{rn}"
            return s

        ttk.Label(top, text="Source").grid(row=0, column=0, sticky="w")
        src_var = tk.StringVar(value=src_list[0])
        ttk.Combobox(top, textvariable=src_var, values=src_list, state="readonly", width=12) \
            .grid(row=0, column=1, padx=(4, 12))

        ttk.Label(top, text="Sink").grid(row=0, column=2, sticky="w")
        sink_var = tk.StringVar(value=sink_list[0])
        ttk.Combobox(top, textvariable=sink_var, values=sink_list, state="readonly", width=12) \
            .grid(row=0, column=3, padx=(4, 12))

        show_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Show All Paths", variable=show_all_var) \
            .grid(row=0, column=4, padx=(4, 12))

        # Optional Find control
        PLACEHOLDER = "Find: A,123 or 123"
        ttk.Label(top, text="Find residue").grid(row=0, column=5, sticky="w")
        find_var = tk.StringVar(value="")
        find_ent = ttk.Entry(top, textvariable=find_var, width=18)
        find_ent.grid(row=0, column=6, padx=(4, 12))

        def _normalize_find(q: str):
            import re
            q = (q or "").strip()
            if not q: return ""
            q = q.replace(";", ",")
            q = re.sub(r"\s+", "", q)
            return "" if q == PLACEHOLDER.replace(" ", "") else q

        def _show_ph(_=None):
            if not find_var.get():
                try:
                    find_ent.configure(foreground=self.current_palette.get("subtext", "#777"))
                except:
                    find_ent.configure(foreground="#777")
                find_ent.delete(0, "end")
                find_ent.insert(0, PLACEHOLDER)
                find_ent._is_ph = True

        def _clear_ph(_=None):
            if getattr(find_ent, "_is_ph", False):
                find_ent.delete(0, "end")
                try:
                    find_ent.configure(foreground=self.current_palette.get("text", "#000"))
                except:
                    find_ent.configure(foreground="#000")
                find_ent._is_ph = False

        find_ent.bind("<FocusIn>", _clear_ph)
        find_ent.bind("<FocusOut>", _show_ph)
        _show_ph()

        # Frequency Explorer butonu (varsa)
        def _open_freq_with_compat():
            """
            Compatibility layer:
            If normalized frequencies are stored as:
              {pdb: {"pdb_pct": {...}, ...}}
            convert to:
              {pdb: {...}}  (flat map)
            so Frequency Explorer can read it.
            """
            try:
                af = getattr(self, "all_normalized_frequencies", None)
                if isinstance(af, dict) and af:
                    # If any pdb entry is a dict that contains "pdb_pct", flatten everything
                    sample = next(iter(af.values()))
                    if isinstance(sample, dict) and isinstance(sample.get("pdb_pct"), dict):
                        fixed = {}
                        for k, v in af.items():
                            if isinstance(v, dict) and isinstance(v.get("pdb_pct"), dict):
                                fixed[k] = v["pdb_pct"]
                            elif isinstance(v, dict):
                                fixed[k] = v
                            else:
                                fixed[k] = {}
                        self.all_normalized_frequencies = fixed
            except Exception:
                pass

            self._open_frequency_tab(notebook, pdb_key)

        ttk.Button(top, text="Frequency Explorer",
                   command=_open_freq_with_compat) \
            .grid(row=0, column=8, padx=(12, 0))

        # --- Treeview + status ---
        columns = ("#", "Path", "Cost")
        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        tv = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
        tv.heading("#", text="#")
        tv.column("#", width=50, anchor="center")
        tv.heading("Path", text="Path")
        #tv.column("Path", width=720,anchor="center")
        tv.column("Path", width=720, anchor="w", stretch=True)
        tv.heading("Cost", text="Cost")
        tv.column("Cost", width=90, anchor="center")
        #tv.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        ysb = ttk.Scrollbar(table_frame, orient="vertical", command=tv.yview)
        xsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tv.xview)
        tv.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        tv.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        try:
            tv.tag_configure("odd", background="#FFFFFF")
            tv.tag_configure("even", background="#FAFAFA")
        except Exception:
            pass

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        status = ttk.Label(
            bottom, text="",
            anchor="center", justify="center",
            foreground=getattr(self, "current_palette", {"subtext": "#555"}).get("subtext", "#555"),
        )
        status.pack(side="left", fill="x", expand=True)

        # --- Define _refresh_list after the Treeview and status widgets ---
        def _refresh_list(tv=tv, status=status):
            try:
                tv.delete(*tv.get_children())
                src_key = to_key(src_var.get())
                sink_key = to_key(sink_var.get())

                # veri
                rows_all = self._paths_for_pair(pdb_key, "", "", show_all=True)
                rows = self._paths_for_pair(pdb_key, src_key, sink_key, show_all=show_all_var.get())

                q = _normalize_find(find_var.get())
                if q:
                    q_alt = q.replace(",", ":")

                    def _has(node: str) -> bool:
                        node = node.replace(" ", "")
                        return (q in node) or (q_alt in node) or (f":{q}" in node)

                    rows = [r for r in rows if any(_has(n) for n in r[0].split(" \u2192 "))]

                total_cost = 0.0
                n_cost = 0

                for i, (pstr, cost) in enumerate(rows, start=1):
                    num_cost = None
                    if isinstance(cost, (int, float)):
                        try:
                            num_cost = float(cost)
                        except Exception:
                            num_cost = None

                    tv.insert("", "end",
                              values=(i, pstr, f"{num_cost:.4f}" if isinstance(num_cost, float) else ""),
                              tags=("odd",) if i % 2 else ("even",))

                    if num_cost is not None:
                        total_cost += num_cost
                        n_cost += 1

                mean_txt = f" | mean cost = {total_cost / n_cost:.4f}" if n_cost > 0 else ""

                try:
                    status.configure(anchor="center", justify="center")
                except Exception:
                    pass

                if rows_all:
                    status.config(text=f"{len(rows)} listed (of {len(rows_all)} total){mean_txt}.")
                else:
                    status.config(text="0 path in data set → paths_dict_2 empty/keys may not match.")
            except Exception as e:
                try:
                    status.configure(anchor="center", justify="center")
                except Exception:
                    pass
                status.config(text=f"⚠ list failed: {e}")

        ttk.Button(top, text="List Paths", command=_refresh_list).grid(row=0, column=7, padx=(8, 0))
        find_ent.bind("<Return>", lambda e: _refresh_list())

        _refresh_list()

    #####

    def open_cooccurrence_backbone(self):
        import os
        import re
        import tkinter as tk
        from tkinter import ttk, messagebox

        # --- functions must be importable ---
        try:
            from MUSIKALL_functions1 import (
                run_cooccurrence_backbone_for_one_structure,
                run_cooccurrence_backbone_ensemble,
            )
        except Exception as e:
            messagebox.showerror("Import error", f"Backbone functions not found.\n{e}")
            return

        if not getattr(self, "paths_dict_2", None):
            messagebox.showwarning("Backbone", "No computed paths found yet.")
            return

        # ---------------- helpers ----------------
        def _base_only(x):
            return os.path.splitext(os.path.basename(str(x)))[0]

        def _rn_to_int(rn):
            try:
                s = str(rn)
                digits = "".join([c for c in s if c.isdigit()])
                return int(digits) if digits else int(s)
            except Exception:
                return None

        def _split_token_any(s: str):
            """
            Accept:
              - "A:123"
              - "SEG:A:123"  (seg may include ':')
            Return: (seg, ch, rn_str)
            """
            s = (s or "").strip().replace(";", ",")
            s = re.sub(r"\s+", "", s)
            s = s.replace(",", ":")
            parts = [p for p in s.split(":") if p != ""]
            if len(parts) == 2:
                return ("", parts[0], parts[1])
            if len(parts) >= 3:
                seg = ":".join(parts[:-2])
                return (seg, parts[-2], parts[-1])
            return ("", "", s)

        def _norm_token(s: str) -> str:
            s = (s or "").strip().replace(";", ",")
            s = re.sub(r"\s+", "", s)
            return s.replace(",", ":")

        def _ensure_pdb_info_aliases(pdb_keys_local):
            if not isinstance(getattr(self, "pdb_info_dict", None), dict):
                return
            info = self.pdb_info_dict
            base_to_key = {}
            for k, v in info.items():
                base_to_key[_base_only(k).lower()] = k
                fp = (v or {}).get("file_path", "")
                if fp:
                    base_to_key[_base_only(fp).lower()] = k
            for pk in pdb_keys_local:
                if pk in info:
                    continue
                b = _base_only(pk).lower()
                refk = base_to_key.get(b)
                if refk is not None:
                    info[pk] = info.get(refk)

        def _node_to_ep(node, pdb_data):
            """
            returns: (chain, resnum_int, seg_str) or None
            """
            # token-like string
            if isinstance(node, str) and ((":" in node) or ("," in node)) and (not node.strip().isdigit()):
                seg, ch, rn = _split_token_any(node)
                ch = (ch or "").strip().upper()
                rn_i = _rn_to_int(rn)
                if ch and rn_i is not None:
                    return (ch, rn_i, seg.strip())
                return None

            if isinstance(node, dict):
                ch = node.get("chain") or node.get("chain_id") or node.get("chainID") or ""
                rn = node.get("residue_num") if "residue_num" in node else node.get(
                    "resseq", node.get("resid", node.get("resnum"))
                )
                seg = str(node.get("segname") or node.get("seg") or "").strip()
                ch = str(ch).strip().upper()
                rn_i = _rn_to_int(rn)
                if ch and rn_i is not None:
                    return (ch, rn_i, seg)
                return None

            if isinstance(node, tuple) and len(node) >= 3:
                seg = str(node[0] or "").strip()
                ch = str(node[1] or "").strip().upper()
                rn_i = _rn_to_int(node[2])
                if ch and rn_i is not None:
                    return (ch, rn_i, seg)
                return None

            # numeric index -> idx_to_meta
            try:
                gi = int(node)
            except Exception:
                return None

            idx_to_meta = (pdb_data or {}).get("idx_to_meta") or (pdb_data or {}).get("index_to_meta") or {}
            if isinstance(idx_to_meta, dict) and gi in idx_to_meta:
                m = idx_to_meta.get(gi) or {}
                if isinstance(m, dict):
                    ch = (m.get("chain") or m.get("chain_id") or m.get("chainID") or "")
                    rn = m.get("residue_num") if "residue_num" in m else m.get(
                        "resseq", m.get("resid", m.get("resnum"))
                    )
                    seg = str(m.get("segname") or m.get("seg") or "").strip()
                    ch = str(ch).strip().upper()
                    rn_i = _rn_to_int(rn)
                    if ch and rn_i is not None:
                        return (ch, rn_i, seg)

            return None

        def _ep_to_loose(ep):
            if isinstance(ep, str):
                _seg, ch, rn = _split_token_any(ep)
                ch = (ch or "").strip().upper()
                rn_i = _rn_to_int(rn)
                return (ch, rn_i) if ch and rn_i is not None else None
            return None

        def _parse_pair_key(pk):
            s = str(pk).replace(" ", "").replace("→", "->").replace("to", "->")
            m = re.search(r"([A-Za-z0-9]+:\d+[A-Za-z0-9]*)\-\>([A-Za-z0-9]+:\d+[A-Za-z0-9]*)", s)
            if not m:
                return None

            def _tok_to_loose(t):
                ch, rn = t.split(":", 1)
                ch = ch.strip().upper()
                rn_i = _rn_to_int(rn)
                return (ch, rn_i) if ch and rn_i is not None else None

            a = _tok_to_loose(m.group(1))
            b = _tok_to_loose(m.group(2))
            return (a, b) if a and b else None

        def _compute_selected_pair_keys(pdb_key, sel_src, sel_snk):
            selected_pair_keys = set()
            if not sel_src or not sel_snk:
                return selected_pair_keys

            sel_src_loose = set(filter(None, (_ep_to_loose(x) for x in sel_src)))
            sel_snk_loose = set(filter(None, (_ep_to_loose(x) for x in sel_snk)))

            pdb_data = (self.pdb_info_dict or {}).get(pdb_key, {}) or {}
            pair_dict = (self.paths_dict_2 or {}).get(pdb_key, {}) or {}

            for pair_key, pdata in pair_dict.items():
                parsed = _parse_pair_key(pair_key)
                if parsed:
                    if (parsed[0] in sel_src_loose) and (parsed[1] in sel_snk_loose):
                        selected_pair_keys.add(pair_key)
                    continue

                paths = (pdata or {}).get("paths", []) or []
                if not paths:
                    continue
                p0 = next((p for p in paths if p), None)
                if not p0:
                    continue

                a = _node_to_ep(p0[0], pdb_data)
                b = _node_to_ep(p0[-1], pdb_data)
                if not a or not b:
                    continue

                if ((a[0], int(a[1])) in sel_src_loose) and ((b[0], int(b[1])) in sel_snk_loose):
                    selected_pair_keys.add(pair_key)

            return selected_pair_keys

        def _endpoints_from_paths_dict(pdb_key):
            pdb_data = (self.pdb_info_dict or {}).get(pdb_key, {}) or {}
            pair_dict = (self.paths_dict_2 or {}).get(pdb_key, {}) or {}
            src_set, snk_set = set(), set()

            for pdata in pair_dict.values():
                for p in ((pdata or {}).get("paths", []) or []):
                    if not p:
                        continue
                    a = _node_to_ep(p[0], pdb_data)
                    b = _node_to_ep(p[-1], pdb_data)
                    if a:
                        seg = (a[2] or "").strip()
                        src_set.add(f"{seg}:{a[0]}:{a[1]}" if seg else f"{a[0]}:{a[1]}")
                    if b:
                        seg = (b[2] or "").strip()
                        snk_set.add(f"{seg}:{b[0]}:{b[1]}" if seg else f"{b[0]}:{b[1]}")

            def _sort_key(tok):
                seg, ch, rn = _split_token_any(tok)
                rn_i = _rn_to_int(rn) or 0
                return ((ch or "").upper(), rn_i, (seg or "").upper(), tok)

            return (sorted(src_set, key=_sort_key), sorted(snk_set, key=_sort_key))

        def _open_folder(path):
            import threading, os

            # ✅ Always run in Tk main thread
            if threading.current_thread() is not threading.main_thread():
                try:
                    self.after(0, lambda: _open_folder(path))
                except Exception:
                    pass
                return

            try:
                os.startfile(path)
            except Exception:
                try:
                    import subprocess
                    subprocess.Popen(["xdg-open", path])
                except Exception:
                    try:
                        self.log_output(f"Output folder: {path}\n")
                    except Exception:
                        pass

        # ---------------- window ----------------
        pdb_keys = list((self.paths_dict_2 or {}).keys())
        _ensure_pdb_info_aliases(pdb_keys)

        parent = getattr(self, "root", None) or getattr(self, "master", None) or getattr(self, "window", None) or self
        win = tk.Toplevel(parent)
        win.title("Co-occurrence Backbone (Binary paths → Dot product → NxN)")
        win.geometry("1150x720")

        top = ttk.Frame(win)
        top.pack(fill="x", padx=10, pady=10)
        mid = ttk.Frame(win)
        mid.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bottom = ttk.Frame(win)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        pdb_var = tk.StringVar(value=str(pdb_keys[0]) if pdb_keys else "")
        scope_var = tk.StringVar(value="one")  # one / all
        status_var = tk.StringVar(value="")

        ttk.Label(top, text="Structure").grid(row=0, column=0, sticky="w")
        pdb_combo = ttk.Combobox(
            top,
            textvariable=pdb_var,
            state="readonly",
            values=[str(k) for k in pdb_keys],
            width=40,
        )
        pdb_combo.grid(row=0, column=1, padx=(6, 18), sticky="w")

        ttk.Label(top, text="Scope").grid(row=0, column=2, sticky="w")
        ttk.Radiobutton(top, text="Selected structure", value="one", variable=scope_var).grid(
            row=0, column=3, sticky="w"
        )
        ttk.Radiobutton(top, text="All structures", value="all", variable=scope_var).grid(
            row=0, column=4, sticky="w", padx=(10, 0)
        )

        left = ttk.Frame(mid)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(mid)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        ttk.Label(left, text="Sources (select one or more)").pack(anchor="w")
        src_listbox = tk.Listbox(left, selectmode="multiple", height=22, exportselection=False)
        src_listbox.pack(fill="both", expand=True)

        ttk.Label(right, text="Sinks (select one or more)").pack(anchor="w")
        snk_listbox = tk.Listbox(right, selectmode="multiple", height=22, exportselection=False)
        snk_listbox.pack(fill="both", expand=True)

        def _toggle_on_click(lb: tk.Listbox):
            def _handler(e):
                i = lb.nearest(e.y)
                if i < 0:
                    return "break"
                if i in lb.curselection():
                    lb.selection_clear(i)
                else:
                    lb.selection_set(i)
                return "break"

            return _handler

        src_listbox.bind("<Button-1>", _toggle_on_click(src_listbox))
        snk_listbox.bind("<Button-1>", _toggle_on_click(snk_listbox))

        prog = ttk.Progressbar(bottom, mode="indeterminate")
        prog.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(bottom, textvariable=status_var).pack(side="left")

        btns = ttk.Frame(bottom)
        btns.pack(side="right")

        def _resolve_pdb_key_obj():
            sel = pdb_var.get()
            for k in pdb_keys:
                if str(k) == sel:
                    return k
            return pdb_keys[0] if pdb_keys else None

        def _load_endpoints_for_selected():
            src_listbox.delete(0, "end")
            snk_listbox.delete(0, "end")
            chosen_key = _resolve_pdb_key_obj()
            if chosen_key is None:
                return
            srcs, snks = _endpoints_from_paths_dict(chosen_key)
            srcs = [_norm_token(x) for x in srcs]
            snks = [_norm_token(x) for x in snks]
            for s in srcs:
                src_listbox.insert("end", s)
            for t in snks:
                snk_listbox.insert("end", t)
            if srcs:
                src_listbox.select_set(0)
            if snks:
                snk_listbox.select_set(0)

        pdb_combo.bind("<<ComboboxSelected>>", lambda e: _load_endpoints_for_selected())

        # ---------------- RUN ----------------
        def _run():
            pdb_key = _resolve_pdb_key_obj()
            if pdb_key is None:
                messagebox.showwarning("Backbone", "No structures found.")
                return

            sel_src = [src_listbox.get(i) for i in src_listbox.curselection()]
            sel_snk = [snk_listbox.get(i) for i in snk_listbox.curselection()]
            if not sel_src or not sel_snk:
                messagebox.showwarning("Selection required", "Select at least one source and one sink.", parent=win)
                return

            job_dir = getattr(self, "current_job_folder", None) or getattr(self, "job_dir", None)
            if not job_dir:
                messagebox.showwarning("Job folder missing", "current_job_folder/job_dir is missing.", parent=win)
                return

            # output root
            backbone_root = os.path.join(job_dir, "cooccurrence_backbone")
            os.makedirs(backbone_root, exist_ok=True)

            status_var.set("Running...")
            prog.start(12)
            win.update_idletasks()

            try:
                # ---------------- ALL STRUCTURES ----------------
                if scope_var.get() == "all":
                    subset_pd2 = {}
                    for k in pdb_keys:
                        selected_pair_keys = _compute_selected_pair_keys(k, sel_src, sel_snk)
                        if not selected_pair_keys:
                            continue
                        pair_dict_k = (self.paths_dict_2 or {}).get(k, {}) or {}
                        filtered = {pk: pv for pk, pv in pair_dict_k.items() if pk in selected_pair_keys}
                        if filtered:
                            subset_pd2[k] = filtered

                    if not subset_pd2:
                        status_var.set("Done. outputs: 0")
                        messagebox.showwarning(
                            "Backbone",
                            "No matching pairs were found across all structures for your selection.\n"
                            "Tip: pick endpoints that actually appear in computed paths.",
                            parent=win,
                        )
                        return

                    outs = run_cooccurrence_backbone_ensemble(
                        paths_dict_2=subset_pd2,
                        pdb_info_dict=self.pdb_info_dict,
                        out_dir=backbone_root,  # FIX: correct arg name & location
                        logger=self,  # FIX: logger must be object with .log_output
                        selected_pdb_keys=list(subset_pd2.keys()),
                        selected_pairs=None,  # already filtered upstream
                        strict=False,
                        save_counts_png=True,
                        do_kmeans=False,
                        kmeans_k=4,
                        write_diagnostics=True,
                    )

                    status_var.set(f"Done. outputs: {len(outs) if outs else 0}")
                    _open_folder(backbone_root)
                    return

                # ---------------- ONE STRUCTURE ----------------
                selected_pair_keys = _compute_selected_pair_keys(pdb_key, sel_src, sel_snk)
                if not selected_pair_keys:
                    messagebox.showwarning(
                        "No valid pairs",
                        "Your selection does not match any computed pairs for this structure.\n"
                        "Tip: pick endpoints that actually appear in computed paths.",
                        parent=win,
                    )
                    return

                pair_dict = (self.paths_dict_2 or {}).get(pdb_key, {}) or {}
                filtered = {pk: pv for pk, pv in pair_dict.items() if pk in selected_pair_keys}
                if not filtered:
                    messagebox.showwarning("No pairs", "No matching pairs in this structure.", parent=win)
                    return

                pdb_base = _base_only(pdb_key)
                out_dir = os.path.join(backbone_root, "per_structure", pdb_base)
                os.makedirs(out_dir, exist_ok=True)

                tmp_pd2 = {pdb_key: filtered}

                outs = run_cooccurrence_backbone_for_one_structure(
                    pdb_key=pdb_key,
                    paths_dict_2=tmp_pd2,
                    pdb_info_dict=self.pdb_info_dict,
                    out_dir=out_dir,
                    logger=self,  # FIX
                    selected_pairs=None,
                    strict=False,
                    save_counts_png=True,
                    do_kmeans=False,
                    kmeans_k=4,
                    write_diagnostics=True,
                )

                status_var.set(f"Done. outputs: {len(outs) if outs else 0}")
                _open_folder(out_dir)

            finally:
                prog.stop()
                win.update_idletasks()

        ttk.Button(btns, text="Run Backbone", command=_run).pack(side="left")
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="left", padx=(8, 0))

        _load_endpoints_for_selected()


    def open_path_similarity(self):
        import os
        import re
        import tkinter as tk
        from tkinter import ttk, messagebox

        # --- functions must be importable ---
        try:
            from MUSIKALL_functions1 import (
                run_path_similarity_for_one_structure,
                run_path_similarity_ensemble,
            )
        except Exception as e:
            messagebox.showerror("Import error", f"Path similarity functions not found.\n{e}")
            return

        if not getattr(self, "paths_dict_2", None):
            messagebox.showwarning("Path Similarity", "No computed paths found yet.")
            return

        # ---------------- helpers ----------------
        def _base_only(x):
            return os.path.splitext(os.path.basename(str(x)))[0]

        def _rn_to_int(rn):
            try:
                s = str(rn)
                digits = "".join([c for c in s if c.isdigit()])
                return int(digits) if digits else int(s)
            except Exception:
                return None

        def _split_token_any(s: str):
            """
            Accept:
              - "A:123"
              - "SEG:A:123"  (seg may include ':')
            Return: (seg, ch, rn_str)
            """
            s = (s or "").strip().replace(";", ",")
            s = re.sub(r"\s+", "", s)
            s = s.replace(",", ":")
            parts = [p for p in s.split(":") if p != ""]
            if len(parts) == 2:
                return ("", parts[0], parts[1])
            if len(parts) >= 3:
                seg = ":".join(parts[:-2])
                return (seg, parts[-2], parts[-1])
            return ("", "", s)

        def _norm_token(s: str) -> str:
            s = (s or "").strip().replace(";", ",")
            s = re.sub(r"\s+", "", s)
            return s.replace(",", ":")

        def _ensure_pdb_info_aliases(pdb_keys_local):
            if not isinstance(getattr(self, "pdb_info_dict", None), dict):
                return
            info = self.pdb_info_dict
            base_to_key = {}
            for k, v in info.items():
                base_to_key[_base_only(k).lower()] = k
                fp = (v or {}).get("file_path", "")
                if fp:
                    base_to_key[_base_only(fp).lower()] = k
            for pk in pdb_keys_local:
                if pk in info:
                    continue
                b = _base_only(pk).lower()
                refk = base_to_key.get(b)
                if refk is not None:
                    info[pk] = info.get(refk)

        def _node_to_ep(node, pdb_data):
            """
            returns: (chain, resnum_int, seg_str) or None
            """
            # token-like string
            if isinstance(node, str) and ((":" in node) or ("," in node)) and (not node.strip().isdigit()):
                seg, ch, rn = _split_token_any(node)
                ch = (ch or "").strip().upper()
                rn_i = _rn_to_int(rn)
                if ch and rn_i is not None:
                    return (ch, rn_i, seg.strip())
                return None

            if isinstance(node, dict):
                ch = node.get("chain") or node.get("chain_id") or node.get("chainID") or ""
                rn = node.get("residue_num") if "residue_num" in node else node.get(
                    "resseq", node.get("resid", node.get("resnum"))
                )
                seg = str(node.get("segname") or node.get("seg") or "").strip()
                ch = str(ch).strip().upper()
                rn_i = _rn_to_int(rn)
                if ch and rn_i is not None:
                    return (ch, rn_i, seg)
                return None

            if isinstance(node, tuple) and len(node) >= 3:
                seg = str(node[0] or "").strip()
                ch = str(node[1] or "").strip().upper()
                rn_i = _rn_to_int(node[2])
                if ch and rn_i is not None:
                    return (ch, rn_i, seg)
                return None

            # numeric index -> idx_to_meta
            try:
                gi = int(node)
            except Exception:
                return None

            idx_to_meta = (pdb_data or {}).get("idx_to_meta") or (pdb_data or {}).get("index_to_meta") or {}
            if isinstance(idx_to_meta, dict) and gi in idx_to_meta:
                m = idx_to_meta.get(gi) or {}
                if isinstance(m, dict):
                    ch = (m.get("chain") or m.get("chain_id") or m.get("chainID") or "")
                    rn = m.get("residue_num") if "residue_num" in m else m.get(
                        "resseq", m.get("resid", m.get("resnum"))
                    )
                    seg = str(m.get("segname") or m.get("seg") or "").strip()
                    ch = str(ch).strip().upper()
                    rn_i = _rn_to_int(rn)
                    if ch and rn_i is not None:
                        return (ch, rn_i, seg)

            return None

        def _ep_to_loose(ep):
            if isinstance(ep, str):
                _seg, ch, rn = _split_token_any(ep)
                ch = (ch or "").strip().upper()
                rn_i = _rn_to_int(rn)
                return (ch, rn_i) if ch and rn_i is not None else None
            return None

        def _parse_pair_key(pk):
            s = str(pk).replace(" ", "").replace("→", "->").replace("to", "->")
            m = re.search(r"([A-Za-z0-9]+:\d+[A-Za-z0-9]*)\-\>([A-Za-z0-9]+:\d+[A-Za-z0-9]*)", s)
            if not m:
                return None

            def _tok_to_loose(t):
                ch, rn = t.split(":", 1)
                ch = ch.strip().upper()
                rn_i = _rn_to_int(rn)
                return (ch, rn_i) if ch and rn_i is not None else None

            a = _tok_to_loose(m.group(1))
            b = _tok_to_loose(m.group(2))
            return (a, b) if a and b else None

        def _compute_selected_pair_keys(pdb_key, sel_src, sel_snk):
            selected_pair_keys = set()
            if not sel_src or not sel_snk:
                return selected_pair_keys

            sel_src_loose = set(filter(None, (_ep_to_loose(x) for x in sel_src)))
            sel_snk_loose = set(filter(None, (_ep_to_loose(x) for x in sel_snk)))

            pdb_data = (self.pdb_info_dict or {}).get(pdb_key, {}) or {}
            pair_dict = (self.paths_dict_2 or {}).get(pdb_key, {}) or {}

            for pair_key, pdata in pair_dict.items():
                parsed = _parse_pair_key(pair_key)
                if parsed:
                    if (parsed[0] in sel_src_loose) and (parsed[1] in sel_snk_loose):
                        selected_pair_keys.add(pair_key)
                    continue

                paths = (pdata or {}).get("paths", []) or []
                if not paths:
                    continue
                p0 = next((p for p in paths if p), None)
                if not p0:
                    continue

                a = _node_to_ep(p0[0], pdb_data)
                b = _node_to_ep(p0[-1], pdb_data)
                if not a or not b:
                    continue

                if ((a[0], int(a[1])) in sel_src_loose) and ((b[0], int(b[1])) in sel_snk_loose):
                    selected_pair_keys.add(pair_key)

            return selected_pair_keys

        def _endpoints_from_paths_dict(pdb_key):
            pdb_data = (self.pdb_info_dict or {}).get(pdb_key, {}) or {}
            pair_dict = (self.paths_dict_2 or {}).get(pdb_key, {}) or {}
            src_set, snk_set = set(), set()

            for pdata in pair_dict.values():
                for p in ((pdata or {}).get("paths", []) or []):
                    if not p:
                        continue
                    a = _node_to_ep(p[0], pdb_data)
                    b = _node_to_ep(p[-1], pdb_data)
                    if a:
                        seg = (a[2] or "").strip()
                        src_set.add(f"{seg}:{a[0]}:{a[1]}" if seg else f"{a[0]}:{a[1]}")
                    if b:
                        seg = (b[2] or "").strip()
                        snk_set.add(f"{seg}:{b[0]}:{b[1]}" if seg else f"{b[0]}:{b[1]}")

            def _sort_key(tok):
                seg, ch, rn = _split_token_any(tok)
                rn_i = _rn_to_int(rn) or 0
                return ((ch or "").upper(), rn_i, (seg or "").upper(), tok)

            return (sorted(src_set, key=_sort_key), sorted(snk_set, key=_sort_key))

        def _open_folder(path):
            import threading, os

            # ✅ Always run in Tk main thread
            if threading.current_thread() is not threading.main_thread():
                try:
                    self.after(0, lambda: _open_folder(path))
                except Exception:
                    pass
                return

            try:
                os.startfile(path)
            except Exception:
                try:
                    import subprocess
                    subprocess.Popen(["xdg-open", path])
                except Exception:
                    try:
                        self.log_output(f"Output folder: {path}\n")
                    except Exception:
                        pass

        # ---------------- window ----------------
        pdb_keys = list((self.paths_dict_2 or {}).keys())
        _ensure_pdb_info_aliases(pdb_keys)

        parent = getattr(self, "root", None) or getattr(self, "master", None) or getattr(self, "window", None) or self
        win = tk.Toplevel(parent)
        win.title("Path Similarity (Binary paths → Cosine similarity → Clusters)")
        win.geometry("1150x720")

        top = ttk.Frame(win)
        top.pack(fill="x", padx=10, pady=10)
        mid = ttk.Frame(win)
        mid.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        bottom = ttk.Frame(win)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        pdb_var = tk.StringVar(value=str(pdb_keys[0]) if pdb_keys else "")
        scope_var = tk.StringVar(value="one")  # one / all
        status_var = tk.StringVar(value="")

        ttk.Label(top, text="Structure").grid(row=0, column=0, sticky="w")
        pdb_combo = ttk.Combobox(
            top,
            textvariable=pdb_var,
            state="readonly",
            values=[str(k) for k in pdb_keys],
            width=40,
        )
        pdb_combo.grid(row=0, column=1, padx=(6, 18), sticky="w")

        ttk.Label(top, text="Scope").grid(row=0, column=2, sticky="w")
        ttk.Radiobutton(top, text="Selected structure", value="one", variable=scope_var).grid(
            row=0, column=3, sticky="w"
        )
        ttk.Radiobutton(top, text="All structures", value="all", variable=scope_var).grid(
            row=0, column=4, sticky="w", padx=(10, 0)
        )

        ttk.Label(top, text="Threshold").grid(row=0, column=5, sticky="w", padx=(18, 0))
        thr_var = tk.StringVar(value="0.70")
        thr_entry = ttk.Entry(top, textvariable=thr_var, width=8)
        thr_entry.grid(row=0, column=6, sticky="w", padx=(6, 0))

        left = ttk.Frame(mid)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(mid)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        ttk.Label(left, text="Sources (select one or more)").pack(anchor="w")
        src_listbox = tk.Listbox(left, selectmode="multiple", height=22, exportselection=False)
        src_listbox.pack(fill="both", expand=True)

        ttk.Label(right, text="Sinks (select one or more)").pack(anchor="w")
        snk_listbox = tk.Listbox(right, selectmode="multiple", height=22, exportselection=False)
        snk_listbox.pack(fill="both", expand=True)

        def _toggle_on_click(lb: tk.Listbox):
            def _handler(e):
                i = lb.nearest(e.y)
                if i < 0:
                    return "break"
                if i in lb.curselection():
                    lb.selection_clear(i)
                else:
                    lb.selection_set(i)
                return "break"

            return _handler

        src_listbox.bind("<Button-1>", _toggle_on_click(src_listbox))
        snk_listbox.bind("<Button-1>", _toggle_on_click(snk_listbox))

        prog = ttk.Progressbar(bottom, mode="indeterminate")
        prog.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(bottom, textvariable=status_var).pack(side="left")

        btns = ttk.Frame(bottom)
        btns.pack(side="right")

        def _resolve_pdb_key_obj():
            sel = pdb_var.get()
            for k in pdb_keys:
                if str(k) == sel:
                    return k
            return pdb_keys[0] if pdb_keys else None

        def _load_endpoints_for_selected():
            src_listbox.delete(0, "end")
            snk_listbox.delete(0, "end")
            chosen_key = _resolve_pdb_key_obj()
            if chosen_key is None:
                return
            srcs, snks = _endpoints_from_paths_dict(chosen_key)
            srcs = [_norm_token(x) for x in srcs]
            snks = [_norm_token(x) for x in snks]
            for s in srcs:
                src_listbox.insert("end", s)
            for t in snks:
                snk_listbox.insert("end", t)
            if srcs:
                src_listbox.select_set(0)
            if snks:
                snk_listbox.select_set(0)

        pdb_combo.bind("<<ComboboxSelected>>", lambda e: _load_endpoints_for_selected())

        # ---------------- RUN ----------------
        def _run():
            pdb_key = _resolve_pdb_key_obj()
            if pdb_key is None:
                messagebox.showwarning("Path Similarity", "No structures found.")
                return

            sel_src = [src_listbox.get(i) for i in src_listbox.curselection()]
            sel_snk = [snk_listbox.get(i) for i in snk_listbox.curselection()]
            if not sel_src or not sel_snk:
                messagebox.showwarning("Selection required", "Select at least one source and one sink.", parent=win)
                return
            try:
                threshold = float(thr_var.get().strip())
            except Exception:
                messagebox.showwarning("Threshold", "Threshold must be a number, e.g. 0.70", parent=win)
                return

            if threshold < 0.0 or threshold > 1.0:
                messagebox.showwarning("Threshold", "Threshold must be between 0 and 1.", parent=win)
                return
            job_dir = getattr(self, "current_job_folder", None) or getattr(self, "job_dir", None)
            if not job_dir:
                messagebox.showwarning("Job folder missing", "current_job_folder/job_dir is missing.", parent=win)
                return

            # output root
            pathsim_root = os.path.join(job_dir, "path_similarity")
            os.makedirs(pathsim_root, exist_ok=True)

            status_var.set("Running...")
            prog.start(12)
            win.update_idletasks()

            try:
                # ---------------- ALL STRUCTURES ----------------
                if scope_var.get() == "all":
                    subset_pd2 = {}
                    for k in pdb_keys:
                        selected_pair_keys = _compute_selected_pair_keys(k, sel_src, sel_snk)
                        if not selected_pair_keys:
                            continue
                        pair_dict_k = (self.paths_dict_2 or {}).get(k, {}) or {}
                        filtered = {pk: pv for pk, pv in pair_dict_k.items() if pk in selected_pair_keys}
                        if filtered:
                            subset_pd2[k] = filtered

                    if not subset_pd2:
                        status_var.set("Done. outputs: 0")
                        messagebox.showwarning(
                            "Path Similarity",
                            "No matching pairs were found across all structures for your selection.\n"
                            "Tip: pick endpoints that actually appear in computed paths.",
                            parent=win,
                        )
                        return

                    outs = run_path_similarity_ensemble(
                        paths_dict_2=subset_pd2,
                        pdb_info_dict=self.pdb_info_dict,
                        out_dir=pathsim_root,
                        logger=self,
                        selected_pdb_keys=list(subset_pd2.keys()),
                        selected_pairs=None,
                        strict=False,
                        similarity_threshold=threshold,
                        write_diagnostics=True,
                    )

                    status_var.set(f"Done. outputs: {len(outs) if outs else 0}")
                    _open_folder(pathsim_root)
                    return

                # ---------------- ONE STRUCTURE ----------------
                selected_pair_keys = _compute_selected_pair_keys(pdb_key, sel_src, sel_snk)
                if not selected_pair_keys:
                    messagebox.showwarning(
                        "No valid pairs",
                        "Your selection does not match any computed pairs for this structure.\n"
                        "Tip: pick endpoints that actually appear in computed paths.",
                        parent=win,
                    )
                    return

                pair_dict = (self.paths_dict_2 or {}).get(pdb_key, {}) or {}
                filtered = {pk: pv for pk, pv in pair_dict.items() if pk in selected_pair_keys}
                if not filtered:
                    messagebox.showwarning("No pairs", "No matching pairs in this structure.", parent=win)
                    return

                pdb_base = _base_only(pdb_key)
                out_dir = os.path.join(pathsim_root, "per_structure", pdb_base)
                os.makedirs(out_dir, exist_ok=True)

                tmp_pd2 = {pdb_key: filtered}

                outs = run_path_similarity_for_one_structure(
                    pdb_key=pdb_key,
                    paths_dict_2=tmp_pd2,
                    pdb_info_dict=self.pdb_info_dict,
                    out_dir=out_dir,
                    logger=self,
                    selected_pairs=None,
                    strict=False,
                    similarity_threshold=threshold,
                    write_diagnostics=True,
                )

                status_var.set(f"Done. outputs: {len(outs) if outs else 0}")
                _open_folder(out_dir)

            finally:
                prog.stop()
                win.update_idletasks()

        ttk.Button(btns, text="Run Path Similarity", command=_run).pack(side="left")
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="left", padx=(8, 0))

        _load_endpoints_for_selected()

    #####

    def create_job(self):
        jobname = self.jobname_entry.get().strip()
        if not jobname:
            messagebox.showerror("Error", "Please enter a job name!")
            return

        # Create the job folder under Documents/MUSIKALL Projects/jobname
        job_dir = create_job_folder(jobname)  # returns the absolute path

        # class attribute olarak kaydet
        self.jobname = jobname
        self.state["jobname"] = jobname
        self.current_job = job_dir  # use this resolved path consistently
        self.current_job_folder = job_dir

        os.makedirs(os.path.join(job_dir, "pdb_files"), exist_ok=True)
        self.log_output(f"✅ Job '{jobname}' created at {job_dir}\n")

    def upload_pdb_files(self):
        """Uploads PDB files and processes them."""
        jobname = self.jobname_entry.get().strip()
        if not jobname:
            messagebox.showerror("Error", "Please create a job first!")
            return

        file_paths = filedialog.askopenfilenames(
            filetypes=[
                ("Structure Files", "*.pdb *.cif *.mmcif"),
                ("PDB Files", "*.pdb"),
                ("mmCIF Files", "*.cif *.mmcif"),
            ]
        )
        if not file_paths:
            return

        self.log_output(f"📂 {len(file_paths)} PDB files selected.\n")
        threading.Thread(target=self.threaded_load_pdb_files, args=(jobname, file_paths)).start()

    def threaded_load_pdb_files(self, jobname, file_paths):
        """Runs PDB file loading in a separate thread."""
        try:
            self.pdb_info_dict = load_pdb_files(
                jobname,
                file_paths,
                pdb_info_dict=getattr(self, "pdb_info_dict", None),
                logger=self
            )
            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.state["jobname"] = jobname

        except Exception as e:
            self.log_output(f"❌ Error loading PDBs: {str(e)}\n")

    def run_adj_matrix(self):
        """Calculates Adjacency matrices and net cost matrices."""
        jobname = self.jobname_entry.get().strip()
        cutoff_value = self.cutoff_entry.get().strip()

        if not jobname:
            messagebox.showerror("Error", "Please create a job first!")
            return
        if not cutoff_value.replace('.', '', 1).isdigit():
            messagebox.showerror("Error", "Please enter a valid cutoff value!")
            return

        self.log_output(f"🔬 Calculating Adjacency matrices with cutoff {cutoff_value}Å...\n")
        threading.Thread(target=self.threaded_run_adj_matrix, args=(jobname, float(cutoff_value))).start()

    def threaded_run_adj_matrix(self, jobname, cutoff_value):
        """Runs Adjacency matrix calculations in a separate thread."""
        try:
            run_adj_matrix(jobname, cutoff_value, self.pdb_info_dict, self)
            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.state["jobname"] = jobname
            self.state["cutoff_value"] = float(cutoff_value)
            self.log_output("✅ Adjacency matrices stage completed.\n")

        except Exception as e:
            self.log_output(f"❌ Error calculating Adjacency matrices: {str(e)}\n")

    def select_reference_pdb(self):
        """Selects the reference PDB file."""
        file_path = filedialog.askopenfilename(filetypes=[("PDB Files", "*.pdb")])
        if file_path:
            self.ref_pdb_entry.delete(0, tk.END)
            self.ref_pdb_entry.insert(0, file_path)

    def run_residue_mapping(self):
        jobname = self.jobname_entry.get().strip()
        reference_pdb = self.ref_pdb_entry.get().strip()

        source_res_input = self._text_input_value(self.source_res_entry)
        sink_res_input = self._text_input_value(self.sink_res_entry)

        self.log_output(f"📝 Raw source input:\n{source_res_input}\n")
        self.log_output(f"📝 Raw sink input:\n{sink_res_input}\n")

        source_residues = parse_residue_input(source_res_input, gui=self,logger=self)
        sink_residues = parse_residue_input(sink_res_input, gui=self, logger=self)

        if not source_residues or not sink_residues:
            messagebox.showerror("Error", "Invalid residue format!")
            return

        # ✅ Ensure self.state exists
        if not hasattr(self, "state") or not isinstance(self.state, dict):
            self.state = {}

        # ✅ store lightweight inputs
        self.state["jobname"] = jobname
        self.state["reference_pdb"] = reference_pdb
        self.state["source_residues_raw"] = source_res_input
        self.state["sink_residues_raw"] = sink_res_input

        # Skip mapping/alignment path
        if hasattr(self, "skip_alignment_var") and self.skip_alignment_var.get():
            self.log_output("⏭️ Alignment skipped. Seeding residue indices from GUI…\n")
            self._seed_indices_from_gui(source_residues, sink_residues)
            self.log_output("✅ Residue indices seeded without alignment.\n")

            return

        # Normal alignment yolu
        self.log_output("📏 Running Residue Mapping...\n")
        threading.Thread(
            target=self.threaded_run_residue_mapping,
            args=(jobname, reference_pdb, source_residues, sink_residues),
            daemon=True
        ).start()

    def _seed_indices_from_gui(self, source_residues, sink_residues):
        """
        Strict SEGNAME-aware residue lookup.

        Rules:
          - User supplied SEGNAME -> exact SEGNAME + chain + residue required.
          - User did not supply SEGNAME -> only residues that genuinely have
            no SEGNAME may be resolved.
          - No fallback from a SEGNAME-qualified input to chain-only lookup.
        """

        def _canon(x):
            if x in (None, "", " "):
                return None
            return str(x).strip().upper()

        def _digits_only(x):
            try:
                return int("".join(c for c in str(x) if c.isdigit()))
            except Exception:
                return None

        misses_total = 0

        for pdb_key, pdata in (getattr(self, "pdb_info_dict", {}) or {}).items():

            rcm = (pdata or {}).get("residue_chain_map", {}) or {}

            # SEGNAME-optional lookup used when the user enters CHAIN,RESNUM.
            # The key is accepted only when CHAIN+RESNUM identifies exactly one
            # physical residue in this structure, regardless of whether that residue
            # itself has a SEGNAME.
            # (CHAIN, RESNUM) -> unique index, or None if ambiguous
            idxmap_simple = {}

            # Exact SEGNAME lookup used only when the user explicitly supplies one.
            # (SEGNAME, CHAIN, RESNUM) -> index
            idxmap_seg = {}

            for ch_key, lst in rcm.items():

                for r in (lst or []):

                    rn_i = _digits_only(r.get("residue_num"))
                    ix = r.get("index")

                    if rn_i is None or ix is None:
                        continue

                    try:
                        ix = int(ix)
                    except Exception:
                        continue

                    # IMPORTANT:
                    # Do not use ch_key here because it may be "MC:D".
                    # Real chain is stored inside residue metadata.
                    real_chain = r.get("chain")
                    if real_chain in (None, "", " "):
                        real_chain = ch_key

                    ch_u = _canon(real_chain)
                    if ch_u is None:
                        continue

                    # Collect all actual segnames of this residue
                    segs = []

                    for sg in (r.get("all_segnames") or []):
                        sg_u = _canon(sg)
                        if sg_u and sg_u not in segs:
                            segs.append(sg_u)

                    primary_seg = _canon(r.get("segname"))
                    if primary_seg and primary_seg not in segs:
                        segs.append(primary_seg)

                    # Always register CHAIN+RESNUM for SEGNAME-optional input.
                    # If the same CHAIN+RESNUM occurs in more than one physical
                    # residue (e.g. different ribosome SEGNAMEs), mark it ambiguous.
                    key = (ch_u, rn_i)
                    if key in idxmap_simple and idxmap_simple[key] != ix:
                        idxmap_simple[key] = None
                    else:
                        idxmap_simple.setdefault(key, ix)

                    # Also register exact SEGNAME keys for explicit SEGNAME input.
                    for sg_u in segs:
                        idxmap_seg[(sg_u, ch_u, rn_i)] = ix

            def _mk_list(inp):

                out = []

                for it in (inp or []):

                    ch_u = _canon(it.get("chain"))
                    rn_i = _digits_only(it.get("residue_num"))

                    seg_raw = it.get("segname")
                    seg_u = _canon(seg_raw)

                    idx = None

                    if ch_u is not None and rn_i is not None:

                        if seg_u is not None:
                            # STRICT:
                            # User supplied SEGNAME -> exact lookup only.
                            idx = idxmap_seg.get(
                                (seg_u, ch_u, rn_i)
                            )

                        else:
                            # No SEGNAME supplied -> ignore SEGNAME and resolve by
                            # CHAIN+RESNUM, but only when that identity is unique.
                            idx = idxmap_simple.get(
                                (ch_u, rn_i)
                            )

                    rec = {
                        "chain": it.get("chain"),
                        "residue_num": it.get("residue_num"),
                        "index": idx,
                    }

                    if seg_raw not in (None, "", " "):
                        rec["segname"] = seg_raw

                    out.append(rec)

                    if idx is None:
                        if seg_u is not None:
                            self.log_output(
                                f"⚠ {pdb_key}: exact SEGNAME residue not found → "
                                f"{seg_u}:{ch_u}:{rn_i}\n"
                            )
                        else:
                            self.log_output(
                                f"⚠ {pdb_key}: CHAIN+RESNUM is missing or ambiguous → "
                                f"{ch_u}:{rn_i}\n"
                                f"   Specify SEGNAME only if multiple residues share this identity.\n"
                            )
                    else:
                        if seg_u is not None:
                            self.log_output(
                                f"✅ {pdb_key}: matched "
                                f"{seg_u}:{ch_u}:{rn_i} → index {idx}\n"
                            )
                        else:
                            self.log_output(
                                f"✅ {pdb_key}: matched "
                                f"{ch_u}:{rn_i} → index {idx}\n"
                            )

                return out

            src_list = _mk_list(source_residues)
            snk_list = _mk_list(sink_residues)

            pdata["residue_dict"] = {
                "source_residues": src_list,
                "sink_residues": snk_list
            }

            miss = sum(
                1
                for x in (src_list + snk_list)
                if x.get("index") is None
            )

            misses_total += miss

            self.log_output(
                f"🧭 Seeded {pdb_key}: "
                f"{len(src_list)} src, {len(snk_list)} sink "
                f"(missing index: {miss}).\n"
            )

        if misses_total:
            self.log_output(
                "⚠ Index not found for some residues. "
                "These nodes are ignored in K-shortest.\n"
            )
        else:
            self.log_output(
                "✅ The index was successfully mapped for all residues.\n"
            )

    def threaded_run_residue_mapping(self, jobname, reference_pdb, source_residues, sink_residues):
        """Alignment & mapping in background thread; UI donmaz."""
        try:
            from MUSIKALL_functions1 import run_residue_mapping
            import os
        except Exception as e:
            self.log_output(f"❌ Import error in mapping helpers: {e}\n")
            return

        try:
            self.log_output(f"🔍 Starting alignment for {jobname}…\n")

            # 0) Reference file existence check (no heavy parse)
            if not reference_pdb or not os.path.exists(reference_pdb):
                self.log_output(f"❌ Reference PDB not found: {reference_pdb}\n")
                return

            # 1) Resolve ref_key robustly (path OR basename)
            ref_key = None
            ref_base = os.path.basename(reference_pdb).lower()

            for k, v in (self.pdb_info_dict or {}).items():
                fp = (v or {}).get("file_path", "")
                if fp and os.path.normpath(fp) == os.path.normpath(reference_pdb):
                    ref_key = k
                    break
                if fp and os.path.basename(fp).lower() == ref_base:
                    ref_key = k
                    break

            if ref_key is None:
                self.log_output("⚠ Reference PDB is not one of the loaded job PDBs. Alignment will still run, "
                                "but reference GUI seeding will be skipped.\n")

            # 2) DO NOT seed indices here (seeding is only for skip_alignment mode)
            #    This block should only build reference_residues for visualization, if possible.
            # Reference must always be re-seeded from the CURRENT GUI source/sink input.

            # 3) The real alignment/mapping happens here
            try:
                self.pdb_residue_dict = run_residue_mapping(jobname,self.pdb_info_dict,
                    reference_pdb, source_residues, sink_residues, self, logger=self)
                self.log_output("✅ Mapping successfully completed!\n")
            except Exception as e:
                import traceback
                self.log_output(f"❌ Error during mapping: {e}\n")
                self.log_output(traceback.format_exc() + "\n")
                self._pending_ksp = None
                return

            # 4) Preserve mapping state for the current session.
            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}

            # 5) Continue with pending KSP if any
            pend = getattr(self, "_pending_ksp", None)
            if pend:
                j, k = pend
                self._pending_ksp = None
                try:
                    self.after(0, lambda: self._start_ksp_async(j, k))
                except Exception as e:
                    self.log_output(f"⚠ Could not schedule K-shortest: {e}\n")

        except Exception as e:
            self.log_output(f"❌ Mapping thread crashed: {e}\n")
            self._pending_ksp = None

    def _mapping_is_ready(self) -> bool:
        """All source/sink items have a global 'index' set?"""
        for _, pdb_data in (getattr(self, "pdb_info_dict", {}) or {}).items():
            rd = (pdb_data.get("residue_dict") or {})
            for key in ("source_residues", "sink_residues"):
                arr = rd.get(key) or []
                if not arr or any(r.get("index") is None for r in arr):
                    return False
        return True

    def _mapping_signature_from_ui(self) -> str:
        import tkinter as tk

        def _get_text(w):
            if isinstance(w, tk.Text):
                return w.get("1.0", "end").strip()
            return w.get().strip()

        ref = (self.ref_pdb_entry.get().strip() if hasattr(self, "ref_pdb_entry") else "")
        src = _get_text(self.source_res_entry) if hasattr(self, "source_res_entry") else ""
        snk = _get_text(self.sink_res_entry) if hasattr(self, "sink_res_entry") else ""
        skip = bool(getattr(self, "skip_alignment_var", None) and self.skip_alignment_var.get())

        return f"ref={ref}||skip={int(skip)}||src={src}||snk={snk}"

    def calculate_shortest_paths(self):
        import tkinter as tk
        from tkinter import messagebox
        import threading

        def _get_text(widget):
            if isinstance(widget, tk.Text):
                return widget.get("1.0", "end").strip()
            return widget.get().strip()

        jobname = self.jobname_entry.get().strip()
        k_value = self.k_entry.get().strip()

        if not jobname:
            messagebox.showerror("Error", "Please create or load a job first!")
            return
        if not k_value.isdigit():
            messagebox.showerror("Error", "Please enter a valid K value!")
            return
        k = int(k_value)

        # Use the resolved job folder as the single source of truth
        jobpath = getattr(self, "current_job", "") or ""
        if not jobpath:
            messagebox.showerror("Error", "Job folder is not set. Please load a job or create a new one.")
            return

        skip = bool(getattr(self, "skip_alignment_var", None) and self.skip_alignment_var.get())

        # signature
        sig = self._mapping_signature_from_ui()
        prev_sig = None
        if hasattr(self, "state") and isinstance(self.state, dict):
            prev_sig = self.state.get("mapping_signature")

        signature_changed = (prev_sig != sig)

        # Skip mode: seed + run KSP
        if skip:
            src_text = _get_text(self.source_res_entry)
            snk_text = _get_text(self.sink_res_entry)

            src = parse_residue_input(src_text, gui=self)
            snk = parse_residue_input(snk_text, gui=self)
            if not src or not snk:
                messagebox.showerror("Error", "Invalid residue format!")
                return

            self._seed_indices_from_gui(src, snk)

            # Store the analysis signature
            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.state["mapping_signature"] = sig

            self._start_ksp_async(jobpath, k)  # pass the resolved job path
            return

        # Alignment/mapping gerekli mi?
        need_mapping = signature_changed or (not self._mapping_is_ready())

        if need_mapping:
            self.log_output("🔗 Alignment step before K-shortest…\n")
            self._pending_ksp = (jobpath, k)

            reference_pdb = self.ref_pdb_entry.get().strip()
            src_text = _get_text(self.source_res_entry)
            snk_text = _get_text(self.sink_res_entry)

            src = parse_residue_input(src_text, gui=self)
            snk = parse_residue_input(snk_text, gui=self)
            if not src or not snk:
                messagebox.showerror("Error", "Invalid residue format!")
                self._pending_ksp = None
                return

            # Store the analysis signature before mapping starts
            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.state["mapping_signature"] = sig

            threading.Thread(
                target=self.threaded_run_residue_mapping,
                args=(jobpath, reference_pdb, src, snk),  # 👈 jobpath
                daemon=True
            ).start()
            return

        # Mapping ready → run KSP
        self._pending_ksp = None
        self._start_ksp_async(jobpath, k)  # 👈 jobpath

    def _start_ksp_async(self, jobname, k):
        threading.Thread(
            target=self.threaded_calculate_shortest_paths,
            args=(jobname, k),
            daemon=True
        ).start()


    def threaded_calculate_shortest_paths(self, jobpath, k):
        try:
            from MUSIKALL_functions1 import (
                calculate_shortest_paths,
                convert_paths_to_residues,
                save_paths_to_excel,
            )

            self.log_output(f"⏳ Calculating k={k} shortest paths…\n")

            self.paths_dict = calculate_shortest_paths(jobpath, k, self.pdb_info_dict, self)

            self.paths_dict_2 = convert_paths_to_residues(self.paths_dict, self.pdb_info_dict)
            self.log_output("✅ Paths calculated & converted.\n")

            per_pdb_files, overall_file, all_norm = save_paths_to_excel(
                jobpath, self.paths_dict_2, self.pdb_info_dict, gui=self
            )
            self.per_pdb_files = per_pdb_files
            self.overall_file = overall_file
            self.all_normalized_frequencies = all_norm

            # stage
            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.state["k"] = int(k)
            self.state["per_pdb_files"] = per_pdb_files
            self.state["overall_file"] = overall_file

        except Exception as e:
            self.log_output(f"❌ Error calculating/analyzing shortest paths: {e}\n")

    def show_results_window(self):
        """Opens a polished Results window with per-PDB tables and an Overall tab."""
        win = tk.Toplevel(self)
        win.title("Analysis Results")
        win.geometry("1000x700")

        # subtle ttk styling (inherits your palette if available)
        P = getattr(self, "current_palette", {"bg": "#ffffff", "fg": "#000000"})
        style = ttk.Style(win)
        style.configure("Results.TFrame", background=P.get("bg", "#fff"))
        style.configure("Results.TLabel", background=P.get("bg", "#fff"), foreground=P.get("fg", "#000"))
        style.configure("ResultsHeader.TLabel",
                        background=P.get("bg", "#fff"), foreground=P.get("fg", "#000"),
                        font=("Segoe UI", 11, "bold"))
        style.configure("Treeview", rowheight=22, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        container = ttk.Frame(win, style="Results.TFrame")
        container.pack(fill="both", expand=True)

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # Build one tab per PDB (paths & costs)
        paths2 = getattr(self, "paths_dict_2", {}) or {}
        for pdb_id in paths2.keys():
            tab = ttk.Frame(notebook, style="Results.TFrame")
            notebook.add(tab, text=pdb_id)
            self._build_paths_tab(tab, pdb_id)

        # Overall tab (frequency overview)
        overall_tab = ttk.Frame(notebook, style="Results.TFrame")
        notebook.add(overall_tab, text="Overall")
        self._build_overall_tab(overall_tab)

    def _build_paths_tab(self, parent, pdb_id):
        """Replaces populate_results_tab: cleaner treeview with sorting + export."""
        header = ttk.Frame(parent, style="Results.TFrame")
        header.pack(fill="x", pady=(6, 4), padx=8)
        ttk.Label(header, text=f"Paths for {pdb_id}", style="ResultsHeader.TLabel").pack(side="left")

        # Export button
        def _export_tsv():
            fpath = filedialog.asksaveasfilename(defaultextension=".tsv",
                                                 filetypes=[("TSV", "*.tsv"), ("All Files", "*.*")],
                                                 initialfile=f"{pdb_id}_paths.tsv")
            if not fpath:
                return
            cols = tree["columns"]
            rows = [cols]
            for iid in tree.get_children(""):
                rows.append([tree.set(iid, c) for c in cols])
            try:
                with open(fpath, "w", encoding="utf-8") as fh:
                    for r in rows:
                        fh.write("\t".join(str(x) for x in r) + "\n")
                messagebox.showinfo("Export", f"Saved: {fpath}")
            except Exception as e:
                messagebox.showerror("Export", f"Failed to save:\n{e}")

        ttk.Button(header, text="Export TSV", command=_export_tsv).pack(side="right")

        # Table
        cols = ("Source", "Sink", "Path (chain:res → ...)", "Cost")
        tree, _scrollx, _scrolly = self._make_treeview(parent, columns=cols)

        # Fill rows from self.paths_dict_2[pdb_id]
        human_pairs = (getattr(self, "paths_dict_2", {}) or {}).get(pdb_id, {}) or {}
        row_alt = 0
        for _, data in human_pairs.items():
            paths = data.get("paths", [])
            costs = data.get("costs", [])
            for i, path in enumerate(paths):
                if not path:
                    continue
                source = path[0]
                sink = path[-1]
                cost = costs[i] if i < len(costs) else ""
                tag = "even" if (row_alt % 2 == 0) else "odd"
                tree.insert("", "end",
                            values=(source, sink, " → ".join(path), cost),
                            tags=(tag,))
                row_alt += 1

        # auto column width
        for c in cols:
            tree.column(c, width=120 if c != "Path (chain:res → ...)" else 600, anchor="w")

    def _build_overall_tab(self, parent):
        """Replaces populate_overall_results_tab: chart (if matplotlib) + table fallback + export."""
        header = ttk.Frame(parent, style="Results.TFrame")
        header.pack(fill="x", pady=(6, 4), padx=8)
        ttk.Label(header, text="Overall Frequency Analysis", style="ResultsHeader.TLabel").pack(side="left")

        # scope selector (matches your options UI)
        scope_var = tk.StringVar(value=(self.music_opts.freq_scope if hasattr(self, "music_opts") else "per_pdb")
        if hasattr(self, "music_opts") else "per_pdb")
        ttk.Label(header, text="Scope:", style="Results.TLabel").pack(side="left", padx=(16, 6))
        scope_cb = ttk.Combobox(header, textvariable=scope_var, state="readonly",
                                values=["per_pdb", "per_pair", "per_path"], width=10)
        scope_cb.pack(side="left")

        body = ttk.Frame(parent, style="Results.TFrame")
        body.pack(fill="both", expand=True, padx=8, pady=8)

        # left: chart (if available)
        left = ttk.Frame(body, style="Results.TFrame")
        left.pack(side="left", fill="both", expand=True)
        # right: table
        right = ttk.Frame(body, style="Results.TFrame")
        right.pack(side="left", fill="y")

        cols = ("Token", "Frequency", "PDB", "Pair", "PathIdx")
        tree, _sx, _sy = self._make_treeview(right, columns=cols, height=18)

        # Export button
        def _export_overall_tsv():
            fpath = filedialog.asksaveasfilename(defaultextension=".tsv",
                                                 filetypes=[("TSV", "*.tsv"), ("All Files", "*.*")],
                                                 initialfile="overall_frequencies.tsv")
            if not fpath:
                return
            cols_ = tree["columns"]
            rows = [cols_]
            for iid in tree.get_children(""):
                rows.append([tree.set(iid, c) for c in cols_])
            try:
                with open(fpath, "w", encoding="utf-8") as fh:
                    for r in rows:
                        fh.write("\t".join(str(x) for x in r) + "\n")
                messagebox.showinfo("Export", f"Saved: {fpath}")
            except Exception as e:
                messagebox.showerror("Export", f"Failed to save:\n{e}")

        ttk.Button(header, text="Export TSV", command=_export_overall_tsv).pack(side="right")

        # fill function
        chart_holder = {"widget": None}

        def _refresh():
            # clear table
            for iid in tree.get_children(""):
                tree.delete(iid)
            # collect data
            scope = scope_var.get()
            rows = self._aggregate_freqs(scope=scope)  # list of (token, freq, pdb, pair, pathidx)

            # top-N for chart
            rows_sorted = sorted(rows, key=lambda r: r[1], reverse=True)
            top = rows_sorted[:30]

            # fill table
            alt = 0
            for token, freq, pdbk, pairk, pidx in rows_sorted:
                tag = "even" if (alt % 2 == 0) else "odd"
                tree.insert("", "end",
                            values=(token, f"{freq:.3f}", pdbk or "", str(pairk) if pairk is not None else "",
                                    str(pidx) if pidx is not None else ""),
                            tags=(tag,))
                alt += 1

            # draw chart
            for child in left.winfo_children():
                child.destroy()
            self._draw_overall_chart(left, top)

            # auto widths
            tree.column("Token", width=140, anchor="center")
            tree.column("Frequency", width=100, anchor="center")
            tree.column("PDB", width=160, anchor="center")
            tree.column("Pair", width=120, anchor="center")
            tree.column("PathIdx", width=80, anchor="center")

        scope_cb.bind("<<ComboboxSelected>>", lambda e: _refresh())
        _refresh()

    def _draw_overall_chart(self, parent, top_rows):
        """
        Attempts a matplotlib bar chart (top_rows: list[(token, freq, pdb, pair, pathidx)]).
        Falls back to a compact Text if matplotlib not installed.
        """
        # try matplotlib
        try:
            self._lazy_matplotlib()
            matplotlib.use("TkAgg")
            # build figure
            fig = Figure(figsize=(6.5, 4), dpi=100)
            ax = fig.add_subplot(111)
            labels = [r[0] for r in top_rows]
            vals = [r[1] for r in top_rows]
            ax.bar(range(len(vals)), vals)  # use the default Matplotlib color cycle
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
            ax.set_ylabel("Normalized frequency")
            ax.set_title("Top residues by normalized frequency")
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception:
            # fallback: text summary
            box = tk.Text(parent, wrap="word", font=("Arial", 11), height=20)
            box.insert("1.0", "Top residues by normalized frequency (matplotlib not found):\n\n")
            for token, freq, pdbk, pairk, pidx in top_rows:
                box.insert("end", f"• {token:<8s}  f={freq:.3f}  PDB={pdbk}  Pair={pairk}  Path={pidx}\n")
            box.config(state="disabled", bg="white")
            box.pack(fill="both", expand=True)

    def _make_treeview(self, parent, columns, height=20):
        """
        Creates a nice Treeview with scrollbars, zebra rows and sortable headings.
        Returns (tree, scrollx, scrolly).
        """
        frame = ttk.Frame(parent, style="Results.TFrame")
        frame.pack(fill="both", expand=True)

        scrolly = ttk.Scrollbar(frame, orient="vertical")
        scrollx = ttk.Scrollbar(frame, orient="horizontal")

        tree = ttk.Treeview(frame, columns=columns, show="headings",
                            yscrollcommand=scrolly.set, xscrollcommand=scrollx.set, height=height)
        scrolly.config(command=tree.yview)
        scrollx.config(command=tree.xview)

        tree.grid(row=0, column=0, sticky="nsew")
        scrolly.grid(row=0, column=1, sticky="ns")
        scrollx.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        for col in columns:
            tree.heading(col, text=col, command=lambda c=col: self._sort_treeview(tree, c, False))
            tree.column(col, anchor="w", width=120)

        # zebra tags
        tree.tag_configure('odd', background="#F7FAFE")
        tree.tag_configure('even', background="#FFFFFF")

        return tree, scrollx, scrolly

    def _sort_treeview(self, tree, col, reverse):
        """Sorts a Treeview by a given column (basic alphanumeric + float fallback)."""

        def try_float(x):
            try:
                return float(x)
            except Exception:
                return x

        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        data.sort(key=lambda t: try_float(t[0]), reverse=reverse)
        for index, (_, k) in enumerate(data):
            tree.move(k, "", index)
        tree.heading(col, command=lambda: self._sort_treeview(tree, col, not reverse))

    def _aggregate_freqs(self, scope="per_pdb"):
        """
        Collapses self.all_normalized_frequencies to rows for the table/chart.
        Returns a list of tuples: (token, freq, pdb_key, pair_key, path_idx)
        scope ∈ {"per_pdb","per_pair","per_path"} (matches your GUI option)
        """
        out = []
        all_norm = getattr(self, "all_normalized_frequencies", None) or {}
        # expected shape documented earlier in your code
        # all_norm[pdb] ~ dict with possibly:
        #   base token->freq    (per_pdb)
        #   "pairs" -> {pair_key: {
        #                 token->freq           (per_pair fallback)
        #                 "paths"->{idx:{token->freq}}  (per_path)
        #              }}
        for pdb_key, base in (all_norm.items() if isinstance(all_norm, dict) else []):
            base = base or {}
            if scope == "per_pdb":
                # prefer top-level dict (token->freq)  fallback to pair-aggregated mean
                token_map = {}
                if isinstance(base, dict):
                    # collect top-level tokens (exclude "pairs")
                    for k, v in base.items():
                        if k == "pairs":
                            continue
                        # k is token (e.g., "A:150")  v is freq
                        try:
                            f = float(v)
                            token_map[k] = token_map.get(k, 0.0) + f
                        except Exception:
                            pass
                    # if nothing collected, accumulate from pairs
                    if not token_map and "pairs" in base:
                        for pair_key, pdata in (base.get("pairs", {}) or {}).items():
                            # gather from pair-level tokens
                            for tk, fv in (pdata or {}).items():
                                if tk == "paths":
                                    continue
                                try:
                                    token_map[tk] = token_map.get(tk, 0.0) + float(fv)
                                except Exception:
                                    pass
                            # and from paths
                            paths = (pdata.get("paths", {}) or {})
                            for pidx, tmap in paths.items():
                                for tk, fv in (tmap or {}).items():
                                    try:
                                        token_map[tk] = token_map.get(tk, 0.0) + float(fv)
                                    except Exception:
                                        pass
                for tk, fv in token_map.items():
                    out.append((tk, float(fv), pdb_key, None, None))

            elif scope == "per_pair":
                pairs = (base.get("pairs", {}) or {}) if isinstance(base, dict) else {}
                for pair_key, pdata in pairs.items():
                    # prefer pair-level tokens
                    token_map = {}
                    for tk, fv in (pdata or {}).items():
                        if tk == "paths":
                            continue
                        try:
                            token_map[tk] = token_map.get(tk, 0.0) + float(fv)
                        except Exception:
                            pass
                    # if empty, aggregate paths
                    if not token_map:
                        for pidx, tmap in (pdata.get("paths", {}) or {}).items():
                            for tk, fv in (tmap or {}).items():
                                try:
                                    token_map[tk] = token_map.get(tk, 0.0) + float(fv)
                                except Exception:
                                    pass
                    for tk, fv in token_map.items():
                        out.append((tk, float(fv), pdb_key, pair_key, None))

            else:  # per_path
                pairs = (base.get("pairs", {}) or {}) if isinstance(base, dict) else {}
                for pair_key, pdata in pairs.items():
                    paths = (pdata.get("paths", {}) or {})
                    for pidx, tmap in paths.items():
                        for tk, fv in (tmap or {}).items():
                            try:
                                out.append((tk, float(fv), pdb_key, pair_key, pidx))
                            except Exception:
                                pass
        return out

    def populate_results_tab(self, frame, pdb_id):
        """Fills a tab with shortest path and cost analysis results."""
        self._lazy_matplotlib()
        tree = ttk.Treeview(frame, columns=("Source", "Sink", "Path", "Cost"), show="headings")
        tree.heading("Source", text="Source")
        tree.heading("Sink", text="Sink")
        tree.heading("Path", text="Path")
        tree.heading("Cost", text="Cost")

        # Zebra stil
        tree.tag_configure('odd', background="#F9FBFE")
        tree.tag_configure('even', background="#FFFFFF")


        tree.pack(fill="both", expand=True)

        # Read directly from self.paths_dict_2 (human-readable paths)
        human_pairs = getattr(self, "paths_dict_2", {}).get(pdb_id, {})

        for _, data in human_pairs.items():
            paths = data.get("paths", [])
            costs = data.get("costs", [])
            for i, path in enumerate(paths):
                if not path:
                    continue
                source = path[0]
                sink = path[-1]
                cost = costs[i] if i < len(costs) else ""
                tree.insert("", "end", values=(source, sink, " → ".join(path), cost))

######

    def open_music_player(self, written_files, event_logs=None):
        import tkinter as tk
        from tkinter import ttk, messagebox
        import os
        from MUSIKALL_functions1 import play_midi, stop_midi
        import pygame

        event_logs = event_logs or {}
        P = self.current_palette

        # --- window ---
        win_w, win_h = 720, 520
        self.update_idletasks()
        par_x, par_y, par_w = self.winfo_rootx(), self.winfo_rooty(), self.winfo_width()
        target_x = par_x + max(0, (par_w - win_w) // 2)
        target_y = max(40, par_y + 60)

        win = tk.Toplevel(self)
        win.title("🎵 Music Player")
        try:
            win.configure(bg=P["bg"])
        except Exception:
            pass
        win.geometry(f"{win_w}x{win_h}+{target_x}+{target_y}")
        win.protocol("WM_DELETE_WINDOW", lambda: (stop_midi(), win.destroy()))

        # --- top: files ---
        top = ttk.Frame(win)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="Generated files", style="Card.TLabel").pack(side="left")

        files_frame = ttk.Frame(win)
        files_frame.pack(fill="x", padx=8, pady=(0, 8))
        files_tv = ttk.Treeview(files_frame, columns=("file",), show="headings", height=5)
        files_tv.heading("file", text="MIDI Path")
        files_tv.column("file", width=640, anchor="w")
        files_tv.pack(side="left", fill="x", expand=True)
        fbar = ttk.Scrollbar(files_frame, orient="vertical", command=files_tv.yview)
        fbar.pack(side="right", fill="y")
        files_tv.configure(yscrollcommand=fbar.set)

        for f in written_files:
            files_tv.insert("", "end", values=(f,))

        # --- mid: events table (Note(s) shows names, not MIDI numbers) ---
        mid = ttk.Frame(win)
        mid.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        cols = ("#", "Residue", "Note(s)",  "Scope/Path")
        ev_tv = ttk.Treeview(mid, columns=cols, show="headings", height=12)
        for c, w, a in (
                ("#", 60, "center"),
                ("Residue", 120, "center"),
                ("Note(s)", 160, "center"),
                ("Scope/Path", 160, "center"),
        ):
            ev_tv.heading(c, text=c)
            ev_tv.column(c, width=w, anchor=a)
        ev_tv.pack(side="left", fill="both", expand=True)
        ebar = ttk.Scrollbar(mid, orient="vertical", command=ev_tv.yview)
        ebar.pack(side="right", fill="y")
        ev_tv.configure(yscrollcommand=ebar.set)

        # --- bottom: controls ---
        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        play_btn = ttk.Button(btns, text="▶ Play")
        stop_btn = ttk.Button(btns, text="⏹ Stop", command=stop_midi)
        play_btn.pack(side="left", padx=4)
        stop_btn.pack(side="left", padx=4)

        # --- highlight styling ---
        highlight_tag = "playing_row"
        try:
            ev_tv.tag_configure(highlight_tag, background=P.get("muted", "#eaeaea"))
        except Exception:
            ev_tv.tag_configure(highlight_tag, background="#eaeaea")

        # --- state ---
        current = {"path": None, "events": [], "poll_id": None}

        def _load_events_for(path: str):
            """Tabloyu event_logs[path] ile doldurur (nota isimleriyle)."""

            def _pretty_residue_label(x):
                """
                GUI display normalizer for residue labels.
                Removes placeholders like NOSEG / None and leading ':'.
                Does NOT affect audio; only the table text.
                """
                if x is None:
                    return ""
                s = str(x).strip()

                # common placeholder pollution
                if s.startswith("NOSEG:"):
                    s = s[len("NOSEG:"):]
                if s.startswith("None:"):
                    s = s[len("None:"):]
                if s.startswith(":"):
                    s = s[1:]

                # also handle accidental double separators
                while s.startswith(":"):
                    s = s[1:]

                return s.strip()

            ev_tv.delete(*ev_tv.get_children())
            events = list(event_logs.get(path, []))
            # Sort by start_sec
            events.sort(key=lambda e: (float(e.get("start_sec", 0.0)), str(e.get("residue") or e.get("token") or "")))

            for i, e in enumerate(events, start=1):
                residue_raw = e.get("residue") or e.get("token") or ""
                residue = _pretty_residue_label(residue_raw)
                note_txt = e.get("note", "")  # C4 veya C4+E4+G4
                meta = e.get("meta", {}) or {}
                scope = meta.get("scope", "")
                pidx = meta.get("path_index")
                scope_s = f"{scope}#{pidx}" if (scope and pidx) else scope
                ev_tv.insert("", "end", iid=f"row{i}", values=(i, residue, note_txt, scope_s))

            current["path"] = path
            current["events"] = events

        def _on_select_file(_=None):
            sel = files_tv.focus() or ""
            if not sel:
                return
            path = files_tv.item(sel, "values")[0]
            _load_events_for(path)

        files_tv.bind("<<TreeviewSelect>>", _on_select_file)

        # --- polling for highlight while playing ---
        def _poll_highlight():
            if not current["path"]:
                return
            try:
                ms = pygame.mixer.music.get_pos()  # -1: not playing
            except Exception:
                ms = -1
            if ms < 0:
                current["poll_id"] = None
                # temizle highlight
                for iid in ev_tv.get_children():
                    ev_tv.item(iid, tags=())
                return

            t = ms / 1000.0
            # aktif event’i bul
            ev_idx = None
            for i, e in enumerate(current["events"], start=1):
                if float(e.get("start_sec", 0.0)) <= t < float(e.get("end_sec", 0.0)):
                    ev_idx = i
                    break

            # highlight uygula
            for iid in ev_tv.get_children():
                ev_tv.item(iid, tags=())
            if ev_idx is not None:
                iid = f"row{ev_idx}"
                ev_tv.see(iid)
                ev_tv.item(iid, tags=(highlight_tag,))

            current["poll_id"] = win.after(100, _poll_highlight)

        def _play_selected(path=None):
            # Select the first file when none is selected
            if not path:
                sel = files_tv.focus() or ""
                if not sel and written_files:
                    first = files_tv.get_children()[0]
                    files_tv.selection_set(first)
                    files_tv.focus(first)
                    _on_select_file()
                    sel = first
                if sel:
                    path = files_tv.item(sel, "values")[0]
            if not path:
                messagebox.showerror("Play error", "No file selected.")
                return

            if current["path"] != path:
                _load_events_for(path)

            try:
                stop_midi()
                play_midi(path)
            except Exception as e:
                messagebox.showerror("Play error", str(e))
                return

            # Cancel previous polling
            if current["poll_id"]:
                try:
                    win.after_cancel(current["poll_id"])
                except Exception:
                    pass
            current["poll_id"] = win.after(100, _poll_highlight)

        play_btn.configure(command=lambda: _play_selected())

        # Automatically load events for the first file when the list is not empty
        if written_files:
            try:
                first = files_tv.get_children()[0]
                files_tv.selection_set(first)
                files_tv.focus(first)
                _on_select_file()
            except Exception:
                pass

    def _safe_base_octave(self):
        try:
            return int(self.base_octave_entry.get() or 4)
        except Exception:
            self.base_octave_entry.delete(0, tk.END)
            self.base_octave_entry.insert(0, "4")
            return 4

    def reset_aa_defaults(self):
        """Populate the amino-acid grid from the Advanced default scale and base octave."""
        scale_name = self.music_opts.default_scale_name
        base_oct = self.music_opts.default_base_octave
        aa_map = build_default_aa_mapping(scale_name, base_oct)  # {'ALA':'C4', ...}
        for aa3, widgets in self.aa_widgets.items():
            val = aa_map.get(aa3, "C4")
            note, octv = val[:-1], val[-1]
            widgets["note"].set(note)
            widgets["oct"].delete(0, tk.END)
            widgets["oct"].insert(0, octv)

    def _collect_aa_mapping(self):
        """Return the current amino-acid grid selection as {'ALA': 'C4', ...}."""
        mapping = {}
        for aa3, widgets in self.aa_widgets.items():
            note = widgets["note"].get() or "C"
            try:
                octv = int(widgets["oct"].get() or self.music_opts.default_base_octave)
            except Exception:
                octv = self.music_opts.default_base_octave
                widgets["oct"].delete(0, tk.END)
                widgets["oct"].insert(0, str(octv))
            mapping[aa3] = f"{note}{octv}"
        return mapping

    def generate_audio(self):
        jobpath = getattr(self, "current_job", "").strip() if isinstance(getattr(self, "current_job", ""),
                                                                         str) else getattr(self, "current_job", "")
        if not jobpath:
            messagebox.showerror("Error", "Please create a job first!")
            return
        if not getattr(self, "paths_dict_2", None):
            messagebox.showerror("Error", "Run 'Calculate Paths' first!")
            return

        aa_map = self._collect_aa_mapping()
        try:
            res_map = aa_mapping_to_residue_mapping(jobpath, self.paths_dict_2, aa_map, self.pdb_info_dict, gui=self)
        except Exception as e:
            self.log_output(f"❌ aamapping conversion failed: {e}\n")
            return

        # event log iste
        opts = self.music_opts
        setattr(opts, "return_event_log", True)

        def _run():
            try:
                try:
                    self.music_opts.return_event_log = True
                except Exception:
                    pass

                res = pr_generate_audio(
                    jobpath,
                    self.paths_dict_2,
                    res_map,
                    options=self.music_opts,
                    all_normalized_frequencies=getattr(self, "all_normalized_frequencies", None),
                    gui=self,
                    pdb_info_dict=self.pdb_info_dict
                )

                if isinstance(res, tuple) and len(res) == 2:
                    written, event_logs = res
                else:
                    written, event_logs = (res or []), {}

                if written:
                    self.log_output(f"✅ Done. {len(written)} MIDI file(s) created.\n")

                    self.open_music_player(written, event_logs=event_logs)
                else:
                    self.log_output("⚠️ No MIDI files produced.\n")

            except Exception as e:
                self.log_output(f"❌ Audio generation failed: {e}\n")

        threading.Thread(target=_run, daemon=True).start()

    def build_music_sidebar(self, parent):
        box = ttk.LabelFrame(
            parent, text="Sonification", style="Card.TLabelframe", padding=(12, 10)
        )
        box.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))

        ttk.Label(
            box,
            text="Map residue identities to MIDI. Advanced Options controls mapping mode, harmony, dynamics, rhythm, pitch range, and output scope.",
            style="SectionHint.TLabel", wraplength=330, justify="left"
        ).pack(fill="x", pady=(0, 10))

        top = ttk.Frame(box, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="Advanced Options", command=self.open_music_advanced).pack(side="left")
        ttk.Button(top, text="Reset Note Grid", command=self.reset_aa_defaults).pack(side="left", padx=(8, 0))

        info_btn = tk.Label(
            top, text="ⓘ", fg=self.current_palette["accent"], cursor="question_arrow",
            bg=self.current_palette["bg"], font=("Segoe UI", 10)
        )
        info_btn.pack(side="right", padx=(6, 2))
        Tooltip(
            info_btn,
            "The grid defines the root pitch used for residue-identity mapping.\n"
            "Advanced Options contains property mapping, single-residue focus,\n"
            "triads, instrument, tempo, duration, transpose, clamp and velocity settings."
        )

        ttk.Separator(box, orient="horizontal").pack(fill="x", pady=(0, 10))
        ttk.Label(box, text="Residue note grid", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Label(
            box, text="Root note and octave used when residue-grid mapping is selected.",
            style="SectionHint.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        inner = ttk.Frame(box, style="Card.TFrame")
        inner.pack(fill="both", expand=True)
        for c in (0, 3):
            inner.columnconfigure(c, weight=1)

        # Compact two-column residue grid. Full names remain available as tooltips.
        ttk.Label(inner, text="Residue", style="FieldLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(2, 6), pady=(0, 4))
        ttk.Label(inner, text="Note", style="FieldLabel.TLabel").grid(row=0, column=1, sticky="w", padx=3, pady=(0, 4))
        ttk.Label(inner, text="Oct", style="FieldLabel.TLabel").grid(row=0, column=2, sticky="w", padx=3, pady=(0, 4))
        ttk.Label(inner, text="Residue", style="FieldLabel.TLabel").grid(row=0, column=3, sticky="w", padx=(16, 6), pady=(0, 4))
        ttk.Label(inner, text="Note", style="FieldLabel.TLabel").grid(row=0, column=4, sticky="w", padx=3, pady=(0, 4))
        ttk.Label(inner, text="Oct", style="FieldLabel.TLabel").grid(row=0, column=5, sticky="w", padx=3, pady=(0, 4))

        self.aa_widgets = {}
        left_items = ALL_RESIDUES[:14]
        right_items = ALL_RESIDUES[14:]

        def add_row(base_row, col_offset, item):
            aa3, aa1, fullname = item
            lab = ttk.Label(inner, text=f"{aa3} ({aa1})", style="Card.TLabel")
            lab.grid(row=base_row, column=col_offset + 0, padx=(2 if col_offset == 0 else 16, 6), pady=2, sticky="w")
            Tooltip(lab, fullname)

            cb = ttk.Combobox(inner, values=NOTE_NAMES, width=5, state="readonly")
            cb.grid(row=base_row, column=col_offset + 1, padx=3, pady=2, sticky="w")
            oe = ttk.Entry(inner, width=3)
            oe.grid(row=base_row, column=col_offset + 2, padx=3, pady=2, sticky="w")
            self.aa_widgets[aa3] = {"note": cb, "oct": oe}

        for i, item in enumerate(left_items, start=1):
            add_row(i, 0, item)
        for i, item in enumerate(right_items, start=1):
            add_row(i, 3, item)

        self.init_music_options()
        self.reset_aa_defaults()

        ttk.Separator(box, orient="horizontal").pack(fill="x", pady=(10, 10))
        bottom = ttk.Frame(box, style="Card.TFrame")
        bottom.pack(fill="x")
        ttk.Button(
            bottom, text="Generate Audio", command=self.generate_audio,
            style="Accent.TButton"
        ).pack(side="right")

    def init_music_options(self):
        # Options object
        self.music_opts = MusicOptions()

        # --- Amino-acid grid defaults used by Reset Defaults ---
        self.adv_scale_var = tk.StringVar(value=self.music_opts.default_scale_name)
        self.adv_base_octave_var = tk.IntVar(value=self.music_opts.default_base_octave)

        # --- Mapping ---
        self._mapping_mode = tk.StringVar(value=self.music_opts.mapping_mode)  # "aa" | "property" | "single"

        # Property panel
        self._prop_dimension = tk.StringVar(value=getattr(self.music_opts, "property_dimension", "hydrophobicity"))
        self._prop_octave = tk.IntVar(value=getattr(self.music_opts, "property_base_octave", 4))
        self._prop_triad_vars = {}

        # Amino-acid grid sub-options
        self._chord_mode = tk.StringVar(value=self.music_opts.chord_mode)
        self._aa_triad = tk.StringVar(value=getattr(self.music_opts, "aa_triad_name", "Major (I)"))

        # Single aapanel
        self._single_code = tk.StringVar(value=self.music_opts.single_aa_code)
        self._single_triad = tk.StringVar(value=self.music_opts.single_triad_name)
        self._single_octave = tk.IntVar(value=self.music_opts.single_base_octave)
        self._single_others = tk.StringVar(value=self.music_opts.single_others_policy)  # "rest" | "skip"

        # --- Performance / Dynamics ---
        self._vel_mode = tk.StringVar(value=self.music_opts.velocity_mode)  # constant | by_frequency
        self._vel_const = tk.IntVar(value=self.music_opts.velocity_constant)
        self._velocity_min = tk.IntVar(value=getattr(self.music_opts, "velocity_min", 45))
        self._velocity_max = tk.IntVar(value=getattr(self.music_opts, "velocity_max", 120))

        # --- Pitch Range ---
        self._transpose = tk.IntVar(value=self.music_opts.transpose)
        self._clamp_lo = tk.IntVar(value=self.music_opts.clamp_low)
        self._clamp_hi = tk.IntVar(value=self.music_opts.clamp_high)

        # --- Output grouping / Representation of aaFrequencies ---
        # sadece: per_path | per_pair | per_pdb
        self._rep_res_freq = tk.StringVar(value=getattr(self.music_opts, "rep_res_freq", "per_pdb"))

        # --- Rhythm: convert BPM, note value, and rest ratio into beats ---
        self._tempo_var = tk.IntVar(value=self.music_opts.tempo_bpm)
        self._note_value = tk.StringVar(value="Quarter (1/4)")  # UI etiketi
        self._rest_ratio = tk.DoubleVar(value=0.25)  # note_length * rest_ratio

        # Translate current beat values into UI labels
        beats = float(self.music_opts.note_beats or 1.0)
        _cands = [(4.0, "Whole (1/1)"), (2.0, "Half (1/2)"), (1.0, "Quarter (1/4)"),
                  (0.5, "Eighth (1/8)"), (0.25, "Sixteenth (1/16)")]
        self._note_value.set(min(_cands, key=lambda x: abs(x[0] - beats))[1])

        # rest_ratio set
        if beats > 0:
            self._rest_ratio.set(round((self.music_opts.rest_beats or 0.25) / beats, 2))

    def open_music_advanced(self):
        # One-window rule +
        import tkinter as tk
        from tkinter import ttk, messagebox

        if hasattr(self, "_adv_win") and self._adv_win and tk.Toplevel.winfo_exists(self._adv_win):
            self._adv_win.lift()
            return

        # --- ensure tk.Variables exist (idempotent) ---
        def _ensure(var_name, factory):
            if not hasattr(self, var_name) or getattr(self, var_name) is None:
                setattr(self, var_name, factory())
            return getattr(self, var_name)

        if not hasattr(self, "music_opts"):
            self.music_opts = MusicOptions()

        # ===== tk variables (create BEFORE building UI) =====
        # aagrid defaults
        _ensure("adv_scale_var", lambda: tk.StringVar(value=self.music_opts.default_scale_name))
        _ensure("adv_base_octave_var", lambda: tk.IntVar(value=self.music_opts.default_base_octave))

        # Structure / output
        _ensure("_rep_res_freq", lambda: tk.StringVar(value=self.music_opts.rep_res_freq))
        _ensure("_mapping_mode", lambda: tk.StringVar(value=getattr(self.music_opts, "mapping_mode", "aa")))

        # AA-grid suboptions
        _ensure("_chord_mode", lambda: tk.StringVar(value=getattr(self.music_opts, "chord_mode", "single")))
        _ensure("_aa_triad", lambda: tk.StringVar(value=getattr(self.music_opts, "aa_triad_name", "Major (I)")))

        # Property
        _ensure("_prop_dimension",
                lambda: tk.StringVar(value=getattr(self.music_opts, "property_dimension", "hydrophobicity")))
        _ensure("_prop_octave", lambda: tk.IntVar(value=getattr(self.music_opts, "property_base_octave", 4)))

        # Single
        _ensure("_single_code", lambda: tk.StringVar(value=getattr(self.music_opts, "single_aa_code", "K")))
        _ensure("_single_triad", lambda: tk.StringVar(value=getattr(self.music_opts, "single_triad_name", "Major (I)")))
        _ensure("_single_octave", lambda: tk.IntVar(value=getattr(self.music_opts, "single_base_octave", 4)))
        _ensure("_single_others", lambda: tk.StringVar(value=getattr(self.music_opts, "single_others_policy", "rest")))

        # Instrument & dynamics
        _ensure("_program_var", lambda: tk.IntVar(value=self.music_opts.program))
        _ensure("_vel_mode", lambda: tk.StringVar(value=self.music_opts.velocity_mode))  # constant | by_frequency
        _ensure("_vel_const", lambda: tk.IntVar(value=self.music_opts.velocity_constant))

        # Velocity range
        _ensure("_velocity_min", lambda: tk.IntVar(value=getattr(self.music_opts, "velocity_min", 30)))
        _ensure("_velocity_max", lambda: tk.IntVar(value=getattr(self.music_opts, "velocity_max", 110)))

        # Pitch Range
        _ensure("_transpose", lambda: tk.IntVar(value=self.music_opts.transpose))
        _ensure("_clamp_lo", lambda: tk.IntVar(value=self.music_opts.clamp_low))
        _ensure("_clamp_hi", lambda: tk.IntVar(value=self.music_opts.clamp_high))

        # Rhythm
        def _label_for_beats(_b):
            return {4.0: "Whole (1/1)", 2.0: "Half (1/2)", 1.0: "Quarter (1/4)", 0.5: "Eighth (1/8)",
                    0.25: "Sixteenth (1/16)"} \
                .get(float(self.music_opts.note_beats or 1.0), "Quarter (1/4)")

        _ensure("_tempo_var", lambda: tk.IntVar(value=self.music_opts.tempo_bpm))
        _ensure("_note_value", lambda: tk.StringVar(value=_label_for_beats(self.music_opts.note_beats)))
        _ensure("_rest_ratio", lambda: tk.DoubleVar(
            value=max(0.0,
                      float(self.music_opts.rest_beats or 0.25) / max(0.25, float(self.music_opts.note_beats or 1.0)))
        ))

        # Triad presets
        from MUSIKALL_functions1 import get_triad_presets
        triad_names = list(get_triad_presets().keys())

        # ===== window =====
        P = self.current_palette
        w = tk.Toplevel(self)
        self._adv_win = w
        w.title("Advanced Music Options")
        w.configure(bg=P["bg"])

        # --- placement (no animation) ---
        win_w, win_h = 700, 760
        self.update_idletasks()
        par_x, par_y, par_w = self.winfo_rootx(), self.winfo_rooty(), self.winfo_width()
        target_x = par_x + max(0, (par_w - win_w) // 2)
        target_y = max(40, par_y + 60)
        w.geometry(f"{win_w}x{win_h}+{target_x}+{target_y}")
        w.resizable(True, True)

        # theme
        style = ttk.Style(w)
        style.configure("TFrame", background=P["bg"])
        style.configure("TLabel", background=P["bg"], foreground=P.get("fg", "#000"))
        style.configure("Card.TFrame", background=P["bg"])
        style.configure("Card.TLabelframe", background=P["bg"])
        style.configure("Card.TLabelframe.Label", background=P["bg"], foreground=P.get("fg", "#000"))
        style.configure("Card.TLabel", background=P["bg"], foreground=P.get("fg", "#000"))
        style.configure("CardHeader.TLabel", background=P["bg"], foreground=P.get("fg", "#000"),
                        font=("Segoe UI", 10, "bold"))

        # ===== layout: scrollable center + fixed footer =====
        outer = ttk.Frame(w, style="Card.TFrame") 
        outer.pack(fill="both", expand=True)
        sc = ttk.Frame(outer, style="Card.TFrame") 
        sc.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(sc, bg=P["bg"], highlightthickness=0)
        vbar = ttk.Scrollbar(sc, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, style="Card.TFrame")
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side="left", fill="both", expand=True) 
        vbar.pack(side="right", fill="y")

        def _on_inner_config(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_config(_=None):
            canvas.itemconfigure(inner_id, width=canvas.winfo_width())

        inner.bind("<Configure>", _on_inner_config)
        canvas.bind("<Configure>", _on_canvas_config)

        footer = ttk.Frame(outer, style="Card.TFrame") 
        footer.pack(side="bottom", fill="x")

        # helpers
        row = 0

        def head(text):
            nonlocal row
            ttk.Label(inner, text=text, style="CardHeader.TLabel").grid(row=row, column=0, sticky="w", padx=8,
                                                                        pady=(10, 4))
            row += 1

        def line(lbl):
            nonlocal row
            fr = ttk.Frame(inner, style="Card.TFrame") 
            fr.grid(row=row, column=0, sticky="w", padx=8, pady=4)
            ttk.Label(fr, text=lbl, style="Card.TLabel").pack(side="left")
            row += 1
            return fr

        def tip(fr, text):
            ib = tk.Label(fr, text="ⓘ", fg=P["accent"], bg=P["bg"], cursor="question_arrow")
            Tooltip(ib, text) 
            ib.pack(side="left", padx=(6, 0))  # Tooltip objen varsa

        def _note_value_to_beats(label: str) -> float:
            return {"Whole (1/1)": 4.0, "Half (1/2)": 2.0, "Quarter (1/4)": 1.0, "Eighth (1/8)": 0.5,
                    "Sixteenth (1/16)": 0.25}.get(label, 1.0)

        # ===== Output Structure =====
        head("🏗 Output Structure")
        fr = ttk.Frame(inner, style="Card.TFrame") 
        fr.grid(row=row, column=0, sticky="w", padx=8, pady=4) 
        row += 1

        ttk.Label(fr, text="Output grouping", style="Card.TLabel").pack(side="left")
        tip(fr, "How files are grouped: per_path, per_pair, or per_pdb.")
        ttk.Combobox(fr, textvariable=self._rep_res_freq, state="readonly",
                     values=["per_path", "per_pair", "per_pdb"], width=14).pack(side="left", padx=8)

        ttk.Label(fr, text="Mapping mode", style="Card.TLabel").pack(side="left", padx=(12, 0))
        tip(fr, "aa: residue-identity grid; property: biochemical-class harmony; single: focus on one residue type.")
        cb_map = ttk.Combobox(fr, textvariable=self._mapping_mode, state="readonly",
                              values=["aa", "property", "single"], width=12)
        cb_map.pack(side="left", padx=8)

        ttk.Label(fr, text="Velocity", style="Card.TLabel").pack(side="left", padx=(12, 0))
        tip(fr, "constant: fixed loudness\nby_frequency: more frequent residues play louder (normalized).")
        cb_vel = ttk.Combobox(fr, textvariable=self._vel_mode, state="readonly",
                              values=["constant", "by_frequency"], width=12)
        cb_vel.pack(side="left", padx=8)

        # ===== Mapping (slot + 3 panels) =====
        head("🧭 Mapping")
        map_slot = ttk.Frame(inner, style="Card.TFrame") 
        map_slot.grid(row=row, column=0, sticky="we", padx=8, pady=(4, 6)) 
        row += 1
        aa_frame = ttk.Labelframe(map_slot, text="AA Grid (identity → root)", padding=(6, 6), style="Card.TLabelframe")
        prop_frame = ttk.Labelframe(map_slot, text="Property-based harmony", padding=(6, 6), style="Card.TLabelframe")
        single_frame = ttk.Labelframe(map_slot, text="Single-Residue Focus", padding=(6, 6), style="Card.TLabelframe")

        # -- ResidueGRID PANEL --
        fr_aa= ttk.Frame(aa_frame, style="Card.TFrame") 
        fr_aa.pack(fill="x", pady=2)
        ttk.Label(fr_aa, text="Chord mode", style="Card.TLabel").pack(side="left")
        tip(fr_aa, "single: root only  triad: build a chord on the same root.")
        cb_chmode = ttk.Combobox(fr_aa, textvariable=self._chord_mode, state="readonly",
                                 values=["single", "triad"], width=12)
        cb_chmode.pack(side="left", padx=8)

        fr_aa_tri = ttk.Frame(aa_frame, style="Card.TFrame") 
        fr_aa_tri.pack(fill="x", pady=2)
        ttk.Label(fr_aa_tri, text="Residue triad", style="Card.TLabel").pack(side="left")
        ttk.Combobox(fr_aa_tri, textvariable=self._aa_triad, state="readonly",
                     values=triad_names, width=18).pack(side="left", padx=8)

        def _refresh_aa_triad_row(*_):
            if (self._chord_mode.get() or "single") == "triad":
                fr_aa_tri.pack(fill="x", pady=2)
            else:
                fr_aa_tri.pack_forget()

        _refresh_aa_triad_row()
        cb_chmode.bind("<<ComboboxSelected>>", _refresh_aa_triad_row)

        # -- PROPERTY PANEL --
        fr_dim = ttk.Frame(prop_frame, style="Card.TFrame") 
        fr_dim.pack(fill="x", pady=2)
        ttk.Label(fr_dim, text="Property dimension", style="Card.TLabel").pack(side="left")
        tip(fr_dim, "hydrophobicity, charge, or aromaticity")
        dim_cb = ttk.Combobox(fr_dim, textvariable=self._prop_dimension, state="readonly",
                              values=["hydrophobicity", "charge", "aromaticity", "polarity"], width=18)
        dim_cb.pack(side="left", padx=8)

        fr_oct = ttk.Frame(prop_frame, style="Card.TFrame") 
        fr_oct.pack(fill="x", pady=2)
        ttk.Label(fr_oct, text="Fallback base octave", style="Card.TLabel").pack(side="left")
        tip(fr_oct, "If residue grid has no root for a token, use C at this octave.")
        tk.Entry(fr_oct, textvariable=self._prop_octave, width=6,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left", padx=8)

        triad_rows = ttk.Frame(prop_frame, style="Card.TFrame") 
        triad_rows.pack(fill="x", pady=(6, 2))
        self._prop_triad_vars = {}

        def _build_triad_rows():
            for c in triad_rows.winfo_children():
                c.destroy()
            self._prop_triad_vars.clear()
            dim = self._prop_dimension.get()
            classes = {
                "hydrophobicity": ["hydrophobic", "hydrophilic"],
                "charge": ["positive", "negative", "neutral"],
                "aromaticity": ["aromatic", "nonaromatic"],
                "polarity": ["polar", "nonpolar"],
            }.get(dim, [])
            saved_map = getattr(self.music_opts, "property_triads", {}) or {}
            saved_for_dim = saved_map.get(dim, {}) if isinstance(saved_map, dict) else {}
            for cls in classes:
                r = ttk.Frame(triad_rows, style="Card.TFrame") 
                r.pack(fill="x", pady=2)
                ttk.Label(r, text=f"{cls} triad", style="Card.TLabel").pack(side="left")
                v = tk.StringVar(value=saved_for_dim.get(cls, "Major (I)"))
                ttk.Combobox(r, textvariable=v, state="readonly", values=triad_names, width=18).pack(side="left",
                                                                                                     padx=8)
                self._prop_triad_vars[cls] = v

        dim_cb.bind("<<ComboboxSelected>>", lambda _e: _build_triad_rows())

        # -- SINGLE ResiduePANEL --
        fr_s1 = ttk.Frame(single_frame, style="Card.TFrame") 
        fr_s1.pack(fill="x", pady=2)
        ttk.Label(fr_s1, text="Residue (one-letter)", style="Card.TLabel").pack(side="left")
        tip(fr_s1, "Only this residue type plays; all others are rendered as rests or skipped.")
        tk.Entry(fr_s1, textvariable=self._single_code, width=4,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left", padx=8)

        fr_s2 = ttk.Frame(single_frame, style="Card.TFrame") 
        fr_s2.pack(fill="x", pady=2)
        ttk.Label(fr_s2, text="Triad", style="Card.TLabel").pack(side="left")
        ttk.Combobox(fr_s2, textvariable=self._single_triad, state="readonly",
                     values=triad_names, width=18).pack(side="left", padx=8)

        fr_s3 = ttk.Frame(single_frame, style="Card.TFrame") 
        fr_s3.pack(fill="x", pady=2)
        ttk.Label(fr_s3, text="Base octave", style="Card.TLabel").pack(side="left")
        tk.Entry(fr_s3, textvariable=self._single_octave, width=6,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left", padx=8)

        fr_s4 = ttk.Frame(single_frame, style="Card.TFrame") 
        fr_s4.pack(fill="x", pady=2)
        ttk.Label(fr_s4, text="Others", style="Card.TLabel").pack(side="left")
        ttk.Combobox(fr_s4, textvariable=self._single_others, state="readonly",
                     values=["rest", "skip"], width=10).pack(side="left", padx=8)

        # pack default panel
        def _refresh_mapping_panels():
            for f in (aa_frame, prop_frame, single_frame):
                try:
                    f.grid_remove()
                except:
                    pass
            mode = (self._mapping_mode.get() or "aa").lower()
            (aa_frame if mode == "aa" else prop_frame if mode == "property" else single_frame) \
                .grid(row=0, column=0, sticky="we")

        _build_triad_rows()
        _refresh_mapping_panels()
        cb_map.bind("<<ComboboxSelected>>", lambda _e: _refresh_mapping_panels())

        # ===== Instrument & Dynamics =====
        head("🎚 Instrument & Dynamics")
        fr_prog = line("Instrument (MIDI Program)")
        tip(fr_prog, "0: Piano, 40: Violin, 73: Flute …")
        tk.Entry(fr_prog, textvariable=self._program_var, width=6,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left", padx=8)

        fr_vel = line("Velocity")
        tip(fr_vel, "constant: fixed loudness\nby_frequency: residues with higher normalized frequency play louder.")
        ttk.Combobox(fr_vel, textvariable=self._vel_mode, state="readonly",
                     values=["constant", "by_frequency"], width=12).pack(side="left", padx=8)

        fr_cvel = line("Constant velocity")
        tip(fr_cvel, "Used only when mode=constant. Range: 1–127.")
        self._vel_const_entry = tk.Entry(fr_cvel, textvariable=self._vel_const, width=6,
                                         bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000"))
        self._vel_const_entry.pack(side="left", padx=8)

        # Velocity range (by_frequency)
        fr_vrc = line("Velocity range ")
        ttk.Label(fr_vrc, text="Min", style="Card.TLabel").pack(side="left", padx=(8, 4))
        tk.Entry(fr_vrc, textvariable=self._velocity_min, width=4,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left")
        ttk.Label(fr_vrc, text="Max", style="Card.TLabel").pack(side="left", padx=(8, 4))
        tk.Entry(fr_vrc, textvariable=self._velocity_max, width=4,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left")

        def _refresh_velocity_rows(*_):
            vm = (self._vel_mode.get() or "constant").lower()
            try:
                self._vel_const_entry.configure(state=("normal" if vm == "constant" else "disabled"))
            except:
                pass
            for child in fr_vrc.winfo_children():
                try:
                    child.configure(state=("normal" if vm == "by_frequency" else "disabled"))
                except:
                    pass

        _refresh_velocity_rows()
        cb_vel.bind("<<ComboboxSelected>>", _refresh_velocity_rows)

        # ===== Pitch Range =====
        head("🎼 Pitch Range")
        fr_tr = line("Transpose (semitones)")
        tip(fr_tr, "Shift all notes by ±12/24 semitones.")
        tk.Entry(fr_tr, textvariable=self._transpose, width=6,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left", padx=8)

        fr_cl = line("Clamp octaves [low–high]")
        tip(fr_cl, "Limit notes to a target octave span, e.g., 3–6.")
        tk.Entry(fr_cl, textvariable=self._clamp_lo, width=4,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left",
                                                                                                padx=(8, 4))
        ttk.Label(fr_cl, text="–", style="Card.TLabel").pack(side="left")
        tk.Entry(fr_cl, textvariable=self._clamp_hi, width=4,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left",
                                                                                                padx=(4, 8))

        # ===== Rhythm =====
        head("⏱ Rhythm")
        fr_bp = line("Tempo (BPM)")
        tip(fr_bp, "Beats per minute.")
        tk.Entry(fr_bp, textvariable=self._tempo_var, width=6,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left", padx=8)

        fr_nv = line("Note value")
        tip(fr_nv, "Whole, Half, Quarter, Eighth, or Sixteenth.")
        ttk.Combobox(fr_nv, textvariable=self._note_value, state="readonly",
                     values=["Whole (1/1)", "Half (1/2)", "Quarter (1/4)", "Eighth (1/8)", "Sixteenth (1/16)"],
                     width=16).pack(side="left", padx=8)

        fr_rr = line("Rest ratio")
        tip(fr_rr, "Rest duration = note_value * rest_ratio.")
        tk.Entry(fr_rr, textvariable=self._rest_ratio, width=6,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left", padx=8)

        # ===== Residue Grid Defaults =====
        head("⚙ Residue Grid Defaults")
        fr_sc = line("Scale")
        tip(fr_sc, "Scale used by ‘Reset Defaults’ to (re)fill the residue grid.")
        ttk.Combobox(fr_sc, textvariable=self.adv_scale_var, state="readonly",
                     values=["Chromatic (C)", "Major (C)", "Minor (A)"], width=16).pack(side="left", padx=8)

        fr_bo = line("Base octave")
        tip(fr_bo, "Base octave used by ‘Reset Defaults’.")
        tk.Entry(fr_bo, textvariable=self.adv_base_octave_var, width=6,
                 bg=P["bg"], fg=P.get("fg", "#000"), insertbackground=P.get("fg", "#000")).pack(side="left", padx=8)

        # ===== Footer buttons (always visible) =====
        def _apply():
            # Structure
            self.music_opts.rep_res_freq = (self._rep_res_freq.get() or "per_pdb")

            # Mapping + residue grid
            self.music_opts.mapping_mode = (self._mapping_mode.get() or "aa")
            self.music_opts.chord_mode = (self._chord_mode.get() or "single")
            self.music_opts.aa_triad_name = (self._aa_triad.get() or "Major (I)")
            self.music_opts.default_scale_name = self.adv_scale_var.get()
            self.music_opts.default_base_octave = int(self.adv_base_octave_var.get() or 4)

            # Property
            self.music_opts.property_dimension = (self._prop_dimension.get() or "hydrophobicity")
            self.music_opts.property_base_octave = int(self._prop_octave.get() or 4)
            tri_map = dict(getattr(self.music_opts, "property_triads", {}) or {})
            dim = self.music_opts.property_dimension
            tri_map[dim] = {cls: var.get() for cls, var in getattr(self, "_prop_triad_vars", {}).items()}
            self.music_opts.property_triads = tri_map

            # Single
            self.music_opts.single_aa_code = (self._single_code.get().strip().upper()[:1] or "K")
            self.music_opts.single_triad_name = (self._single_triad.get() or "Major (I)")
            self.music_opts.single_base_octave = int(self._single_octave.get() or 4)
            self.music_opts.single_others_policy = (self._single_others.get() or "rest")

            # Instrument & dynamics
            self.music_opts.program = int(self._program_var.get() or 0)
            self.music_opts.velocity_mode = (self._vel_mode.get() or "constant")
            self.music_opts.velocity_constant = int(self._vel_const.get() or 90)
            self.music_opts.velocity_min = int(self._velocity_min.get() or 30)
            self.music_opts.velocity_max = int(self._velocity_max.get() or 110)

            # Pitch
            self.music_opts.transpose = int(self._transpose.get() or 0)
            self.music_opts.clamp_low = int(self._clamp_lo.get() or 3)
            self.music_opts.clamp_high = int(self._clamp_hi.get() or 6)

            # Rhythm
            self.music_opts.tempo_bpm = int(self._tempo_var.get() or 120)
            self.music_opts.note_beats = _note_value_to_beats(self._note_value.get())
            rr = float(self._rest_ratio.get() or 0.25)
            self.music_opts.rest_beats = max(0.0, self.music_opts.note_beats * rr)

            messagebox.showinfo("Advanced Options", "Saved.")

        def _apply_and_reset():
            _apply()
            self.reset_aa_defaults()

        btns = ttk.Frame(footer, style="Card.TFrame") 
        btns.pack(side="left", padx=8, pady=8)
        ttk.Button(btns, text="Save", command=_apply).pack(side="left", padx=6)
        ttk.Button(btns, text="Save & Reset Residue Defaults", command=_apply_and_reset).pack(side="left", padx=6)

        # ===== finalize mapping panels initial state =====
        _refresh_aa_triad_row()

    #######
    def save_colored_pdbs(self):
        """Saves per-PDB colored structures AND a GLOBAL/TOTAL colored reference PDB into the job root."""
        import threading
        from tkinter import messagebox

        jobname = self.jobname_entry.get().strip()
        if not jobname:
            messagebox.showerror("Error", "Please create a job first!")
            return

        self.log_output("🎨 Saving Colored PDBs (per-PDB + GLOBAL/TOTAL)...\n")

        threading.Thread(
            target=self.threaded_save_colored_pdbs,
            args=(jobname,),
            daemon=True
        ).start()

    def threaded_save_colored_pdbs(self, jobname_or_path):
        """
        1) Write per-PDB colored models into:
             <job>/<pdb_base>/<pdb_base>_colored.pdb    (and mmCIF if your function supports it)
           using self.all_normalized_frequencies

        2) Write ONE reference PDB colored by GLOBAL/TOTAL across all conformers into:
             <job>/GLOBAL_TOTAL__<refbase>__colored.pdb
           using self.paths_dict_2
        """
        import os

        try:
            # --- guards ---
            if not jobname_or_path:
                self.log_output("⚠️ Please create a job first.\n")
                return

            if not getattr(self, "all_normalized_frequencies", None):
                self.log_output("⚠️ Run 'Calculate Paths' first (normalized frequencies missing).\n")
                return

            if not getattr(self, "pdb_info_dict", None):
                self.log_output("⚠️ pdb_info_dict is missing. Please (re)load PDB files first.\n")
                return

            # --- resolve job_dir robustly (accepts either job name or an absolute job path) ---
            try:
                from MUSIKALL_functions1 import _job_dir_and_label
            except Exception as e:
                self.log_output(f"❌ Cannot import _job_dir_and_label from MUSIKALL_functions1: {e}\n")
                return

            if isinstance(jobname_or_path, str) and os.path.isdir(jobname_or_path):
                job_dir = jobname_or_path
            else:
                job_dir, _ = _job_dir_and_label(jobname_or_path)

            pdb_dir = os.path.join(job_dir, "pdb_files")
            if not os.path.isdir(pdb_dir):
                self.log_output(f"❌ PDB folder not found: {pdb_dir}\n")
                return

            self.log_output(f"📁 Job dir: {job_dir}\n")
            self.log_output(f"📁 PDB dir: {pdb_dir}\n")

            # --- 1) per-PDB colored models ---
            try:
                from MUSIKALL_functions1 import save_colored_pdbs as pr_save_colored_pdbs
                pr_save_colored_pdbs(
                    job_dir,
                    self.all_normalized_frequencies,
                    pdb_info_dict=self.pdb_info_dict,
                    logger=self,
                    paths_dict_2=getattr(self, "paths_dict_2", None)
                )

                self.log_output("🎨 Per-PDB colored models saved.\n")
            except Exception as e:
                self.log_output(f"❌ Per-PDB coloring failed: {e}\n")

            # --- 2) GLOBAL/TOTAL colored reference PDB into job root ---
            try:
                from MUSIKALL_functions1 import (
                    save_global_total_colored_reference_pdb as pr_save_global_total
                )
                paths_dict_2 = getattr(self, "paths_dict_2", None) or {}

                pr_save_global_total(
                    job_dir,  # IMPORTANT: pass resolved folder path
                    paths_dict_2,
                    reference_pdb=None,  # default: first .pdb in <job>/pdb_files
                    logger=self
                )
                self.log_output("🎨 GLOBAL/TOTAL colored reference PDB saved in the job folder.\n")
            except Exception as e:
                self.log_output(f"⚠️ GLOBAL/TOTAL coloring skipped: {e}\n")

            # Refresh the interactive viewer cache after writing colored models.
            self.build_interactive_cache(force=True)

        except Exception as e:
            self.log_output(f"❌ Error saving colored PDBs: {e}\n")

    def show_3d_structures(self):
        import os
        import sys
        import subprocess
        from tkinter import messagebox

        if not self.jobname_entry.get().strip():
            messagebox.showerror("Error", "Please create a job first!")
            return

        if not getattr(self, "paths_dict_2", None):
            messagebox.showerror("Error", "Please calculate shortest paths first!")
            return

        if not self._interactive_cache_ready:
            if not self._interactive_cache_building:
                self.build_interactive_cache()
            messagebox.showinfo(
                "Viewer is preparing",
                "Interactive viewer files are being prepared in the background.\nPlease try again in a moment."
            )
            return

        html_files = [
            self._interactive_cache[k]
            for k in sorted(self._interactive_cache.keys())
            if os.path.exists(self._interactive_cache[k])
        ]

        if not html_files:
            messagebox.showerror("Error", "No interactive viewer files are ready.")
            return

        if hasattr(self, "_viewer_proc") and self._viewer_proc is not None:
            try:
                if self._viewer_proc.poll() is None:
                    self.log_output("ℹ Interactive viewer is already open.\n")
                    return
            except Exception:
                pass

        try:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
                viewer_exe = os.path.join(
                    os.path.dirname(sys.executable),
                    "MUSIKALL_3d_viewer.exe"
                )

                if not os.path.exists(viewer_exe):
                    messagebox.showerror(
                        "Error",
                        f"3D viewer executable not found:\n{viewer_exe}"
                    )
                    return

                cmd = [viewer_exe] + html_files

            else:
                viewer_script = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "MUSIKALL_3d_viewer.py"
                )

                if not os.path.exists(viewer_script):
                    messagebox.showerror(
                        "Error",
                        f"Viewer script not found:\n{viewer_script}"
                    )
                    return

                cmd = [sys.executable, viewer_script] + html_files

            self._viewer_proc = subprocess.Popen(cmd)
            self.log_output("✅ Interactive viewer opened instantly from cache.\n")

        except Exception as e:
            messagebox.showerror("Error", f"Could not open 3D viewer:\n{e}")
            self.log_output(f"❌ Could not open 3D viewer: {e}\n")

    def _draw_backbone_preview(self, parent_frame, structure,
                               start_residues=None, end_residues=None,
                               freq_map=None):
        """
        Offline 3D preview using a C-alpha polyline and frequency-colored beads.
        - Bead size scales with frequency while retaining a visible baseline at f=0.
        - Start/End nodes use outlined triangles with dedicated labels.
        - Micro-labels are small, bead-colored, and drawn behind the beads;
          press L to toggle labels and D to change decluttering density.
        """
        self._lazy_matplotlib()

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib import cm
        from matplotlib import colors as mcolors
        
        # --- Helper: start/end set used to suppress micro-labels ---
        def _norm_keys(res_list):
            S = set()
            if not res_list:
                return S
            for ch, rn in res_list:
                chs = str(ch).strip()
                rns = str(rn).strip()
                digits = "".join(filter(str.isdigit, rns))
                S.add((chs, rns))
                if digits:
                    S.add((chs, digits))
            return S

        START_KEYS = _norm_keys(start_residues)
        END_KEYS = _norm_keys(end_residues)
        SKIP_KEYS = START_KEYS | END_KEYS

        # --- 1) C-alpha coordinates ---
        chains = {}
        try:
            for model in structure:
                for chain in model:
                    pts = []
                    for res in chain:
                        if res.id[0] != ' ':
                            continue
                        if res.has_id("CA"):
                            p = res["CA"].coord
                        else:
                            coords = [a.coord for a in res]
                            p = (sum(coords) / len(coords)) if coords else None
                        if p is None:
                            continue
                        x, y, z = map(float, p)
                        resseq = int(res.id[1])
                        icode = (res.id[2] or '').strip()
                        rid = f"{resseq}{icode}"
                        pts.append((x, y, z, chain.id, rid))
                    if pts:
                        chains[chain.id] = pts
        except Exception:
            chains = {}

        if not chains:
            fig = Figure(figsize=(6, 5), dpi=100)
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No valid Cα data.", ha="center", va="center",
                    fontsize=11, color="#666", transform=ax.transAxes)
            ax.axis("off")
            canvas = FigureCanvasTkAgg(fig, master=parent_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            if not hasattr(self, "_embedded_canvases"):
                self._embedded_canvases = []
            self._embedded_canvases.append(canvas)
            return canvas

        # --- 2) Frekans normalize 0–1 ---
        lookup = {}
        orig_pct = {}  # retain original percentage values

        if isinstance(freq_map, dict) and freq_map:
            tmp = {}
            for k, v in freq_map.items():
                try:
                    if isinstance(k, str) and ":" in k:
                        ch, rn = k.split(":", 1)
                        tmp[(ch.strip(), str(rn).strip())] = float(v)
                    elif isinstance(k, tuple) and len(k) == 2:
                        ch, rn = k
                        tmp[(str(ch).strip(), str(rn).strip())] = float(v)
                except Exception:
                    continue

            # Interpret freq_map values as percentages on a 0–100 scale
            # Convert to 0–1 for color mapping without renormalizing by the maximum
            for key, v in tmp.items():
                v_clamped = max(0.0, min(float(v), 100.0))  # clamp to the 0–100 range
                orig_pct[key] = v_clamped  # true percentage for labels
                lookup[key] = v_clamped / 100.0  # 0–1 value for color mapping

        # --- 3) Figure and axes ---
        fig = Figure(figsize=(6, 5), dpi=100)
        ax = fig.add_subplot(111, projection="3d")

        for _, pts in chains.items():
            xs, ys, zs, _, _ = zip(*pts)
            ax.plot(xs, ys, zs, linewidth=1.1, alpha=0.65, color="#8a8a8a")

        # --- 4) Data arrays and compact labels ---
        all_x, all_y, all_z = [], [], []
        all_val, all_lbl, all_key = [], [], []
        norm = mcolors.Normalize(vmin=0.0, vmax=1.0, clip=True)
        threshold = 0.05  # Threshold for displaying frequency in labels

        for _, pts in chains.items():
            for (x, y, z, ch, rid) in pts:
                v = 0.0
                if lookup:
                    digits = "".join(filter(str.isdigit, rid))
                    v = lookup.get((ch, rid), lookup.get((ch, digits), 0.0))
                all_x.append(x)
                all_y.append(y)
                all_z.append(z)
                all_val.append(v)
                all_key.append((ch, rid))
                if v >= threshold:
                    digits = "".join(filter(str.isdigit, rid))
                    pct = orig_pct.get((ch, rid), orig_pct.get((ch, digits), 0.0))
                    all_lbl.append(f"{ch},{rid},{pct:.1f}%")
                else:
                    all_lbl.append(f"{ch},{rid}")

        all_val_arr = np.asarray(all_val, float)

        # --- 5) Micro-labels: draw first so beads remain on top ---
        from matplotlib import patheffects as pe

        def _rgba_to_hex(rgba):
            return mcolors.to_hex(rgba, keep_alpha=False)

        def _luminance(rgb):
            r, g, b = rgb[:3];  return 0.2126 * r + 0.7152 * g + 0.0722 * b

        rgba_colors = cm.plasma(norm(all_val_arr))
        hex_colors = [_rgba_to_hex(rgba) for rgba in rgba_colors]

        micro_labels = []  # bu canvasa ait list
        widget_micro_visible_default = True  # visible by default

        for i, (x, y, z) in enumerate(zip(all_x, all_y, all_z)):
            ch, rid = all_key[i]
            if (ch, rid) in SKIP_KEYS:
                micro_labels.append(None)
                continue
            rgba = rgba_colors[i]
            stroke_fg = "white" if _luminance(rgba) < 0.45 else "black"
            # small, behind the beads, clipped to the axes
            txt = ax.text(
                x, y, z, all_lbl[i],
                color=hex_colors[i],
                fontsize=6,
                zorder=1,  # low z-order keeps scatter points above labels
                clip_on=True
            )
            txt.set_path_effects([pe.withStroke(linewidth=1.2, foreground=stroke_fg, alpha=0.9)])
            micro_labels.append(txt)

        # --- 6) Scatter: draw beads above labels ---
        size_min, size_max, gamma = 110.0, 360.0, 0.65
        vals_gamma = np.power(all_val_arr, gamma)
        sizes = size_min + (size_max - size_min) * vals_gamma

        sc = ax.scatter(
            all_x, all_y, all_z,
            s=sizes,
            c=all_val_arr, cmap=cm.plasma, norm=norm,
            marker="o", depthshade=True, zorder=10  # beads in the foreground
        )
        sc.set_picker(True)

        # --- Colorbar (inset) ---
        try:
            from mpl_toolkits.axes_grid1.inset_locator import inset_axes
            ticks = np.linspace(0, 1, 5)
            cax = inset_axes(ax, width="3%", height="60%", loc="center right",
                             bbox_to_anchor=(0.08, 0.0, 1.0, 1.0),
                             bbox_transform=ax.transAxes, borderpad=0.0)
            cb = fig.colorbar(sc, cax=cax, orientation="vertical", ticks=ticks)

            # Etiketler % cinsinden
            cb.set_label("Frequency (%)", fontsize=9)
            cb.ax.set_yticklabels([f"{int(t * 100)}" for t in ticks])
            cb.ax.tick_params(labelsize=8)

        except Exception:
            pass

        # --- 7) Start/End overlay with outlined triangles and dedicated labels ---
        def _outline_residues(res_list, edge_hex, marker):
            if not res_list:
                return
            import matplotlib.patheffects as pe2
            for ch, rn in res_list:
                chs = str(ch).strip()
                rns = str(rn).strip()
                digits = "".join(filter(str.isdigit, rns))
                pts = chains.get(chs)
                if not pts:
                    continue
                target = None
                for (x, y, z, _, rid) in pts:
                    if rid == rns:
                        target = (x, y, z)
                        break
                if target is None and digits:
                    for (x, y, z, _, rid) in pts:
                        if rid == digits:
                            target = (x, y, z)
                            break
                if target is None:
                    continue
                x, y, z = target
                ax.scatter([x], [y], [z],
                           s=(sizes.mean() * 1.8),
                           facecolors="none", edgecolors=edge_hex,
                           marker=marker, linewidths=2.0,
                           depthshade=False, zorder=12)
                t = ax.text(x, y, z, f"{chs}:{rns}",
                            color=edge_hex, fontsize=9, zorder=13)
                t.set_path_effects([pe2.withStroke(linewidth=2.0, foreground="black")])

        _outline_residues(start_residues, "#00e676", "^")
        _outline_residues(end_residues, "#ff5252", "v")

        # --- 8) Axis appearance ---
        all_pts = np.column_stack([all_x, all_y, all_z]) if all_x else np.zeros((0, 3))
        if all_pts.size:
            spans = np.ptp(all_pts, axis=0)
            spans = np.where(spans == 0, 1.0, spans)
            ax.set_box_aspect(tuple(spans))
        else:
            ax.set_box_aspect((1, 1, 1))
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title("Backbone (Cα) Preview")
        ax.grid(False)
        try:
            ax.view_init(elev=18, azim=-60)
        except Exception:
            pass

        # --- 9) Canvas and keyboard shortcuts ---
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)

        # L ile mikro-etiket toggle
        def _toggle_micro_labels(event=None):
            nonlocal widget_micro_visible_default
            widget_micro_visible_default = not widget_micro_visible_default
            for t in micro_labels:
                if t is not None:
                    t.set_visible(widget_micro_visible_default)
            canvas.draw_idle()

        widget.bind("<Key-l>", _toggle_micro_labels)
        widget.bind("<Key-L>", _toggle_micro_labels)
        widget.focus_set()

        # --- 10) Decluttering and density mode controlled by D ---
        import numpy as _np
        from matplotlib.transforms import Bbox
        prior_idx = _np.argsort(-vals_gamma)  # highest frequency first
        density_modes = [("Dense", 2), ("Smart", 8), ("Sparse", 16)]
        widget._label_density_mode = 1

        def _rects_intersect(a: Bbox, b: Bbox):
            return (a.x0 < b.x1 and a.x1 > b.x0 and a.y0 < b.y1 and a.y1 > b.y0)

        def _inflate_bbox(bb: Bbox, pad):
            return Bbox.from_extents(bb.x0 - pad, bb.y0 - pad, bb.x1 + pad, bb.y1 + pad)

        def _declutter_labels(event=None):
            if not micro_labels:
                return
            renderer = canvas.get_renderer()
            _, pad = density_modes[widget._label_density_mode]
            taken = []
            # Start with all valid labels visible
            for t in micro_labels:
                if t is not None:
                    t.set_visible(True)
            # Hide overlapping labels according to priority
            for i in prior_idx:
                t = micro_labels[i]
                if t is None or (not t.get_visible()):
                    continue
                bb = t.get_window_extent(renderer=renderer)
                bb = _inflate_bbox(bb, pad)
                if any(_rects_intersect(bb, r) for r in taken):
                    t.set_visible(False)
                else:
                    taken.append(bb)
            canvas.draw_idle()

        canvas.mpl_connect("draw_event", _declutter_labels)

        def _cycle_density(event=None):
            widget._label_density_mode = (widget._label_density_mode + 1) % len(density_modes)
            _declutter_labels()

        widget.bind("<Key-d>", _cycle_density)
        widget.bind("<Key-D>", _cycle_density)
        _declutter_labels()  # initial layout

        # --- 11) Hover tooltip independent of micro-label visibility ---
        try:
            import mplcursors
            cur = mplcursors.cursor(sc, hover=True)

            @cur.connect("add")
            def _on_add(sel):
                i = int(sel.index)
                ann = sel.annotation
                ann.set_text(all_lbl[i])
                ann.get_bbox_patch().set(fc="black", ec="white", alpha=0.92, lw=0.8)
                ann.set_fontsize(10)
                ann.set_ha("left")
                ann.set_va("bottom")
        except Exception:
            pass

        # --- 12) Per-canvas size scaling ---
        widget._size_scale_factor = 1.0

        def _apply_size():
            new_sizes = (size_min * widget._size_scale_factor) + \
                        ((size_max * widget._size_scale_factor) - (size_min * widget._size_scale_factor)) * vals_gamma
            sc.set_sizes(new_sizes)
            canvas.draw_idle()

        def _inc_size(event=None):
            widget._size_scale_factor = min(6.0, widget._size_scale_factor + 0.25)
            _apply_size()

        def _dec_size(event=None):
            widget._size_scale_factor = max(0.25, widget._size_scale_factor - 0.25)
            _apply_size()

        widget.bind("<Control-plus>", _inc_size)
        widget.bind("<Control-KP_Add>", _inc_size)
        widget.bind("<Control-minus>", _dec_size)
        widget.bind("<Control-KP_Subtract>", _dec_size)

        if not hasattr(self, "_embedded_canvases"):
            self._embedded_canvases = []
        self._embedded_canvases.append(canvas)
        return canvas





        # Example: enable buttons if you have them
        # self.calc_paths_btn.config(state=("normal" if has_pdb else "disabled"))
        # self.save_colored_btn.config(state=("normal" if has_freq else "disabled"))
        # self.show_3d_btn.config(state=("normal" if (has_paths or has_freq) else "disabled"))

        # Also restore any listboxes/treeviews if you keep them
        # e.g., repopulate PDB list widget from self.pdb_info_dict keys.



if __name__ == "__main__":
    MUSIKALL_GUI().mainloop()
