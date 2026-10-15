"""Download the public 2024 yellow-taxi Parquet files and the zone lookup."""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

from taxi_insights.paths import MONTHS, RAW_DIR, RAW_ZONES, TRIP_URL, ZONE_URL

USER_AGENT = "nyc-taxi-insights/1.0 (educational analysis; public TLC files)"
RETRIES = 4


def trip_url(month: str) -> str:
    if month not in MONTHS:
        raise ValueError(f"month must be one of {MONTHS}, got {month!r}")
    return TRIP_URL.format(month=month)


def trip_destination(month: str) -> Path:
    return RAW_DIR / f"yellow_tripdata_2024-{month}.parquet"


def _request(url: str, method: str = "GET") -> urllib.request.Request:
    return urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})


def content_length(url: str) -> int | None:
    with urllib.request.urlopen(_request(url, "HEAD"), timeout=60) as response:
        length = response.headers.get("Content-Length")
    return int(length) if length else None


def _complete(path: Path, expected: int | None) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    if expected is None:
        return True
    return path.stat().st_size == expected


def download_file(url: str, destination: Path) -> Path:
    """Download `url` to `destination`, skipping the transfer when sizes match."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = content_length(url)
    if _complete(destination, expected):
        print(f"skip {destination.name} ({destination.stat().st_size:,} bytes)")
        return destination

    partial = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            print(f"get  {destination.name} (attempt {attempt})")
            with (
                urllib.request.urlopen(_request(url), timeout=180) as response,
                partial.open("wb") as handle,
            ):
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            partial.replace(destination)
            size = destination.stat().st_size
            if expected is not None and size != expected:
                raise OSError(f"{destination.name} is {size} bytes, expected {expected}")
            print(f"done {destination.name} ({size:,} bytes)")
            return destination
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            print(f"fail {destination.name}: {exc}")
    raise RuntimeError(f"could not download {url}") from last_error


def download_all() -> list[Path]:
    """Download the zone lookup and all twelve 2024 yellow-taxi months."""
    saved = [download_file(ZONE_URL, RAW_ZONES)]
    for month in MONTHS:
        saved.append(download_file(trip_url(month), trip_destination(month)))
    return saved


def main() -> None:
    download_all()


if __name__ == "__main__":
    main()
