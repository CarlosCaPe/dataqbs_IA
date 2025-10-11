"""TLS compare audios package (renamed from telus_compara_audios).

This package was renamed to remove legacy branding. Any code importing the old
package name should migrate to `tls_compara_audios`.
"""

from . import paths  # noqa: F401

__all__ = ["paths"]
