from pydantic import BaseModel, Field
from src.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from src.utils.paths import resolve_path
from src.utils.text import count_tokens, truncate_text
from src.safety.blocked_file import BlockedFile

import csv
import io
import re
import zlib
import struct
import base64
from pathlib import Path
from xml.etree import ElementTree as ET


# Extensions we treat as plain text (reuse read_file behaviour).
_TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".sh", ".bash", ".zsh", ".html", ".htm", ".css", ".xml", ".log",
    ".csv", ".tsv", ".sql", ".rst", ".tex",
}


class ReadArtifactParams(BaseModel):
    path: str = Field(
        ...,
        description="Path to the file to read (relative to working directory or absolute path)",
    )
    limit: int | None = Field(
        None,
        ge=1,
        description="Maximum number of rows/lines to return for tabular or "
        "long text files. If omitted, returns a sensible default cap.",
    )
    sheet: str | None = Field(
        None,
        description="For spreadsheet files (.xlsx), the sheet name or 1-based "
        "index to read. Defaults to the first sheet.",
    )


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _read_text_file(path: Path, limit: int | None) -> ToolResult:
    if path.stat().st_size > 10 * 1024 * 1024:
        return ToolResult.error_result(
            f"File too large ({path.stat().st_size / (1024*1024):.1f}MB). "
            f"Maximum is 10MB."
        )
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")
        content = "(decoded as latin-1)\n" + content

    lines = content.splitlines()
    if limit:
        lines = lines[:limit]
    output = "\n".join(f"{i+1:6}|{l}" for i, l in enumerate(lines))
    if limit and len(content.splitlines()) > limit:
        output += f"\n... [truncated, showing first {limit} of {len(content.splitlines())} lines]"
    return ToolResult.success_result(
        output,
        metadata={"type": "text", "lines": len(lines)},
    )


def _read_csv_file(path: Path, limit: int | None, delimiter: str) -> ToolResult:
    max_rows = limit or 500
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            rows = []
            for row in reader:
                rows.append(row)
                if len(rows) > max_rows:
                    break
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            rows = []
            for row in reader:
                rows.append(row)
                if len(rows) > max_rows:
                    break

    if not rows:
        return ToolResult.success_result("(empty file)", metadata={"type": "csv", "rows": 0})

    header = rows[0]
    col_w = [len(str(c)) for c in header]
    for r in rows[1:]:
        for i, c in enumerate(r):
            if i < len(col_w):
                col_w[i] = max(col_w[i], len(str(c)))

    def fmt(r: list) -> str:
        cells = []
        for i, c in enumerate(r):
            w = col_w[i] if i < len(col_w) else 0
            cells.append(str(c).ljust(w))
        return " | ".join(cells)

    out = [fmt(header), "-+-".join("-" * w for w in col_w)]
    out.extend(fmt(r) for r in rows[1:])
    truncated = len(rows) > max_rows
    if truncated:
        out.append(f"... [truncated, showing first {max_rows} of {len(rows)} rows]")
    return ToolResult.success_result(
        "\n".join(out),
        metadata={"type": "csv", "rows": len(rows), "columns": len(header)},
    )


