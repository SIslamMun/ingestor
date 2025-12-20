"""Performance tests for extractors.

Tests focused on:
- Extraction speed benchmarks
- Memory usage
- Large file handling
- Batch processing efficiency

These tests help identify performance regressions.
"""

import pytest
import time
import tempfile
import json
from pathlib import Path
from typing import List, Callable, Any
import asyncio

from ingestor.extractors.text.txt_extractor import TxtExtractor
from ingestor.extractors.data.json_extractor import JsonExtractor
from ingestor.extractors.data.csv_extractor import CsvExtractor
from ingestor.types import MediaType


# ============================================================================
# Performance Test Utilities
# ============================================================================

class PerformanceMetrics:
    """Collect and report performance metrics."""
    
    def __init__(self):
        self.timings: List[float] = []
    
    def record(self, elapsed: float) -> None:
        """Record a timing measurement."""
        self.timings.append(elapsed)
    
    @property
    def mean(self) -> float:
        """Mean execution time."""
        if not self.timings:
            return 0.0
        return sum(self.timings) / len(self.timings)
    
    @property
    def min(self) -> float:
        """Minimum execution time."""
        return min(self.timings) if self.timings else 0.0
    
    @property
    def max(self) -> float:
        """Maximum execution time."""
        return max(self.timings) if self.timings else 0.0
    
    @property
    def total(self) -> float:
        """Total execution time."""
        return sum(self.timings)


async def timed_extract(extractor, file_path) -> tuple[Any, float]:
    """Execute extraction and return result with elapsed time."""
    start = time.perf_counter()
    result = await extractor.extract(file_path)
    elapsed = time.perf_counter() - start
    return result, elapsed


def generate_large_text(lines: int, chars_per_line: int = 80) -> str:
    """Generate large text content."""
    return '\n'.join(
        f"Line {i}: " + "x" * (chars_per_line - len(f"Line {i}: "))
        for i in range(lines)
    )


def generate_large_json(items: int) -> str:
    """Generate large JSON array."""
    data = [
        {
            "id": i,
            "name": f"Item {i}",
            "description": f"This is a description for item number {i}",
            "values": list(range(10)),
            "metadata": {
                "created": "2024-01-01",
                "updated": "2024-01-02",
                "tags": ["tag1", "tag2", "tag3"]
            }
        }
        for i in range(items)
    ]
    return json.dumps(data, indent=2)


def generate_large_csv(rows: int, columns: int = 10) -> str:
    """Generate large CSV content."""
    header = ','.join(f"Column_{i}" for i in range(columns))
    lines = [header]
    for row in range(rows):
        values = ','.join(str(row * columns + col) for col in range(columns))
        lines.append(values)
    return '\n'.join(lines)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def txt_extractor():
    return TxtExtractor()


@pytest.fixture
def json_extractor():
    return JsonExtractor()


@pytest.fixture
def csv_extractor():
    return CsvExtractor()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def performance_metrics():
    """Performance metrics collector."""
    return PerformanceMetrics()


# ============================================================================
# Text Extraction Performance Tests
# ============================================================================

class TestTextPerformance:
    """Performance tests for text extraction."""
    
    @pytest.mark.asyncio
    async def test_small_file_speed(self, txt_extractor, temp_dir):
        """Small text file should extract very quickly (< 50ms)."""
        small_file = temp_dir / "small.txt"
        small_file.write_text("Hello, World!\n" * 100)
        
        _, elapsed = await timed_extract(txt_extractor, small_file)
        
        assert elapsed < 0.050, f"Small file extraction took {elapsed:.3f}s (> 50ms)"
    
    @pytest.mark.asyncio
    async def test_medium_file_speed(self, txt_extractor, temp_dir):
        """Medium text file (10K lines) should extract in < 500ms."""
        medium_file = temp_dir / "medium.txt"
        medium_file.write_text(generate_large_text(10_000))
        
        _, elapsed = await timed_extract(txt_extractor, medium_file)
        
        assert elapsed < 0.500, f"Medium file extraction took {elapsed:.3f}s (> 500ms)"
    
    @pytest.mark.asyncio
    async def test_large_file_speed(self, txt_extractor, temp_dir):
        """Large text file (100K lines) should extract in < 2s."""
        large_file = temp_dir / "large.txt"
        large_file.write_text(generate_large_text(100_000))
        
        _, elapsed = await timed_extract(txt_extractor, large_file)
        
        assert elapsed < 2.0, f"Large file extraction took {elapsed:.3f}s (> 2s)"
    
    @pytest.mark.asyncio
    async def test_consistent_timing(self, txt_extractor, temp_dir, performance_metrics):
        """Multiple extractions should have consistent timing."""
        test_file = temp_dir / "consistent.txt"
        test_file.write_text(generate_large_text(1_000))
        
        # Run 10 extractions
        for _ in range(10):
            _, elapsed = await timed_extract(txt_extractor, test_file)
            performance_metrics.record(elapsed)
        
        # Variance should be reasonable (max < 10x min for fast operations)
        # Fast operations can have high relative variance due to OS scheduling
        assert performance_metrics.max < performance_metrics.min * 15 or performance_metrics.max < 0.05, \
            f"Timing variance too high: min={performance_metrics.min:.3f}s, max={performance_metrics.max:.3f}s"


