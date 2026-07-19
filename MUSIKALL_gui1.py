import json
import threading
from tkinter import messagebox, ttk, filedialog

import matplotlib
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import ctypes
import tkinter as tk
from PIL import Image, ImageTk

def _resource_path(rel: str) -> str:

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)


def _set_windows_appid(appid: str = "MUSIKALL.App"):

    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
        except Exception:
            pass


def _qt_3d_viewer_process(tab_payloads):
    import sys
    import os

    from PySide6.QtCore import QUrl
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
    from PySide6.QtWebEngineWidgets import QWebEngineView

    class ViewerWindow(QMainWindow):
        def closeEvent(self, event):
            try:
                tabs = self.centralWidget()
                if tabs is not None:
                    for i in range(tabs.count()):
                        w = tabs.widget(i)
                        try:
                            if w is not None:
                                w.setHtml("")
                                w.deleteLater()
                        except Exception:
                            pass

                app = QApplication.instance()
                if app is not None:
                    app.quit()
            except Exception:
                pass

            event.accept()

            import os
            os._exit(0)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setQuitOnLastWindowClosed(True)

    win = ViewerWindow()
    win.setWindowTitle("3D Structures")
    win.resize(1200, 900)

    tabs = QTabWidget()
    win.setCentralWidget(tabs)

    for item in tab_payloads:
        title = item["title"]
        html = item["html"]

        view = QWebEngineView()
        view.setHtml(html, QUrl("file:///"))
        tabs.addTab(view, title)

    win.show()
    app.exec()

    os._exit(0)

from MUSIKALL_functions1 import (
    create_job_folder,
    load_pdb_files,
    run_adj_matrix,
    parse_residue_input,
    play_midi,
    stop_midi,
    MusicOptions,
    NOTE_NAMES,
    ALL_RESIDUES,
    build_default_aa_mapping,
    aa_mapping_to_residue_mapping,
    generate_audio as pr_generate_audio
)


def _unique_filename(path):

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





