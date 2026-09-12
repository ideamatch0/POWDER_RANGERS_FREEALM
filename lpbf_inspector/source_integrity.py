"""Fast source identity checks; size/mtime checks are not cryptographic hashes."""
from pathlib import Path


def file_stamp(path):
    stat=Path(path).stat()
    return [stat.st_size,stat.st_mtime_ns]


def verify_source(path,expected):
    if file_stamp(path)!=list(expected):
        raise ValueError('Source image changed. Re-analyse this job before reviewing or exporting: '+Path(path).name)


def verify_report_sources(snapshot):
    frames=[f for detail in snapshot['details'] for f in detail['frames'] if f]
    frames.extend(f for scene in snapshot['scenes'] for f in scene['frames'])
    seen=set()
    for frame in frames:
        path=frame['path']
        if path not in seen:
            verify_source(path,frame['source_stamp']);seen.add(path)
