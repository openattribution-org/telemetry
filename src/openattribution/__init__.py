"""OpenAttribution namespace package."""

# Use pkgutil to support namespace packages across multiple installation paths.
# This allows openattribution.telemetry, openattribution.telemetry_server, and
# openattribution.aims to be installed as separate packages while sharing the
# openattribution namespace.
from pkgutil import extend_path  # noqa: E402

__path__ = extend_path(__path__, __name__)
