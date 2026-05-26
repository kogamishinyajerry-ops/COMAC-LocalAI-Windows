# -*- mode: python ; coding: utf-8 -*-
"""
COMAC-LocalAI-Windows PyInstaller Spec File
构建独立 Windows 可执行文件
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

# 项目根目录 (SPEC 是 PyInstaller 全局变量 = spec 文件的绝对路径)
PROJECT_ROOT = Path(SPEC).parent.resolve()
APP_NAME = "COMAC-LocalAI"
MAIN_SCRIPT = "app.py"

# ============================================================================
# 隐藏导入 — 所有 PyInstaller 无法自动检测的模块
# ============================================================================
hidden_imports = [
    # Gradio 核心
    'gradio', 'gradio.blocks', 'gradio.components', 'gradio.templates', 'gradio.flagging',
    # Gradio 额外依赖
    'aiohttp', 'aiohttp.http', 'aiohttp.client', 'aiohttp.web',
    'websockets', 'websockets.client', 'websockets.server',
    'httpx', 'httpx._client', 'httpx._models',
    'markdown', 'markdown.core', 'markdown.extensions',
    'yaml', 'yaml.cyaml', 'yaml.loader',
    'pydantic', 'pydantic.main', 'pydantic.fields',
    'python_multipart', 'multipart',
    # Ollama
    'ollama', 'ollama_client',
    # 数据处理 + 图像处理
    'pandas', 'openpyxl', 'xlsxwriter',
    'docx', 'pptx',
    'PIL', 'PIL._imaging', 'PIL.Image', 'PIL.ImageOps', 'PIL.ImageDraw', 'PIL.ImageFont',
    'Pillow',
    # PDF 处理
    'pdfplumber', 'fitz',
    # 模板引擎
    'jinja2', 'markupsafe',
    # 数学/科学计算
    'numpy', 'numpy.random', 'numpy.fft',
    # 文件监控
    'watchdog', 'watchdog.observers',
    # XML处理
    'lxml', 'lxml.etree',
    # 配色输出
    'colorama',
    # JSON
    'json', 'json.decoder', 'json.encoder',
    # 本地模块
    'parsers', 'parsers.parser_factory',
    'parsers.pdf_parser', 'parsers.docx_parser',
    'parsers.excel_parser', 'parsers.pptx_parser',
    'parsers.txt_parser', 'parsers.base_parser',
    'converters', 'converters.converter_factory',
    'converters.native_converter', 'converters.libreoffice_converter',
    'converters.base_converter',
    'fillers', 'fillers.template_engine',
    'fillers.ai_fill_assistant', 'fillers.batch_filler',
    'audit', 'audit.sensitive_detector',
    'audit.ai_auditor', 'audit.document_diff', 'audit.template_checker',
    'batch', 'batch.batch_processor',
    'batch.batch_converter', 'batch.batch_summarizer', 'batch.task_history',
    'blocks',
    'knowledge_classifier', 'knowledge_graph',
    'ollama_rag', 'report_generator', 'excel_styler',
    'comac_assistant', 'enhanced_assistant',
    'cli_chat', 'task_manager',
    # Jinja2 依赖
    'pytz', 'babel',
    # openpyxl 依赖
    'et_xmlfile',
    # docx 依赖
    'typing_extensions',
    # pdfplumber 依赖
    'pdfminer', 'pdfminer.high_level', 'pdfminer.pdfpage',
    'pdfminer.pdfparser', 'pdfminer.pdfdocument',
]

# ============================================================================
# 数据文件 — 模板、静态资源、配置
# ============================================================================
datas = [
    # 模板目录
    (str(PROJECT_ROOT / 'templates'), 'templates'),
    # 静态资源
    (str(PROJECT_ROOT / 'static'), 'static'),
    # Blocks 模块
    (str(PROJECT_ROOT / 'blocks'), 'blocks'),
    # 配置文件
    (str(PROJECT_ROOT / 'config.py'), '.'),
    (str(PROJECT_ROOT / 'models.json'), '.'),
    (str(PROJECT_ROOT / 'requirements.txt'), '.'),
    # 自动收集所有包的数据文件（修复 version.txt 等缺失问题）
] + collect_data_files('safehttpx') + collect_data_files('groovy') + collect_data_files('gradio')

# 可选的培训材料
training_dir = PROJECT_ROOT / 'training-materials'
if training_dir.exists():
    datas.append((str(training_dir), 'training-materials'))

# ============================================================================
# 排除项 — 减小体积
# ============================================================================
excludes = [
    'matplotlib', 'scipy', 'sklearn', 'torch', 'transformers',
    'tkinter', 'test', 'unittest',
    'pyodbc', 'odbc', 'sqlite3',
]

# ============================================================================
# 构建配置
# ============================================================================
a = Analysis(
    [MAIN_SCRIPT],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ============================================================================
# 合并所有依赖为单一可执行文件
# ============================================================================
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 保留控制台以便查看错误日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # 可设置 icon.ico
)
