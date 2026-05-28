#!/usr/bin/env python3
"""
断网前验证脚本
检查所有组件是否就绪
"""

import sys
from pathlib import Path

def check_ollama():
    """检查 Ollama 服务"""
    print("\n=== 1. Ollama 服务检查 ===")
    try:
        import ollama
        response = ollama.list()
        print(f"✅ Ollama 已连接")

        # ollama.list() 返回 ListResponse，使用 .models 属性
        models_data = getattr(response, 'models', []) or []
        model_names = []
        for m in models_data:
            if hasattr(m, 'model'):
                model_names.append(m.model)
            elif isinstance(m, dict):
                model_names.append(m.get('name', '') or m.get('model', ''))
            elif isinstance(m, str):
                model_names.append(m)

        required = ['qwen:7b-q4_K_M']

        for model in required:
            if model in model_names:
                print(f"   ✅ {model} 已加载")
            else:
                print(f"   ⚠️  {model} 未加载（请确认 ollama-models\\ 下有 GGUF 文件并运行 setup.bat）")

        return True
    except Exception as e:
        print(f"❌ Ollama 连接失败: {e}")
        print("   请运行: install-offline.bat 或 setup.bat")
        return False

def check_models():
    """检查模型是否可用"""
    print("\n=== 2. 模型功能测试 ===")
    try:
        from ollama_client import OllamaClient, MODEL_DOC

        # 测试单一 7B 模型
        for model, name in [(MODEL_DOC, MODEL_DOC)]:
            try:
                client = OllamaClient(model)
                result = client.generate("你好", num_predict=50)
                if result and len(result) > 0:
                    print(f"   ✅ {name} 响应正常")
                else:
                    print(f"   ⚠️  {name} 返回为空")
            except Exception as e:
                print(f"   ❌ {name} 调用失败: {e}")

        return True
    except Exception as e:
        print(f"❌ 模型检查失败: {e}")
        return False

def check_modules():
    """检查所有模块导入"""
    print("\n=== 3. 模块完整性检查 ===")
    modules = [
        ("parsers", ["ParserFactory"]),
        ("converters", ["ConverterFactory"]),
        ("fillers", ["TemplateEngine", "AIFillAssistant"]),
        ("batch", ["BatchProcessor", "BatchSummarizer"]),
        ("audit", ["SensitiveDetector", "AIAuditor"]),
        ("presentations", ["HTMLReportGenerator", "PPTGenerator", "Animated展示Generator"]),
    ]

    all_ok = True
    for module_name, expected in modules:
        try:
            module = __import__(module_name, fromlist=expected)
            missing = [n for n in expected if not hasattr(module, n)]
            if missing:
                print(f"   ⚠️  {module_name}: 缺少 {missing}")
                all_ok = False
            else:
                print(f"   ✅ {module_name}")
        except ImportError as e:
            print(f"   ❌ {module_name}: 导入失败 - {e}")
            all_ok = False

    return all_ok

def check_app():
    """检查 app.py 语法"""
    print("\n=== 4. 应用入口检查 ===")
    try:
        with open("app.py", "r") as f:
            compile(f.read(), "app.py", "exec")
        print("   ✅ app.py 语法正确")

        with open("ollama_client.py", "r") as f:
            compile(f.read(), "ollama_client.py", "exec")
        print("   ✅ ollama_client.py 语法正确")

        return True
    except SyntaxError as e:
        print(f"   ❌ 语法错误: {e}")
        return False

def check_dependencies():
    """检查依赖包"""
    print("\n=== 5. 依赖包检查 ===")
    required = [
        "gradio", "docx", "pptx", "pandas", "openpyxl",
        "pdfplumber", "fitz", "jinja2", "ollama"
    ]

    all_ok = True
    for pkg in required:
        try:
            __import__(pkg)
            print(f"   ✅ {pkg}")
        except ImportError:
            print(f"   ❌ {pkg} 未安装（运行: pip install -r requirements.txt）")
            all_ok = False

    return all_ok

