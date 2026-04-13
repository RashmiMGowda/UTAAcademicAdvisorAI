from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"
REPORT_MD = DOCS_DIR / "final_report.md"
REPORT_RTF = DOCS_DIR / "final_report.rtf"
REPORT_DOCX = DOCS_DIR / "AI_Academic_Advisor_Final_Report.docx"
PRESENTATION_TEMPLATE = Path("/Users/rashmigowda/Downloads/AI_Academic_Advisor_presentation.pptx")
PRESENTATION_OUT = DOCS_DIR / "AI_Academic_Advisor_Final_Presentation.pptx"

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
ET.register_namespace("a", A_NS)
ET.register_namespace("p", P_NS)


def _rtf_escape(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\line ")
    )


def _plain_text(text: str) -> str:
    return text.replace("**", "").replace("`", "")


def markdown_to_rtf(md: str) -> str:
    lines = md.splitlines()
    in_code = False
    code_lines: list[str] = []
    out = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Times New Roman;}{\f1 Menlo;}}",
        r"\paperw12240\paperh15840\margl1440\margr1440\margt1440\margb1440",
    ]
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = _plain_text(" ".join(part.strip() for part in paragraph if part.strip()))
            if text:
                out.append(rf"\pard\f0\fs24 {_rtf_escape(text)}\par")
            paragraph = []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                out.append(rf"\pard\li360\f1\fs18 {_rtf_escape(chr(10).join(code_lines))}\par")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            continue

        if line.startswith("# "):
            flush_paragraph()
            out.append(rf"\pard\sa160\f0\b\fs40 {_rtf_escape(_plain_text(line[2:].strip()))}\b0\par")
            continue
        if line.startswith("## "):
            flush_paragraph()
            out.append(rf"\pard\sa140\f0\b\fs30 {_rtf_escape(_plain_text(line[3:].strip()))}\b0\par")
            continue
        if line.startswith("### "):
            flush_paragraph()
            out.append(rf"\pard\sa120\f0\b\fs26 {_rtf_escape(_plain_text(line[4:].strip()))}\b0\par")
            continue
        if line.startswith("- "):
            flush_paragraph()
            out.append(rf"\pard\li720\fi-360\f0\fs24 \'95\tab {_rtf_escape(_plain_text(line[2:].strip()))}\par")
            continue

        paragraph.append(line)

    flush_paragraph()
    out.append("}")
    return "\n".join(out)


def build_report() -> None:
    md = REPORT_MD.read_text()
    REPORT_RTF.write_text(markdown_to_rtf(md))
    subprocess.run(
        [
            "/usr/bin/textutil",
            "-convert",
            "docx",
            "-output",
            str(REPORT_DOCX),
            str(REPORT_RTF),
        ],
        check=True,
    )


def set_shape_paragraphs(shape, paragraphs: list[str]) -> None:
    tx_body = shape.find(f"{{{P_NS}}}txBody")
    if tx_body is None:
        return
    for child in list(tx_body):
        if child.tag == f"{{{A_NS}}}p":
            tx_body.remove(child)
    if not paragraphs:
        paragraphs = [""]
    for text in paragraphs:
        p = ET.SubElement(tx_body, f"{{{A_NS}}}p")
        if text:
            r = ET.SubElement(p, f"{{{A_NS}}}r")
            ET.SubElement(r, f"{{{A_NS}}}rPr", lang="en-US", sz="2200")
            t = ET.SubElement(r, f"{{{A_NS}}}t")
            t.text = text
        ET.SubElement(p, f"{{{A_NS}}}endParaRPr", lang="en-US")


def build_presentation() -> None:
    shutil.copyfile(PRESENTATION_TEMPLATE, PRESENTATION_OUT)
    slide_updates = {
        1: [["AI Academic Advisor"], ["Final Project Presentation", "Rashmi Mudli Gowda, Venezer Odhiambo, Somya Dass, Seraph Lin"]],
        2: [["Agenda"], ["Problem & Motivation", "System Architecture", "Heavy and Light RAG Design", "Results, Limits, and Future Work"]],
        3: [["Why This Project Matters"]],
        4: [["Problem Statement"]],
        5: [["Problem Statement"], ["Students search through many UTA PDFs for simple advising answers", "Generic chatbots can sound fluent but miss official degree details", "Our goal was grounded, document-backed advising with a usable web interface"]],
        6: [["Methodology"]],
        7: [["Methodology"], ["Ingest official UTA PDFs with MinerU parsing", "Build heavy RAG storage with chunks, vectors, and graph artifacts", "Build a compact retrieval store for fast advisor responses", "Serve answers through FastAPI, React, and Supabase chat persistence"], [""]],
        8: [["System Architecture"]],
        9: [["System Architecture"], ["Heavy layer: parsing, chunking, embeddings, graph storage", "Light layer: fast structured retrieval for semester plans, prerequisites, and topic-based queries", "Frontend layer: login, chat history, optional program selection, new chat flow"]],
        10: [["Innovation Showcase"], ["Hybrid design: heavy RAG as the knowledge backbone, light RAG as the fast app layer", "Parsed-cache rebuild path separates PDF parsing from indexing", "Graduate routing and topic retrieval were refined for MSCS, certificates, and PhD documents"]],
        11: [["Results and Critical Evaluation"]],
        12: [["Results and Critical Evaluation"], ["The app now answers from official UTA PDFs instead of hardcoded demo text", "MSCS AI queries now surface graduate Intelligent Systems courses more accurately", "Main limitation: full OpenAI-backed heavy rebuild is constrained by API quota and cost", "Evaluation is currently strongest in manual query validation rather than full benchmark metrics"]],
        13: [["Future Scope"]],
        14: [["Future Scope"], ["Complete a fully refreshed heavy vector/graph rebuild with stable funded or local embeddings", "Add stronger automated evaluation and citation-style source surfacing", "Expand to more advising sources such as catalogs, departmental pages, and syllabi", "Improve hybrid query planning so structured and semantic retrieval combine automatically"]],
        15: [["Thank You"], ["Questions?"]],
    }

    with ZipFile(PRESENTATION_OUT, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    with ZipFile(PRESENTATION_OUT, "w", compression=ZIP_DEFLATED) as zout:
        for name, data in files.items():
            if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                match = re.search(r"slide(\d+)\.xml$", name)
                slide_num = int(match.group(1)) if match else None
                if slide_num in slide_updates:
                    root = ET.fromstring(data)
                    shapes = [
                        sp
                        for sp in root.findall(f".//{{{P_NS}}}sp")
                        if sp.find(f"{{{P_NS}}}txBody") is not None
                    ]
                    updates = slide_updates[slide_num]
                    for idx, paragraphs in enumerate(updates):
                        if idx < len(shapes):
                            set_shape_paragraphs(shapes[idx], paragraphs)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            zout.writestr(name, data)


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    build_report()
    build_presentation()
    print(REPORT_DOCX)
    print(PRESENTATION_OUT)


if __name__ == "__main__":
    main()
