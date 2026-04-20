import asyncio
import io
import re
import shutil
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import requests
import fitz  # PyMuPDF
from app.config import settings
from app.services.latex_parser import LatexParser
from app.services.agent_service import generate_report_with_agent
from app.logger import setup_logger

logger = setup_logger("arxiv")


class ArxivService:
    def __init__(self):
        self.papers_dir = Path(settings.papers_dir)
        self.images_dir = Path(settings.images_dir)
        self.latex_dir = Path(settings.latex_dir)
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.latex_dir.mkdir(parents=True, exist_ok=True)
        self.latex_parser = LatexParser()

    def fetch_arxiv_metadata(self, arxiv_id: str) -> Dict[str, Any]:
        """Fetch paper metadata from arXiv Atom API."""
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                return {}
            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entry = root.find(".//atom:entry", ns)
            if entry is None:
                return {}
            title_el = entry.find("atom:title", ns)
            author_els = entry.findall("atom:author/atom:name", ns)
            summary_el = entry.find("atom:summary", ns)
            return {
                "title": title_el.text.strip() if title_el is not None and title_el.text else "",
                "authors": [a.text.strip() for a in author_els if a.text],
                "abstract": summary_el.text.strip() if summary_el is not None and summary_el.text else "",
            }
        except Exception as e:
            logger.warning(f"[{arxiv_id}] Failed to fetch arXiv metadata: {e}")
            return {}

    def _extract_arxiv_id(self, url: str) -> str:
        url = url.strip()
        if "arxiv.org" in url:
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")
            return parts[-1]
        return url

    def download_latex_source(self, arxiv_id: str) -> Optional[Path]:
        """Download LaTeX source to persistent directory. Returns path to extracted tex dir."""
        tex_dir = self._get_latex_dir(arxiv_id)
        tar_path = tex_dir / f"{arxiv_id}.tar.gz"

        if tex_dir.exists() and any(tex_dir.glob("*.tex")):
            logger.info(f"[{arxiv_id}] LaTeX source already exists at {tex_dir}, skipping download")
            return tex_dir

        tex_dir.mkdir(parents=True, exist_ok=True)
        url = f"https://arxiv.org/e-print/{arxiv_id}"
        logger.info(f"[{arxiv_id}] Downloading LaTeX source from {url}")

        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                logger.info(f"[{arxiv_id}] LaTeX source downloaded: {len(resp.content)} bytes")
                tar_path.write_bytes(resp.content)
                self._extract_tar_to_dir(resp.content, tex_dir)
                logger.info(f"[{arxiv_id}] LaTeX source extracted to {tex_dir}")
                return tex_dir
            elif resp.status_code == 404:
                logger.warning(f"[{arxiv_id}] LaTeX source not available (404)")
                return None
            else:
                logger.error(f"[{arxiv_id}] Failed to download LaTeX: HTTP {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"[{arxiv_id}] Exception downloading LaTeX: {e}")
            return None

    def _get_latex_dir(self, arxiv_id: str) -> Path:
        return self.latex_dir / arxiv_id

    def _extract_tar_to_dir(self, tar_data: bytes, output_dir: Path) -> None:
        try:
            with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if not member.name.startswith("__"):
                        tar.extract(member, output_dir)
        except Exception as e:
            logger.error(f"Failed to extract tar archive: {e}")

    def find_tex_files(self, tex_dir: Path) -> List[Path]:
        tex_files = list(tex_dir.rglob("*.tex"))
        logger.info(f"Found {len(tex_files)} .tex files in {tex_dir}")
        return tex_files

    def find_main_tex(self, tex_files: List[Path]) -> Optional[Path]:
        for tex_file in tex_files:
            try:
                content = tex_file.read_text(encoding="utf-8", errors="ignore")
                if "\\documentclass" in content:
                    logger.info(f"Found main tex file: {tex_file.name}")
                    return tex_file
            except Exception:
                continue
        if tex_files:
            logger.warning(f"No \\documentclass found, using first tex file: {tex_files[0].name}")
            return tex_files[0]
        return None

    def convert_pdf_to_png(self, pdf_path: Path, output_path: Path, dpi: int = 150) -> bool:
        """Convert a PDF image file (from LaTeX source) to PNG for web display."""
        try:
            doc = fitz.open(str(pdf_path))
            page = doc[0]
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            pix.save(str(output_path))
            doc.close()
            return True
        except Exception as e:
            logger.warning(f"PDF to PNG failed for {pdf_path.name}: {e}")
            return False

    def _convert_eps_to_png(self, eps_path: Path, output_path: Path) -> bool:
        import subprocess
        try:
            result = subprocess.run(
                ["pdftoppm", "-png", "-r", "150", str(eps_path), str(output_path.with_suffix(""))],
                capture_output=True, timeout=30
            )
            if result.returncode == 0:
                generated = output_path.with_name(output_path.stem + "-1.png")
                if generated.exists():
                    generated.rename(output_path)
                    return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        try:
            result = subprocess.run(
                ["inkscape", str(eps_path), "--export-filename", str(output_path), "--export-dpi", "150"],
                capture_output=True, timeout=30
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        logger.warning(f"Could not convert EPS {eps_path.name}")
        return False

    def _find_image_file(self, tex_dir: Path, image_name: str) -> Optional[Path]:
        """Find actual image file in tex_dir matching the referenced name (with various extensions)."""
        # image_name may have no extension or a partial path like "figures/arch"
        base = Path(image_name).stem
        subdir = Path(image_name).parent
        search_dir = tex_dir / subdir if subdir != Path(".") else tex_dir

        extensions = [".pdf", ".png", ".jpg", ".jpeg", ".eps"]
        for ext in extensions:
            candidate = search_dir / (base + ext)
            if candidate.exists():
                return candidate
        # Also try without subdir (some papers put all images in root)
        for ext in extensions:
            candidate = tex_dir / (base + ext)
            if candidate.exists():
                return candidate
        return None

    def _crop_pdf_white_margins(self, pdf_path: Path, output_path: Path) -> bool:
        """Use pdfcrop to remove white margins from a PDF."""
        try:
            result = subprocess.run(
                ["pdfcrop", str(pdf_path), str(output_path)],
                capture_output=True,
                timeout=30,
            )
            return result.returncode == 0 and output_path.exists()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _compile_tikz_figure(self, tex_dir: Path, fig_content: str, output_path: Path) -> bool:
        """Compile a tikz figure to PNG using the paper's preamble."""
        # Find main tex to get preamble
        tex_files = list(tex_dir.rglob("*.tex"))
        main_tex = self.find_main_tex(tex_files)
        if not main_tex:
            return False

        main_content = main_tex.read_text(encoding="utf-8", errors="ignore")
        docclass_idx = main_content.find("\\documentclass")
        begin_doc_idx = main_content.find("\\begin{document}")
        if docclass_idx == -1 or begin_doc_idx == -1:
            return False

        preamble = main_content[docclass_idx:begin_doc_idx]

        # Clean figure content: remove caption/label
        fig_clean = fig_content
        fig_clean = re.sub(r"\\caption\{[^}]*\}", "", fig_clean, flags=re.DOTALL)
        fig_clean = re.sub(r"\\label\{[^}]*\}", "", fig_clean)

        tex_content = f"""{preamble}
\\begin{{document}}
\\thispagestyle{{empty}}
\\nopagecolor
{fig_clean}
\\end{{document}}
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tex_path = tmpdir_path / "fig.tex"
            tex_path.write_text(tex_content, encoding="utf-8")

            # Copy auxiliary files from tex_dir (styles, small images, etc.)
            for f in tex_dir.iterdir():
                if f.is_file() and f.suffix in [".sty", ".cls", ".bst", ".bib"]:
                    shutil.copy2(f, tmpdir_path / f.name)
            # Also copy subdirectories (figures/, tables/, etc.)
            for subdir in tex_dir.iterdir():
                if subdir.is_dir():
                    dst = tmpdir_path / subdir.name
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(subdir, dst)

            try:
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", str(tex_path.name)],
                    cwd=tmpdir,
                    capture_output=True,
                    timeout=120,
                )
                pdf_path = tmpdir_path / "fig.pdf"
                if not pdf_path.exists():
                    stderr_text = result.stderr.decode("utf-8", errors="ignore")[:300] if result.stderr else ""
                    stdout_text = result.stdout.decode("utf-8", errors="ignore")[-500:] if result.stdout else ""
                    logger.warning(
                        f"Tikz compilation produced no PDF for {output_path.name}. "
                        f"stderr: {stderr_text}, stdout tail: {stdout_text}"
                    )
                    return False

                # Crop white margins before converting to PNG
                cropped_pdf = tmpdir_path / "fig-cropped.pdf"
                if self._crop_pdf_white_margins(pdf_path, cropped_pdf):
                    pdf_path = cropped_pdf
                    logger.info(f"Cropped white margins for {output_path.name}")

                self.convert_pdf_to_png(pdf_path, output_path, dpi=150)
                return True
            except subprocess.TimeoutExpired:
                logger.warning(f"Tikz compilation timed out for {output_path.name}")
            except Exception as e:
                logger.warning(f"Tikz compilation failed for {output_path.name}: {e}")

        return False

    def extract_images_from_latex(self, tex_dir: Path, output_dir: Path, figures: List[Dict[str, str]]) -> List[Path]:
        """Extract images from figure environments. Preserve original filenames for external images; compile tikz."""
        image_files = []
        output_dir.mkdir(parents=True, exist_ok=True)
        seen_names: set[str] = set()

        for i, fig in enumerate(figures, 1):
            img_name = fig.get("image_file", "").strip()
            raw_content = fig.get("raw", "")

            if img_name:
                # External image file
                src_path = self._find_image_file(tex_dir, img_name)
                if src_path:
                    ext = src_path.suffix.lower()
                    base_name = src_path.stem
                    if base_name not in seen_names:
                        seen_names.add(base_name)
                        out_path = output_dir / f"{base_name}.png"
                        if ext == ".pdf":
                            if self.convert_pdf_to_png(src_path, out_path):
                                image_files.append(out_path)
                        elif ext in [".png", ".jpg", ".jpeg"]:
                            shutil.copy2(src_path, out_path)
                            image_files.append(out_path)
                        elif ext == ".eps":
                            if self._convert_eps_to_png(src_path, out_path):
                                image_files.append(out_path)
                    continue

            # No external image — try to compile tikz
            if "\\begin{tikzpicture}" in raw_content or "\\tikz" in raw_content:
                label = fig.get("label", f"fig_{i:03d}")
                out_name = f"{label}.png" if label else f"fig_{i:03d}.png"
                out_path = output_dir / out_name
                if out_path.name not in seen_names:
                    seen_names.add(out_path.name)
                    logger.info(f"Compiling tikz figure {i} -> {out_name}")
                    if self._compile_tikz_figure(tex_dir, raw_content, out_path):
                        image_files.append(out_path)

        logger.info(f"Extracted {len(image_files)} images from LaTeX source")
        return image_files

    def process_paper(self, arxiv_id: str) -> Dict[str, Any]:
        """Full pipeline: download LaTeX -> parse -> generate report. No PDF fallback."""
        logger.info(f"[{arxiv_id}] ===== Starting paper processing =====")
        result = {
            "arxiv_id": arxiv_id,
            "title": "",
            "title_zh": "",
            "authors": "",
            "affiliation": "",
            "abstract": "",
            "report_md": "",
            "raw_sections": [],
            "images": [],
            "status": "processing",
            "error_msg": None,
        }

        paper_images_dir = self.images_dir / arxiv_id
        paper_images_dir.mkdir(parents=True, exist_ok=True)

        # Step 0: Fetch arXiv metadata (authors are more reliable from API)
        arxiv_meta = self.fetch_arxiv_metadata(arxiv_id)
        meta_authors = arxiv_meta.get("authors", [])
        meta_title = arxiv_meta.get("title", "")
        meta_abstract = arxiv_meta.get("abstract", "")

        # Step 1: Download or reuse LaTeX source
        tex_dir = self.download_latex_source(arxiv_id)
        if not tex_dir:
            result["status"] = "failed"
            result["error_msg"] = "LaTeX source not available for this paper"
            logger.error(f"[{arxiv_id}] ===== FAILED: No LaTeX source =====")
            return result

        # Step 2: Find and parse main tex
        try:
            tex_files = self.find_tex_files(tex_dir)
            if not tex_files:
                raise RuntimeError("No .tex files found in archive")

            main_tex = self.find_main_tex(tex_files)
            if not main_tex:
                raise RuntimeError("Could not identify main tex file")

            logger.info(f"[{arxiv_id}] Parsing LaTeX structure...")
            parsed = self.latex_parser.parse(main_tex)
            logger.info(
                f"[{arxiv_id}] Parsed: title={parsed.get('title', '')[:60]}, "
                f"sections={len(parsed.get('sections', []))}, "
                f"figures={len(parsed.get('figures', []))}"
            )

            # Step 3: Extract images from LaTeX source (in figure order, skipping logos)
            image_paths = self.extract_images_from_latex(tex_dir, paper_images_dir, parsed.get("figures", []))
            result["images"] = [str(p.name) for p in image_paths]

            # Fill basic info
            latex_title = parsed.get("title", "")
            latex_authors = parsed.get("authors", [])
            latex_abstract = parsed.get("abstract", "")

            # Title: prefer LaTeX (usually cleaner), fallback to arXiv API
            result["title"] = latex_title or meta_title

            # Authors: arXiv API is more reliable for author names
            latex_author_names = [a.get("name", "").strip() for a in latex_authors]
            # Heuristic: if LaTeX extracted only 1 suspicious author (too short, contains %, or looks like institution)
            suspicious = (
                len(latex_author_names) == 1 and latex_author_names[0]
                and (len(latex_author_names[0]) < 5 or "%" in latex_author_names[0] or "@" in latex_author_names[0])
            )
            if meta_authors and (not latex_author_names or suspicious or all(n == "" for n in latex_author_names)):
                result["authors"] = ", ".join(meta_authors)
            else:
                result["authors"] = ", ".join(n for n in latex_author_names if n)

            # Affiliation: extract from LaTeX \author (if it contains institution info)
            affiliations = []
            for a in latex_authors:
                aff = a.get("affiliation", "").strip()
                if aff and aff not in affiliations and len(aff) < 200:
                    affiliations.append(aff)
            # If no affiliation found in LaTeX, try to infer from suspicious single-author content
            if not affiliations and len(latex_author_names) == 1 and latex_author_names[0]:
                raw = latex_author_names[0]
                # e.g. "\large JD.com" -> extract "JD.com"
                cleaned = re.sub(r"[\\%].*", "", raw).strip()
                if cleaned and len(cleaned) < 100:
                    affiliations.append(cleaned)
            result["affiliation"] = ", ".join(affiliations)

            # Abstract: prefer LaTeX (usually more complete), fallback to arXiv API
            result["abstract"] = latex_abstract or meta_abstract
            result["raw_sections"] = parsed.get("sections", [])

            # Step 4: Generate report with Agent
            logger.info(f"[{arxiv_id}] Starting paper reading agent...")
            report_md = asyncio.run(
                generate_report_with_agent(arxiv_id, parsed, paper_images_dir, image_paths)
            )
            result["report_md"] = report_md

            result["status"] = "done"
            logger.info(f"[{arxiv_id}] ===== Processing completed successfully =====")
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{arxiv_id}] Processing failed: {error_msg}")
            if not any(paper_images_dir.iterdir()):
                paper_images_dir.rmdir()
            result["status"] = "failed"
            result["error_msg"] = error_msg
            logger.error(f"[{arxiv_id}] ===== Processing FAILED =====")
            return result


arxiv_service = ArxivService()