palettes = {
    "aqua": {
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
    "lilac": {
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
    "sunset": {
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
    "forest": {
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
    "slate": {
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
    "dark": {
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

    def __init__(self, *args, **kwargs):

            super().__init__(*args, **kwargs)

            self.title("MUSIKALL")
            self.geometry("1200x750")


            _set_windows_appid("MUSIKALL.Prod")


            ico_path = _resource_path("icon.ico")
            png_path = _resource_path("icon.png")

            self._icon_ref = None
            self.icon_image = None


            if sys.platform.startswith("win") and os.path.exists(ico_path):
                try:
                    self.iconbitmap(ico_path)
                except Exception:
                    pass


            if os.path.exists(png_path):
                try:
                    self._icon_ref = tk.PhotoImage(file=png_path)
                    self.iconphoto(True, self._icon_ref)
                except Exception:
                    try:
                        self.icon_image = Image.open(png_path)
                    except Exception:
                        self.icon_image = None

            self.set_theme(palette="aqua")
            self.create_menu()
            self.show_welcome_screen()

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
                    _base_key,
                    _resolve_job_dir,
                )

                def _viewer_key_from_token(token):
                    """
                    Exact viewer key:
                        CHAIN:RESSEQ
                        CHAIN:RESSEQICODE
                        SEG:CHAIN:RESSEQ
                        SEG:CHAIN:RESSEQICODE
                    """
                    if token is None:
                        return None
                    try:
                        parts = [p.strip() for p in str(token).split(":") if p.strip() != ""]
                        if len(parts) == 2:
                            ch, rn = parts
                            seg = ""
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

                        return f"{seg}:{ch}:{rn}" if seg else f"{ch}:{rn}"
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
                        pdb_data = self.pdb_info_dict.get(pdb_key, {})
                        orig_path = pdb_data.get("file_path")
                        if not orig_path:
                            continue

                        pdb_base = os.path.splitext(os.path.basename(orig_path))[0]

                        colored_pdb = os.path.join(job_dir, pdb_base, f"{pdb_base}_colored.pdb")
                        colored_cif = os.path.join(job_dir, pdb_base, f"{pdb_base}_colored.cif")

                        if os.path.exists(colored_pdb):
                            colored_path = colored_pdb
                        elif os.path.exists(colored_cif):
                            colored_path = colored_cif
                        else:
                            continue

                        start_residues, end_residues = extract_start_end_residues_safe(
                            self.paths_dict_2, pdb_key
                        )

                        # exact structure keys from colored model
                        _nodes, node_coords, residue_names = extract_residue_nodes_and_coords(colored_path)
                        structure_key_set = set(node_coords.keys())  # e.g. A:123 or A:123A

                        adj = pdb_data.get("adj_matrix")
                        node_index_map = pdb_data.get("node_index_map", {}) or {}

                        # graph nodes = exact precomputed graph nodes that also exist in structure
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
                                ch, rn = vk.split(":", 1)
                                graph_nodes.append([ch, rn])

                        # edges from precomputed adjacency
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
                                        if akey is None or bkey is None or akey == bkey:
                                            continue

                                        ach, arn = akey.split(":", 1)
                                        bch, brn = bkey.split(":", 1)
                                        all_edges.append([[ach, arn], [bch, brn]])
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

                        html_path = os.path.join(job_dir, pdb_base, f"{pdb_base}_interactive.html")
                        with open(html_path, "w", encoding="utf-8") as fh:
                            fh.write(html)

                        cache[pdb_key] = html_path

                    except Exception as e:
                        self.log_output(f"⚠ interactive cache failed for {pdb_key}: {e}\n")

                self._interactive_cache = cache
                self._interactive_cache_ready = True
                self.log_output("✅ Interactive viewer cache prepared.\n")

            finally:
                self._interactive_cache_building = False

        threading.Thread(target=worker, daemon=True).start()

    def _make_colorbar(self, parent_frame):

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib import cm
        from matplotlib import colors as mcolors

        fig = Figure(figsize=(0.6, 3.5), dpi=100)
        cax = fig.add_axes([0.25, 0.05, 0.5, 0.9])

        norm = mcolors.Normalize(vmin=0.0, vmax=1.0)

        sm = cm.ScalarMappable(cmap=cm.plasma, norm=norm)
        sm.set_array([])

        cb = fig.colorbar(
            sm,
            cax=cax,
            orientation='vertical',
            ticks=[0.0, 0.25, 0.5, 0.75, 1.0]
        )
        cb.set_label('Normalized Frequency (B-factor 0–1)', fontsize=8)

        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="y")

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

        matplotlib.use('TkAgg', force=True)
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        plt.rcParams['figure.max_open_warning'] = 0
        mpl.rcParams['agg.path.chunksize'] = 10000


        self._mpl_ready = True

    def set_theme(self, palette="aqua"):
        P = palettes.get(palette, palettes["aqua"])
        self.current_palette = P
        self.current_theme = palette


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


        style.configure("TFrame", background=P["bg"])
        style.configure("Card.TFrame", background=P["bg"])
        style.configure("Muted.TFrame", background=P["muted"])

        style.configure("TLabel", background=P["bg"], foreground=P["text"])
        style.configure("Sub.TLabel", background=P["bg"], foreground=P["subtext"])


        style.configure(
            "Card.TLabelframe",
            background=P["bg"],
            bordercolor=P["border"],
            relief="solid"
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=P["bg"],
            foreground=P["text"],
            font=("Arial", 11, "bold")
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
                # içindeki ham Tk Label/Frame vb. de güncellensin
                for child in w.winfo_children():
                    try:
                        if isinstance(child, (tk.Label, tk.Frame)):
                            child.configure(bg=P["bg"], fg=P["text"])
                    except Exception:
                        pass
        except Exception:
            pass

        for attr in ("welcome_frame", "main_pw", "left_col", "right_col"):
            if hasattr(self, attr):
                frame = getattr(self, attr)
                if frame and frame.winfo_exists():
                    frame.configure(bg=P["bg"])

    def recolor_raw_widgets(self):
        P = self.current_palette


        for child in self.winfo_children():
            self._recolor_recursive(child, P)


        self.configure(bg=P["bg"])


        if hasattr(self, "welcome_frame") and self.welcome_frame.winfo_exists():
            self.welcome_frame.configure(bg=P["bg"])
            for child in self.welcome_frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=P["bg"], fg=P["text"])
                elif isinstance(child, tk.Button):
                    child.configure(bg=P["accent"], fg=P["accent_fg"], activebackground=P["focus"])

        # Eğer main_pw (PanedWindow) varsa
        if hasattr(self, "main_pw") and self.main_pw.winfo_exists():
            self.main_pw.configure(bg=P["bg"])

        # Eğer sol/sağ kolon varsa
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
        "CHAIN:RES" veya "SEG:CHAIN:RES" → (seg, chain, res)
        seg yoksa "" döner.
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


    def show_welcome_screen(self):
        """Shows the welcome screen with a Start button and an improved image display."""

        self.welcome_frame = tk.Frame(self, bg=self.current_palette["bg"])
        self.welcome_frame.pack(fill="both", expand=True)

        # Başlık
        tk.Label(
            self.welcome_frame,
            text="Welcome to MUSIKALL!",
            font=("Arial", 26, "bold"),
            bg=self.current_palette["bg"],
            fg=self.current_palette["text"]
        ).pack(pady=20)

        try:
            icon_path = _resource_path("icon.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = img.resize((100, 100), Image.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                tk.Label(self.welcome_frame, image=self.logo_img,
                         bg=self.current_palette["bg"]).pack(pady=10)
        except Exception:
            pass

        tk.Label(
            self.welcome_frame,
            text="Transcribing allosteric communication pathways in protein structures to audio-visual",
            font=("Arial", 14),
            bg=self.current_palette["bg"],
            fg=self.current_palette["text"]
        ).pack(pady=10)


        ttk.Button(
            self.welcome_frame,
            text="Start",
            command=self.show_main_interface,
            style="Accent.TButton"
        ).pack(pady=20)


        try:
            welcome_path = _resource_path("welcome.png")
            if os.path.exists(welcome_path):
                img2 = Image.open(welcome_path)
                img2 = img2.resize((720, 250), Image.LANCZOS)
                self.welcome_img = ImageTk.PhotoImage(img2)
                tk.Label(self.welcome_frame, image=self.welcome_img,
                         bg=self.current_palette["bg"]).pack(pady=10)
        except Exception:
            pass

        # Copyright
        tk.Label(
            self.welcome_frame,
            text="© 2026 Kurkcuoglu Levitas Lab, Istanbul Technical University. All rights reserved.",
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


        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="💾 Save Job", command=self.save_job)
        file_menu.add_command(label="📂 Load Job", command=self.load_job)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        menu_bar.add_cascade(label="File", menu=file_menu)

        # 📖 Help Menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="📗 Quick Start", command=self.open_quick_start)
        help_menu.add_command(label="📘 User Guide", command=self.open_user_guide)
        help_menu.add_command(label="ℹ Theory & Info", command=self.open_theory_info)
        help_menu.add_command(label="🎧 Music Playground", command=self.open_music_playground)
        menu_bar.add_cascade(label="Help", menu=help_menu)


        cite_menu = tk.Menu(menu_bar, tearoff=0)
        cite_menu.add_command(label="How to Cite", command=self.show_cite)
        menu_bar.add_cascade(label="Cite", menu=cite_menu)

        Contact_menu = tk.Menu(menu_bar, tearoff=0)
        Contact_menu.add_command(label="Contact Us", command=self.show_Contact)
        menu_bar.add_cascade(label="Contact", menu=Contact_menu)

        self.config(menu=menu_bar)

    def open_quick_start(self):
        win = tk.Toplevel(self)
        win.title("📗 MUSIKALL – Quick Start")
        win.geometry("900x650")

        text = """
        # 🚀 Quick Start (MUSIKALL)

        Go from **PDB → paths → visualization → MIDI** in the minimum number of steps.

        ---

        ## 1) Create a Job
        - Enter a **Job Name**
        - Click **Create Job**
        → MUSIKALL creates a job folder; all outputs are saved there.

        ---

        ## 2) Upload PDBs
        - Click **Upload PDBs**
        - Select one or more `.pdb` files
        → Files are copied into the job’s PDB folder.

        **Tip:** Put apo/bound/mutant conformers into the **same job** for direct comparison.

        ---

        ## 3) Build the RIN (Adjacency + Edge Weights)
        - Go to **Adjacency & Edge Weights**
        - Set the **cutoff distance** (keep it the same across all structures in the job)
        - Click **Run**
        → MUSIKALL writes per-structure adjacency and edge-weight (cost) matrices in each PDB’s output folder.

        ---

        ## 4) Select Sources & Sinks

        Residues are specified using structured identifiers.
        Basic format:

        - `CHAIN,RESNUM`
        - Ranges allowed: `A,150-153`
        - Multiple selections separated by `;`
        Example: `A,312-320;B,45-60`

        Advanced formats (when needed):

        If your structure contains insertion codes (icode) or segment names (segname),
        you may need extended identifiers:

        - `CHAIN:RESNUM`
        - `CHAIN:RESNUM:ICODE`
        - `SEG:CHAIN:RESNUM`
        - `SEG:CHAIN:RESNUM:ICODE`

        Examples:
        - `A:150`
        - `A:150:A`                 (with insertion code A)
        - `PROT:A:150`
        - `PROT:A:150:A`

        Notes:
        - Use `;` to separate multiple chains or selections.
        - Use `-` to define residue ranges.
        - Residue identifiers must match exactly what appears in the PDB.
        - For large complexes, including SEGNAME ensures unambiguous mapping.

        If unsure, inspect the PDB header or use the built-in residue listing tools.

        ---

        ## 5) Run K-Shortest Paths (KSP)
        - Choose **K**
        - Click **Run KSP**
        → MUSIKALL computes K shortest routes for each source→sink pair and summarizes residue usage (frequency).

        ---

        ## 6) Visualize Hotspots (optional but recommended)
        - **Save Colored PDBs** (frequency written into B-factor; open in PyMOL/Chimera and color by B-factor)
        and/or
        - **Show 3D Structures** (built-in viewer)

        ---

        ## 7) (Optional) Co-occurrence Backbone
        - Run **Co-occurrence/Backbone** after KSP
        → Creates a residue×residue co-usage heatmap showing which residues tend to appear together across routes.

        ---

        ## 8) Generate Audio 🎶
        - Configure mapping (Residue Grid), chord mode, tempo, velocity mode
        - Choose output grouping:
          - `per_path`, `per_pair`, or `per_pdb`
        - Click **🎶 Generate Audio**
        → MIDI files are saved under the job’s music output folder; the built-in player can audition them.

        ---

        ## Workflow Summary
        **Create Job → Upload PDBs → Build RIN → Select Source/Sink → Run KSP → (Visualize / Backbone) → Generate Audio**
        """

        txt = tk.Text(win, wrap="word", font=("Arial", 12))
        txt.insert("1.0", text)
        txt.config(state="disabled", bg="white")
        txt.pack(fill="both", expand=True, padx=10, pady=10)

        scroll = ttk.Scrollbar(win, command=txt.yview)
        txt.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

    def open_user_guide(self):
        win = tk.Toplevel(self)
        win.title("📘 MUSIKALL – User Guide (Detailed)")
        win.geometry("950x700")

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True)

        text = """
        # 📘 MUSIKALL — User Guide (Detailed)

        MUSIKALL analyzes long-range communication in biomolecular structures by combining:
        - **Residue Interaction Networks (RINs)** from 3D heavy-atom contacts,
        - **weighted edge costs** derived from contact statistics,
        - **K-Shortest Paths (KSP)** ensembles (multiple alternative communication routes),
        - optional **Co-occurrence / Backbone** analysis (residue co-usage across paths),
        - visualization outputs (e.g., **B-factor frequency coloring**),
        - and **sonification** (MIDI generation) of residues and paths.

        This guide is written to match MUSIKALL’s implemented behavior and file outputs.

        ---

        ## 1) Jobs and folder structure

        A **Job** is a self-contained workspace:
        - You create/select a job to define the output root directory.
        - MUSIKALL writes matrices, paths, plots, colored PDBs, and MIDI outputs inside the job folder.

        Typical layout (conceptual):
        - `<job_dir>/pdb_files/` (input copies)
        - `<job_dir>/<PDBID>/` (per-structure analysis outputs, e.g., matrices)
        - `<job_dir>/colored_pdbs/` (B-factor colored structures)
        - `<job_dir>/music/` (MIDI outputs; exact substructure depends on settings)
        - `<job_dir>/cooccurrence/` or a chosen output directory (backbone heatmaps; depends on your GUI path)

        (Exact folder names depend on your GUI configuration, but the workflow is job-scoped.)

        ---

        ## 2) Input structures (PDB handling)

        ### 2.1 What MUSIKALL reads
        From each PDB, MUSIKALL extracts:
        - Chains and residues (residue name + residue ID/number),
        - Heavy atoms and their coordinates (used for contact counting),
        - Optional identifiers where present/needed:
          - **SEGNAME**
          - **Insertion code (icode)**

        ### 2.2 Why SEGNAME / icode can matter
        Some structures (large assemblies, ribosome-like systems, unusual chain IDs) require residue identity beyond just `chain + resnum`.
        MUSIKALL utilities used by residue mapping, backbone/co-occurrence, and music token parsing are designed to be tolerant of:
        - `SEG:CHAIN:RESNUM`
        - `CHAIN:RESNUM:ICODE`
        - `SEG:CHAIN:RESNUM:ICODE`

        ---

        ## 3) Build the RIN (Adjacency & Edge Weights)

        This step constructs the graph used in all path-based analyses.

        ### 3.1 Nodes
        Each residue is a **node**. MUSIKALL maintains a stable mapping:
        - node index `0..R-1` ↔ residue identity (chain/resnum + optional segname/icode)

        ### 3.2 Edges (contact rule)
        Two residues *i* and *j* are connected based on **heavy-atom contacts** within a cutoff distance `rcutt`:
        - MUSIKALL counts **Nᵢⱼ = number of heavy atom–atom pairs** (one atom from residue i, one from residue j) whose distance ≤ `rcutt`.

        ### 3.3 Adjacency strength (implemented definition)
        Let:
        - **Nᵢ** = number of heavy atoms in residue i  
        - **Nⱼ** = number of heavy atoms in residue j  
        - **Nᵢⱼ** = number of heavy-atom pairs within `rcutt`  

        MUSIKALL defines the adjacency strength as:

            aᵢⱼ = √( (Nᵢ · Nⱼ) / Nᵢⱼ )

        Important interpretation (because of the reciprocal form):
        - **More contacts (larger Nᵢⱼ)** → **smaller aᵢⱼ**
        - **Fewer contacts** → **larger aᵢⱼ**

        So in MUSIKALL, *aᵢⱼ* behaves like an “inverse contact density” measure.

        ### 3.4 Edge weight used for path search
        MUSIKALL converts adjacency strength into an **edge weight** (used as the path “cost”):

            edgeweightᵢⱼ = 1 / (aᵢⱼ + 1e−6)

        Because aᵢⱼ decreases when contacts increase:
        - **More contacts** → **smaller aᵢⱼ** → **larger edgeweightᵢⱼ**
        - **Fewer contacts** → **larger aᵢⱼ** → **smaller edgeweightᵢⱼ**

        Practical consequence:
        - The KSP step operates on the numeric edgeweight matrix as implemented. Keep cutoff consistent across structures in a job for fair comparisons.

        ### 3.5 Output files (per PDB)
        For each structure, MUSIKALL writes:
        - `<PDBID>_adj_matrix.txt`  (aᵢⱼ values)
        - `<PDBID>_edgeweight_matrix.txt`  (edgeweightᵢⱼ values used for KSP)

        ---

        ## 4) Residue Mapping (optional; recommended for multi-PDB jobs)

        Residue mapping aligns residue identifiers across multiple structures to a **common reference** so that:
        - “Source/Sink residue selections” refer to the same physical residues across conformers.

        Key characteristics of MUSIKALL’s mapping approach:
        - It is **reference-based index/number matching** (not sequence alignment).
        - It is designed to be robust for cases where chain IDs alone can be misleading (e.g., assemblies where segname encodes biological identity).

        If you trust that residue numbering is already consistent across all PDBs:
        - You may enable **Skip Residue Mapping** (MUSIKALL uses chain:number selections directly per structure).

        ---

        ## 5) Selecting Sources and Sinks (residue specification)

        You specify residues as **chain + residue number**, with ranges and multiple chains.

        Examples:
        - `A,150-153`
        - `B,200`
        - `A,312-320;B,45-60`

        Rules:
        - Use `;` to separate chain blocks.
        - Use `-` for ranges.
        - Make sure residues exist in the relevant structure and chain.

        Advanced token forms (may appear in logs/exports depending on your build):
        - `SEG:CHAIN:RESNUM`
        - `CHAIN:RESNUM:ICODE`
        - `SEG:CHAIN:RESNUM:ICODE`

        ---

        ## 6) K-Shortest Paths (KSP)

        ### 6.1 What MUSIKALL computes
        For each source → sink pair:
        1. MUSIKALL builds a weighted graph from the structure’s **edgeweight matrix**.
        2. It computes **K shortest simple paths** (no repeated nodes) using a NetworkX k-shortest routine.
        3. It stores the path ensemble per pair and summarizes residue usage.

        ### 6.2 Why K > 1 matters
        Protein communication is often **redundant**. Using K paths captures:
        - alternative corridors,
        - route diversity,
        - and robustness beyond a single shortest path.

        ### 6.3 Residue frequency (usage)
        MUSIKALL tracks how often residues appear across paths (and can aggregate by scope):
        - within a single path,
        - across all paths of a pair,
        - across all selected paths in a structure.

        These frequencies drive:
        - visualization hotspots (B-factor coloring),
        - and music dynamics (when velocity is set to by-frequency).

        ---

        ## 7) Co-occurrence Backbone (residue co-usage heatmaps)

        If enabled in your build, MUSIKALL provides a **co-occurrence backbone** analysis.

        ### 7.1 Definition (implemented)
        Each path is converted into an N-length binary vector:
        - `x_p[k] = 1` if residue k appears in path p, else `0`.

        Let `M` be the matrix whose rows are the path vectors (`K × N`).
        The co-occurrence matrix is:

            C = Σ_p (x_p x_pᵀ) = MᵀM

        So:
        - `C[i, j]` = number of paths in which residues i and j appear together.

        ### 7.2 “Used-only” plotting behavior
        For clarity, MUSIKALL plots only residues that actually appear in the selected path set:
        - It computes `used_idx` from the union of residues seen in the selected paths.
        - Heatmaps are generated from `C_used = C[used_idx, used_idx]`.

        ### 7.3 Output files (names used by MUSIKALL)
        Backbone plots are written as PNGs (per structure), for example:
        - `BACKBONE__PERCENT__<pdb_base>__K<K>__m<m>.png`
        Optional (if enabled):
        - `BACKBONE__COUNT__...png`
        - `BACKBONE__BINARY__...png`
        Diagnostics (if enabled) can also be written to help debug mapping/token issues.

        ---

        ## 8) Visualization outputs

        ### 8.1 Save Colored PDBs (B-factor encoding)
        MUSIKALL can write normalized residue frequency values into the PDB **B-factor** column.
        - Open output PDBs in PyMOL/Chimera/Mol* and color by B-factor to see hotspots.

        ### 8.2 Built-in 3D viewer
        Use the internal viewer for quick inspection and comparisons across structures.

        ---

        ## 9) Music module (MIDI generation)

        MUSIKALL converts residues and/or paths into MIDI sequences.

        ### 9.1 Key options (MusicOptions in MUSIKALL)
        - `rep_res_freq`: output grouping mode (`per_path` | `per_pair` | `per_pdb`)
        - `mapping_mode`: `aa` | `property` | `single`
        - `chord_mode`: `single` | `triad`
        - `program`: MIDI instrument program number (General MIDI)
        - `tempo_bpm`, `note_beats`, `rest_beats`
        - `transpose`, `clamp_low`, `clamp_high`
        - `velocity_mode`: `constant` | `by_frequency`
          - `velocity_constant`
          - `velocity_min`, `velocity_max`
          - `freq_scope`: `per_path` | `per_pair` | `per_pdb`

        Note:
        - `align_mode` exists in the options (`aligned` | `legacy`). If your current build does not expose or use it, treat it as reserved for future ordering/alignment behavior.

        ### 9.2 Output organization (`rep_res_freq`)
        - `per_path`: one MIDI per path (most granular; preserves route order).
        - `per_pair`: one MIDI per source–sink pair.
        - `per_pdb`: one MIDI per structure (a “fingerprint” for that conformer/condition).

        ---

        ## 10) Best practices (reproducibility)
        - Keep `rcutt` (cutoff) constant across structures in the same job.
        - Keep K constant when comparing conditions.
        - If you change core parameters, create a new job or versioned job name.
        - For large assemblies, be consistent about segname/icode handling and residue mapping.

        ---

        ## 11) Troubleshooting (common issues)

        - **No paths found**
          - Source and sink may be disconnected under the chosen cutoff/weights.
          - Verify residues exist; try adjusting `rcutt`.

        - **Residue not found**
          - Check chain IDs and residue numbering (and insertion codes if present).

        - **Backbone heatmap empty**
          - Means no usable residues were collected from the selected paths.
          - Check diagnostics output for unmapped token examples.

        - **MIDI too high/low or clipped**
          - Adjust `transpose` and `clamp_low/clamp_high`.

        ---

        ## Glossary
        - **RIN**: residue-level network from heavy-atom contact statistics
        - **aᵢⱼ**: adjacency strength term used by MUSIKALL (√(Nᵢ·Nⱼ/Nᵢⱼ))
        - **edgeweight**: 1/(aᵢⱼ+1e−6), used for path search
        - **KSP**: K shortest simple paths between source and sink
        - **Residue frequency**: residue usage across selected paths (by scope)
        - **Co-occurrence backbone**: residue×residue co-usage matrix C = MᵀM
        - **rep_res_freq**: MIDI organization mode (per_path / per_pair / per_pdb)

        ✅ MUSIKALL supports a complete pipeline: **structure → network → paths → statistics/plots → sound**.
        """

        frame = ttk.Frame(notebook)
        notebook.add(frame, text="User Guide")

        txt = tk.Text(frame, wrap="word", font=("Arial", 12))
        txt.insert("1.0", text)
        txt.config(state="disabled", bg="white")
        txt.pack(fill="both", expand=True, padx=10, pady=10)

        scroll = ttk.Scrollbar(frame, command=txt.yview)
        txt.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

    def open_theory_info(self):
        win = tk.Toplevel(self)
        win.title("ℹ MUSIKALL – Theory & Info")
        win.geometry("900x650")

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True)

        theories = {

            "RIN & KSP": """
        🧩 Residue Interaction Networks (RIN) & K-Shortest Paths (KSP)

        MUSIKALL models long-range communication in biomolecular structures using
        a graph-theoretical framework. The theory implemented here follows
        standard network analysis principles applied to structure-derived contact maps.

        ---

        🔹 1) Residue Interaction Network (RIN)

        A Residue Interaction Network represents a biomolecular structure as a graph:

        • Nodes:
          Each residue (amino acid or nucleotide) is represented as one node.
          Node identity is defined by:
            - chain ID
            - residue number
            - optional insertion code (icode)
            - optional segment name (segname), if required

        This ensures robust residue identification in large assemblies.

        • Edges:
          Two residues i and j are considered connected if at least one pair
          of heavy atoms (non-hydrogen atoms) lies within a user-defined cutoff distance r_cut.

        This creates an undirected contact graph G = (V, E).

        ---

        🔹 2) Contact quantification and adjacency strength

        Instead of using a purely binary contact (0/1), MUSIKALL quantifies
        how strongly two residues interact based on heavy-atom contact counts.

        For residues i and j:

            Nᵢ   = number of heavy atoms in residue i
            Nⱼ   = number of heavy atoms in residue j
            Nᵢⱼ  = number of heavy atom–atom pairs (one in i, one in j)
                    with distance ≤ r_cut

        MUSIKALL defines adjacency strength:

            Aᵢⱼ = Nᵢⱼ / √(Nᵢ · Nⱼ)

        This is a normalized contact density:

        • Larger Nᵢⱼ → larger Aᵢⱼ
        • Normalization by √(Nᵢ·Nⱼ) reduces bias from residue size

        Thus Aᵢⱼ represents size-corrected contact intensity.

        If Nᵢⱼ = 0, no edge is created.

        ---

        🔹 3) Edge cost used for path search

        Path algorithms require a cost function where lower values represent
        “more favorable” communication.

        MUSIKALL converts adjacency strength to cost as:

            costᵢⱼ = 1 / (Aᵢⱼ + ε)

        where ε is a small constant for numerical stability.

        Consequences:

        • Strong contact (large Aᵢⱼ) → small cost
        • Weak contact (small Aᵢⱼ) → large cost

        The weighted graph G(V, E, cost) is then used for path search.

        ---

        🔹 4) K-Shortest Simple Paths (KSP)

        Given:
        • a weighted graph
        • one or more source residues
        • one or more sink residues

        MUSIKALL computes the K shortest simple paths
        (simple = no repeated nodes) between source–sink pairs.

        Implementation:
        • Uses NetworkX k-shortest simple path functionality
          (Yen-style algorithmic behavior)
        • Returns paths ordered by total path cost (ascending)

        Why K > 1 is important:

        Protein communication is rarely limited to a single route.
        Alternative pathways often coexist.

        Using K paths captures:
        • redundancy
        • alternative corridors
        • distributed signaling patterns

        ---

        🔹 5) Residue frequency (node usage)

        After computing a path ensemble, MUSIKALL can compute
        residue usage frequency.

        For residue r:

            F_r = (number of selected paths containing r) / (normalization factor)

        Normalization depends on scope:
        • per_path
        • per_pair
        • per_pdb

        Residues with high F_r behave as communication hubs
        within the chosen analysis scope.

        ---

        🔹 6) Co-occurrence backbone (pairwise residue coupling)

        To analyze how residues are used together across paths,
        MUSIKALL constructs a co-occurrence matrix.

        For each path p:
        • define binary vector x_p ∈ {0,1}^N
          where x_p[k] = 1 if residue k is in path p

        Let M be the matrix whose rows are x_p.

        The co-occurrence matrix is:

            C = MᵀM

        Thus:

            C[i, j] = number of paths where residues i and j co-appear

        MUSIKALL typically visualizes:

        • COUNT heatmap
        • PERCENT heatmap (scaled to max = 100)
        • optional BINARY heatmap (C > 0)

        Plots are usually generated on the “used-only” residue subset
        for interpretability.
        
        Interpretation:

        • Node frequency captures marginal residue importance.
        • Co-occurrence captures joint usage patterns between residues.

        In probabilistic terms:
        - Frequency ≈ first-order marginal usage
        - Co-occurrence ≈ second-order joint distribution within the path ensemble

        Thus, the backbone matrix reveals coordinated residue groups
        that tend to function together across alternative communication routes.

        

        ---

        Summary

        • RIN defines structural connectivity.
        • Weighted costs define communication resistance.
        • KSP extracts multiple low-cost routes.
        • Frequency and co-occurrence summarize dominant residues
          and residue pairs within the ensemble.

        This framework provides a network-based representation
        of structure-encoded communication.
        """,

            "Musical Mapping": """
        🎶 Musical Mapping Theory in MUSIKALL

        MUSIKALL implements a deterministic sonification framework
        that maps molecular tokens (residues) into MIDI events.

        The mapping is systematic and reproducible.

        ---

        🔹 1) Tokens → Musical Events

        A token corresponds to a residue identifier, such as:

        • CHAIN:RESNUM
        • SEG:CHAIN:RESNUM
        • CHAIN:RESNUM:ICODE
        • SEG:CHAIN:RESNUM:ICODE

        Each token becomes:

        • a single note   (chord_mode = "single")
        • or a triad      (chord_mode = "triad")

        ---

        🔹 2) Identity → Pitch (Residue Grid)

        Each residue type maps to a root pitch defined in the editable Residue Grid:

            residue_type → (note_name, octave)

        Pitch is converted to MIDI note number:

            MIDI = 12 × (octave + 1) + pitch_class(note_name)

        where pitch_class ∈ {0..11} for C, C#, ..., B.

        This ensures:
        • reproducible identity-to-pitch mapping
        • user control via grid editing

        ---

        🔹 3) Triad construction (optional harmony)

        If chord_mode = "triad", additional notes are added
        using an interval set Δ (in semitones).

        Common interval sets:

        • Major       {0,4,7}
        • Minor       {0,3,7}
        • Diminished  {0,3,6}
        • Augmented   {0,4,8}
        • Sus2        {0,2,7}
        • Sus4        {0,5,7}

        If root pitch = p:

            chord = { p + δ | δ ∈ Δ }

        All notes in the chord are emitted simultaneously.

        If chord_mode = "single", only p is emitted.

        ---

        🔹 4) Pitch shaping (transpose and clamping)

        For each generated pitch q:

        • Apply transpose τ:
              q' = q + τ

        • Clamp to allowed octave window:
              lower = 12 × (O_low + 1)
              upper = 12 × (O_high + 1) + 11
              q'' = min(max(q', lower), upper)

        This prevents extreme registers.

        Clamping applies to every pitch in a triad.

        ---

        🔹 5) Temporal structure (rhythm)

        Timing parameters:

        • tempo_bpm = T
        • note_beats = b_note
        • rest_beats = b_rest

        Seconds per beat:

            sec_per_beat = 60 / T

        Event duration:

            duration_seconds = b_note × sec_per_beat

        After each event:
        • optional silence of b_rest beats

        Ordering rules:

        • per_path mode → residues follow path order
        • per_pair / per_pdb → residues are sorted deterministically
          (by seg, chain, resid, icode) before emission

        ---

        🔹 6) Dynamics (velocity)

        Velocity ∈ [1,127].

        Two modes:

        (A) constant
            v = fixed value (optionally with small humanization)

        (B) by_frequency
            v_r = v_min + (v_max − v_min) × F_r

        where F_r ∈ [0,1] is normalized residue frequency
        under the selected scope.

        Thus:
        • more frequently used residues → louder output
        • rarely used residues → softer output

        ---

        🔹 7) Representation policy (rep_res_freq)

        Defines how residues are grouped into MIDI files:

        • per_path
            One file per path.
            Preserves route topology in time.

        • per_pair
            One file per source–sink pair.
            Uses unique residue set across that pair’s paths,
            sorted deterministically.

        • per_pdb
            One file per structure.
            Uses unique residue set across selected paths,
            sorted deterministically.

        This defines musical form at the file level.

        ---

        Summary

        MUSIKALL sonification pipeline:

        • residue identity → pitch
        • optional chord intervals → harmony
        • path or sorted order → temporal structure
        • residue frequency → dynamics
        • representation policy → musical form

        The mapping is deterministic, reproducible,
        and controlled by explicit user parameters.
        """
        }

        for title, text in theories.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=title)

            txt = tk.Text(frame, wrap="word", font=("Arial", 12))
            txt.insert("1.0", text)
            txt.config(state="disabled", bg="white")
            txt.pack(fill="both", expand=True, padx=10, pady=10)

            scroll = ttk.Scrollbar(frame, command=txt.yview)
            txt.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")

    def open_music_playground(self):
        import os, re, tempfile, tkinter as tk
        from tkinter import ttk, messagebox
        try:
            from midiutil import MIDIFile

            from MUSIKALL_functions1 import (
                ALL_RESIDUES, NOTE_NAMES, get_triad_presets,
                note_to_midi, apply_transpose_clamp
            )
        except Exception as e:
            messagebox.showerror("Missing deps", f"Imports failed:\n{e}")
            return


        P = getattr(self, "current_palette", {"bg": "white", "fg": "black", "accent": "#06c"})
        win = tk.Toplevel(self)
        win.title("🎧 Music Playground — listen to any option")
        win.geometry("1100x780")
        win.configure(bg=P["bg"])
        s = ttk.Style(win)
        for k in ("TFrame", "TLabel", "Card.TFrame", "Card.TLabel", "CardHeader.TLabel", "Card.TLabelframe"):
            s.configure(k, background=P["bg"], foreground=P.get("fg", "#000"))
        s.configure("CardHeader.TLabel", font=("Segoe UI", 11, "bold"))


        def _beats_from_label(lbl: str) -> float:
            return {"Whole (1/1)": 4.0, "Half (1/2)": 2.0, "Quarter (1/4)": 1.0, "Eighth (1/8)": 0.5,
                    "Sixteenth (1/16)": 0.25}.get(lbl, 1.0)

        def _opt_bpm():
            return int(
                getattr(self, "_tempo_var", None).get() if hasattr(self, "_tempo_var") else getattr(self.music_opts,
                                                                                                    "tempo_bpm", 120))

        def _opt_program():
            return int(
                getattr(self, "_program_var", None).get() if hasattr(self, "_program_var") else getattr(self.music_opts,
                                                                                                        "program", 0))

        def _opt_note_beats():
            return _beats_from_label(self._note_value.get()) if hasattr(self, "_note_value") else float(
                getattr(self.music_opts, "note_beats", 1.0))

        def _opt_rest_beats():
            if hasattr(self, "_rest_ratio"):
                try:
                    return max(0.0, _opt_note_beats() * float(self._rest_ratio.get()))
                except:
                    pass
            return float(getattr(self.music_opts, "rest_beats", 0.25))

        def _opt_transpose():
            return int(
                getattr(self, "_transpose", None).get() if hasattr(self, "_transpose") else getattr(self.music_opts,
                                                                                                    "transpose", 0))

        def _opt_clamp_lo():
            return int(
                getattr(self, "_clamp_lo", None).get() if hasattr(self, "_clamp_lo") else getattr(self.music_opts,
                                                                                                  "clamp_low", 3))

        def _opt_clamp_hi():
            return int(
                getattr(self, "_clamp_hi", None).get() if hasattr(self, "_clamp_hi") else getattr(self.music_opts,
                                                                                                  "clamp_high", 6))

        def _opt_chord_mode():
            return (
                getattr(self, "_chord_mode", None).get() if hasattr(self, "_chord_mode") else getattr(self.music_opts,
                                                                                                      "chord_mode",
                                                                                                      "single")).lower()

        def _opt_triad():
            return (getattr(self, "_aa_triad", None).get() if hasattr(self, "_aa_triad") else getattr(self.music_opts,
                                                                                                      "aa_triad_name",
                                                                                                      "Major (I)"))

        def _opt_prop_dim():
            return (getattr(self, "_prop_dimension", None).get() if hasattr(self, "_prop_dimension") else getattr(
                self.music_opts, "property_dimension", "hydrophobicity"))

        def _opt_prop_oct():
            return int(
                getattr(self, "_prop_octave", None).get() if hasattr(self, "_prop_octave") else getattr(self.music_opts,
                                                                                                        "property_base_octave",
                                                                                                        4))

        def _opt_single():  # (one-letter, triad, base_oct, policy)
            aa= (getattr(self, "_single_code", None).get().strip().upper()[:1] if hasattr(self,
                                                                                           "_single_code") else getattr(
                self.music_opts, "single_aa_code", "K"))
            tri = (getattr(self, "_single_triad", None).get() if hasattr(self, "_single_triad") else getattr(
                self.music_opts, "single_triad_name", "Major (I)"))
            octv = int(getattr(self, "_single_octave", None).get() if hasattr(self, "_single_octave") else getattr(
                self.music_opts, "single_base_octave", 4))
            pol = (getattr(self, "_single_others", None).get() if hasattr(self, "_single_others") else getattr(
                self.music_opts, "single_others_policy", "rest"))
            return aa, tri, octv, pol

        TRIADS = get_triad_presets()

        def _apply_range(m):
            return apply_transpose_clamp(m, _opt_transpose(), _opt_clamp_lo(), _opt_clamp_hi())

        def _write_and_play(midi_notes, name="play", velocity=95):
            mid = MIDIFile(1)
            tr = 0

            mid.addTempo(tr, 0, int(_opt_bpm()))
            mid.addProgramChange(tr, 0, 0, int(_opt_program()))

            t = 0.0
            dur = float(_opt_note_beats())

            try:
                v = int(float(velocity))
            except:
                v = 90

            v = max(1, min(127, v))

            for m in midi_notes:
                try:
                    m_int = int(m)
                except:
                    continue

                mid.addNote(tr, 0, m_int, float(t), float(dur), v)
                t += dur + float(_opt_rest_beats())

            tmp = os.path.join(tempfile.gettempdir(), f"{name}.mid")

            with open(tmp, "wb") as fh:
                mid.writeFile(fh)

            play_midi(tmp)

        # ---- Header
        top = ttk.Frame(win, style="Card.TFrame") 
        top.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(top,
                  text="Pick anything below and press ▶ to hear. Uses your Advanced settings (tempo, program, range, etc.).",
                  style="CardHeader.TLabel").pack(side="left")
        ttk.Button(top, text="⏹ Stop", command=stop_midi).pack(side="right")

        # ---- Notebook
        nb = ttk.Notebook(win) 
        nb.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # =========================================================

        tab1 = ttk.Frame(nb, style="Card.TFrame")
        nb.add(tab1, text="Residue Grid")
        ttk.Label(tab1,
                  text="Plays the current residue →root mapping from the main grid. Triad/single depends on Advanced → Chord mode.",
                  style="Card.TLabel").pack(anchor="w", padx=6, pady=6)

        aa_box = ttk.Labelframe(tab1, text="Amino acids", padding=(6, 6), style="Card.TLabelframe")
        aa_box.pack(fill="both", expand=True, padx=6, pady=6)

        canvas = tk.Canvas(aa_box, bg=P["bg"], highlightthickness=0)
        inner = ttk.Frame(canvas, style="Card.TFrame")
        vs = ttk.Scrollbar(aa_box, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y") 
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _grid_root(aa3):
            wset = (getattr(self, "aa_widgets", {}) or {}).get(aa3)
            if not wset: return None
            n = (wset["note"].get() or "C").strip()
            try:
                o = int((wset["oct"].get() or "4").strip())
            except:
                o = 4
            return f"{n}{o}"

        def _notes_from_root_str(root_str):
            rm = note_to_midi(root_str)
            if _opt_chord_mode() == "triad":
                return [_apply_range(rm + iv) for iv in TRIADS.get(_opt_triad(), [0])]
            return [_apply_range(rm)]

        for aa3, aa1, fullname in ALL_RESIDUES:
            row = ttk.Frame(inner, style="Card.TFrame") 
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{aa3} ({aa1}) – {fullname}", style="Card.TLabel").pack(side="left", padx=6)

            def _mkplay(a=aa3):
                def _inner():
                    r = _grid_root(a)
                    if not r: return
                    _write_and_play(_notes_from_root_str(r), f"AA_{a}")

                return _inner

            ttk.Button(row, text="▶ Play", command=_mkplay()).pack(side="right", padx=4)

        # =========================================================

        tab2 = ttk.Frame(nb, style="Card.TFrame") 
        nb.add(tab2, text="Triads")
        ctl = ttk.Frame(tab2, style="Card.TFrame") 
        ctl.pack(fill="x", padx=6, pady=(6, 0))
        ttk.Label(ctl, text="Root", style="Card.TLabel").pack(side="left")
        _t2_root = tk.StringVar(value="C")
        ttk.Combobox(ctl, textvariable=_t2_root, values=NOTE_NAMES, width=5, state="readonly").pack(side="left", padx=4)
        ttk.Label(ctl, text="Oct", style="Card.TLabel").pack(side="left")
        _t2_oct = tk.IntVar(value=_opt_prop_oct())
        tk.Spinbox(ctl, from_=0, to=9, width=4, textvariable=_t2_oct, bg=P["bg"], fg=P.get("fg", "#000"),
                   insertbackground=P.get("fg", "#000")).pack(side="left", padx=4)

        tri_box = ttk.Labelframe(tab2, text="Triad presets", padding=(6, 6), style="Card.TLabelframe")
        tri_box.pack(fill="both", expand=True, padx=6, pady=6)

        for nm, ivs in TRIADS.items():
            row = ttk.Frame(tri_box, style="Card.TFrame") 
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=nm, style="Card.TLabel").pack(side="left", padx=6)

            def _mkplay(name=nm, _ivs=list(ivs)):
                def _inner():
                    root_str = f"{_t2_root.get()}{int(_t2_oct.get() or 4)}"
                    rm = note_to_midi(root_str)
                    notes = [_apply_range(rm + iv) for iv in _ivs]
                    _write_and_play(notes, f"TRI_{name}")

                return _inner

            ttk.Button(row, text="▶ Play", command=_mkplay()).pack(side="right", padx=4)

        # =========================================================

        tab3 = ttk.Frame(nb, style="Card.TFrame") 
        nb.add(tab3, text="Property")
        ttk.Label(tab3, text="Pick a biochemical property and class  choose root source  the class’s triad plays.",
                  style="Card.TLabel").pack(anchor="w", padx=6, pady=6)

        top3 = ttk.Frame(tab3, style="Card.TFrame") 
        top3.pack(fill="x", padx=6, pady=6)
        dims = ["hydrophobicity", "charge", "aromaticity", "polarity"]

        classes_by_dim = {
            "hydrophobicity": ["hydrophobic", "hydrophilic"],
            "charge": ["positive", "negative", "neutral"],
            "aromaticity": ["aromatic", "nonaromatic"],
            "polarity": ["polar", "nonpolar"],
        }

        ttk.Label(top3, text="Dimension", style="Card.TLabel").pack(side="left")
        _p_dim = tk.StringVar(value=_opt_prop_dim())
        ttk.Combobox(top3, textvariable=_p_dim, values=dims, width=16, state="readonly").pack(side="left", padx=6)

        row1 = ttk.Frame(tab3, style="Card.TFrame")
        row1.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(row1, text="Class", style="Card.TLabel").pack(side="left")
        _p_class = tk.StringVar(value="")
        _class_cb = ttk.Combobox(row1, textvariable=_p_class, values=[], width=18, state="readonly")
        _class_cb.pack(side="left", padx=6)

        row2 = ttk.Frame(tab3, style="Card.TFrame")
        row2.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(row2, text="Root source", style="Card.TLabel").pack(side="left")
        _p_root_mode = tk.StringVar(value="aagrid")  # aagrid / Custom / Fallback
        ttk.Combobox(row2, textvariable=_p_root_mode, values=["aagrid", "Custom", "Fallback"], width=12,
                     state="readonly").pack(side="left", padx=6)
        ttk.Label(row2, text="Note", style="Card.TLabel").pack(side="left", padx=(12, 4))
        _p_root_note = tk.StringVar(value="C")
        ttk.Combobox(row2, textvariable=_p_root_note, values=NOTE_NAMES, width=5, state="readonly").pack(side="left")
        ttk.Label(row2, text="Oct", style="Card.TLabel").pack(side="left", padx=(12, 4))
        _p_root_oct = tk.IntVar(value=_opt_prop_oct())
        tk.Spinbox(row2, from_=0, to=9, width=4, textvariable=_p_root_oct, bg=P["bg"], fg=P.get("fg", "#000"),
                   insertbackground=P.get("fg", "#000")).pack(side="left")

        def _prop_play():

            tri_map = getattr(self.music_opts, "property_triads", {}) or {}
            tri = (tri_map.get(_p_dim.get(), {}) or {}).get(_p_class.get(), "Major (I)")

            if _p_root_mode.get() == "aagrid":

                pick = tk.Toplevel(win)
                pick.title("Pick Residue Root") 
                pick.configure(bg=P["bg"])
                lst = ttk.Frame(pick, style="Card.TFrame") 
                lst.pack(padx=8, pady=8)
                tk_sel = {"root": None}

                def _pick_and_close(root_str):
                    tk_sel["root"] = root_str 
                    pick.destroy()

                for aa3, aa1, fullname in ALL_RESIDUES:
                    # main grid’den oku
                    wset = (getattr(self, "aa_widgets", {}) or {}).get(aa3)
                    rs = f"{(wset['note'].get() or 'C')}{(wset['oct'].get() or '4')}" if wset else "C4"
                    r = ttk.Frame(lst, style="Card.TFrame") 
                    r.pack(fill="x", pady=1)
                    ttk.Label(r, text=f"{aa3} ({aa1}) – {fullname}  | {rs}", style="Card.TLabel").pack(side="left")
                    ttk.Button(r, text="Use", command=lambda s=rs: _pick_and_close(s)).pack(side="right")
                pick.wait_window()
                root_str = tk_sel["root"] or f"C{_opt_prop_oct()}"
            elif _p_root_mode.get() == "Custom":
                root_str = f"{_p_root_note.get()}{int(_p_root_oct.get() or 4)}"
            else:
                root_str = f"C{_opt_prop_oct()}"
            rm = note_to_midi(root_str)
            notes = [_apply_range(rm + iv) for iv in get_triad_presets().get(tri, [0])]
            _write_and_play(notes, f"PROP_{_p_dim.get()}_{_p_class.get()}")

        ttk.Button(tab3, text="▶ Play", command=_prop_play).pack(anchor="w", padx=6, pady=(0, 6))

        def _refresh_classes(*_):
            vals = classes_by_dim.get(_p_dim.get(), [])
            _class_cb.configure(values=vals)
            if vals: _p_class.set(vals[0])

        _p_dim.trace_add("write", _refresh_classes)
        _refresh_classes()

        # =========================================================

        tab4 = ttk.Frame(nb, style="Card.TFrame") 
        nb.add(tab4, text="Single‑AA")
        one_codes = [a1 for _, a1, _ in ALL_RESIDUES]
        ttk.Label(tab4, text="Preview your Single‑aasettings (target aatriad at the chosen base octave).",
                  style="Card.TLabel").pack(anchor="w", padx=6, pady=6)

        row = ttk.Frame(tab4, style="Card.TFrame") 
        row.pack(fill="x", padx=6, pady=6)
        ttk.Label(row, text="Target AA", style="Card.TLabel").pack(side="left")
        _s_aa, _s_tr, _s_octv, _ = _opt_single()
        _s_aa_var = tk.StringVar(value=_s_aa)
        ttk.Combobox(row, textvariable=_s_aa_var, values=one_codes, width=4, state="readonly").pack(side="left", padx=6)

        ttk.Label(row, text="Triad", style="Card.TLabel").pack(side="left", padx=(12, 4))
        _s_triad = tk.StringVar(value=_s_tr) 
        ttk.Combobox(row, textvariable=_s_triad, values=list(TRIADS.keys()), width=18, state="readonly").pack(
            side="left")

        ttk.Label(row, text="Base Oct", style="Card.TLabel").pack(side="left", padx=(12, 4))
        _s_oct = tk.IntVar(value=_s_octv) 
        tk.Spinbox(row, from_=0, to=9, width=4, textvariable=_s_oct, bg=P["bg"], fg=P.get("fg", "#000"),
                   insertbackground=P.get("fg", "#000")).pack(side="left")

        def _s_play():
            rm = note_to_midi(f"C{int(_s_oct.get() or 4)}")
            notes = [_apply_range(rm + iv) for iv in TRIADS.get(_s_triad.get(), [0])]
            _write_and_play(notes, f"SINGLE_{_s_aa_var.get()}")

        ttk.Button(tab4, text="▶ Play", command=_s_play).pack(anchor="w", padx=6, pady=(0, 6))

        # =========================================================

        tab5 = ttk.Frame(nb, style="Card.TFrame")
        nb.add(tab5, text="Custom")
        r1 = ttk.Frame(tab5, style="Card.TFrame")
        r1.pack(fill="x", padx=6, pady=6)
        ttk.Label(r1, text="Chord mode", style="Card.TLabel").pack(side="left")
        _c_mode = tk.StringVar(value=_opt_chord_mode())
        ttk.Combobox(r1, textvariable=_c_mode, values=["single", "triad"], width=10, state="readonly").pack(side="left",
                                                                                                            padx=6)
        ttk.Label(r1, text="Triad", style="Card.TLabel").pack(side="left", padx=(12, 4))
        _c_triad = tk.StringVar(value=_opt_triad())
        ttk.Combobox(r1, textvariable=_c_triad, values=list(TRIADS.keys()), width=18, state="readonly").pack(
            side="left")

        r2 = ttk.Frame(tab5, style="Card.TFrame")
        r2.pack(fill="x", padx=6, pady=6)
        ttk.Label(r2, text="Root", style="Card.TLabel").pack(side="left")
        _c_root = tk.StringVar(value="C")
        ttk.Combobox(r2, textvariable=_c_root, values=NOTE_NAMES, width=5, state="readonly").pack(side="left", padx=4)
        ttk.Label(r2, text="Oct", style="Card.TLabel").pack(side="left")
        _c_oct = tk.IntVar(value=_opt_prop_oct())
        tk.Spinbox(r2, from_=0, to=9, width=4, textvariable=_c_oct, bg=P["bg"], fg=P.get("fg", "#000"),
                   insertbackground=P.get("fg", "#000")).pack(side="left", padx=4)

        r3 = ttk.Frame(tab5, style="Card.TFrame")
        r3.pack(fill="x", padx=6, pady=6)
        ttk.Label(r3, text="Velocity preview (0..1 freq → loudness if by_frequency)", style="Card.TLabel").pack(
            side="left")
        _c_freq = tk.DoubleVar(value=0.5)
        tk.Scale(r3, from_=0.0, to=1.0, orient="horizontal", resolution=0.01, length=200, variable=_c_freq,
                 bg=P["bg"], highlightthickness=0).pack(side="left", padx=8)

        def _vel_from_freq(freq):
            mode = (getattr(self, "_vel_mode", None).get() if hasattr(self, "_vel_mode") else getattr(self.music_opts,
                                                                                                      "velocity_mode",
                                                                                                      "constant"))
            if mode == "by_frequency":
                return int(30 + max(0.0, min(1.0, freq)) * 90)
            return int(
                getattr(self, "_vel_const", None).get() if hasattr(self, "_vel_const") else getattr(self.music_opts,
                                                                                                    "velocity_constant",
                                                                                                    90))

        def _c_play():
            root_str = f"{_c_root.get()}{int(_c_oct.get() or 4)}"
            rm = note_to_midi(root_str)
            if _c_mode.get() == "triad":
                notes = [_apply_range(rm + iv) for iv in TRIADS.get(_c_triad.get(), [0])]
            else:
                notes = [_apply_range(rm)]
            _write_and_play(notes, f"CUSTOM_{_c_mode.get()}_{_c_triad.get()}", velocity=_vel_from_freq(_c_freq.get()))

        ttk.Button(tab5, text="▶ Play", command=_c_play).pack(anchor="w", padx=6, pady=(0, 6))


        win.protocol("WM_DELETE_WINDOW", lambda: (stop_midi(), win.destroy()))

    def show_cite(self):
            """Displays the citation information in a copyable but read-only format."""
            cite_window = tk.Toplevel(self)
            cite_window.title("How to Cite")
            cite_window.geometry("700x250")

            tk.Label(cite_window, text="How to Cite MUSIKALL:", font=("Arial", 14, "bold")).pack(pady=10)

            citation_text = """         
        1. Paper Name, Authors, Journal, Year.

        Please cite these publications when using MUSIKALL.
        """

            cite_entry = tk.Text(cite_window, height=6, width=80, wrap="word", font=("Arial", 12), padx=10, pady=5)
            cite_entry.insert("1.0", citation_text)
            cite_entry.config(state="disabled", bg=self.cget("bg"), relief="flat")  # Read-only, düz arka plan
            cite_entry.pack(padx=15, pady=5)

            def copy_to_clipboard():
                self.clipboard_clear()
                self.clipboard_append(citation_text)
                self.update()
                messagebox.showinfo("Copied!", "Citation copied to clipboard.")

            tk.Button(cite_window, text="📋 Copy Citation", font=("Arial", 12, "bold"), command=copy_to_clipboard).pack(
                pady=10)

    def show_Contact(self):
        """Displays the Adjacency information with a copyable email field."""
        Adjacency_window = tk.Toplevel(self)
        Adjacency_window.title("Contact Us")
        Adjacency_window.geometry("400x200")

        tk.Label(Adjacency_window, text="Contact Us", font=("Arial", 14, "bold")).pack(pady=10)

        tk.Label(Adjacency_window, text="📍 Kurkcuoglu Levitas Lab., Istanbul Technical University", font=("Arial", 12)).pack(pady=5)

        tk.Label(Adjacency_window, text="📧 Email:", font=("Arial", 12)).pack()

        # Read-only Entry for email (copyable but not editable)
        email = "ozdezeynepg@gmail.com"
        email_entry = tk.Entry(Adjacency_window, font=("Arial", 12), width=30, justify="center")
        email_entry.insert(0, email)
        email_entry.config(state="readonly")
        email_entry.pack(pady=5)

        # **Copy Button**
        def copy_email():
            self.clipboard_clear()
            self.clipboard_append(email)
            self.update()
            messagebox.showinfo("Copied!", "Email copied to clipboard.")

        tk.Button(Adjacency_window, text="Copy Email", command=copy_email).pack(pady=10)

    def show_main_interface(self):
        self.welcome_frame.destroy()


        bg = getattr(self, "current_palette", {}).get("bg", "#FFFFFF")

        self.main_pw = tk.PanedWindow(self, orient="horizontal", bg=bg, sashrelief="flat", bd=0)
        self.main_pw.pack(fill="both", expand=True)

        self.left_col = tk.Frame(self.main_pw, bg=bg)
        self.right_col = tk.Frame(self.main_pw, width=320, bg=bg)

        self.main_pw.add(self.left_col, stretch="always")
        self.main_pw.add(self.right_col)

        section1 = ttk.LabelFrame(self.left_col, text="📂 PDB Upload & Adjacency Matrix", style="Card.TLabelframe")
        section1.pack(fill="x", padx=10, pady=5)

        reset_btn1 = ttk.Button(section1, text="⟲", width=2, command=self.reset_section1)
        reset_btn1.grid(row=0, column=99, padx=(36,0), pady=5, sticky="ne")

        ttk.Label(section1, text="Job Name:").grid(row=0, column=0, padx=5, pady=5)
        self.jobname_entry = tk.Entry(section1, width=30)
        self.jobname_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(section1, text="Create Job", command=self.create_job).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(section1, text="Upload PDBs", command=self.upload_pdb_files).grid(row=1, column=0, padx=5, pady=5)

        ttk.Label(section1, text="Cutoff Value (Å):").grid(row=1, column=1, padx=5, pady=5)
        self.cutoff_entry = tk.Entry(section1, width=10)
        self.cutoff_entry.grid(row=1, column=2, padx=5, pady=5)
        self.cutoff_entry.insert(0, "4.5")
        ttk.Button(section1, text="Calculate Adjacency Matrix", command=self.run_adj_matrix).grid(
            row=1, column=3, padx=5, pady=5
        )

        # 🔀 Section 3 — K Shortest Paths
        section3 = ttk.LabelFrame(self.left_col, text="🔀 K Shortest Paths", style="Card.TLabelframe")
        section3.pack(fill="x", padx=10, pady=5)

        # ===== Inputs (flat, no nested frames with borders) =====
        inputs = ttk.Frame(section3)
        inputs.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 6))
        inputs.columnconfigure(1, weight=1)

        # Reference + Select + Skip
        ttk.Label(inputs, text="Reference PDB:").grid(row=1, column=0, padx=(0, 8), pady=4, sticky="w")
        self.ref_pdb_entry = getattr(self, "ref_pdb_entry", tk.Entry(inputs, width=40))
        self.ref_pdb_entry.grid(row=1, column=1, padx=(0, 8), pady=4, sticky="ew")
        ttk.Button(inputs, text="Select", command=self.select_reference_pdb).grid(row=1, column=2, padx=(0, 8), pady=4)

        self.skip_alignment_var = getattr(self, "skip_alignment_var", tk.BooleanVar(value=False))
        tools = ttk.Frame(inputs)
        tools.grid(row=1, column=3, padx=(0, 0), pady=4, sticky="e")

        ttk.Checkbutton(tools, text="Skip alignment", variable=self.skip_alignment_var).pack(side="left")

        reset_btn3 = ttk.Button(section3, text="⟲", width=2, command=self.reset_section3)
        reset_btn3.grid(row=1, column=99, padx=(40, 0), pady=5, sticky="ne")

        # --- spacer after Reference row ---
        _inputs_sp1 = ttk.Frame(inputs, height=20)
        _inputs_sp1.grid(row=2, column=0, columnspan=4, sticky="ew")
        _inputs_sp1.grid_propagate(False)

        # Sources
        ttk.Label(inputs, text="Source residues:").grid(row=3, column=0, padx=(0, 8), pady=4, sticky="w")

        # 🔹 Multi-line Text widget (supports ';' and new lines)
        self.source_res_entry = getattr(self, "source_res_entry", tk.Text(inputs, height=2, width=40))
        self.source_res_entry.grid(row=3, column=1, padx=(0, 8), pady=4, sticky="ew")
        self.source_res_entry.delete("1.0", "end")


        info_btn_src = tk.Label(
            inputs,
            text="ⓘ",
            fg=self.current_palette["accent"],
            cursor="question_arrow",
            bg=self.current_palette["bg"]
        )
        info_btn_src.grid(row=3, column=2, sticky="w", padx=(0, 8))
        Tooltip(
            info_btn_src,
            "Input format:\n"
            "- Basic format: CHAIN,start-end  or  CHAIN,res1,res2,...\n"
            "  Example:  DA,1047-1050   or   DA,1047,1050,1100\n"
            "\n"
            "- If the PDB uses SEGNAMES (segment IDs):\n"
            "    SEGNAME:CHAIN,start-end\n"
            "    SEGNAME:CHAIN,res1,res2,...\n"
            "  Example:  MC:DA,1047-1050   or   MC:DA,1047\n"
            "\n"
            "- Multiple entries can be separated by ';' or by new lines.\n"
            "Examples:\n"
            "DA,1047-1050; DB,2000\n"
            "MC:DA,1047-1050; MB:DA,2000\n"
        )

        # --- spacer between Source and Sink ---
        _inputs_sp2 = ttk.Frame(inputs, height=8)
        _inputs_sp2.grid(row=4, column=0, columnspan=4, sticky="ew")
        _inputs_sp2.grid_propagate(False)

        # Sinks
        ttk.Label(inputs, text="Sink residues:").grid(row=5, column=0, padx=(0, 8), pady=4, sticky="w")

        self.sink_res_entry = getattr(self, "sink_res_entry", tk.Text(inputs, height=2, width=40))
        self.sink_res_entry.grid(row=5, column=1, padx=(0, 8), pady=4, sticky="ew")
        self.sink_res_entry.delete("1.0", "end")

        info_btn_sink = tk.Label(
            inputs,
            text="ⓘ",
            fg=self.current_palette["accent"],
            cursor="question_arrow",
            bg=self.current_palette["bg"]
        )
        info_btn_sink.grid(row=5, column=2, sticky="w", padx=(0, 8))
        Tooltip(
            info_btn_sink,
            "Input format:\n"
            "- Basic format: CHAIN,start-end  or  CHAIN,res1,res2,...\n"
            "  Example:  DA,2000-2010   or   DA,2000,2005,2010\n"
            "\n"
            "- If the PDB uses SEGNAMES (segment IDs):\n"
            "    SEGNAME:CHAIN,start-end\n"
            "    SEGNAME:CHAIN,res1,res2,...\n"
            "  Example:  MC:DA,2000-2010   or   MC:DA,2000\n"
            "\n"
            "- Multiple entries can be separated by ';' or by new lines.\n"
            "Examples:\n"
            "DA,2000-2010; DB,2500\n"
            "MC:DA,2000-2010; MB:DA,2500\n"
        )

        # —— small vertical spacing instead of a separator line ——
        _spacer = ttk.Frame(section3, height=20)
        _spacer.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 0))
        _spacer.grid_propagate(False)

        # ===== Actions row (Reset on the left  K + buttons on the right) =====
        actions = ttk.Frame(section3)
        actions.grid(row=3, column=0, sticky="ew", padx=10, pady=(6, 6))

        right = ttk.Frame(actions)
        right.grid(row=0, column=1, sticky="e")

        ttk.Label(right, text="K value:").pack(side="left", padx=(0, 6))
        try:
            self.k_entry.destroy()
        except Exception:
            pass
        self.k_entry = tk.Spinbox(right, from_=1, to=999, width=8)
        self.k_entry.delete(0, "end")
        self.k_entry.insert(0, "20")
        self.k_entry.pack(side="left", padx=(0, 12))

        _calc_cmd = getattr(self, "_on_ksp_calculate", None) or self.calculate_shortest_paths
        ttk.Button(right, text="Calculate Shortest Paths", command=_calc_cmd).pack(side="left", padx=(0, 8))
        ttk.Button(right, text="Path Explorer", command=self.open_path_explorer).pack(side="left")
        ttk.Button(right, text="Cooccurrence Backbone", command=self.open_cooccurrence_backbone).pack(side="left",padx=(8, 0))
        ttk.Button(right, text="Path Similarity", command=self.open_path_similarity).pack(side="left", padx=(8, 0))
        # ===== Progress + status =====
        self.ksp_prog = getattr(self, "ksp_prog", ttk.Progressbar(section3, mode="indeterminate"))
        self.ksp_prog.grid(row=4, column=0, sticky="ew", padx=10, pady=(6, 2))
        self.ksp_prog.grid_remove()

        self.ksp_status = getattr(self, "ksp_status", ttk.Label(section3, style="Sub.TLabel", text=""))
        self.ksp_status.grid(row=5, column=0, sticky="w", padx=10, pady=(0, 10))

        #Bolum4
        # ========= 📊 Property Tracks =========
        section_prop = ttk.LabelFrame(self.left_col, text="📊 Property Tracks", style="Card.TLabelframe")
        section_prop.pack(fill="x", padx=10, pady=5)

        # Checkboxes
        self.chk_hydro_var = tk.BooleanVar()
        self.chk_charge_var = tk.BooleanVar()
        self.chk_aroma_var = tk.BooleanVar()
        self.chk_polarity_var = tk.BooleanVar()

        ttk.Checkbutton(section_prop, text="Hydrophobicity", variable=self.chk_hydro_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Checkbutton(section_prop, text="Charge", variable=self.chk_charge_var).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Checkbutton(section_prop, text="Aromaticity", variable=self.chk_aroma_var).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Checkbutton(section_prop, text="Polarity", variable=self.chk_polarity_var).grid(
            row=0, column=3, sticky="w"
        )

        # Min score
        ttk.Label(section_prop, text="Min FreqScore for plotting:").grid(
            row=1, column=0, padx=4, pady=3, sticky="w"
        )
        self.min_score_var = tk.IntVar(value=1)
        ttk.Spinbox(section_prop, from_=0, to=10, textvariable=self.min_score_var, width=5).grid(
            row=1, column=1, sticky="w"
        )


        self.only_figures_var = tk.BooleanVar()
        ttk.Checkbutton(section_prop, text="Only figures (use existing Excel)", variable=self.only_figures_var).grid(
            row=1, column=2, sticky="w"
        )

        ttk.Button(section_prop, text="Generate Tracks", command=self._run_property_tracks).grid(
            row=2, column=0, columnspan=4, pady=8
        )


        section5 = ttk.LabelFrame(self.left_col, text="🎨 Visualization", style="Card.TLabelframe")
        section5.pack(fill="x", padx=10, pady=5)

        reset_btn5 = ttk.Button(section5, text="⟲", width=2, command=self.reset_section5)
        reset_btn5.grid(row=0, column=99, padx=(375,0), pady=0, sticky="ne")

        ttk.Button(section5, text="Save PDBs", command=self.save_colored_pdbs).grid(row=0, column=0, padx=5,
                                                                                            pady=5)
        ttk.Button(section5, text="Show 3D Structures", command=self.show_3d_structures).grid(row=0, column=1, padx=5,
                                                                                              pady=5)


        self.build_music_sidebar(self.right_col)


        self.output_text = tk.Text(self, height=15, width=100)
        self.output_text.pack(fill="both", padx=10, pady=10)

    def _run_property_tracks(self):
        import os
        import pandas as pd
        from tkinter import messagebox

        from MUSIKALL_functions1 import (
            build_property_matrix_for_pdb,
            plot_property_tracks_single,
            plot_property_tracks_multi,
            export_property_excel_aligned,
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
        self.k_entry.delete(0, tk.END)
        self.k_entry.insert(0, "20")

        # KSP-derived main results
        self.paths_dict = {}
        self.paths_dict_2 = {}
        self.all_normalized_frequencies = {}

        # Excel output references
        self.per_pdb_files = None
        self.overall_file = None

        # Viewer/cache results
        self._interactive_cache = {}
        self._interactive_cache_ready = False
        self._interactive_cache_building = False

        # Optional downstream analysis results
        for attr in [
            "cooccurrence_results",
            "path_similarity_results",
            "backbone_results",
            "cooccurrence_matrix",
            "path_similarity_matrix",
            "global_frequency_map",
        ]:
            if hasattr(self, attr):
                setattr(self, attr, {})

        # Remove path-dependent state entries only
        if hasattr(self, "state") and isinstance(self.state, dict):
            for key in [
                "paths_dict",
                "paths_dict_2",
                "all_normalized_frequencies",
                "per_pdb_files",
                "overall_file",
                "cooccurrence_results",
                "path_similarity_results",
                "backbone_results",
            ]:
                self.state.pop(key, None)

            self.state["last_completed_stage"] = "section3_reset"

        self.last_completed_stage = "section3_reset"

        self.log_output(
            "♻️ Section 3 reset: KSP, frequencies, co-occurrence, path similarity, and viewer cache cleared.\n")

    import os, re, tkinter as tk

    from tkinter import ttk, messagebox

    # --- PATH EXPLORER ----------------------------------------------------------
    def open_path_explorer(self):
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
        """'A,123' / 'A:123A' / ' A 123 ' → ('A','123A')  sadece sayıysa ('','123')."""
        import re
        if not s: return ("", "")
        t = str(s).strip().replace(";", ",")
        t = re.sub(r"\s+", "", t)
        if ":" in t:
            ch, rn = t.split(":", 1)
        elif "," in t:
            ch, rn = t.split(",", 1)
        else:
            ch, rn = "", t
        return (ch.upper(), rn)

    def _node_matches(self, want: tuple[str, str], got: tuple[str, str]) -> bool:
        """Zincir aynı (veya istenen zincir boş) + residue tam eşit veya sayısal kısmı eşit."""
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

        pdb_data = getattr(self, "pdb_info_dict", {}).get(pdb_id, {}) or {}


        nim = pdb_data.get("node_index_map")
        if isinstance(nim, dict) and len(nim) > 0:
            out = {}
            for k, v in nim.items():
                try:
                    out[int(k)] = str(v)
                except Exception:

                    continue
            if out:
                return out


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

        # Şema: { "s -> t": {"paths":[...], "costs":[...]} , ... }
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

        out = []
        want_src = self._canon_node(src)
        want_sink = self._canon_node(sink)


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
                _seg1, ch1, rn1 = self._split_token(first)
                first_ok = self._node_matches(want_src, (ch1.upper(), rn1))
            else:
                # Index ise
                try:
                    first_ok = self._index_matches_residue(pdb_id_for_map, int(first), want_src)
                except Exception:
                    first_ok = False

            # --- LAST (sink) match ---
            if ":" in last:
                _segN, chN, rnN = self._split_token(last)
                last_ok = self._node_matches(want_sink, (chN.upper(), rnN))
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

        txt = getattr(self, "output_text", None)
        if txt is not None:
            try:

                def _append():
                    txt.insert("end", message)
                    txt.see("end")


                txt.after(0, _append)
            except Exception:
                print(message, end="")
        else:
            print(message, end="")

        try:
            job_dir = getattr(self, "current_job_folder", None)

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
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(message)
        except Exception:
            pass

    def _endpoints_from_pdb_paths(self, pdb_key):
        sources, sinks = set(), set()
        for path, _ in self._iter_paths_for_pdb(pdb_key):
            if not path: continue
            first, last = str(path[0]), str(path[-1])
            sources.add(first)
            sinks.add(last)

        def _fmt(node: str) -> str:
            if ":" in node:
                ch, rn = node.split(":", 1)
                return f"{ch},{rn}"
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


        def _open_freq_with_compat():

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


        def _refresh_list(tv=tv, status=status):
            try:
                tv.delete(*tv.get_children())
                src_key = to_key(src_var.get())
                sink_key = to_key(sink_var.get())


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
                        out_dir=backbone_root,
                        logger=self,
                        selected_pdb_keys=list(subset_pd2.keys()),
                        selected_pairs=None,
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


        job_dir = create_job_folder(jobname)


        self.jobname = jobname
        self.state["jobname"] = jobname
        self.current_job = job_dir  #
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
            self.last_completed_stage = "pdb_loaded"
            self.state["last_completed_stage"] = self.last_completed_stage
            self.autosave_job("pdb_loaded")

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
            self.last_completed_stage = "matrices_ready"
            self.state["last_completed_stage"] = self.last_completed_stage
            self.autosave_job("matrices_ready")
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

        source_res_input = self.source_res_entry.get().strip()
        sink_res_input = self.sink_res_entry.get().strip()

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


        self.state["jobname"] = jobname
        self.state["reference_pdb"] = reference_pdb
        self.state["source_residues_raw"] = source_res_input
        self.state["sink_residues_raw"] = sink_res_input


        if hasattr(self, "skip_alignment_var") and self.skip_alignment_var.get():
            self.log_output("⏭️ Alignment skipped. Seeding residue indices from GUI…\n")
            self._seed_indices_from_gui(source_residues, sink_residues)
            self.log_output("✅ Residue indices seeded without alignment.\n")


            self.last_completed_stage = "mapping_done"
            self.state["last_completed_stage"] = self.last_completed_stage
            self.autosave_job("mapping_done")
            return


        self.log_output("📏 Running Residue Mapping...\n")
        threading.Thread(
            target=self.threaded_run_residue_mapping,
            args=(jobname, reference_pdb, source_residues, sink_residues),
            daemon=True
        ).start()

    def _seed_indices_from_gui(self, source_residues, sink_residues):


        def _canon(x):
            return str(x).strip().upper() if x is not None else None

        def _digits_only(x):
            try:
                return int("".join(c for c in str(x) if c.isdigit()))
            except Exception:
                return None

        misses_total = 0
        for pdb_key, pdata in (getattr(self, "pdb_info_dict", {}) or {}).items():
            rcm = (pdata or {}).get("residue_chain_map", {}) or {}


            idxmap_simple = {}

            idxmap_seg = {}


            for ch, lst in rcm.items():
                ch_u = _canon(ch)
                for r in (lst or []):
                    rn_i = _digits_only(r.get("residue_num"))
                    ix = r.get("index")
                    if rn_i is None or ix is None:
                        continue


                    key = (ch_u, rn_i)
                    if key in idxmap_simple and idxmap_simple[key] != ix:

                        idxmap_simple[key] = None
                    else:
                        idxmap_simple[key] = ix


                    seg = r.get("segname")
                    seg_u = _canon(seg)
                    if seg_u:
                        idxmap_seg[(seg_u, ch_u, rn_i)] = ix

            def _mk_list(inp):
                out = []
                for it in (inp or []):
                    ch_u = _canon(it.get("chain"))
                    rn_i = _digits_only(it.get("residue_num"))
                    seg = it.get("segname")
                    seg_u = _canon(seg)

                    idx = None

                    if seg_u is not None and rn_i is not None:
                        idx = idxmap_seg.get((seg_u, ch_u, rn_i))

                    if idx is None and rn_i is not None:
                        idx = idxmap_simple.get((ch_u, rn_i))

                    rec = {
                        "chain": it.get("chain"),
                        "residue_num": it.get("residue_num"),
                        "index": idx,
                    }

                    if seg is not None:
                        rec["segname"] = seg

                    out.append(rec)
                return out

            src_list = _mk_list(source_residues)
            snk_list = _mk_list(sink_residues)
            pdata["residue_dict"] = {"source_residues": src_list, "sink_residues": snk_list}

            miss = sum(1 for x in (src_list + snk_list) if x.get("index") is None)
            misses_total += miss
            self.log_output(
                f"🧭 Seeded {pdb_key}: "
                f"{len(src_list)} src, {len(snk_list)} sink (missing index: {miss}).\n"
            )

        if misses_total:
            self.log_output(
                "⚠ Index not found for some residues. These nodes are ignored in K-shortest.\n"
            )
        else:
            self.log_output("✅ The index was successfully mapped for all residues..\n")

    def threaded_run_residue_mapping(self, jobname, reference_pdb, source_residues, sink_residues):

        try:
            from MUSIKALL_functions1 import run_residue_mapping
            import os
        except Exception as e:
            self.log_output(f"❌ Import error in mapping helpers: {e}\n")
            return

        try:
            self.log_output(f"🔍 Starting alignment for {jobname}…\n")


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
            try:
                if ref_key is not None:
                    rd = (self.pdb_info_dict.get(ref_key, {}) or {}).get("residue_dict", {}) or {}
                    self.reference_residues = []
                    for r in (rd.get("source_residues", []) or []):
                        r2 = dict(r);
                        r2["type"] = "Source"
                        self.reference_residues.append(r2)
                    for r in (rd.get("sink_residues", []) or []):
                        r2 = dict(r);
                        r2["type"] = "Sink"
                        self.reference_residues.append(r2)
                else:
                    self.reference_residues = []
            except Exception:
                self.reference_residues = []

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

            # 4) Stage + autosave (critical)
            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.last_completed_stage = "mapping_done"
            self.state["last_completed_stage"] = self.last_completed_stage
            self.autosave_job("mapping_done")

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

        # ✅ job folder tek kaynak
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

            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.state["mapping_signature"] = sig

            self._start_ksp_async(jobpath, k)  # 👈 jobpath gönder
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

            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.state["mapping_signature"] = sig

            threading.Thread(
                target=self.threaded_run_residue_mapping,
                args=(jobpath, reference_pdb, src, snk),
                daemon=True
            ).start()
            return

        # mapping hazır → KSP
        self._pending_ksp = None
        self._start_ksp_async(jobpath, k)

    def _start_ksp_async(self, jobname, k):
        threading.Thread(
            target=self.threaded_calculate_shortest_paths,
            args=(jobname, k),
            daemon=True
        ).start()

    def _ksp_cache_path(self, jobpath):
        import os
        return os.path.join(jobpath, "ksp_cache.pkl")

    def _save_ksp_cache(self, jobpath):
        import pickle
        payload = {
            "paths_dict_2": getattr(self, "paths_dict_2", None),
            "all_normalized_frequencies": getattr(self, "all_normalized_frequencies", None),
            "overall_file": getattr(self, "overall_file", None),
            "per_pdb_files": getattr(self, "per_pdb_files", None),
            "pdb_info_dict": getattr(self, "pdb_info_dict", None),
            "adjacency_matrices": getattr(self, "adjacency_matrices", None),
            "net_cost_matrices": getattr(self, "net_cost_matrices", None),
        }
        with open(self._ksp_cache_path(jobpath), "wb") as f:
            pickle.dump(payload, f)

    def _restore_ksp_cache(self, jobpath):
        import os, pickle
        p = self._ksp_cache_path(jobpath)
        if not os.path.exists(p):
            return False
        with open(p, "rb") as f:
            payload = pickle.load(f) or {}
        self.paths_dict_2 = payload.get("paths_dict_2")
        self.all_normalized_frequencies = payload.get("all_normalized_frequencies")
        self.overall_file = payload.get("overall_file")
        self.per_pdb_files = payload.get("per_pdb_files")
        return True

    def threaded_calculate_shortest_paths(self, jobpath, k):
        try:
            from MUSIKALL_functions1 import (
                calculate_shortest_paths,
                convert_paths_to_residues,
                save_paths_to_excel,
            )
            self.reset_section3()
            self.k_entry.delete(0, tk.END)
            self.k_entry.insert(0, str(k))

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
            self.last_completed_stage = "ksp_done"
            self.state["last_completed_stage"] = self.last_completed_stage
            self.build_interactive_cache(force=True)


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
            ax.bar(range(len(vals)), vals)  # renk vermiyoruz (UI yönergenize uygun)
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

            def _pretty_residue_label(x):

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

            events.sort(key=lambda e: (float(e.get("start_sec", 0.0)), str(e.get("residue") or e.get("token") or "")))

            for i, e in enumerate(events, start=1):
                residue_raw = e.get("residue") or e.get("token") or ""
                residue = _pretty_residue_label(residue_raw)
                note_txt = e.get("note", "")
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

                for iid in ev_tv.get_children():
                    ev_tv.item(iid, tags=())
                return

            t = ms / 1000.0

            ev_idx = None
            for i, e in enumerate(current["events"], start=1):
                if float(e.get("start_sec", 0.0)) <= t < float(e.get("end_sec", 0.0)):
                    ev_idx = i
                    break


            for iid in ev_tv.get_children():
                ev_tv.item(iid, tags=())
            if ev_idx is not None:
                iid = f"row{ev_idx}"
                ev_tv.see(iid)
                ev_tv.item(iid, tags=(highlight_tag,))

            current["poll_id"] = win.after(100, _poll_highlight)

        def _play_selected(path=None):
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


            if current["poll_id"]:
                try:
                    win.after_cancel(current["poll_id"])
                except Exception:
                    pass
            current["poll_id"] = win.after(100, _poll_highlight)

        play_btn.configure(command=lambda: _play_selected())


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


                    if not hasattr(self, "state") or not isinstance(self.state, dict):
                        self.state = {}
                    self.last_completed_stage = "music_done"
                    self.state["last_completed_stage"] = self.last_completed_stage


                    self.state["last_music_files"] = list(written)


                    try:
                        self.after(0, lambda: self.autosave_job("music_done"))
                    except Exception:

                        try:
                            self.autosave_job("music_done")
                        except Exception:
                            pass

                    self.open_music_player(written, event_logs=event_logs)
                else:
                    self.log_output("⚠️ No MIDI files produced.\n")

            except Exception as e:
                self.log_output(f"❌ Audio generation failed: {e}\n")

        threading.Thread(target=_run, daemon=True).start()

    def build_music_sidebar(self, parent):
        box = ttk.LabelFrame(parent, text="🎵 Generate Audio", style="Card.TLabelframe", padding=(8, 8))
        box.pack(side="top", fill="both", expand=True, padx=8, pady=8)

        top = ttk.Frame(box, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 6))
        ttk.Button(top, text="Advanced…", command=self.open_music_advanced).pack(side="left", padx=4)
        ttk.Button(top, text="Reset Defaults", command=self.reset_aa_defaults).pack(side="left", padx=4)

        info_btn = tk.Label(top, text="ⓘ", fg=self.current_palette["accent"], cursor="question_arrow",
                            bg=self.current_palette["bg"])
        info_btn.pack(side="left", padx=(6, 0))
        Tooltip(info_btn,
                "AA→note assignment: choose a note and octave for each amino acid.\n"
                "‘Reset Defaults’ will reassign notes according to the scale/octave set in Advanced Options.\n"
                "‘Generate MIDI’ will sequence the paths and produce music files."
                )


        inner = ttk.Frame(box, style="Card.TFrame")
        inner.pack(fill="both", expand=True, padx=4, pady=4)


        hdr = ttk.Frame(inner, style="Card.TFrame")
        hdr.grid(row=0, column=0, columnspan=25, sticky="w", padx=4, pady=(2, 6))

        ttk.Label(hdr, text="AA", font=("Arial", 10, "bold"), style="Card.TLabel").grid(row=0, column=0, padx=(40, 4),
                                                                                        sticky="w")
        ttk.Label(hdr, text="Note", font=("Arial", 10, "bold"), style="Card.TLabel").grid(row=0, column=1, padx=(82, 4),
                                                                                          sticky="w")
        ttk.Label(hdr, text="Oct", font=("Arial", 10, "bold"), style="Card.TLabel").grid(row=0, column=2, padx=(16, 4),
                                                                                         sticky="w")

        ttk.Label(hdr, text="AA", font=("Arial", 10, "bold"), style="Card.TLabel").grid(row=0, column=3, padx=(40, 4),
                                                                                        sticky="w")
        ttk.Label(hdr, text="Note", font=("Arial", 10, "bold"), style="Card.TLabel").grid(row=0, column=4, padx=(82, 4),
                                                                                          sticky="w")
        ttk.Label(hdr, text="Oct", font=("Arial", 10, "bold"), style="Card.TLabel").grid(row=0, column=5, padx=(21, 4),
                                                                                         sticky="w")


        self.aa_widgets = {}
        left_items = ALL_RESIDUES[:14]
        right_items = ALL_RESIDUES[14:]

        def add_row(base_row, col_offset, item):
            aa3, aa1, fullname = item
            ttk.Label(inner, text=f"{aa3} ({aa1}) – {fullname}", style="Card.TLabel").grid(
                row=base_row, column=col_offset + 0, padx=4, pady=2, sticky="w")

            note_frame = ttk.Frame(inner, style="Card.TFrame", padding=(2, 0))
            note_frame.grid(row=base_row, column=col_offset + 1, padx=4, pady=2, sticky="w")

            cb = ttk.Combobox(note_frame, values=NOTE_NAMES, width=6, state="readonly")
            cb.pack(fill="x", expand=True)

            oe = ttk.Entry(inner, width=3)
            oe.grid(row=base_row, column=col_offset + 2, padx=4, pady=2, sticky="w")

            self.aa_widgets[aa3] = {"note": cb, "oct": oe}

        for i, item in enumerate(left_items, start=1):
            add_row(i, 0, item)
        for i, item in enumerate(right_items, start=1):
            add_row(i, 3, item)

        self.init_music_options()
        self.reset_aa_defaults()

        bottom = ttk.Frame(box, style="Card.TFrame")
        bottom.pack(fill="x", pady=(10, 6))
        ttk.Button(bottom, text="🎶 Generate Audio", command=self.generate_audio).pack(side="left", padx=6, pady=2)

    def init_music_options(self):

        self.music_opts = MusicOptions()

        self.adv_scale_var = tk.StringVar(value=self.music_opts.default_scale_name)
        self.adv_base_octave_var = tk.IntVar(value=self.music_opts.default_base_octave)


        self._mapping_mode = tk.StringVar(value=self.music_opts.mapping_mode)  # "aa" | "property" | "single"


        self._prop_dimension = tk.StringVar(value=getattr(self.music_opts, "property_dimension", "hydrophobicity"))
        self._prop_octave = tk.IntVar(value=getattr(self.music_opts, "property_base_octave", 4))
        self._prop_triad_vars = {}


        self._chord_mode = tk.StringVar(value=self.music_opts.chord_mode)
        self._aa_triad = tk.StringVar(value=getattr(self.music_opts, "aa_triad_name", "Major (I)"))


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

        self._rep_res_freq = tk.StringVar(value=getattr(self.music_opts, "rep_res_freq", "per_pdb"))


        self._tempo_var = tk.IntVar(value=self.music_opts.tempo_bpm)
        self._note_value = tk.StringVar(value="Quarter (1/4)")
        self._rest_ratio = tk.DoubleVar(value=0.25)


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
            ib.pack(side="left", padx=(6, 0))

        def _note_value_to_beats(label: str) -> float:
            return {"Whole (1/1)": 4.0, "Half (1/2)": 2.0, "Quarter (1/4)": 1.0, "Eighth (1/8)": 0.5,
                    "Sixteenth (1/16)": 0.25}.get(label, 1.0)

        # ===== Output Structure =====
        head("🏗 Output Structure")
        fr = ttk.Frame(inner, style="Card.TFrame") 
        fr.grid(row=row, column=0, sticky="w", padx=8, pady=4) 
        row += 1

        ttk.Label(fr, text="Normalized aaFrequencies", style="Card.TLabel").pack(side="left")
        tip(fr, "How files are grouped: per_path, per_pair, or per_pdb.")
        ttk.Combobox(fr, textvariable=self._rep_res_freq, state="readonly",
                     values=["per_path", "per_pair", "per_pdb"], width=14).pack(side="left", padx=8)

        ttk.Label(fr, text="Select Representation", style="Card.TLabel").pack(side="left", padx=(12, 0))
        tip(fr, "aa: identity grid  property: harmony by biochemical group  single: focus one AA.")
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
        aa_frame = ttk.Labelframe(map_slot, text="aaGrid (identity → root)", padding=(6, 6), style="Card.TLabelframe")
        prop_frame = ttk.Labelframe(map_slot, text="Property-based harmony", padding=(6, 6), style="Card.TLabelframe")
        single_frame = ttk.Labelframe(map_slot, text="Single Residuefocus", padding=(6, 6), style="Card.TLabelframe")

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
        ttk.Label(fr_aa_tri, text="Residuetriad", style="Card.TLabel").pack(side="left")
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
                              values=["hydrophobicity", "charge", "aromaticity"], width=18)
        dim_cb.pack(side="left", padx=8)

        fr_oct = ttk.Frame(prop_frame, style="Card.TFrame") 
        fr_oct.pack(fill="x", pady=2)
        ttk.Label(fr_oct, text="Fallback base octave", style="Card.TLabel").pack(side="left")
        tip(fr_oct, "If Residuegrid has no root for a token, use C at this octave.")
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
        ttk.Label(fr_s1, text="Residue(one-letter)", style="Card.TLabel").pack(side="left")
        tip(fr_s1, "Only this Residueplays  others rest/skip.")
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

        # ===== ResidueGrid Defaults =====
        head("⚙ ResidueGrid Defaults")
        fr_sc = line("Scale")
        tip(fr_sc, "Scale used by ‘Reset Defaults’ to (re)fill the Residuegrid.")
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

            # Mapping + Residuegrid
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
        ttk.Button(btns, text="Save & Reset ResidueDefaults", command=_apply_and_reset).pack(side="left", padx=6)

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

            try:
                from MUSIKALL_functions1 import (
                    save_global_total_colored_reference_pdb as pr_save_global_total
                )
                paths_dict_2 = getattr(self, "paths_dict_2", None) or {}

                pr_save_global_total(
                    job_dir,
                    paths_dict_2,
                    reference_pdb=None,
                    logger=self
                )
                self.log_output("🎨 GLOBAL/TOTAL colored reference PDB saved in the job folder.\n")
            except Exception as e:
                self.log_output(f"⚠️ GLOBAL/TOTAL coloring skipped: {e}\n")

            if not hasattr(self, "state") or not isinstance(self.state, dict):
                self.state = {}
            self.last_completed_stage = "colored_models_done"
            self.state["last_completed_stage"] = self.last_completed_stage
            self.state["colored_models_dir"] = str(job_dir)

            self.build_interactive_cache(force=True)
            try:
                self.after(0, lambda: self.autosave_job("colored_models_done"))
            except Exception:
                self.autosave_job("colored_models_done")

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
                    base_dir,
                    "MUSIKALL_3d_viewer",
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

        self._lazy_matplotlib()

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib import cm
        from matplotlib import colors as mcolors
        import numpy as np

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


        lookup = {}
        orig_pct = {}

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


            for key, v in tmp.items():
                v_clamped = max(0.0, min(float(v), 100.0))
                orig_pct[key] = v_clamped
                lookup[key] = v_clamped / 100.0


        fig = Figure(figsize=(6, 5), dpi=100)
        ax = fig.add_subplot(111, projection="3d")

        for _, pts in chains.items():
            xs, ys, zs, _, _ = zip(*pts)
            ax.plot(xs, ys, zs, linewidth=1.1, alpha=0.65, color="#8a8a8a")


        all_x, all_y, all_z = [], [], []
        all_val, all_lbl, all_key = [], [], []
        norm = mcolors.Normalize(vmin=0.0, vmax=1.0, clip=True)
        threshold = 0.05

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

        from matplotlib import patheffects as pe

        def _rgba_to_hex(rgba):
            return mcolors.to_hex(rgba, keep_alpha=False)

        def _luminance(rgb):
            r, g, b = rgb[:3];  return 0.2126 * r + 0.7152 * g + 0.0722 * b

        rgba_colors = cm.plasma(norm(all_val_arr))
        hex_colors = [_rgba_to_hex(rgba) for rgba in rgba_colors]

        micro_labels = []
        widget_micro_visible_default = True

        for i, (x, y, z) in enumerate(zip(all_x, all_y, all_z)):
            ch, rid = all_key[i]
            if (ch, rid) in SKIP_KEYS:
                micro_labels.append(None)
                continue
            rgba = rgba_colors[i]
            stroke_fg = "white" if _luminance(rgba) < 0.45 else "black"

            txt = ax.text(
                x, y, z, all_lbl[i],
                color=hex_colors[i],
                fontsize=6,
                zorder=1,
                clip_on=True
            )
            txt.set_path_effects([pe.withStroke(linewidth=1.2, foreground=stroke_fg, alpha=0.9)])
            micro_labels.append(txt)


        size_min, size_max, gamma = 110.0, 360.0, 0.65
        vals_gamma = np.power(all_val_arr, gamma)
        sizes = size_min + (size_max - size_min) * vals_gamma

        sc = ax.scatter(
            all_x, all_y, all_z,
            s=sizes,
            c=all_val_arr, cmap=cm.plasma, norm=norm,
            marker="o", depthshade=True, zorder=10
        )
        sc.set_picker(True)


        try:
            from mpl_toolkits.axes_grid1.inset_locator import inset_axes
            ticks = np.linspace(0, 1, 5)
            cax = inset_axes(ax, width="3%", height="60%", loc="center right",
                             bbox_to_anchor=(0.08, 0.0, 1.0, 1.0),
                             bbox_transform=ax.transAxes, borderpad=0.0)
            cb = fig.colorbar(sc, cax=cax, orientation="vertical", ticks=ticks)


            cb.set_label("Frequency (%)", fontsize=9)
            cb.ax.set_yticklabels([f"{int(t * 100)}" for t in ticks])
            cb.ax.tick_params(labelsize=8)

        except Exception:
            pass


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


        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)

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


        import numpy as _np
        from matplotlib.transforms import Bbox
        prior_idx = _np.argsort(-vals_gamma)
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

            for t in micro_labels:
                if t is not None:
                    t.set_visible(True)

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
        _declutter_labels()

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

    def save_job(self):
        jobname = self.jobname_entry.get().strip()
        if not jobname:
            messagebox.showerror("Error", "Please create/select a job first.")
            return

        try:
            from MUSIKALL_functions1 import save_job_snapshot
            job_dir = save_job_snapshot(jobname, self, also_save_run=False)
            self.log_output(f"💾 Job saved: {job_dir}\n")
        except Exception as e:
            self.log_output(f"❌ Save job failed: {e}\n")
            messagebox.showerror("Save Job", str(e))

    def autosave_job(self, stage=None):

        try:
            jobpath = getattr(self, "current_job_folder", None) or getattr(self, "current_job", None)
            if not jobpath:
                return

            # her zaman state + pdb_info_dict
            self._save_job_state(jobpath)

            st = stage or getattr(self, "last_completed_stage", "")

            if st in ("matrices_ready", "mapping_done", "ksp_done", "music_done", "colored_models_done"):
                self._save_matrices_cache(jobpath)

            if st in ("ksp_done", "music_done", "colored_models_done"):

                self._save_ksp_cache(jobpath)

        except Exception as e:
            self.log_output(f"⚠ Autosave failed: {e}\n")

    def load_job(self):
        from tkinter import filedialog, messagebox
        import os

        job_dir = filedialog.askdirectory(title="Select MUSIKALL Job Folder")
        if not job_dir:
            return

        try:
            self.current_job = job_dir

            from MUSIKALL_functions1 import load_job_snapshot
            state = load_job_snapshot(job_dir, self)

            jobname = state.get("jobname") or os.path.basename(job_dir)
            self.jobname_entry.delete(0, "end")
            self.jobname_entry.insert(0, jobname)


            self._refresh_after_job_load()

            self.log_output(f"📂 Job loaded: {job_dir}\n")
            self.log_output(f"ℹ️ Stage: {getattr(self, 'last_completed_stage', None)}\n")

        except Exception as e:
            self.log_output(f"❌ Load job failed: {e}\n")
            messagebox.showerror("Load Job", str(e))

    def _refresh_after_job_load(self):
        """
        Minimal UI refresh hook.
        Enable/disable buttons based on what is present.
        You can expand this as needed.
        """
        has_pdb = bool(getattr(self, "pdb_info_dict", None))
        has_paths = bool(getattr(self, "paths_dict_2", None))
        has_freq = bool(getattr(self, "all_normalized_frequencies", None))


    def _job_state_path(self, jobpath):
        import os
        return os.path.join(jobpath, "job_state.pkl")

    def _save_job_state(self, jobpath):
        import pickle
        payload = {
            "state": getattr(self, "state", {}) or {},
            "last_completed_stage": getattr(self, "last_completed_stage", None),
            "pdb_info_dict": getattr(self, "pdb_info_dict", None),
            "mapping_signature": (getattr(self, "state", {}) or {}).get("mapping_signature"),
        }
        with open(self._job_state_path(jobpath), "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        return True

    def _restore_job_state(self, jobpath):
        import os, pickle
        p = self._job_state_path(jobpath)
        if not os.path.exists(p):
            return False
        with open(p, "rb") as f:
            payload = pickle.load(f) or {}

        # restore basics
        self.state = payload.get("state") or {}
        self.last_completed_stage = payload.get("last_completed_stage", None)

        # critical
        self.pdb_info_dict = payload.get("pdb_info_dict") or {}

        return True

    def _matrices_cache_path(self, jobpath):
        import os
        return os.path.join(jobpath, "matrices_cache.npz")

    def _save_matrices_cache(self, jobpath):

        import numpy as np

        payload = {}

        adj = getattr(self, "adjacency_matrices", None)
        ncm = getattr(self, "net_cost_matrices", None)


        if isinstance(adj, dict):
            for k, v in adj.items():
                if v is None:
                    continue
                payload[f"adj::{str(k)}"] = np.asarray(v)
        if isinstance(ncm, dict):
            for k, v in ncm.items():
                if v is None:
                    continue
                payload[f"ncm::{str(k)}"] = np.asarray(v)

        if not payload:
            return False

        np.savez_compressed(self._matrices_cache_path(jobpath), **payload)
        return True

    def _restore_matrices_cache(self, jobpath):

        import os
        import numpy as np

        p = self._matrices_cache_path(jobpath)
        if not os.path.exists(p):
            return False

        data = np.load(p, allow_pickle=False)

        adj = {}
        ncm = {}

        for name in data.files:
            if name.startswith("adj::"):
                k = name.split("::", 1)[1]
                adj[k] = data[name]
            elif name.startswith("ncm::"):
                k = name.split("::", 1)[1]
                ncm[k] = data[name]

        # Restore
        self.adjacency_matrices = adj
        self.net_cost_matrices = ncm
        return True


if __name__ == "__main__":
    MUSIKALL_GUI().mainloop()