def _read_xlsx(path: Path, limit: int | None, sheet: str | None) -> ToolResult:
    import zipfile

    max_rows = limit or 1000
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        # shared strings
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root:
                texts = [t.text or "" for t in si.iter() if _strip_ns(t.tag) == "t"]
                shared.append("".join(texts))
        # workbook sheet list
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        sheet_names = [
            s.attrib.get("name")
            for s in wb.iter()
            if _strip_ns(s.tag) == "sheet"
        ]
        sheet_files = sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        if sheet is None:
            idx = 0
        else:
            try:
                idx = int(sheet) - 1
            except ValueError:
                idx = sheet_names.index(sheet) if sheet in sheet_names else 0
        if idx < 0 or idx >= len(sheet_files):
            idx = 0
        target = sheet_files[idx]
        root = ET.fromstring(z.read(target))

        def col_to_int(ref: str) -> int:
            m = re.match(r"([A-Z]+)(\d+)", ref)
            if not m:
                return 0
            col = 0
            for ch in m.group(1):
                col = col * 26 + (ord(ch) - 64)
            return col - 1

        rows: list[list[str]] = []
        for row in root.iter():
            if _strip_ns(row.tag) != "row":
                continue
            cells: dict[int, str] = {}
            max_c = -1
            for c in row:
                ref = c.attrib.get("r", "")
                ci = col_to_int(ref)
                val = None
                t = c.attrib.get("t")
                if t == "s":
                    v = c.find("{*}v")
                    if v is not None and v.text is not None:
                        val = shared[int(v.text)] if int(v.text) < len(shared) else ""
                else:
                    v = c.find("{*}v")
                    if v is not None:
                        val = v.text
                if val is None:
                    # inline string
                    is_el = c.find("{*}is")
                    if is_el is not None:
                        val = "".join(t.text or "" for t in is_el.iter() if _strip_ns(t.tag) == "t")
                cells[ci] = val or ""
                max_c = max(max_c, ci)
            if max_c >= 0:
                row_list = [cells.get(i, "") for i in range(max_c + 1)]
                rows.append(row_list)
            if len(rows) > max_rows:
                break

    if not rows:
        return ToolResult.success_result("(empty sheet)", metadata={"type": "xlsx"})
    header = rows[0]
    col_w = [len(str(c)) for c in header]
    for r in rows[1:]:
        for i, c in enumerate(r):
            if i < len(col_w):
                col_w[i] = max(col_w[i], len(str(c)))
    out = [
        " | ".join(str(c).ljust(col_w[i]) for i, c in enumerate(header)),
        "-+-".join("-" * w for w in col_w),
    ]
    out.extend(
        " | ".join(str(c).ljust(col_w[i]) for i, c in enumerate(r))
        for r in rows[1:]
    )
    if len(rows) > max_rows:
        out.append(f"... [truncated, showing first {max_rows} rows]")
    name = sheet_names[idx] if idx < len(sheet_names) else target
    return ToolResult.success_result(
        f"Sheet: {name}\n\n" + "\n".join(out),
        metadata={"type": "xlsx", "sheet": name, "rows": len(rows)},
    )


def _read_docx(path: Path, limit: int | None) -> ToolResult:
    import zipfile

    max_paras = limit or 2000
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))

        def para_text(p) -> str:
            return "".join(
                t.text or "" for t in p.iter() if _strip_ns(t.tag) == "t"
            )

        paragraphs = []
        for p in root.iter():
            if _strip_ns(p.tag) == "p":
                text = para_text(p)
                if text or not paragraphs:
                    paragraphs.append(text)
                if len(paragraphs) >= max_paras:
                    break

    # strip trailing empties
    while paragraphs and not paragraphs[-1]:
        paragraphs.pop()
    out = "\n\n".join(paragraphs)
    if not out.strip():
        out = "(no extractable text)"
    if len(paragraphs) >= max_paras:
        out += f"\n\n... [truncated, showing first {max_paras} paragraphs]"
    return ToolResult.success_result(
        out,
        metadata={"type": "docx", "paragraphs": len(paragraphs)},
    )


def _pdf_text_from_stream(data: bytes) -> str:
    texts: list[str] = []
    # find stream ... endstream blocks, try to inflate and extract text
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL):
        raw = m.group(1)
        # strip leading EOL already consumed; try zlib
        try:
            dec = zlib.decompress(raw)
        except Exception:
            continue
        # extract text from (...) Tj / TJ operators
        for tm in re.finditer(rb"\((?:[^()\\]|\\.)*\)", dec):
            s = tm.group(0)[1:-1]
            s = s.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
            try:
                texts.append(s.decode("latin-1"))
            except Exception:
                pass
    return "\n".join(t for t in texts if t.strip())


def _read_pdf(path: Path, limit: int | None) -> ToolResult:
    data = path.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    text = _pdf_text_from_stream(data)
    if not text.strip():
        return ToolResult.success_result(
            f"(no extractable text — PDF text is likely image-based or encoded)\n"
            f"Detected pages: {pages or 'unknown'}",
            metadata={"type": "pdf", "pages": pages},
        )
    lines = text.splitlines()
    if limit:
        lines = lines[:limit]
    out = "\n".join(lines)
    if limit and len(text.splitlines()) > limit:
        out += f"\n... [truncated, showing first {limit} lines of {len(text.splitlines())}]"
    return ToolResult.success_result(
        out,
        metadata={"type": "pdf", "pages": pages, "extracted_lines": len(lines)},
    )


