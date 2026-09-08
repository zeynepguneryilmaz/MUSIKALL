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

A ready-to-use Windows installer is available from the latest GitHub release:

[Download MUSIKALL for Windows](https://github.com/zeynepguneryilmaz/MUSIKALL/releases/latest)

Download `MUSIKALL_Setup.exe` from the **Assets** section of the release page and run the installer.

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
