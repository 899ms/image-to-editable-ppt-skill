#!/usr/bin/env python3
import argparse
import json
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
PML_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
ASPECT_16_9 = 16 / 9
ASPECT_TOLERANCE = 0.03
EMU_PER_INCH = 914400

RELATIONSHIP = f"{{{REL_NS}}}Relationship"
OVERRIDE = f"{{{CONTENT_TYPES_NS}}}Override"
DEFAULT = f"{{{CONTENT_TYPES_NS}}}Default"


IMAGE_REL = f"{OFFICE_REL_NS}/image"
NOTES_MASTER_REL = f"{OFFICE_REL_NS}/notesMaster"
NOTES_SLIDE_REL = f"{OFFICE_REL_NS}/notesSlide"
SLIDE_REL = f"{OFFICE_REL_NS}/slide"
SLIDE_LAYOUT_REL = f"{OFFICE_REL_NS}/slideLayout"
SLIDE_MASTER_REL = f"{OFFICE_REL_NS}/slideMaster"
THEME_REL = f"{OFFICE_REL_NS}/theme"


CONTENT_TYPES = {
    ".bin": "application/vnd.openxmlformats-officedocument.presentationml.printerSettings",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".xml": "application/xml",
    ".rels": "application/vnd.openxmlformats-package.relationships+xml",
}


def emu(value):
    return int(round(float(value) * EMU_PER_INCH))


def is_wide_slide(width, height):
    return abs((float(width) / float(height)) / ASPECT_16_9 - 1) <= ASPECT_TOLERANCE


def slide_size_type(width, height):
    return "wide" if is_wide_slide(width, height) else "custom"


def rels_xml(relationships):
    body = "".join(
        f'<Relationship Id="{rel["id"]}" Type="{rel["type"]}" Target="{rel["target"]}"'
        + (f' TargetMode="{rel["target_mode"]}"' if rel.get("target_mode") else "")
        + "/>"
        for rel in relationships
    )
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}">{body}</Relationships>'


def rel_source_part(rels_name):
    directory = posixpath.dirname(rels_name)
    if directory.endswith("/_rels"):
        directory = posixpath.dirname(directory)
    source = posixpath.basename(rels_name)[:-5]
    return posixpath.normpath(posixpath.join(directory, source))


def resolve_target(rels_name, target):
    if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
        return None
    source = rel_source_part(rels_name)
    return posixpath.normpath(posixpath.join(posixpath.dirname(source), target))


def relative_target(from_part, to_part):
    source_dir = posixpath.dirname(from_part)
    return posixpath.relpath(to_part, source_dir)


def parse_relationships(z, rels_name):
    if rels_name not in z.namelist():
        return []
    root = ET.fromstring(z.read(rels_name))
    relationships = []
    for rel in root.findall(RELATIONSHIP):
        relationships.append(
            {
                "id": rel.attrib["Id"],
                "type": rel.attrib["Type"],
                "target": rel.attrib.get("Target", ""),
                "target_mode": rel.attrib.get("TargetMode"),
            }
        )
    return relationships


