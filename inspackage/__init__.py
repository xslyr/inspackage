from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("inspackage")
except PackageNotFoundError:  # código-fonte usado sem instalar o pacote (ex.: PYTHONPATH=.)
    __version__ = "0.0.0+unknown"
