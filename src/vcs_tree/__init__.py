"""Inventory Git and Jujutsu repositories below a directory."""

from vcs_tree.scanner import find_repo_roots, vcs_tree

__all__ = ["find_repo_roots", "vcs_tree"]
__version__ = "0.1.0"
from .delta import DeltaCalculator, HistoryDeltaCalculator
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
    PulseEnvelope,
    RepositoryMode,
    Retention,
    SnapshotEnvelope,
    WriterPolicy,
    dumps,
    loads,
)
from .pulse import PulseOrchestrator, PulseSelectionError
from .snapshot import SnapshotCollector, SnapshotResult, discover_repository_roots

__all__ = [
    "Backend",
    "Certainty",
    "CollectionError",
    "CollectionOutcome",
    "CollectionState",
    "ContractError",
    "DeltaEnvelope",
    "Event",
    "HistoryBoundary",
    "HistoryBoundaryState",
    "HistoryStore",
    "IntegrityState",
    "ObjectId",
    "PulseEnvelope",
    "Placement",
    "RepositoryMode",
    "Retention",
    "SnapshotEnvelope",
    "WriterPolicy",
    "dumps",
    "loads",
    "HistoryLedger",
    "LedgerCorruptError",
    "LedgerError",
    "LedgerStatus",
    "StatePaths",
    "WriterMismatchError",
    "resolve_paths",
    "GitAdapter",
    "GitObservation",
    "JjAdapter",
    "JjObservation",
    "SnapshotCollector",
    "SnapshotResult",
    "discover_repository_roots",
    "DeltaCalculator",
    "HistoryDeltaCalculator",
    "PulseOrchestrator",
    "PulseSelectionError",
]
