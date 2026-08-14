"""Raw-file encoding/delimiter detection and streaming."""
import csv
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class SourceInfo:
    path: Path
    encoding: str
    delimiter: str

def detect_source(path: Path) -> SourceInfo:
    sample = path.read_bytes()[:65536]
    if sample.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
        text = sample.decode(encoding)
    elif any(byte >= 128 for byte in sample):
        try:
            text = sample.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            encoding = "cp1252"
            text = sample.decode(encoding)
    else:
        # An ASCII-only prefix is valid in both UTF-8 and Windows-1252. CMS
        # text fields can contain Windows punctuation much later in large
        # files, so cp1252 is the safe single-byte fallback for this case.
        encoding = "cp1252"
        text = sample.decode(encoding)
    try:
        delimiter = csv.Sniffer().sniff(text, delimiters="|\t,;").delimiter
    except csv.Error:
        counts = {d: text.count(d) for d in ("|", "\t", ",", ";")}
        delimiter = max(counts, key=counts.get)
        if counts[delimiter] == 0:
            raise ValueError(f"Could not detect delimiter for {path}")
    return SourceInfo(path, encoding, delimiter)

def rows(source: SourceInfo):
    with source.path.open("r", encoding=source.encoding, newline="") as handle:
        yield from csv.DictReader(handle, delimiter=source.delimiter)

def raw_headers(source: SourceInfo) -> list[str]:
    with source.path.open("r", encoding=source.encoding, newline="") as handle:
        return next(csv.reader(handle, delimiter=source.delimiter))
