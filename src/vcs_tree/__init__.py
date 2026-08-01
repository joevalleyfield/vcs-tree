"""Inventory Git and Jujutsu repositories below a directory."""

from vcs_tree.scanner import find_repo_roots, vcs_tree

__all__ = ["find_repo_roots", "vcs_tree"]
__version__ = "0.1.0"
from .git_adapter import GitAdapter, GitObservation
from .jj_adapter import JjAdapter, JjObservation
from .ledger import (
    HistoryLedger,
    LedgerCorruptError,
    LedgerError,
    LedgerStatus,
    StatePaths,
    WriterMismatchError,
    resolve_paths,
)
from .models import (
    Backend,
    Certainty,
    CollectionError,
    CollectionOutcome,
    CollectionState,
    ContractError,
    DeltaEnvelope,
    Event,
    HistoryBoundary,
    HistoryBoundaryState,
    HistoryStore,
    IntegrityState,
    ObjectId,
    Placement,
    RepositoryMode,
    Retention,
    SnapshotEnvelope,
    WriterPolicy,
    dumps,
    loads,
)

__all__ = [
    "Backend", "Certainty", "CollectionError", "CollectionOutcome", "CollectionState",
    "ContractError", "DeltaEnvelope", "Event", "HistoryBoundary", "HistoryBoundaryState",
    "HistoryStore", "IntegrityState", "ObjectId", "Placement", "RepositoryMode", "Retention",
    "SnapshotEnvelope", "WriterPolicy", "dumps", "loads",
    "HistoryLedger", "LedgerCorruptError", "LedgerError", "LedgerStatus", "StatePaths",
    "WriterMismatchError", "resolve_paths",
    "GitAdapter", "GitObservation",
    "JjAdapter", "JjObservation",
]
