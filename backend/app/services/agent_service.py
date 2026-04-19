"""Paper Reading Agent — built on kosong (the engine behind kimi-cli)."""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional

from kosong.contrib.chat_provider.openai_legacy import OpenAILegacy
from kosong import Message, step, ToolResult

def tool_result_to_message(result: ToolResult) -> Message:
    return Message(
        role="tool",
        tool_call_id=result.tool_call_id,
        content=result.return_value.output,
    )
from kosong.message import ImageURLPart, TextPart
from kosong.tooling import CallableTool2, ToolOk, ToolReturnValue
from kosong.tooling.simple import SimpleToolset
from pydantic import BaseModel, Field

from app.config import settings
from app.logger import setup_logger

logger = setup_logger("agent")

SYSTEM_PROMPT = """你是学术论文阅读助手。你的任务是阅读一篇 arXiv 论文的 LaTeX 源码，并生成一份结构化中文阅读报告。

工作方式：
1. 你可以使用 read_section 工具读取论文的任意 section 的完整内容
2. 你可以使用 view_image 工具查看论文中的图片（多模态理解）
3. 当你收集到足够信息后，调用 write_report 工具生成最终报告并结束任务

阅读策略：
- 先读标题、摘要和目录结构，了解论文主题
- 根据重要性选择 section 阅读（通常 Introduction、Method、Experiments 最重要）
- 不要一次性读取所有 section，逐步深入
- 看到复杂的架构图或实验结果时，调用 view_image 查看图片
- 理解图片与文本的对应关系，在报告中恰当引用

报告格式要求：
- 使用中文撰写，学术术语可保留英文
- 保留数学公式 $...$ 和 $$...$$
- 引用图片时使用 Markdown 语法: ![描述](/images/{arxiv_id}/文件名.png)
- 输出纯 Markdown，不要用 ```markdown 代码块包裹
- 结构包含：研究背景、方法概述、核心贡献、实验结果、总结

注意：
- 不要编造内容，只基于你实际阅读的内容生成报告
- 如果某部分信息不足，如实说明
"""


# ── Tool Parameters ──────────────────────────────────────────

class ReadSectionParams(BaseModel):
    section_title: str = Field(description="Title of the section to read")


class ViewImageParams(BaseModel):
    image_filename: str = Field(description="Filename of the image to view")


class WriteReportParams(BaseModel):
    report_md: str = Field(description="The final structured reading report in Markdown")


# ── Tools ─────────────────────────────────────────────────────

class ReadSectionTool(CallableTool2[ReadSectionParams]):
    name: str = "read_section"
    params: type[ReadSectionParams] = ReadSectionParams
    description: str = "Read the full content of a specific paper section"

    def __init__(self, sections: Dict[str, str]):
        super().__init__()
        self.sections = sections

    async def __call__(self, params: ReadSectionParams) -> ToolReturnValue:
        content = self.sections.get(params.section_title)
        if content is None:
            available = "\n".join(f"- {k}" for k in self.sections.keys())
            return ToolOk(
                output=f"Section '{params.section_title}' not found.\n\nAvailable sections:\n{available}"
            )
        return ToolOk(output=f"Section: {params.section_title}\n\n{content}")


class ViewImageTool(CallableTool2[ViewImageParams]):
    name: str = "view_image"
    params: type[ViewImageParams] = ViewImageParams
    description: str = "View an image from the paper. Returns the image for multimodal understanding."

    def __init__(self, image_dir: Path, image_map: Dict[str, Dict[str, str]]):
        super().__init__()
        self.image_dir = image_dir
        self.image_map = image_map

    async def __call__(self, params: ViewImageParams) -> ToolReturnValue:
        img_path = self.image_dir / params.image_filename
        if not img_path.exists():
            available = "\n".join(f"- {k}" for k in self.image_map.keys())
            return ToolOk(
                output=f"Image '{params.image_filename}' not found.\n\nAvailable images:\n{available}"
            )

        # Read image and encode as base64
        image_data = img_path.read_bytes()
        b64 = base64.b64encode(image_data).decode("utf-8")
        mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
        url = f"data:{mime};base64,{b64}"

        meta = self.image_map.get(params.image_filename, {})
        caption = meta.get("caption", "")
        label = meta.get("label", "")

        text = f"Image: {params.image_filename}"
        if caption:
            text += f"\nCaption: {caption}"
        if label:
            text += f"\nLabel: {label}"

        # Return both text description and the actual image
        return ToolOk(output=[TextPart(text=text), ImageURLPart(image_url={"url": url})])


class WriteReportTool(CallableTool2[WriteReportParams]):
    name: str = "write_report"
    params: type[WriteReportParams] = WriteReportParams
    description: str = "Write the final structured reading report and finish the task"

    def __init__(self):
        super().__init__()
        self.report: Optional[str] = None

    async def __call__(self, params: WriteReportParams) -> ToolReturnValue:
        self.report = params.report_md
        return ToolOk(output="Report has been written successfully. The task is complete.")


# ── Agent ─────────────────────────────────────────────────────