def check_directories():
    """检查必要目录"""
    print("\n=== 6. 目录结构检查 ===")
    dirs = ["temp/uploads", "temp/outputs", "templates", "static"]
    all_ok = True
    for d in dirs:
        path = Path(d)
        if path.exists():
            print(f"   ✅ {d}")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"   ⚠️  {d} 不存在，已创建")

    return all_ok

def check_ocr_tools():
    """检查 OCR 工具"""
    print("\n=== 7. OCR 工具检查 ===")
    ocr_dir = Path.home() / "ollama-doc-models"

    if not ocr_dir.exists():
        print(f"   ⚠️  ~/ollama-doc-models 不存在")
        return False

    ocrtext = ocr_dir / "ocrtext"
    pdfocr = ocr_dir / "pdfocr.sh"

    if ocrtext.exists():
        print(f"   ✅ ocrtext 存在")
    else:
        print(f"   ⚠️  ocrtext 不存在（图片OCR不可用）")

    if pdfocr.exists():
        print(f"   ✅ pdfocr.sh 存在")
    else:
        print(f"   ⚠️  pdfocr.sh 不存在（PDF OCR不可用）")

    return True

def check_ollama_models_env():
    """检查 OLLAMA_MODELS 是否指向项目内目录"""
    print("\n=== 8. OLLAMA_MODELS 环境变量检查 ===")
    import os
    ollama_models = os.environ.get("OLLAMA_MODELS", "")
    if not ollama_models:
        print("   ⚠️  OLLAMA_MODELS 环境变量未设置（默认使用 %APPDATA% 目录）")
        return False
    if "ollama-cache" in ollama_models:
        print(f"   ✅ OLLAMA_MODELS = {ollama_models} (项目内)")
        return True
    print(f"   ⚠️  OLLAMA_MODELS = {ollama_models} (可能不是项目内目录)")
    return False

def check_libreoffice():
    """检查 LibreOffice 是否可用"""
    print("\n=== 9. LibreOffice 可用性检查 ===")
    try:
        from converters.converter_factory import ConverterFactory
        converter = ConverterFactory()
        if converter.libreoffice is not None:
            print("   ✅ LibreOffice 可用")
            return True
        else:
            print("   ⚠️  LibreOffice 不可用（PDF 转换功能受限）")
            return False
    except Exception as e:
        print(f"   ⚠️  LibreOffice 检测失败: {e}")
        return False

def main():
    print("=" * 50)
    print("COMAC 离线AI平台 - 断网前验证")
    print("=" * 50)

    results = []

    results.append(("Ollama服务", check_ollama()))
    results.append(("模型功能", check_models()))
    results.append(("模块完整", check_modules()))
    results.append(("应用语法", check_app()))
    results.append(("依赖包", check_dependencies()))
    results.append(("目录结构", check_directories()))
    results.append(("OCR工具", check_ocr_tools()))
    results.append(("OLLAMA_MODELS环境变量", check_ollama_models_env()))
    results.append(("LibreOffice", check_libreoffice()))

    print("\n" + "=" * 50)
    print("验证结果汇总")
    print("=" * 50)

    for name, ok in results:
        status = "✅ 通过" if ok else "⚠️  异常"
        print(f"   {name}: {status}")

    all_ok = all(r[1] for r in results)

    print("\n" + "=" * 50)
    if all_ok:
        print("✅ 所有检查通过，可以断网测试")
        print("\n启动命令:")
        print("   1. 运行 install-offline.bat 或 setup.bat")
        print("   2. 从 .venv\\Scripts\\python.exe app.py 启动")
        print("   3. 访问 http://localhost:7860")
    else:
        print("⚠️  部分检查异常，修复后再断网测试")
        print("\n常见问题解决:")
        print("   - 模型未加载: 确保 ollama-models\\ 下有 GGUF 文件，运行 setup.bat")
        print("   - 依赖缺失: 运行 install-offline.bat（离线）或 pip install -r requirements.txt（在线）")
        print("   - Ollama未运行: 运行 setup.bat 或 start.bat")
    print("=" * 50)

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