def presentation_slide_parts(z):
    rels = parse_relationships(z, "ppt/_rels/presentation.xml.rels")
    slide_parts = []
    for rel in rels:
        if rel["type"] == SLIDE_REL and rel.get("target_mode") != "External":
            slide_parts.append(posixpath.normpath(posixpath.join("ppt", rel["target"])))
    if slide_parts:
        return slide_parts
    return sorted(name for name in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", name))


def slide_size_from_deck(deck):
    slide = deck.get("slide", {})
    return emu(slide.get("width", 13.333)), emu(slide.get("height", 7.5))


def content_type_for_part(z, part_name):
    suffix = Path(part_name).suffix.lower()
    fallback = CONTENT_TYPES.get(suffix)
    try:
        root = ET.fromstring(z.read("[Content_Types].xml"))
    except Exception:
        return fallback
    for override in root.findall(OVERRIDE):
        if override.attrib.get("PartName") == "/" + part_name:
            return override.attrib.get("ContentType", fallback)
    for default in root.findall(DEFAULT):
        if default.attrib.get("Extension", "").lower() == suffix.lstrip("."):
            return default.attrib.get("ContentType", fallback)
    return fallback


def next_part_name(prefix, source_part, used_names):
    suffix = Path(source_part).suffix.lower()
    counter = 1
    while True:
        candidate = f"{prefix}{counter}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1


def common_content_types(slide_count, copied_parts, notes_indices=None):
    notes_indices = notes_indices or []
    defaults = {
        "rels": CONTENT_TYPES[".rels"],
        "xml": CONTENT_TYPES[".xml"],
    }
    overrides = [
        ('/ppt/presentation.xml', 'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'),
        ('/ppt/slideMasters/slideMaster1.xml', 'application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml'),
        ('/ppt/slideLayouts/slideLayout1.xml', 'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml'),
        ('/ppt/theme/theme1.xml', 'application/vnd.openxmlformats-officedocument.theme+xml'),
        ('/docProps/core.xml', 'application/vnd.openxmlformats-package.core-properties+xml'),
        ('/docProps/app.xml', 'application/vnd.openxmlformats-officedocument.extended-properties+xml'),
    ]
    for index in range(1, slide_count + 1):
        overrides.append((f"/ppt/slides/slide{index}.xml", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"))
    if notes_indices:
        overrides.append(("/ppt/notesMasters/notesMaster1.xml", "application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml"))
        for index in notes_indices:
            overrides.append((f"/ppt/notesSlides/notesSlide{index}.xml", "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"))
    for part_name, content_type in copied_parts.items():
        suffix = Path(part_name).suffix.lower().lstrip(".")
        if content_type and suffix in {"png", "jpg", "jpeg", "gif", "svg"}:
            defaults[suffix] = content_type
        elif content_type:
            overrides.append(("/" + part_name, content_type))
    default_xml = "".join(f'<Default Extension="{ext}" ContentType="{ctype}"/>' for ext, ctype in sorted(defaults.items()))
    override_xml = "".join(f'<Override PartName="{part}" ContentType="{ctype}"/>' for part, ctype in overrides)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="{CONTENT_TYPES_NS}">{default_xml}{override_xml}</Types>'


def presentation_xml(slide_count, width, height):
    slide_ids = "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, slide_count + 1))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{OFFICE_REL_NS}" xmlns:p="{PML_NS}">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>{slide_ids}</p:sldIdLst>
  <p:sldSz cx="{width}" cy="{height}" type="{slide_size_type(width / EMU_PER_INCH, height / EMU_PER_INCH)}"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""


def presentation_rels_xml(slide_count):
    relationships = [{"id": "rId1", "type": SLIDE_MASTER_REL, "target": "slideMasters/slideMaster1.xml"}]
    for index in range(1, slide_count + 1):
        relationships.append({"id": f"rId{index + 1}", "type": SLIDE_REL, "target": f"slides/slide{index}.xml"})
    return rels_xml(relationships)


def write_common_parts(z, slide_count, width, height, notes_count=0):
    presentation_format = "Widescreen" if slide_size_type(width / EMU_PER_INCH, height / EMU_PER_INCH) == "wide" else "Custom"
    z.writestr("_rels/.rels", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>""")
    z.writestr("docProps/core.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Image to editable PPT</dc:title></cp:coreProperties>""")
    z.writestr("docProps/app.xml", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Codex</Application><PresentationFormat>{presentation_format}</PresentationFormat><Slides>{slide_count}</Slides></Properties>""")
    z.writestr("ppt/presentation.xml", presentation_xml(slide_count, width, height))
    z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels_xml(slide_count))
    z.writestr("ppt/slideMasters/slideMaster1.xml", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{OFFICE_REL_NS}" xmlns:p="{PML_NS}"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>""")
    z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="{SLIDE_LAYOUT_REL}" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="{THEME_REL}" Target="../theme/theme1.xml"/></Relationships>""")
    z.writestr("ppt/slideLayouts/slideLayout1.xml", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{OFFICE_REL_NS}" xmlns:p="{PML_NS}" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>""")
    z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL_NS}"><Relationship Id="rId1" Type="{SLIDE_MASTER_REL}" Target="../slideMasters/slideMaster1.xml"/></Relationships>""")
    z.writestr("ppt/theme/theme1.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="ImageToEditablePPT"><a:themeElements><a:clrScheme name="Office"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1><a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F1F1F"/></a:dk2><a:lt2><a:srgbClr val="F8F8F8"/></a:lt2><a:accent1><a:srgbClr val="0F766E"/></a:accent1><a:accent2><a:srgbClr val="E66B00"/></a:accent2><a:accent3><a:srgbClr val="F6D365"/></a:accent3><a:accent4><a:srgbClr val="57C4B8"/></a:accent4><a:accent5><a:srgbClr val="666666"/></a:accent5><a:accent6><a:srgbClr val="111111"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme><a:fontScheme name="PingFang"><a:majorFont><a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/><a:cs typeface="PingFang SC"/></a:majorFont><a:minorFont><a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/><a:cs typeface="PingFang SC"/></a:minorFont></a:fontScheme><a:fmtScheme name="Office"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>""")
    if notes_count:
        z.writestr("ppt/notesMasters/notesMaster1.xml", notes_master_xml())
        z.writestr("ppt/notesMasters/_rels/notesMaster1.xml.rels", notes_master_rels_xml())


def xml_text(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def notes_slide_xml(text):
    paras = "".join(
        f'<a:p><a:r><a:rPr lang="zh-CN" sz="1200"/><a:t>{xml_text(line)}</a:t></a:r><a:endParaRPr lang="zh-CN" sz="1200"/></a:p>'
        for line in str(text).splitlines()
    ) or '<a:p><a:endParaRPr lang="zh-CN" sz="1200"/></a:p>'
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{OFFICE_REL_NS}" xmlns:p="{PML_NS}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Notes Placeholder"/><p:cNvSpPr txBox="1"/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="685800" y="914400"/><a:ext cx="5486400" cy="6858000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/>{paras}</p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:notes>"""


def notes_rels_xml(slide_index):
    return rels_xml(
        [
            {"id": "rId1", "type": NOTES_MASTER_REL, "target": "../notesMasters/notesMaster1.xml"},
            {"id": "rId2", "type": SLIDE_REL, "target": f"../slides/slide{slide_index}.xml"},
        ]
    )


def notes_master_xml():
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:notesMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{OFFICE_REL_NS}" xmlns:p="{PML_NS}">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
</p:notesMaster>"""


def notes_master_rels_xml():
    return rels_xml([{"id": "rId1", "type": THEME_REL, "target": "../theme/theme1.xml"}])


def unique_rel_id(relationships):
    used = {rel["id"] for rel in relationships}
    index = 1
    while f"rId{index}" in used:
        index += 1
    return f"rId{index}"


def copied_slide_relationships(source_zip, source_slide, output_slide, used_parts, copied_parts, notes_index=None):
    rels_name = f"{posixpath.dirname(source_slide)}/_rels/{posixpath.basename(source_slide)}.rels"
    output_rels_part = f"{posixpath.dirname(output_slide)}/_rels/{posixpath.basename(output_slide)}.rels"
    relationships = []
    pending_parts = []
    for rel in parse_relationships(source_zip, rels_name):
        if rel["type"] == SLIDE_LAYOUT_REL:
            relationships.append({"id": rel["id"], "type": SLIDE_LAYOUT_REL, "target": "../slideLayouts/slideLayout1.xml"})
            continue
        if rel["type"] == NOTES_SLIDE_REL:
            continue
        if rel.get("target_mode") == "External":
            relationships.append(rel)
            continue
        resolved = resolve_target(rels_name, rel["target"])
        if not resolved:
            continue
        if resolved not in source_zip.namelist():
            continue
        if rel["type"] != IMAGE_REL:
            raise SystemExit(f"Unsupported internal slide relationship in page PPTX: {rel['type']} -> {rel['target']}")
        dest = next_part_name("ppt/media/image", resolved, used_parts)
        content_type = content_type_for_part(source_zip, resolved)
        copied_parts[dest] = content_type
        pending_parts.append((resolved, dest))
        relationships.append({"id": rel["id"], "type": rel["type"], "target": relative_target(output_rels_part, dest)})
    if not any(rel["type"] == SLIDE_LAYOUT_REL for rel in relationships):
        relationships.insert(0, {"id": "rIdLayout", "type": SLIDE_LAYOUT_REL, "target": "../slideLayouts/slideLayout1.xml"})
    if notes_index is not None:
        relationships.append({"id": unique_rel_id(relationships), "type": NOTES_SLIDE_REL, "target": f"../notesSlides/notesSlide{notes_index}.xml"})
    return rels_xml(relationships), pending_parts


def page_pptx_from_job(run_dir, page):
    result = page.get("result") or {}
    page_result = result.get("page_result") or {}
    candidate = page_result.get("page_pptx") or result.get("page_pptx") or page.get("page_pptx")
    if not candidate:
        candidate = Path(page.get("page_dir", "")) / "page.pptx"
    path = Path(candidate)
    if not path.is_absolute():
        path = run_dir / path
    return path


def assemble_deck(run_dir, deck, jobs, out_path):
    pages = list(jobs.get("pages", []))
    if not pages:
        raise SystemExit("No recorded pages to assemble.")
    width, height = slide_size_from_deck(deck)
    used_parts = set()
    copied_parts = {}
    notes_by_page = load_notes(run_dir, deck)
    notes_indices = sorted(notes_by_page)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as out_zip:
        write_common_parts(out_zip, len(pages), width, height, len(notes_indices))
        for slide_index, page in enumerate(pages, start=1):
            page_pptx = page_pptx_from_job(run_dir, page)
            if not page_pptx.exists():
                raise SystemExit(f"Missing page PPTX for {page.get('page_id')}: {page_pptx}")
            with zipfile.ZipFile(page_pptx) as source_zip:
                source_slides = presentation_slide_parts(source_zip)
                if not source_slides:
                    raise SystemExit(f"{page_pptx} has no slides.")
                source_slide = source_slides[0]
                output_slide = f"ppt/slides/slide{slide_index}.xml"
                out_zip.writestr(output_slide, source_zip.read(source_slide))
                notes_index = slide_index if slide_index in notes_by_page else None
                rels, pending_parts = copied_slide_relationships(source_zip, source_slide, output_slide, used_parts, copied_parts, notes_index)
                out_zip.writestr(f"ppt/slides/_rels/slide{slide_index}.xml.rels", rels)
                for src, dest in pending_parts:
                    out_zip.writestr(dest, source_zip.read(src))
                if notes_index is not None:
                    out_zip.writestr(f"ppt/notesSlides/notesSlide{notes_index}.xml", notes_slide_xml(notes_by_page[notes_index].get("text", "")))
                    out_zip.writestr(f"ppt/notesSlides/_rels/notesSlide{notes_index}.xml.rels", notes_rels_xml(slide_index))
        out_zip.writestr("[Content_Types].xml", common_content_types(len(pages), copied_parts, notes_indices))
    return out


def load_notes(run_dir, deck):
    notes_path = deck.get("notes_manifest")
    if not notes_path:
        return {}
    path = Path(notes_path)
    if not path.is_absolute():
        path = run_dir / path
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {int(entry.get("page_index", 0)): entry for entry in data.get("notes", []) if entry.get("text")}


def main():
    parser = argparse.ArgumentParser(description="Assemble final deck by concatenating recorded page-level PPTX files.")
    parser.add_argument("run", help="Run directory containing deck_manifest.json and page_jobs.json.")
    parser.add_argument("--out", required=True, help="Final PPTX path.")
    args = parser.parse_args()
    run_dir = Path(args.run).resolve()
    deck = json.loads((run_dir / "deck_manifest.json").read_text(encoding="utf-8"))
    jobs = json.loads((run_dir / "page_jobs.json").read_text(encoding="utf-8"))
    out = assemble_deck(run_dir, deck, jobs, args.out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