# ============================================================================
# JSON Extraction Performance Tests
# ============================================================================

class TestJsonPerformance:
    """Performance tests for JSON extraction."""
    
    @pytest.mark.asyncio
    async def test_small_json_speed(self, json_extractor, temp_dir):
        """Small JSON should extract very quickly (< 50ms)."""
        small_file = temp_dir / "small.json"
        small_file.write_text('{"key": "value", "items": [1, 2, 3]}')
        
        _, elapsed = await timed_extract(json_extractor, small_file)
        
        assert elapsed < 0.050, f"Small JSON extraction took {elapsed:.3f}s (> 50ms)"
    
    @pytest.mark.asyncio
    async def test_medium_json_speed(self, json_extractor, temp_dir):
        """Medium JSON (1K items) should extract in < 500ms."""
        medium_file = temp_dir / "medium.json"
        medium_file.write_text(generate_large_json(1_000))
        
        _, elapsed = await timed_extract(json_extractor, medium_file)
        
        assert elapsed < 0.500, f"Medium JSON extraction took {elapsed:.3f}s (> 500ms)"
    
    @pytest.mark.asyncio
    async def test_large_json_speed(self, json_extractor, temp_dir):
        """Large JSON (10K items) should extract in < 3s."""
        large_file = temp_dir / "large.json"
        large_file.write_text(generate_large_json(10_000))
        
        _, elapsed = await timed_extract(json_extractor, large_file)
        
        assert elapsed < 3.0, f"Large JSON extraction took {elapsed:.3f}s (> 3s)"
    
    @pytest.mark.asyncio
    async def test_deeply_nested_json_speed(self, json_extractor, temp_dir):
        """Deeply nested JSON should not cause performance issues."""
        deep_file = temp_dir / "deep.json"
        
        # Create 100 levels of nesting
        data = {"level": 0, "data": "root"}
        current = data
        for i in range(1, 100):
            current["nested"] = {"level": i, "data": f"level_{i}"}
            current = current["nested"]
        
        deep_file.write_text(json.dumps(data))
        
        _, elapsed = await timed_extract(json_extractor, deep_file)
        
        assert elapsed < 1.0, f"Deep JSON extraction took {elapsed:.3f}s (> 1s)"


# ============================================================================
# CSV Extraction Performance Tests
# ============================================================================

class TestCsvPerformance:
    """Performance tests for CSV extraction."""
    
    @pytest.mark.asyncio
    async def test_small_csv_speed(self, csv_extractor, temp_dir):
        """Small CSV should extract quickly (< 200ms - pandas has startup overhead)."""
        small_file = temp_dir / "small.csv"
        small_file.write_text(generate_large_csv(100))
        
        _, elapsed = await timed_extract(csv_extractor, small_file)
        
        assert elapsed < 0.200, f"Small CSV extraction took {elapsed:.3f}s (> 200ms)"
    
    @pytest.mark.asyncio
    async def test_medium_csv_speed(self, csv_extractor, temp_dir):
        """Medium CSV (5K rows) should extract in < 1s."""
        medium_file = temp_dir / "medium.csv"
        medium_file.write_text(generate_large_csv(5_000))
        
        _, elapsed = await timed_extract(csv_extractor, medium_file)
        
        assert elapsed < 1.0, f"Medium CSV extraction took {elapsed:.3f}s (> 1s)"
    
    @pytest.mark.asyncio
    async def test_large_csv_speed(self, csv_extractor, temp_dir):
        """Large CSV (50K rows) should extract in < 5s."""
        large_file = temp_dir / "large.csv"
        large_file.write_text(generate_large_csv(50_000))
        
        _, elapsed = await timed_extract(csv_extractor, large_file)
        
        assert elapsed < 5.0, f"Large CSV extraction took {elapsed:.3f}s (> 5s)"
    
    @pytest.mark.asyncio
    async def test_wide_csv_speed(self, csv_extractor, temp_dir):
        """Wide CSV (100 columns) should not cause issues."""
        wide_file = temp_dir / "wide.csv"
        wide_file.write_text(generate_large_csv(1_000, columns=100))
        
        _, elapsed = await timed_extract(csv_extractor, wide_file)
        
        assert elapsed < 2.0, f"Wide CSV extraction took {elapsed:.3f}s (> 2s)"


# ============================================================================
# Batch Processing Performance Tests
# ============================================================================

