# MUSIKALL

MUSIKALL is a Python-based software framework for calculating, analyzing, visualizing, and sonifying k-shortest communication pathways in biomolecular structures.

Biomolecular structures are represented as residue interaction networks, and communication routes are evaluated using ensembles of alternative low-cost pathways. MUSIKALL supports proteins, RNA/DNA structures, and hybrid biomolecular assemblies such as ribosomes, as well as both single-structure and multi-structure analyses. Standard polymer residues are represented as residue-level network nodes and their heavy atoms are used for contact counting.

## Main Features

- Residue interaction network construction
- k-shortest communication pathway calculation
- Multiple source and sink node selection
- Single-structure and multi-structure analysis
- Residue participation frequency analysis
- Residue-pair co-occurrence analysis
- Pathway similarity analysis
- Physicochemical property annotation
- Frequency-encoded structural outputs
- Interactive 3D molecular visualization
- MIDI-based pathway sonification
- Tabular and graphical output generation

## Windows Standalone Application

A ready-to-use Windows build is available from the latest GitHub release:

[Download MUSIKALL for Windows](https://github.com/zeynepguneryilmaz/MUSIKALL/releases/latest)

The standalone build allows MUSIKALL to be used without manually installing Python or individual dependencies.

## Google Colab

MUSIKALL can also be run in a web browser using Google Colab:

[Open MUSIKALL in Google Colab](https://colab.research.google.com/drive/1Sr_BIIDFpsr_oROwXrh4QZawf9sAMDAp)

The Colab edition provides a browser-based workflow for pathway calculations and downstream analyses without requiring a local Python installation.

## Running from Source

Python 3.11 is recommended.

```bash
git clone https://github.com/zeynepguneryilmaz/MUSIKALL.git
cd MUSIKALL
pip install -r requirements.txt
python MUSIKALL_gui1.py
```

## Building the Windows Application

From the repository root, install the required packages and run PyInstaller with the provided spec file:

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller MUSIKALL.spec
```

The build output is written under `dist/MUSIKALL/`. The installer can then be compiled with Inno Setup using `musikall.iss`.

## Version Note

In the current release, path-similarity node handling uses a consistent node-to-global-index conversion workflow before incidence-matrix construction. The k-shortest path calculation, contact normalization, edge-cost definition, cosine similarity calculation, and threshold-based clustering method are unchanged.

## Citation

Citation metadata for MUSIKALL is maintained in the repository-level [`CITATION.cff`](CITATION.cff) file. On GitHub, use **Cite this repository** to obtain the current software citation.

When the MUSIKALL journal article is published, the recommended article citation can be added to `CITATION.cff` as the preferred citation without changing the software interface.

Official repository: https://github.com/zeynepguneryilmaz/MUSIKALL

## License

MUSIKALL is distributed under the MIT License. See [`LICENSE`](LICENSE).

The repository also bundles third-party software used for molecular visualization. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the applicable third-party license information.
