#!/usr/bin/env python3
"""Deliver the Sunday Globe front page to the grader.

The entry is a pre-rendered 1024x1024 PNG (entry.png, next to this file).
This program checks the image is exactly what the competition asks for and
then places an identical copy at the output location the harness provides.

Checks, in order:
  1. the source file exists and is at most 1 MiB;
  2. it starts with the PNG signature and its IHDR says 1024x1024;
  3. the copy written to the output directory has the same SHA-256 and the
     same PNG signature and IHDR as the source.

Stdlib only. No network, no arguments. Exit 0 on success, 1 on any failure.
"""

import hashlib
import os
import struct
import sys

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1024 * 1024
TARGET_WIDTH = 1024
TARGET_HEIGHT = 1024


def png_dimensions(blob):
    """Return (width, height) from a PNG byte string, or None if malformed."""
    if len(blob) < 24 or blob[:8] != PNG_SIGNATURE:
        return None
    if blob[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", blob[16:24])
    return width, height


def sha256_hex(blob):
    return hashlib.sha256(blob).hexdigest()


class Shipper:
    """Reads the source image, validates it, writes the copy, re-validates."""

    def __init__(self):
        here = os.path.dirname(os.path.abspath(__file__))
        self.source_path = os.path.join(here, "entry.png")
        out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
        self.dest_path = os.path.join(out_dir, "entry.png")

    def read_source(self):
        try:
            with open(self.source_path, "rb") as handle:
                return handle.read()
        except OSError as exc:
            print(f"error: cannot read {self.source_path}: {exc}", file=sys.stderr)
            return None

    def validate(self, blob, label):
        if blob is None:
            return False
        if len(blob) > MAX_BYTES:
            print(f"error: {label} is {len(blob)} bytes, over the 1 MiB cap",
                  file=sys.stderr)
            return False
        dims = png_dimensions(blob)
        if dims is None:
            print(f"error: {label} is not a well-formed PNG", file=sys.stderr)
            return False
        if dims != (TARGET_WIDTH, TARGET_HEIGHT):
            print(f"error: {label} is {dims[0]}x{dims[1]}, need "
                  f"{TARGET_WIDTH}x{TARGET_HEIGHT}", file=sys.stderr)
            return False
        return True

    def deliver(self, blob):
        if os.path.abspath(self.source_path) == os.path.abspath(self.dest_path):
            raise OSError("source and destination are the same file")
        os.makedirs(os.path.dirname(self.dest_path), exist_ok=True)
        with open(self.dest_path, "wb") as handle:
            handle.write(blob)

    def confirm(self, expected_digest):
        try:
            with open(self.dest_path, "rb") as handle:
                copied = handle.read()
        except OSError as exc:
            print(f"error: cannot re-read {self.dest_path}: {exc}",
                  file=sys.stderr)
            return False
        if sha256_hex(copied) != expected_digest:
            print("error: copy digest does not match the source",
                  file=sys.stderr)
            return False
        return self.validate(copied, "copy")

    def run(self):
        blob = self.read_source()
        if not self.validate(blob, "source"):
            return 1
        digest = sha256_hex(blob)
        try:
            self.deliver(blob)
        except OSError as exc:
            print(f"error: cannot write {self.dest_path}: {exc}",
                  file=sys.stderr)
            return 1
        if not self.confirm(digest):
            return 1
        print(f"ok: {self.dest_path} {len(blob)} bytes sha256={digest}")
        return 0


def main():
    return Shipper().run()


if __name__ == "__main__":
    sys.exit(main())
