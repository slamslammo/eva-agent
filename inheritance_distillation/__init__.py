"""Same-scenario inherited-prior distillation from runtime traces."""

from .bundle_writer import write_distilled_prior_bundle
from .pipeline import distill_runtime_dirs, distill_trace_bundles

__all__ = [
    "distill_runtime_dirs",
    "distill_trace_bundles",
    "write_distilled_prior_bundle",
]