def _read_image(path: Path) -> ToolResult:
    data = path.read_bytes()
    fmt = path.suffix.lower().lstrip(".")
    width = height = None
    kind = fmt.upper()

    if fmt in (".png",):
        kind = "PNG"
        if len(data) > 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
            width, height = struct.unpack(">II", data[16:24])
    elif fmt in (".jpg", ".jpeg"):
        kind = "JPEG"
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                height, width = struct.unpack(">HH", data[i + 5 : i + 9])
                break
            seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
            i += 2 + seg_len
    elif fmt in (".gif",):
        kind = "GIF"
        if data[:6] in (b"GIF87a", b"GIF89a"):
            width, height = struct.unpack("<HH", data[6:10])
    elif fmt in (".bmp",):
        kind = "BMP"
        if len(data) > 26 and data[:2] == b"BM":
            width, height = struct.unpack("<II", data[18:26])

    size = path.stat().st_size
    b64 = base64.b64encode(data).decode("ascii")
    meta = [f"Image: {path.name}", f"Format: {kind}"]
    if width and height:
        meta.append(f"Dimensions: {width} x {height} px")
    meta.append(f"Size: {size} bytes ({size/1024:.1f} KB)")
    meta.append(
        "Note: this is a text-only model, so image pixels cannot be viewed. "
        "Above is structural metadata only. OCR/visual analysis requires a vision model or a dependency."
    )
    return ToolResult.success_result(
        "\n".join(meta),
        metadata={
            "type": "image",
            "format": kind,
            "width": width,
            "height": height,
            "size_bytes": size,
            "base64_preview": b64[:200] + ("..." if len(b64) > 200 else ""),
        },
    )


class ReadArtifactTool(Tool):
    name = "read_artifact"
    description = (
        "Read a file of many types and return its content as text. "
        "Supports: text/code/json/yaml, CSV/TSV (rendered as a table), "
        "Excel (.xlsx), Word (.docx), PDF (best-effort text extraction), "
        "and images (PNG/JPEG/GIF/BMP — returns structural metadata only, "
        "since the model is text-only and cannot see pixels)."
    )
    kind = ToolKind.READ
    schema = ReadArtifactParams

    MAX_OUTPUT_TOKENS = 25000

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ReadArtifactParams(**invocation.params)
        path = resolve_path(invocation.cwd, params.path)

        if not path.exists():
            return ToolResult.error_result(f"File not found: {path}")
        if not path.is_file():
            return ToolResult.error_result(f"Path is not a file: {path}")

        block = await BlockedFile(path.name, self.name).execute()
        if block:
            return block

        ext = path.suffix.lower()

        try:
            if ext in (".csv", ".tsv"):
                result = _read_csv_file(path, params.limit, "," if ext == ".csv" else "\t")
            elif ext == ".xlsx":
                result = _read_xlsx(path, params.limit, params.sheet)
            elif ext == ".docx":
                result = _read_docx(path, params.limit)
            elif ext == ".pdf":
                result = _read_pdf(path, params.limit)
            elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"):
                result = _read_image(path)
            elif ext in _TEXT_EXTS:
                result = _read_text_file(path, params.limit)
            else:
                # unknown: try text, fall back to metadata
                try:
                    result = _read_text_file(path, params.limit)
                except Exception:
                    result = ToolResult.success_result(
                        f"(binary/unknown file: {path.name}, "
                        f"{path.stat().st_size} bytes — no text view available)",
                        metadata={"type": "unknown", "size_bytes": path.stat().st_size},
                    )
        except Exception as e:
            return ToolResult.error_result(f"Failed to read {path.name}: {e}")

        if result.success and count_tokens(result.output) > self.MAX_OUTPUT_TOKENS:
            result.output = truncate_text(
                result.output,
                self.config.model_name,
                self.MAX_OUTPUT_TOKENS,
                suffix="\n... [output truncated]",
            )
            result.truncated = True
        return result