class PaperAgent:
    """An agent that reads a paper incrementally and produces a report."""

    def __init__(
        self,
        arxiv_id: str,
        parsed: Dict[str, Any],
        image_dir: Path,
        image_paths: List[Path],
    ):
        self.arxiv_id = arxiv_id
        self.parsed = parsed
        self.image_dir = image_dir
        self.image_paths = image_paths
        self.max_steps = 30

        # Build section map (title -> content)
        self.sections: Dict[str, str] = {}
        for s in parsed.get("sections", []):
            title = s.get("title", "").strip()
            content = s.get("content", "").strip()
            if title:
                self.sections[title] = content

        # Build image metadata map (filename -> {caption, label})
        self.image_map: Dict[str, Dict[str, str]] = {}
        figures = parsed.get("figures", [])
        for i, p in enumerate(image_paths):
            meta = {"caption": "", "label": ""}
            if i < len(figures):
                meta["caption"] = figures[i].get("caption", "")
                meta["label"] = figures[i].get("label", "")
            self.image_map[p.name] = meta

        # Create LLM provider
        # reasoning_key="reasoning_content" is required for Kimi K2.5 thinking mode
        self.provider = OpenAILegacy(
            model=settings.moonshot_model,
            api_key=settings.moonshot_api_key,
            base_url=settings.moonshot_base_url,
            reasoning_key="reasoning_content",
        )

        # Create tools
        self.write_tool = WriteReportTool()
        self.toolset = SimpleToolset([
            ReadSectionTool(self.sections),
            ViewImageTool(self.image_dir, self.image_map),
            self.write_tool,
        ])

    def _build_initial_prompt(self) -> str:
        title = self.parsed.get("title", "")
        authors = ", ".join(a.get("name", "") for a in self.parsed.get("authors", []))
        abstract = self.parsed.get("abstract", "")

        sections_list = "\n".join(f"- {t}" for t in self.sections.keys())
        images_list = "\n".join(
            f"- {p.name} ({self.image_map.get(p.name, {}).get('caption', 'no caption')})"
            for p in self.image_paths
        )

        return f"""请阅读以下论文并生成结构化中文阅读报告。

**论文标题**: {title}
**作者**: {authors}
**摘要**: {abstract}

**可用 Section**（你可以用 read_section 工具读取任意 section 的完整内容）:
{sections_list}

**可用图片**（你可以用 view_image 工具查看）:
{images_list}

请逐步阅读论文，先了解整体结构，再深入关键 section，必要时查看图片理解图-文关系，最后生成报告。
注意：不要一次性读取所有 section，根据重要性选择。报告中引用图片时使用路径 `/images/{self.arxiv_id}/<filename>`。
"""

    async def run(self) -> str:
        """Run the agent loop and return the generated report."""
        history: List[Message] = [
            Message(role="user", content=self._build_initial_prompt())
        ]

        for step_no in range(1, self.max_steps + 1):
            logger.info(f"[{self.arxiv_id}] Agent step {step_no}/{self.max_steps}")

            result = await step(
                self.provider,
                SYSTEM_PROMPT,
                self.toolset,
                history,
            )

            # Append assistant message
            history.append(result.message)

            # Check if report was written via tool call
            if self.write_tool.report is not None:
                logger.info(f"[{self.arxiv_id}] Report written at step {step_no}")
                return self.write_tool.report

            if not result.tool_calls:
                # No tool calls — model output text directly
                # If it looks like a report (has markdown headers), use it
                text = result.message.extract_text(" ") if hasattr(result.message, "extract_text") else str(result.message.content)
                if isinstance(text, str) and text.strip().startswith("#"):
                    logger.info(f"[{self.arxiv_id}] Model output looks like a report, using it")
                    return text.strip()
                # Otherwise continue the loop
                continue

            # Execute tools and append results
            tool_results = await result.tool_results()
            for tr in tool_results:
                history.append(tool_result_to_message(tr))
                logger.info(
                    f"[{self.arxiv_id}] Tool {tr.tool_call_id} -> "
                    f"{'error' if tr.return_value.is_error else 'ok'}"
                )
                if tr.tool_call_id.startswith("write_report"):
                    if self.write_tool.report:
                        return self.write_tool.report

        # Max steps reached
        logger.warning(f"[{self.arxiv_id}] Agent reached max steps ({self.max_steps})")
        # Try to extract any report-like content from the last assistant message
        last_assistant = None
        for msg in reversed(history):
            if msg.role == "assistant":
                last_assistant = msg
                break
        if last_assistant:
            text = last_assistant.extract_text(" ") if hasattr(last_assistant, "extract_text") else str(last_assistant.content)
            if isinstance(text, str):
                return text.strip()
        return "Agent failed to generate a report within the maximum number of steps."


# ── Public API ────────────────────────────────────────────────

async def generate_report_with_agent(
    arxiv_id: str,
    parsed: Dict[str, Any],
    image_dir: Path,
    image_paths: List[Path],
) -> str:
    """High-level entry point: run the paper reading agent."""
    agent = PaperAgent(arxiv_id, parsed, image_dir, image_paths)
    return await agent.run()
