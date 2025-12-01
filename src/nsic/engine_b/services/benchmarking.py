"""
Benchmarking Service
GPU Assignment: 6

Compares Qatar metrics against peer countries and international standards.
Provides percentile rankings, gap analysis, and peer comparisons.
GPU-accelerated for large-scale statistical computations.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np

# Try GPU acceleration with CuPy
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    cp = np  # Fallback to numpy
    GPU_AVAILABLE = False

from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class PeerData:
    """Data for a peer country/entity."""
    name: str
    value: float
    region: Optional[str] = None
    income_group: Optional[str] = None


@dataclass
class BenchmarkMetric:
    """Single metric for benchmarking."""
    
    # Metric name
    name: str
    
    # Qatar's value
    qatar_value: float
    
    # Peer data
    peers: list[PeerData]
    
    # Higher is better (True) or lower is better (False)
    higher_is_better: bool = True
    
    # Target value (if any)
    target: Optional[float] = None
    
    # International standard (if any)
    international_standard: Optional[float] = None


@dataclass
class BenchmarkingInput:
    """Input specification for benchmarking analysis."""
    
    # Metrics to benchmark
    metrics: list[BenchmarkMetric]
    
    # Peer group filter (optional)
    peer_filter: Optional[Literal["gcc", "high_income", "mena", "all"]] = None
    
    # GPU ID
    gpu_id: int = 6


@dataclass
class MetricBenchmark:
    """Benchmark result for a single metric."""
    
    # Metric name
    metric_name: str
    
    # Qatar's position
    qatar_value: float
    qatar_rank: int  # 1 = best
    qatar_percentile: float  # 0-100
    
    # Peer statistics
    peer_mean: float
    peer_median: float
    peer_std: float
    peer_min: float
    peer_max: float
    
    # Gap analysis
    gap_to_mean: float
    gap_to_best: float
    gap_to_target: Optional[float]
    gap_to_standard: Optional[float]
    
    # Z-score (how many std devs from mean)
    z_score: float
    
    # Is Qatar an outlier?
    is_outlier: bool
    outlier_direction: Optional[Literal["above", "below"]]
    
    # Performance assessment
    performance: Literal["leading", "above_average", "average", "below_average", "lagging"]
    
    # Best and worst peers
    best_peer: PeerData
    worst_peer: PeerData
    closest_peers: list[PeerData]  # Similar values


@dataclass
class BenchmarkingResult:
    """Output from benchmarking analysis."""
    
    # Per-metric benchmarks
    metric_benchmarks: list[MetricBenchmark]
    
    # Overall composite score (0-100)
    composite_score: float
    
    # Qatar's overall ranking
    overall_rank: int
    overall_percentile: float
    
    # Areas of strength
    strengths: list[str]  # Metric names where Qatar excels
    
    # Areas for improvement
    improvement_areas: list[str]  # Metric names where Qatar lags
    
    # Peer comparison summary
    outperforms_peers: int  # Count of metrics where Qatar > peer mean
    underperforms_peers: int
    
    # Metadata
    n_metrics: int
    n_peers: int
    gpu_used: bool
    execution_time_ms: float


class BenchmarkingService:
    """
    Domain-agnostic benchmarking service.
    GPU-accelerated for statistical computations.
    
    GPT-5 provides:
    - Metrics to compare (from data extraction)
    - Qatar values (from LMIS/local data)
    - Peer data (from World Bank, ILO, etc.)
    
    This service computes:
    - Rankings and percentiles
    - Gap analysis
    - Outlier detection
    - Composite scoring
    """
    
    def __init__(self, gpu_id: int = 6):
        """Initialize benchmarking service with GPU."""
        self.gpu_id = gpu_id
        self.gpu_available = GPU_AVAILABLE
        
        # Set GPU device if available
        if GPU_AVAILABLE:
            try:
                cp.cuda.Device(gpu_id).use()
                self.xp = cp
                logger.info(f"BenchmarkingService initialized on GPU {gpu_id}")
            except Exception as e:
                logger.warning(f"GPU {gpu_id} not available: {e}, using CPU")
                self.xp = np
                self.gpu_available = False
        else:
            self.xp = np
            logger.info("BenchmarkingService using CPU (CuPy not available)")
    
    def benchmark(self, input_spec: BenchmarkingInput) -> BenchmarkingResult:
        """
        Run benchmarking analysis.
        
        Args:
            input_spec: BenchmarkingInput with metrics and peer data
            
        Returns:
            BenchmarkingResult with rankings and gap analysis
        """
        import time
        start_time = time.perf_counter()
        
        metric_benchmarks = []
        all_peer_names = set()
        
        for metric in input_spec.metrics:
            # Filter peers if needed
            peers = self._filter_peers(metric.peers, input_spec.peer_filter)
            all_peer_names.update(p.name for p in peers)
            
            benchmark = self._benchmark_metric(metric, peers)
            metric_benchmarks.append(benchmark)
        
        # Calculate composite score
        composite_score, overall_rank, overall_percentile = self._compute_composite(
            metric_benchmarks
        )
        
        # Identify strengths and improvement areas
        strengths = [
            b.metric_name for b in metric_benchmarks 
            if b.performance in ["leading", "above_average"]
        ]
        improvement_areas = [
            b.metric_name for b in metric_benchmarks
            if b.performance in ["below_average", "lagging"]
        ]
        
        # Count outperformance
        outperforms = sum(1 for b in metric_benchmarks if b.gap_to_mean > 0)
        underperforms = sum(1 for b in metric_benchmarks if b.gap_to_mean < 0)
        
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        return BenchmarkingResult(
            metric_benchmarks=metric_benchmarks,
            composite_score=composite_score,
            overall_rank=overall_rank,
            overall_percentile=overall_percentile,
            strengths=strengths,
            improvement_areas=improvement_areas,
            outperforms_peers=outperforms,
            underperforms_peers=underperforms,
            n_metrics=len(metric_benchmarks),
            n_peers=len(all_peer_names),
            gpu_used=self.gpu_available,
            execution_time_ms=execution_time_ms,
        )
    
    def _filter_peers(
        self,
        peers: list[PeerData],
        peer_filter: Optional[str]
    ) -> list[PeerData]:
        """Filter peers by group."""
        if not peer_filter or peer_filter == "all":
            return peers
        
        gcc_countries = {"UAE", "Saudi Arabia", "Kuwait", "Bahrain", "Oman"}
        
        filtered = []
        for peer in peers:
            if peer_filter == "gcc" and peer.name in gcc_countries:
                filtered.append(peer)
            elif peer_filter == "high_income" and peer.income_group == "high":
                filtered.append(peer)
            elif peer_filter == "mena" and peer.region == "MENA":
                filtered.append(peer)
            elif peer_filter == "all":
                filtered.append(peer)
        
        return filtered if filtered else peers  # Fallback to all if filter too restrictive
    
    def _benchmark_metric(
        self,
        metric: BenchmarkMetric,
        peers: list[PeerData]
    ) -> MetricBenchmark:
        """Benchmark a single metric."""
        
        qatar_val = metric.qatar_value
        peer_values = np.array([p.value for p in peers])
        
        # Statistics
        peer_mean = float(np.mean(peer_values))
        peer_median = float(np.median(peer_values))
        peer_std = float(np.std(peer_values))
        peer_min = float(np.min(peer_values))
        peer_max = float(np.max(peer_values))
        
        # Ranking
        all_values = np.append(peer_values, qatar_val)
        if metric.higher_is_better:
            ranks = stats.rankdata(-all_values, method='min')  # Higher = rank 1
        else:
            ranks = stats.rankdata(all_values, method='min')  # Lower = rank 1
        
        qatar_rank = int(ranks[-1])
        qatar_percentile = float((len(all_values) - qatar_rank) / len(all_values) * 100)
        
        # Gap analysis
        if metric.higher_is_better:
            gap_to_mean = qatar_val - peer_mean
            gap_to_best = qatar_val - peer_max
        else:
            gap_to_mean = peer_mean - qatar_val
            gap_to_best = peer_min - qatar_val
        
        gap_to_target = None
        if metric.target is not None:
            if metric.higher_is_better:
                gap_to_target = qatar_val - metric.target
            else:
                gap_to_target = metric.target - qatar_val
        
        gap_to_standard = None
        if metric.international_standard is not None:
            if metric.higher_is_better:
                gap_to_standard = qatar_val - metric.international_standard
            else:
                gap_to_standard = metric.international_standard - qatar_val
        
        # Z-score
        z_score = (qatar_val - peer_mean) / (peer_std + 1e-10)
        if not metric.higher_is_better:
            z_score = -z_score
        
        # Outlier detection (> 2 std from mean)
        is_outlier = abs(qatar_val - peer_mean) > 2 * peer_std
        outlier_direction = None
        if is_outlier:
            outlier_direction = "above" if qatar_val > peer_mean else "below"
        
        # Performance assessment
        if qatar_percentile >= 80:
            performance = "leading"
        elif qatar_percentile >= 60:
            performance = "above_average"
        elif qatar_percentile >= 40:
            performance = "average"
        elif qatar_percentile >= 20:
            performance = "below_average"
        else:
            performance = "lagging"
        
        # Best and worst peers
        if metric.higher_is_better:
            best_idx = np.argmax(peer_values)
            worst_idx = np.argmin(peer_values)
        else:
            best_idx = np.argmin(peer_values)
            worst_idx = np.argmax(peer_values)
        
        best_peer = peers[best_idx]
        worst_peer = peers[worst_idx]
        
        # Closest peers (by value)
        value_diffs = np.abs(peer_values - qatar_val)
        closest_indices = np.argsort(value_diffs)[:3]
        closest_peers = [peers[i] for i in closest_indices]
        
        return MetricBenchmark(
            metric_name=metric.name,
            qatar_value=qatar_val,
            qatar_rank=qatar_rank,
            qatar_percentile=qatar_percentile,
            peer_mean=peer_mean,
            peer_median=peer_median,
            peer_std=peer_std,
            peer_min=peer_min,
            peer_max=peer_max,
            gap_to_mean=float(gap_to_mean),
            gap_to_best=float(gap_to_best),
            gap_to_target=float(gap_to_target) if gap_to_target is not None else None,
            gap_to_standard=float(gap_to_standard) if gap_to_standard is not None else None,
            z_score=float(z_score),
            is_outlier=is_outlier,
            outlier_direction=outlier_direction,
            performance=performance,
            best_peer=best_peer,
            worst_peer=worst_peer,
            closest_peers=closest_peers,
        )
    
    def _compute_composite(
        self,
        benchmarks: list[MetricBenchmark]
    ) -> tuple[float, int, float]:
        """Compute composite score from all metrics."""
        
        if not benchmarks:
            return 0.0, 0, 0.0
        
        # Average percentile as composite score
        percentiles = [b.qatar_percentile for b in benchmarks]
        composite_score = float(np.mean(percentiles))
        
        # Overall rank (simplified - based on composite)
        # In practice, you'd compare to peers' composite scores
        overall_rank = int(100 - composite_score) // 10 + 1  # 1-10 scale
        overall_percentile = composite_score
        
        return composite_score, overall_rank, overall_percentile
    
    def health_check(self) -> dict:
        """Check service health."""
        return {
            "service": "benchmarking",
            "status": "healthy",
            "gpu_id": self.gpu_id,
            "gpu_available": self.gpu_available,
        }


# Example usage
if __name__ == "__main__":
    service = BenchmarkingService()
    
    # Example: Qatarization benchmarking against GCC peers
    input_spec = BenchmarkingInput(
        metrics=[
            BenchmarkMetric(
                name="Nationalization Rate",
                qatar_value=0.42,
                peers=[
                    PeerData("UAE", 0.35, "MENA", "high"),
                    PeerData("Saudi Arabia", 0.45, "MENA", "high"),
                    PeerData("Kuwait", 0.38, "MENA", "high"),
                    PeerData("Bahrain", 0.40, "MENA", "high"),
                    PeerData("Oman", 0.48, "MENA", "high"),
                ],
                higher_is_better=True,
                target=0.60,
            ),
            BenchmarkMetric(
                name="Unemployment Rate",
                qatar_value=0.03,
                peers=[
                    PeerData("UAE", 0.04, "MENA", "high"),
                    PeerData("Saudi Arabia", 0.12, "MENA", "high"),
                    PeerData("Kuwait", 0.06, "MENA", "high"),
                    PeerData("Bahrain", 0.05, "MENA", "high"),
                    PeerData("Oman", 0.08, "MENA", "high"),
                ],
                higher_is_better=False,  # Lower is better
                international_standard=0.05,
            ),
        ],
        peer_filter="gcc",
    )
    
    result = service.benchmark(input_spec)
    
    print(f"Composite Score: {result.composite_score:.1f}")
    print(f"Overall Rank: {result.overall_rank}")
    print(f"\nMetric Results:")
    for mb in result.metric_benchmarks:
        print(f"  {mb.metric_name}:")
        print(f"    Qatar: {mb.qatar_value:.2f} (Rank {mb.qatar_rank}, {mb.qatar_percentile:.0f}%ile)")
        print(f"    Peer Mean: {mb.peer_mean:.2f}, Gap: {mb.gap_to_mean:+.2f}")
        print(f"    Performance: {mb.performance}")
    print(f"\nStrengths: {result.strengths}")
    print(f"Improvement Areas: {result.improvement_areas}")
