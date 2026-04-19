import asyncio
import io
import re
import shutil
import tarfile
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

    def extract_images_from_latex(self, tex_dir: Path, output_dir: Path, figures: List[Dict[str, str]]) -> List[Path]:
        """Extract images referenced in figure environments. Preserve original filenames (PDF->PNG)."""
        image_files = []
        output_dir.mkdir(parents=True, exist_ok=True)
        seen_names: set[str] = set()

        for fig in figures:
            img_name = fig.get("image_file", "").strip()
            if not img_name:
                continue

            src_path = self._find_image_file(tex_dir, img_name)
            if not src_path:
                logger.warning(f"Could not find image file for: {img_name}")
                continue

            ext = src_path.suffix.lower()
            # Preserve original base name; force .png for web display
            base_name = src_path.stem
            if base_name in seen_names:
                # Deduplicate if same image referenced multiple times
                continue
            seen_names.add(base_name)

            out_name = f"{base_name}.png"
            out_path = output_dir / out_name

            if ext == ".pdf":
                if self.convert_pdf_to_png(src_path, out_path):
                    image_files.append(out_path)
            elif ext in [".png", ".jpg", ".jpeg"]:
                shutil.copy2(src_path, out_path)
                image_files.append(out_path)
            elif ext == ".eps":
                if self._convert_eps_to_png(src_path, out_path):
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
            "abstract": "",
            "report_md": "",
            "raw_sections": [],
            "images": [],
            "status": "processing",
            "error_msg": None,
        }

        paper_images_dir = self.images_dir / arxiv_id
        paper_images_dir.mkdir(parents=True, exist_ok=True)

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
            result["title"] = parsed.get("title", "")
            authors_list = parsed.get("authors", [])
            result["authors"] = ", ".join([a.get("name", "") for a in authors_list])
            result["abstract"] = parsed.get("abstract", "")
            result["raw_sections"] = parsed.get("sections", [])

            # Step 4: Generate report with Agent
            logger.info(f"[{arxiv_id}] Starting paper reading agent...")
            report_md = asyncio.run(
                generate_report_with_agent(arxiv_id, parsed, paper_images_dir, image_paths)
            )
            result["report_md"] = report_md

            # Extract Chinese title from report
            title_match = re.search(r"^#\s+(.+)$", report_md, re.MULTILINE)
            if title_match:
                result["title_zh"] = title_match.group(1).strip()

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
