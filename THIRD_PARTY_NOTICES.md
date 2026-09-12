# Third-party components

Ariadne's source distribution does not vendor dependency source or binaries. Installation resolves these packages separately. Their installed distributions include authoritative license notices; preserve those notices if creating a bundled executable. This file does not relicense dependencies.

| Component | Upstream |
| --- | --- |
| Pillow | https://github.com/python-pillow/Pillow |
| NumPy | https://github.com/numpy/numpy |
| SciPy | https://github.com/scipy/scipy |
| Shapely / GEOS | https://github.com/shapely/shapely |
| scikit-image | https://github.com/scikit-image/scikit-image |
| pyembroidery 1.5.1 | https://github.com/EmbroidePy/pyembroidery |
| Python / Tcl / Tk | https://www.python.org/ and https://www.tcl-lang.org/ |

Numerical and image-processing wheels can include additional native libraries and licenses. Consult each installed distribution's `dist-info` license files before redistributing those wheels or a frozen application. The public source ZIP, sdist and pure-Python Ariadne wheel include only Ariadne's code and documentation.
