"""
COMAC离线AI文档处理平台
简洁的Gradio界面
"""

import gradio as gr
from pathlib import Path

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)
(Path("temp/uploads")).mkdir(parents=True, exist_ok=True)
(Path("temp/outputs")).mkdir(parents=True, exist_ok=True)

from parsers.parser_factory import ParserFactory
from converters.converter_factory import ConverterFactory
from fillers.template_engine import TemplateEngine
from fillers.ai_fill_assistant import AIFillAssistant
from batch.batch_processor import BatchProcessor
from audit.sensitive_detector import SensitiveDetector
from audit.ai_auditor import AIAuditor

parser = ParserFactory()
converter = ConverterFactory()
detector = SensitiveDetector()
auditor = AIAuditor()
template_engine = TemplateEngine()
ai_fill = AIFillAssistant()

SUPPORTED_FORMATS = [".docx", ".doc", ".pdf", ".pptx", ".ppt", ".xlsx", ".xls", ".txt"]


def save_file(file_obj):
    if file_obj is None:
        return None
    upload_dir = Path("temp/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    if hasattr(file_obj, 'name'):
        filename = file_obj.name
    elif isinstance(file_obj, str):
        filename = file_obj
    elif hasattr(file_obj, 'orig_name'):
        filename = file_obj.orig_name
    else:
        filename = 'uploaded_file'

    ext = Path(filename).suffix
    unique_name = f"{len(list(upload_dir.glob('*')))}{ext}"
    save_path = upload_dir / unique_name

    with open(save_path, "wb") as f:
        if hasattr(file_obj, 'read'):
            content = file_obj.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
            f.write(content)
        elif isinstance(file_obj, bytes):
            f.write(file_obj)
        elif isinstance(file_obj, str) and Path(file_obj).exists():
            import shutil
            shutil.copy(file_obj, save_path)
        else:
            f.write(str(file_obj).encode('utf-8'))

    return str(save_path)


def summarize(file_obj):
    if file_obj is None:
        return "请先上传文档"
    try:
        file_path = save_file(file_obj)
        doc = parser.parse(file_path)
        content = doc.content[:8000]
        from ollama_client import OllamaClient, MODEL_DOC
        client = OllamaClient(MODEL_DOC)
        prompt = f"请总结以下文档的要点，字数控制在300字以内：\n\n{content}"
        summary = client.generate(prompt)
        return summary
    except Exception as e:
        return f"错误: {str(e)}"


def convert_file(file_obj, conversion_type):
    if file_obj is None:
        return "请先上传文档"
    try:
        file_path = save_file(file_obj)
        input_path = Path(file_path)
        conversions = {
            "Word -> PDF": (".docx", ".pdf"),
            "Word -> TXT": (".docx", ".txt"),
            "PDF -> TXT": (".pdf", ".txt"),
            "PPT -> PDF": (".pptx", ".pdf"),
            "Excel -> CSV": (".xlsx", ".csv"),
            "Excel -> PDF": (".xlsx", ".pdf"),
        }
        src_ext, dst_ext = conversions.get(conversion_type, (None, None))
        output_path = input_path.parent / f"{input_path.stem}_converted{dst_ext}"
        result = converter.convert(str(input_path), str(output_path))
        if result.success:
            return f"成功: {result.output_path}"
        else:
            return f"失败: {result.error}"
    except Exception as e:
        return f"错误: {str(e)}"


def detect_sensitive(file_obj):
    if file_obj is None:
        return "请先上传文档"
    try:
        file_path = save_file(file_obj)
        result = detector.detect_file(file_path)
        if result.is_clean:
            return "未检测到敏感信息"
        else:
            lines = [f"[{f.severity.upper()}] {f.category}: {f.matched_text}" for f in result.findings]
            return "发现敏感信息:\n" + "\n".join(lines)
    except Exception as e:
        return f"错误: {str(e)}"


def get_template_list():
    templates_dir = Path("templates")
    if not templates_dir.exists():
        return ["无模板"]
    templates = []
    for tpl in templates_dir.rglob("*.jinja2"):
        rel_path = tpl.relative_to(templates_dir)
        templates.append(str(rel_path).replace(".jinja2", ""))
    return templates if templates else ["无模板"]


def fill_template(template_name, data_text):
    if not template_name or template_name == "无模板":
        return "请选择有效模板"
    try:
        import json
        data = json.loads(data_text) if data_text.strip() else {}
        content = template_engine.render(template_name, data)
        output_path = Path("temp/outputs") / f"{template_name}_filled.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"填充成功: {content[:500]}..."
    except Exception as e:
        return f"错误: {str(e)}"


with gr.Blocks(title="COMAC AI文档处理") as app:
    gr.Markdown("# COMAC AI文档处理平台")
    gr.Markdown("*基于本地大模型 - 安全可靠*")

    with gr.Tabs():
        with gr.Tab("📄 文档摘要"):
            file1 = gr.File(label="上传文档", file_count="single", file_types=SUPPORTED_FORMATS)
            btn1 = gr.Button("生成摘要", variant="primary")
            out1 = gr.Textbox(label="摘要结果", lines=10)
            btn1.click(fn=summarize, inputs=file1, outputs=out1)

        with gr.Tab("🔄 格式转换"):
            file2 = gr.File(label="上传文档", file_count="single", file_types=SUPPORTED_FORMATS)
            conv_type = gr.Dropdown(
                choices=["Word -> PDF", "Word -> TXT", "PDF -> TXT", "PPT -> PDF", "Excel -> CSV", "Excel -> PDF"],
                label="转换类型",
                value="Word -> PDF"
            )
            btn2 = gr.Button("开始转换", variant="primary")
            out2 = gr.Textbox(label="转换结果", lines=4)
            btn2.click(fn=convert_file, inputs=[file2, conv_type], outputs=out2)

        with gr.Tab("✏️ 智能填充"):
            template_select = gr.Dropdown(choices=get_template_list(), label="选择模板")
            data_input = gr.Textbox(label="填充数据 (JSON)", lines=4, placeholder='{"key": "value"}')
            btn3 = gr.Button("智能填充", variant="primary")
            out3 = gr.Textbox(label="填充结果", lines=10)
            btn3.click(fn=fill_template, inputs=[template_select, data_input], outputs=out3)

        with gr.Tab("🔍 敏感检测"):
            file5 = gr.File(label="上传文档", file_count="single", file_types=SUPPORTED_FORMATS)
            btn5 = gr.Button("检测敏感信息", variant="primary")
            out5 = gr.Textbox(label="检测结果", lines=10)
            btn5.click(fn=detect_sensitive, inputs=file5, outputs=out5)

    gr.Markdown("---")
    gr.Markdown("*所有处理均在本地完成，数据不会上传*")

if __name__ == "__main__":
    print("Starting COMAC AI文档处理平台...")
    print("Access: http://localhost:7860")
    app.launch(server_name="0.0.0.0", server_port=7860, share=False, allowed_paths=["temp/"], show_error=True)
