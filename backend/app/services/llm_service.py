import json
from typing import Optional, Dict, Any, List
from openai import OpenAI
from app.config import settings
from app.logger import setup_logger

logger = setup_logger("llm")


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.moonshot_api_key,
            base_url=settings.moonshot_base_url,
        )
        self.model = settings.moonshot_model

    def _call(self, messages: List[Dict[str, str]], temperature: float = 1.0) -> str:
        if not settings.moonshot_api_key:
            raise ValueError("MOONSHOT_API_KEY not set")
        logger.info(f"Calling LLM API: model={self.model}, messages_count={len(messages)}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            content = response.choices[0].message.content or ""
            logger.info(f"LLM API response received, length={len(content)}")
            return content
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise RuntimeError(f"LLM API call failed: {e}")

    def generate_report(self, paper_info: Dict[str, Any], image_paths: List[str] = None) -> str:
        """Generate a structured Chinese reading report based on parsed LaTeX content."""
        title = paper_info.get("title", "")
        logger.info(f"Generating report for paper: {title[:80]}")

        authors = paper_info.get("authors", "")
        abstract = paper_info.get("abstract", "")
        sections = paper_info.get("sections", [])
        figures = paper_info.get("figures", [])
        tables = paper_info.get("tables", [])
        algorithms = paper_info.get("algorithms", [])
        image_paths = image_paths or []

        # Build section summaries
        section_texts = []
        for s in sections[:12]:  # Include more sections
            section_texts.append(f"Section: {s.get('title', '')}\n{s.get('content', '')[:3000]}")
        sections_combined = "\n\n".join(section_texts)

        # Build figure descriptions
        figure_texts = []
        for i, fig in enumerate(figures[:5], 1):
            figure_texts.append(f"Figure {i}: {fig.get('caption', '')} (file: {fig.get('image_file', '')})")
        figures_combined = "\n".join(figure_texts) if figure_texts else "No figures extracted."

        # Build table descriptions
        table_texts = []
        for i, tbl in enumerate(tables[:3], 1):
            table_texts.append(f"Table {i}: {tbl.get('caption', '')}\n{tbl.get('tabular', '')[:400]}")
        tables_combined = "\n\n".join(table_texts) if table_texts else "No tables extracted."

        # Build algorithm descriptions
        algo_texts = []
        for i, algo in enumerate(algorithms[:2], 1):
            algo_texts.append(f"Algorithm {i}: {algo.get('caption', '')}\n{algo.get('content', '')[:1500]}")
        algorithms_combined = "\n\n".join(algo_texts) if algo_texts else "No algorithms extracted."

        # Build image references for the prompt based on ACTUALLY extracted images
        image_refs = []
        for i, img_name in enumerate(image_paths[:10], 1):
            # Find matching figure caption if available
            caption = ""
            if i <= len(figures):
                caption = figures[i-1].get('caption', '')
            image_refs.append(f"- ./{img_name}: {caption}")
        images_for_prompt = "\n".join(image_refs) if image_refs else "No images available."

        system_prompt = """You are an expert academic paper analyst. Your task is to read the provided paper structure and generate a concise Chinese reading report. The report should help researchers quickly understand what this paper is about.

Rules:
1. Write in academic Chinese. Keep professional terms in English when appropriate (e.g., Transformer, perplexity, BLEU).
2. Preserve all LaTeX math formulas in their original form ($...$ and $$...$$).
3. Keep figure/table references like \ref{fig:1} as-is.
4. Be concise but informative. This is NOT a full translation, but a structured summary.
5. For the "Method" section, explain the core idea clearly. For "Experiments", highlight key results and comparisons.
6. If pseudo-code is available, summarize the algorithm flow in a clean code block.
7. Include relevant figures in the report using Markdown image syntax: ![description](./figure_XXX.png)
8. Output valid Markdown directly. Do NOT wrap the output in ```markdown code blocks."""

        user_prompt = f"""Please generate a structured Chinese reading report for the following paper:

**Title**: {title}
**Authors**: {authors}
**Abstract**: {abstract}

**Sections**:
{sections_combined}

**Figures**:
{figures_combined}

**Tables**:
{tables_combined}

**Algorithms**:
{algorithms_combined}

**Available images** (use these in the report with ![caption](./figure_XXX.png)):
{images_for_prompt}

Please generate the report in the following format:

# [Chinese Title]

## 论文概览
- **原始标题**: {title}
- **作者**: {authors}
- **核心贡献**:
  - (bullet points summarizing contributions)

## 研究背景与动机
(Summarize the problem, motivation, and related work)

## 方法
(Explain the core methodology, architecture, and key formulas. Keep formulas as $...$)

### 关键图表
(Include relevant figures here using ![description](./figure_XXX.png))

## 实验结果
### 主要结果
| 指标 | 数值/对比 | 备注 |
|------|----------|------|
| (extract key metrics from tables) |

### 关键发现
(Bullet points of key experimental findings)

## 伪代码
```python
# If algorithm available, rewrite in clean Python-like pseudocode
# Otherwise omit this section
```

## 总结
### 主要贡献
### 局限性
### 未来方向

Generate the complete Markdown report now:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._call(messages, temperature=1.0)

    def chat_about_paper(self, question: str, context: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Answer a question about the paper based on raw content."""
        messages = [
            {"role": "system", "content": "You are an academic research assistant. Answer the user's question based on the provided paper content. Be precise and cite specific sections or formulas when possible. Preserve LaTeX formulas in your response."},
            {"role": "user", "content": f"Paper content:\n{context}\n\nQuestion: {question}"},
        ]
        if history:
            # Insert history before the last user message
            messages = [messages[0]] + history + [messages[-1]]
        return self._call(messages, temperature=1.0)


llm_service = LLMService()
