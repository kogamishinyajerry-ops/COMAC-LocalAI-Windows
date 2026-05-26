"""
动画/MG展示生成器
生成动画脚本、SVG动画和交互式展示
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class Animated展示Generator:
    """
    动画展示生成器 - 生成动画脚本和SVG动画
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_svg_animated_flowchart(
        self,
        title: str,
        nodes: List[Dict],
        connections: List[tuple],
        filename: str = "flowchart.svg"
    ) -> str:
        """
        生成SVG动画流程图

        Args:
            title: 图表标题
            nodes: 节点列表 [{"id": "...", "label": "...", "x": 0, "y": 0, "color": "#0066CC"}]
            connections: 连接关系 [(from_id, to_id), ...]
            filename: 输出文件名
        """
        # SVG尺寸
        width, height = 800, 600
        node_width, node_height = 120, 60

        svg_parts = [
            f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
    <defs>
        <style>
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: scale(0.8); }}
                to {{ opacity: 1; transform: scale(1); }}
            }}
            @keyframes drawLine {{
                from {{ stroke-dashoffset: 100; }}
                to {{ stroke-dashoffset: 0; }}
            }}
            .node {{
                animation: fadeIn 0.5s ease-out forwards;
                opacity: 0;
            }}
            .arrow {{
                stroke-dasharray: 100;
                animation: drawLine 0.8s ease-out forwards;
                stroke-dashoffset: 100;
            }}
            text {{ font-family: "Microsoft YaHei", sans-serif; }}
            title {{ font-size: 24px; font-weight: bold; fill: #333; }}
            .node-label {{ font-size: 14px; fill: #fff; text-anchor: middle; dominant-baseline: middle; }}
            .node-title {{ font-size: 12px; fill: #ccc; text-anchor: middle; }}
        </style>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#666"/>
        </marker>
    </defs>

    <!-- 背景 -->
    <rect width="{width}" height="{height}" fill="#f8f9fa"/>

    <!-- 标题 -->
    <text x="{width//2}" y="30" text-anchor="middle" class="title">{title}</text>
'''
        ]

        # 绘制连接线
        node_map = {n["id"]: (n["x"], n["y"]) for n in nodes}
        for i, (from_id, to_id) in enumerate(connections):
            if from_id in node_map and to_id in node_map:
                x1, y1 = node_map[from_id]
                x2, y2 = node_map[to_id]
                delay = i * 0.15
                svg_parts.append(
                    f'    <line class="arrow" x1="{x1}" y1="{y1 + node_height//2}" '
                    f'x2="{x2}" y2="{y2 + node_height//2}" '
                    f'stroke="#666" stroke-width="2" marker-end="url(#arrowhead)" '
                    f'style="animation-delay: {delay}s"/>'
                )

        # 绘制节点
        colors = ["#0066CC", "#7c3aed", "#00d4ff", "#00ff88", "#ffa502"]
        for i, node in enumerate(nodes):
            x, y = node["x"], node["y"]
            color = node.get("color", colors[i % len(colors)])
            delay = i * 0.1

            svg_parts.append(
                f'    <g class="node" style="animation-delay: {delay}s">\n'
                f'        <rect x="{x - node_width//2}" y="{y}" '
                f'width="{node_width}" height="{node_height}" rx="8" '
                f'fill="{color}" stroke="{color}" stroke-width="1"/>\n'
                f'        <text x="{x}" y="{y + node_height//2 - 8}" '
                f'class="node-label">{node.get("label", node["id"])}</text>\n'
                f'        <text x="{x}" y="{y + node_height//2 + 12}" '
                f'class="node-title">{node.get("title", "")}</text>\n'
                f'    </g>'
            )

        svg_parts.append('</svg>')

        svg_content = '\n'.join(svg_parts)
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        return str(output_path)

    def generate_motion_graphics_script(
        self,
        scenes: List[Dict],
        filename: str = "mg_script.json"
    ) -> str:
        """
        生成MG动画脚本（可用于Lottie/AE等工具）

        Args:
            scenes: 场景列表，每个场景包含 duration, elements 等
            filename: 输出文件名
        """
        script = {
            "version": "1.0",
            "title": "商飞离线AI平台演示",
            "created": datetime.now().isoformat(),
            "scenes": scenes
        }

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)

        return str(output_path)

    def generate_html_animated_presentation(
        self,
        title: str,
        slides: List[Dict],
        filename: str = "animated_presentation.html"
    ) -> str:
        """
        生成HTML动画演示文稿

        Args:
            title: 演示标题
            slides: 幻灯片列表
            filename: 输出文件名
        """
        html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            overflow: hidden;
        }

        .presentation {
            width: 100vw;
            height: 100vh;
            position: relative;
        }

        .slide {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 60px;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.5s ease, visibility 0.5s ease;
        }

        .slide.active {
            opacity: 1;
            visibility: visible;
        }

        .slide-content {
            max-width: 1000px;
            width: 100%;
        }

        h1 {
            font-size: 3.5em;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 30px;
        }

        h2 {
            font-size: 2.5em;
            color: #00d4ff;
            margin-bottom: 25px;
        }

        p {
            font-size: 1.4em;
            line-height: 1.8;
            color: #ccc;
            margin-bottom: 15px;
        }

        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-top: 30px;
        }

        .feature-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }

        .feature-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,212,255,0.2);
        }

        .feature-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }

        .feature-title {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #fff;
        }

        .feature-desc {
            font-size: 1em;
            color: #a0a0a0;
        }

        .timeline {
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-top: 30px;
        }

        .timeline-item {
            display: flex;
            align-items: center;
            gap: 20px;
            opacity: 0;
            transform: translateX(-30px);
            animation: slideIn 0.5s ease-out forwards;
        }

        @keyframes slideIn {
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        .timeline-number {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.2em;
            flex-shrink: 0;
        }

        .timeline-content {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 12px;
            flex-grow: 1;
        }

        .controls {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 15px;
            z-index: 100;
        }

        .btn {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: #fff;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
        }

        .btn:hover {
            background: rgba(0,212,255,0.3);
            border-color: #00d4ff;
        }

        .progress-bar {
            position: fixed;
            top: 0;
            left: 0;
            height: 3px;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            transition: width 0.3s;
            z-index: 100;
        }

        .slide-counter {
            position: fixed;
            bottom: 30px;
            right: 30px;
            font-size: 0.9em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="progress-bar" id="progress"></div>

    <div class="presentation" id="presentation">
        {slides_html}
    </div>

    <div class="controls">
        <button class="btn" onclick="prevSlide()">上一页</button>
        <button class="btn" onclick="nextSlide()">下一页</button>
    </div>

    <div class="slide-counter" id="counter">1 / {total}</div>

    <script>
        let current = 0;
        const slides = document.querySelectorAll('.slide');
        const total = slides.length;

        function showSlide(n) {
            slides.forEach((s, i) => {
                s.classList.remove('active');
                if (i === n) {
                    s.classList.add('active');
                    // 重触发动画
                    s.querySelectorAll('.timeline-item').forEach((item, j) => {
                        item.style.animation = 'none';
                        item.offsetHeight;
                        item.style.animation = `slideIn 0.5s ease-out ${j * 0.15}s forwards`;
                    });
                }
            });
            document.getElementById('counter').textContent = `${n + 1} / ${total}`;
            document.getElementById('progress').style.width = `${((n + 1) / total) * 100}%`;
        }

        function nextSlide() {
            current = (current + 1) % total;
            showSlide(current);
        }

        function prevSlide() {
            current = (current - 1 + total) % total;
            showSlide(current);
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
        });

        showSlide(0);
    </script>
</body>
</html>
'''

        slides_html = []
        for i, slide in enumerate(slides):
            slides_html.append(f'<div class="slide{" active" if i == 0 else ""}">')
            slides_html.append(f'<div class="slide-content">{slide.get("content", "")}</div>')
            slides_html.append('</div>')

        html = html_template.format(
            title=title,
            slides_html='\n'.join(slides_html),
            total=len(slides)
        )

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return str(output_path)

    def create_demo_flow_visualization(
        self,
        title: str = "文档处理流程",
        filename: str = "flow_demo.html"
    ) -> str:
        """
        创建交互式流程演示

        Args:
            title: 演示标题
            filename: 输出文件名
        """
        nodes = [
            {"id": "input", "label": "文档输入", "title": "支持多种格式", "x": 100, "y": 50, "color": "#0066CC"},
            {"id": "parse", "label": "智能解析", "title": "OCR + 结构化", "x": 280, "y": 50, "color": "#7c3aed"},
            {"id": "classify", "label": "分类识别", "title": "AI 自动分类", "x": 460, "y": 50, "color": "#00d4ff"},
            {"id": "extract", "label": "关键提取", "title": "实体 + 关系", "x": 640, "y": 50, "color": "#00ff88"},
            {"id": "output", "label": "结构化输出", "title": "JSON/表格", "x": 640, "y": 150, "color": "#ffa502"},
        ]

        connections = [
            ("input", "parse"),
            ("parse", "classify"),
            ("classify", "extract"),
            ("extract", "output"),
        ]

        return self.generate_svg_animated_flowchart(title, nodes, connections, filename)


def create_sample_presentation(output_dir: str = "outputs") -> dict:
    """
    创建示例动画演示

    Returns:
        dict: 生成的各个文件的路径
    """
    gen = Animated展示Generator(output_dir)

    slides = [
        {
            "content": '''
                <h1>商飞离线AI文档处理平台</h1>
                <p style="text-align:center;margin-top:40px;">安全 · 高效 · 智能</p>
                <p style="text-align:center;color:#666;margin-top:60px;">物理断网环境下的AI赋能解决方案</p>
            '''
        },
        {
            "content": '''
                <h2>核心功能</h2>
                <div class="feature-grid">
                    <div class="feature-card">
                        <div class="feature-icon">📄</div>
                        <div class="feature-title">智能解析</div>
                        <div class="feature-desc">支持PDF、Word、图片等格式自动解析</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">🎯</div>
                        <div class="feature-title">精准提取</div>
                        <div class="feature-desc">关键信息自动识别与结构化提取</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">🔒</div>
                        <div class="feature-title">安全可靠</div>
                        <div class="feature-desc">全离线运行，数据不出内网</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">⚡</div>
                        <div class="feature-title">批量处理</div>
                        <div class="feature-desc">支持大批量文档自动化处理</div>
                    </div>
                </div>
            '''
        },
        {
            "content": '''
                <h2>技术架构</h2>
                <div class="timeline">
                    <div class="timeline-item">
                        <div class="timeline-number">1</div>
                        <div class="timeline-content">
                            <strong>文档输入</strong><br>
                            多格式支持：PDF、Word、Excel、图片
                        </div>
                    </div>
                    <div class="timeline-item">
                        <div class="timeline-number">2</div>
                        <div class="timeline-content">
                            <strong>智能解析层</strong><br>
                            OCR识别 + 布局分析 + 结构化提取
                        </div>
                    </div>
                    <div class="timeline-item">
                        <div class="timeline-number">3</div>
                        <div class="timeline-content">
                            <strong>AI模型层</strong><br>
                            Ollama + Qwen/DeepSeek 离线大模型
                        </div>
                    </div>
                    <div class="timeline-item">
                        <div class="timeline-number">4</div>
                        <div class="timeline-content">
                            <strong>应用输出层</strong><br>
                            摘要、表格、报告、批量导出
                        </div>
                    </div>
                </div>
            '''
        },
        {
            "content": '''
                <h2>部署方案</h2>
                <div class="feature-grid">
                    <div class="feature-card">
                        <div class="feature-icon">🏢</div>
                        <div class="feature-title">单机部署</div>
                        <div class="feature-desc">适用于小规模团队</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">🏭</div>
                        <div class="feature-title">集群部署</div>
                        <div class="feature-desc">支持高并发多用户</div>
                    </div>
                </div>
                <p style="margin-top:40px;text-align:center;color:#666;">
                    根据业务规模灵活选择部署方案
                </p>
            '''
        }
    ]

    results = {
        "html_presentation": gen.generate_html_animated_presentation(
            "商飞离线AI文档处理平台", slides, "demo_presentation.html"
        ),
        "flow_svg": gen.create_demo_flow_visualization(),
        "mg_script": gen.generate_motion_graphics_script([
            {
                "scene_id": 1,
                "duration": 3,
                "elements": [
                    {"type": "text", "content": "商飞离线AI平台", "animation": "fadeIn"}
                ]
            }
        ])
    }

    return results
