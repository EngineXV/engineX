"""Engine Tools - Tool library for the Engine agent framework"""

__version__ = "0.1.0"

from .credentials import (
    CREDENTIAL_SPECS,
    CredentialError,
    CredentialSpec,
    CredentialStoreAdapter,
)


def __getattr__(name: str):
    """Lazy import for tools that require fastmcp"""
    if name == "register_all_tools":
        from .tools import register_all_tools

        return register_all_tools
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "CredentialStoreAdapter",
    "CredentialSpec",
    "CredentialError",
    "CREDENTIAL_SPECS",
    "register_all_tools",
]
