"""Read-only storage budget for a planned render; no rendering or cleanup."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sys

GIB = 1024 ** 3


def storage_budget(samples, output_dir, remaining_frames, temporary_gib=2.0,
                   reserve_gib=2.0, safety_factor=1.25):
    """Budget additional bytes using the largest representative stored frame.

    Already present files are accounted for by disk_usage.free, not subtracted
    again. Samples must use the planned frame storage format/settings.
    """
    if isinstance(remaining_frames, bool) or not isinstance(remaining_frames, int) or remaining_frames < 0:
        raise ValueError("remaining_frames must be a nonnegative integer")
    if not all(math.isfinite(v) and v >= 0 for v in (temporary_gib, reserve_gib)):
        raise ValueError("temporary/reserve GiB must be finite and nonnegative")
    if not math.isfinite(safety_factor) or safety_factor < 1:
        raise ValueError("safety_factor must be finite and at least 1")
    output_dir = Path(output_dir).resolve(strict=True)
    if not output_dir.is_dir():
        raise ValueError("output_dir must be an existing directory on the target filesystem")
    sizes = []
    for sample in samples:
        sample = Path(sample).resolve(strict=True)
        if not sample.is_file() or sample.stat().st_size <= 0:
            raise ValueError("samples must be nonempty files")
        sizes.append(sample.stat().st_size)
    if not sizes:
        raise ValueError("at least one representative frame sample is required")
    frame_bytes = math.ceil(max(sizes) * remaining_frames * safety_factor)
    temporary_bytes = math.ceil(temporary_gib * GIB)
    reserve_bytes = math.ceil(reserve_gib * GIB)
    required = frame_bytes + temporary_bytes + reserve_bytes
    free = shutil.disk_usage(output_dir).free
    return {
        "status": "PASS" if free >= required else "BLOCKED",
        "output_filesystem_directory": str(output_dir),
        "sample_count": len(sizes), "largest_sample_bytes": max(sizes),
        "remaining_frames": remaining_frames, "safety_factor": safety_factor,
        "additional_frame_bytes": frame_bytes,
        "temporary_bytes": temporary_bytes, "reserve_bytes": reserve_bytes,
        "required_free_bytes": required, "available_free_bytes": free,
        "shortfall_bytes": max(0, required - free),
        "scope": "Storage estimate only; not render authorization or media acceptance.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="append", required=True,
                        help="Representative frame in planned storage format; repeat for varied scenes")
    parser.add_argument("--output-dir", required=True, help="Existing directory on target filesystem")
    parser.add_argument("--remaining-frames", type=int, required=True)
    parser.add_argument("--temporary-gib", type=float, default=2.0,
                        help="Additional encoding/copy temporary space (default 2 GiB; adjust to pipeline)")
    parser.add_argument("--reserve-gib", type=float, default=2.0)
    parser.add_argument("--safety-factor", type=float, default=1.25)
    args = parser.parse_args(argv)
    try:
        report = storage_budget(args.sample, args.output_dir, args.remaining_frames,
                                args.temporary_gib, args.reserve_gib, args.safety_factor)
    except (OSError, ValueError) as exc:
        print(f"Storage preflight error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
