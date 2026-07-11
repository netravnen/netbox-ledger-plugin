from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('netbox-ledger-tracker')
except PackageNotFoundError:
    __version__ = '0.0.0.dev0+unknown'
