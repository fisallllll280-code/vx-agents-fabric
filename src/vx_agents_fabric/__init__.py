"""VX agent coordination fabric for VAIXLNS."""
from .contracts import AgentSpec, Artifact, TaskEnvelope, WorkflowReport
from .registry import AgentRegistry, default_registry
from .orchestrator import EngineeringOrchestrator
from .artifact_archive import ArtifactArchive
from .failure_memory import FailureMemory
from .ledger import IntegrityLedger

__all__ = [
    "AgentSpec", "Artifact", "TaskEnvelope", "WorkflowReport",
    "AgentRegistry", "default_registry", "EngineeringOrchestrator",
    "ArtifactArchive", "FailureMemory", "IntegrityLedger",
]
