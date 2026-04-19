#!/usr/bin/env python3
"""LaTeX Parser - Extract structured content from LaTeX source files."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any


class LatexParser:
    """Parser for LaTeX documents."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, message: str):
        if self.verbose:
            print(f"[LATEX] {message}")

    def read_tex_file(self, filepath: Path) -> str:
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        for encoding in encodings:
            try:
                return filepath.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return filepath.read_text(encoding="utf-8", errors="ignore")

    def resolve_inputs(self, content: str, base_dir: Path, depth: int = 0, max_depth: int = 5) -> str:
        if depth >= max_depth:
            return content

        def replace_input(match):
            filename = match.group(1)
            for ext in [".tex", ""]:
                input_path = base_dir / (filename + ext)
                if input_path.exists():
                    try:
                        sub_content = self.read_tex_file(input_path)
                        sub_content = self.resolve_inputs(sub_content, input_path.parent, depth + 1, max_depth)
                        return f"\n% BEGIN INPUT: {filename}\n{sub_content}\n% END INPUT: {filename}\n"
                    except Exception as e:
                        return f"% ERROR including {filename}: {e}"
            return f"% FILE NOT FOUND: {filename}"

        pattern = r"\\(?:input|include)\{([^}]+)\}"
        return re.sub(pattern, replace_input, content)

    def extract_documentclass(self, content: str) -> Optional[Dict[str, str]]:
        pattern = r"\\documentclass\[(.*?)\]\{(.*?)\}"
        match = re.search(pattern, content)
        if match:
            return {"options": match.group(1).split(",") if match.group(1) else [], "class": match.group(2)}
        pattern = r"\\documentclass\{(.*?)\}"
        match = re.search(pattern, content)
        if match:
            return {"options": [], "class": match.group(1)}
        return None

    def _extract_balanced_braces(self, content: str, start_keyword: str) -> str:
        """Extract content inside balanced braces after a keyword like \\title{...}"""
        idx = content.find(start_keyword)
        if idx == -1:
            return ""
        idx += len(start_keyword)
        while idx < len(content) and content[idx].isspace():
            idx += 1
        if idx >= len(content) or content[idx] != "{":
            return ""
        idx += 1
        depth = 1
        result = []
        while idx < len(content) and depth > 0:
            ch = content[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            result.append(ch)
            idx += 1
        return "".join(result)

    def extract_title(self, content: str) -> str:
        raw = self._extract_balanced_braces(content, r"\title")
        if raw:
            text = self.clean_latex_text(raw)
            # Remove stray braces often left by graphics commands in titles
            text = re.sub(r"[{}]", "", text)
            # Remove leading % (leftover from comment-like syntax in titles)
            text = re.sub(r"^\s*%\s*", "", text)
            return text.strip()
        return ""

    def extract_authors(self, content: str) -> List[Dict[str, str]]:
        authors = []
        author_opt_pattern = r"\\author\[(.*?)\]\{(.*?)\}"
        for match in re.finditer(author_opt_pattern, content, re.DOTALL):
            authors.append({
                "name": self.clean_latex_text(match.group(1)),
                "affiliation": self.clean_latex_text(match.group(2)),
                "email": "",
            })
        if not authors:
            author_pattern = r"\\author\{([^}]*)\}"
            for match in re.finditer(author_pattern, content, re.DOTALL):
                author_text = match.group(1)
                lines = [l.strip() for l in author_text.split("\\") if l.strip()]
                if lines:
                    authors.append({
                        "name": self.clean_latex_text(lines[0]),
                        "affiliation": self.clean_latex_text(" ".join(lines[1:])),
                        "email": "",
                    })
        return authors

    def extract_abstract(self, content: str) -> str:
        pattern = r"\\begin\{abstract\}(.*?)\\end\{abstract\}"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return self.clean_latex_text(match.group(1))
        return ""

    def extract_sections(self, content: str) -> List[Dict[str, Any]]:
        sections = []
        pattern = r"\\(section|subsection|subsubsection)\*?\{([^}]*)\}"
        matches = list(re.finditer(pattern, content, re.DOTALL))
        for i, match in enumerate(matches):
            level = match.group(1)
            title = self.clean_latex_text(match.group(2))
            start = match.end()
            if i < len(matches) - 1:
                end = matches[i + 1].start()
                section_content = content[start:end]
            else:
                section_content = content[start:]
            sections.append({
                "title": title,
                "level": level,
                "content": self.clean_latex_text(section_content),
                "raw_content": section_content,
            })
        return sections

    def extract_figures(self, content: str) -> List[Dict[str, str]]:
        figures = []
        pattern = r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}"
        for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
            fig_content = match.group(1)
            caption_match = re.search(r"\\caption\{([^}]*)\}", fig_content, re.DOTALL)
            caption = self.clean_latex_text(caption_match.group(1)) if caption_match else ""
            label_match = re.search(r"\\label\{([^}]*)\}", fig_content)
            label = label_match.group(1) if label_match else ""
            include_match = re.search(r"\\includegraphics(?:\[.*?\])?\{([^}]*)\}", fig_content)
            image_file = include_match.group(1) if include_match else ""
            figures.append({"caption": caption, "label": label, "image_file": image_file, "raw": fig_content})
        return figures

    def extract_algorithms(self, content: str) -> List[Dict[str, str]]:
        algorithms = []
        pattern = r"\\begin\{algorithm\*?\}(.*?)\\end\{algorithm\*?\}"
        for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
            alg_content = match.group(1)
            caption_match = re.search(r"\\caption\{([^}]*)\}", alg_content, re.DOTALL)
            caption = self.clean_latex_text(caption_match.group(1)) if caption_match else ""
            label_match = re.search(r"\\label\{([^}]*)\}", alg_content)
            label = label_match.group(1) if label_match else ""
            algorithms.append({"caption": caption, "label": label, "content": self.clean_latex_text(alg_content), "raw": alg_content})
        return algorithms

    def extract_tables(self, content: str) -> List[Dict[str, str]]:
        tables = []
        pattern = r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}"
        for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
            table_content = match.group(1)
            caption_match = re.search(r"\\caption\{([^}]*)\}", table_content, re.DOTALL)
            caption = self.clean_latex_text(caption_match.group(1)) if caption_match else ""
            label_match = re.search(r"\\label\{([^}]*)\}", table_content)
            label = label_match.group(1) if label_match else ""
            tabular_match = re.search(r"\\begin\{tabular\}(.*?)\\end\{tabular\}", table_content, re.DOTALL)
            tabular = tabular_match.group(1) if tabular_match else ""
            tables.append({"caption": caption, "label": label, "tabular": self.clean_latex_text(tabular), "raw": table_content})
        return tables

    def extract_equations(self, content: str) -> List[Dict[str, str]]:
        equations = []
        patterns = [
            (r"\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}", "equation"),
            (r"\\begin\{align\*?\}(.*?)\\end\{align\*?\}", "align"),
            (r"\\begin\{gather\*?\}(.*?)\\end\{gather\*?\}", "gather"),
            (r"\\\[(.*?)\\\]", "displaymath"),
        ]
        for pattern, env_type in patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                equations.append({"type": env_type, "content": match.group(1).strip(), "raw": match.group(0)})
        return equations

    def clean_latex_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"(?<!\\)%.*?\n", "\n", text)
        # Iteratively remove commands with single-level brace arguments
        for _ in range(10):
            new_text = re.sub(r"\\[a-zA-Z]+(\*)?\s*(\[[^\]]*\])?\s*\{[^{}]*\}", "", text)
            if new_text == text:
                break
            text = new_text
        text = re.sub(r"\\[a-zA-Z]+(\*)?", "", text)
        text = re.sub(r"\\[,;:!\"']", "", text)
        text = re.sub(r"~", " ", text)
        text = re.sub(r"\$\$.*?\$\$", lambda m: m.group(0), text, flags=re.DOTALL)
        text = re.sub(r"\$.*?\$", lambda m: m.group(0), text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def parse(self, tex_file: Path) -> Dict[str, Any]:
        content = self.read_tex_file(tex_file)
        resolved_content = self.resolve_inputs(content, tex_file.parent)
        doc_match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", resolved_content, re.DOTALL | re.IGNORECASE)
        doc_content = doc_match.group(1) if doc_match else resolved_content
        return {
            "documentclass": self.extract_documentclass(resolved_content),
            "title": self.extract_title(resolved_content),
            "authors": self.extract_authors(resolved_content),
            "abstract": self.extract_abstract(resolved_content),
            "sections": self.extract_sections(doc_content),
            "figures": self.extract_figures(doc_content),
            "tables": self.extract_tables(doc_content),
            "algorithms": self.extract_algorithms(doc_content),
            "equations": self.extract_equations(doc_content),
        }
