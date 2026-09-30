"""Stage 3-6 empirical analysis.

Consumes validated extraction records plus the two gold standards and produces
the numbers behind RQ2 and RQ4-RQ8. Independent of any model provider.

Modules
-------
empirical   flattening, ranking metrics, cluster bootstrap, RQ2, RQ8,
            calibration, cross-domain comparison
selftest    synthetic corpora with planted structure; run this first

The causal stage itself (per-record causal impact, edge stability) reuses
`stage0/impact.py` and `stage0/discovery.py` rather than duplicating them, so
there is one implementation of Structural Hamming Distance in the project and
one place for it to be wrong.
"""

__all__ = ["empirical"]
__version__ = "0.1.0"