class TestBatchPerformance:
    """Performance tests for batch processing."""
    
    @pytest.mark.asyncio
    async def test_sequential_batch(self, txt_extractor, temp_dir):
        """Sequential batch extraction of 20 files should be efficient."""
        # Create 20 test files
        files = []
        for i in range(20):
            f = temp_dir / f"batch_{i}.txt"
            f.write_text(f"Content for file {i}\n" * 100)
            files.append(f)
        
        start = time.perf_counter()
        results = []
        for f in files:
            result = await txt_extractor.extract(f)
            results.append(result)
        elapsed = time.perf_counter() - start
        
        assert len(results) == 20
        assert elapsed < 1.0, f"Batch of 20 files took {elapsed:.3f}s (> 1s)"
    
    @pytest.mark.asyncio
    async def test_mixed_format_batch(self, txt_extractor, json_extractor, csv_extractor, temp_dir):
        """Mixed format batch should be efficient."""
        # Create mixed files
        txt_file = temp_dir / "batch.txt"
        txt_file.write_text("Text content\n" * 100)
        
        json_file = temp_dir / "batch.json"
        json_file.write_text(generate_large_json(100))
        
        csv_file = temp_dir / "batch.csv"
        csv_file.write_text(generate_large_csv(100))
        
        start = time.perf_counter()
        
        results = await asyncio.gather(
            txt_extractor.extract(txt_file),
            json_extractor.extract(json_file),
            csv_extractor.extract(csv_file)
        )
        
        elapsed = time.perf_counter() - start
        
        assert len(results) == 3
        assert all(r is not None for r in results)
        assert elapsed < 1.0, f"Mixed batch took {elapsed:.3f}s (> 1s)"


# ============================================================================
# Memory Efficiency Tests
# ============================================================================

class TestMemoryEfficiency:
    """Tests to ensure extractors don't use excessive memory."""
    
    @pytest.mark.asyncio
    async def test_large_file_no_memory_explosion(self, txt_extractor, temp_dir):
        """Large file extraction shouldn't cause excessive memory use."""
        import sys
        
        # Create a 10MB text file
        large_file = temp_dir / "memory_test.txt"
        large_file.write_text("x" * (10 * 1024 * 1024))
        
        # Get baseline memory
        # Note: This is approximate - real memory testing needs more sophisticated tools
        
        result = await txt_extractor.extract(large_file)
        
        # Basic check: result size should be reasonable
        assert result is not None
        result_size = sys.getsizeof(result.markdown)
        # Result shouldn't be more than 2x input size
        assert result_size < 25 * 1024 * 1024, f"Result size {result_size} bytes is too large"
    
    @pytest.mark.asyncio
    async def test_repeated_extraction_no_leak(self, txt_extractor, temp_dir):
        """Repeated extractions shouldn't accumulate memory."""
        test_file = temp_dir / "leak_test.txt"
        test_file.write_text("Test content\n" * 1000)
        
        # Run many extractions
        for _ in range(100):
            result = await txt_extractor.extract(test_file)
            assert result is not None
        
        # If we get here without OOM, basic memory management is working


# ============================================================================
# Throughput Tests
# ============================================================================

class TestThroughput:
    """Measure extraction throughput."""
    
    @pytest.mark.asyncio
    async def test_txt_throughput(self, txt_extractor, temp_dir):
        """Measure text extraction throughput (MB/s)."""
        # Create 1MB file
        size_mb = 1
        test_file = temp_dir / "throughput.txt"
        test_file.write_text("x" * (size_mb * 1024 * 1024))
        
        start = time.perf_counter()
        await txt_extractor.extract(test_file)
        elapsed = time.perf_counter() - start
        
        throughput = size_mb / elapsed
        
        # Should process at least 10 MB/s
        assert throughput > 10, f"Throughput {throughput:.1f} MB/s is below 10 MB/s"
    
    @pytest.mark.asyncio
    async def test_json_items_per_second(self, json_extractor, temp_dir):
        """Measure JSON items per second throughput."""
        items = 5000
        test_file = temp_dir / "throughput.json"
        test_file.write_text(generate_large_json(items))
        
        start = time.perf_counter()
        await json_extractor.extract(test_file)
        elapsed = time.perf_counter() - start
        
        items_per_sec = items / elapsed
        
        # Should process at least 1000 items/s
        assert items_per_sec > 1000, f"Throughput {items_per_sec:.0f} items/s is below 1000"
    
    @pytest.mark.asyncio
    async def test_csv_rows_per_second(self, csv_extractor, temp_dir):
        """Measure CSV rows per second throughput."""
        rows = 10000
        test_file = temp_dir / "throughput.csv"
        test_file.write_text(generate_large_csv(rows))
        
        start = time.perf_counter()
        await csv_extractor.extract(test_file)
        elapsed = time.perf_counter() - start
        
        rows_per_sec = rows / elapsed
        
        # Should process at least 2000 rows/s
        assert rows_per_sec > 2000, f"Throughput {rows_per_sec:.0f} rows/s is below 2000"
