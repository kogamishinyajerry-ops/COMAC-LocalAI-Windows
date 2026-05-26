"""
HTML报告生成器
基于模板和数据生成可视化HTML报告
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class HTMLReportGenerator:
    """
    HTML报告生成器 - 将处理结果生成为可视化HTML报告
    """

    DEFAULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {style}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{header_title}</h1>
            <p class="subtitle">{subtitle}</p>
            <div class="meta">
                <span>生成时间: {timestamp}</span>
                <span>状态: {status}</span>
            </div>
        </div>

        <div class="content">
            {content}
        </div>

        <div class="footer">
            <p>{footer}</p>
        </div>
    </div>
</body>
</html>
"""

    DEFAULT_STYLE = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #a0a0a0; margin-bottom: 15px; }
        .meta { display: flex; justify-content: center; gap: 20px; }
        .meta span { background: rgba(124,58,237,0.2); padding: 5px 15px; border-radius: 15px; font-size: 0.85em; }
        .content { background: rgba(255,255,255,0.05); border-radius: 16px; padding: 30px; }
        .section { margin-bottom: 25px; }
        .section h2 { color: #00d4ff; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .card { background: rgba(0,0,0,0.2); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
        .card-title { font-weight: bold; margin-bottom: 10px; color: #fff; }
        .card-content { color: #a0a0a0; line-height: 1.6; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 0.8em; }
        .badge-success { background: rgba(0,255,136,0.2); color: #00ff88; }
        .badge-warning { background: rgba(255,165,2,0.2); color: #ffa502; }
        .badge-error { background: rgba(255,71,87,0.2); color: #ff4757; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { color: #7c3aed; }
        .footer { text-align: center; padding: 30px; color: #666; font-size: 0.85em; }
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_summary_report(
        self,
        title: str,
        data: Dict[str, Any],
        filename: Optional[str] = None
    ) -> str:
        """
        生成摘要报告

        Args:
            title: 报告标题
            data: 包含 summary, key_points, statistics 等字段
            filename: 输出文件名
        """
        if filename is None:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        content = self._build_summary_content(data)

        html = self.DEFAULT_TEMPLATE.format(
            title=title,
            header_title=title,
            subtitle=data.get("subtitle", ""),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            status=data.get("status", "已完成"),
            style=self.DEFAULT_STYLE,
            content=content,
            footer="商飞离线AI文档处理平台 - 自动生成"
        )

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return str(output_path)

    def _build_summary_content(self, data: Dict) -> str:
        """构建摘要报告内容"""
        html_parts = []

        # 概述
        if "summary" in data:
            html_parts.append(f'''
            <div class="section">
                <h2>📋 概述</h2>
                <div class="card">
                    <div class="card-content">{data["summary"]}</div>
                </div>
            </div>
            ''')

        # 关键指标
        if "key_metrics" in data:
            metrics_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;">'
            for metric in data["key_metrics"]:
                metrics_html += f'''
                <div class="card" style="text-align:center;">
                    <div style="font-size:2em;color:#00d4ff;">{metric.get("value", "-")}</div>
                    <div style="color:#a0a0a0;font-size:0.85em;">{metric.get("label", "")}</div>
                </div>
                '''
            metrics_html += '</div>'

            html_parts.append(f'''
            <div class="section">
                <h2>📊 关键指标</h2>
                {metrics_html}
            </div>
            ''')

        # 要点列表
        if "key_points" in data:
            points_html = '<ul style="list-style:none;padding:0;">'
            for point in data["key_points"]:
                points_html += f'<li style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">• {point}</li>'
            points_html += '</ul>'

            html_parts.append(f'''
            <div class="section">
                <h2>📝 关键要点</h2>
                <div class="card">{points_html}</div>
            </div>
            ''')

        # 数据表格
        if "table_data" in data:
            table = data["table_data"]
            headers = table.get("headers", [])
            rows = table.get("rows", [])

            table_html = '<table><thead><tr>'
            for h in headers:
                table_html += f'<th>{h}</th>'
            table_html += '</tr></thead><tbody>'

            for row in rows:
                table_html += '<tr>'
                for cell in row:
                    table_html += f'<td>{cell}</td>'
                table_html += '</tr>'
            table_html += '</tbody></table>'

            html_parts.append(f'''
            <div class="section">
                <h2>📈 数据详情</h2>
                <div class="card">{table_html}</div>
            </div>
            ''')

        # 问题列表
        if "issues" in data:
            issues_html = '<ul style="list-style:none;padding:0;">'
            for issue in data["issues"]:
                severity = issue.get("severity", "warning")
                badge_class = f"badge-{severity}"
                issues_html += f'''
                <li style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                    <span class="badge {badge_class}">{severity.upper()}</span>
                    {issue.get("description", "")}
                </li>
                '''
            issues_html += '</ul>'

            html_parts.append(f'''
            <div class="section">
                <h2>⚠️ 问题记录</h2>
                <div class="card">{issues_html}</div>
            </div>
            ''')

        return '\n'.join(html_parts)

    def generate_document_report(
        self,
        document_info: Dict,
        extraction_result: Dict,
        filename: Optional[str] = None
    ) -> str:
        """
        生成文档分析报告

        Args:
            document_info: 文档基本信息
            extraction_result: 提取结果
            filename: 输出文件名
        """
        if filename is None:
            filename = f"doc_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        data = {
            "subtitle": f"文档: {document_info.get('filename', 'Unknown')}",
            "status": "分析完成",
            "summary": extraction_result.get("summary", ""),
            "key_metrics": [
                {"label": "字数", "value": document_info.get("word_count", "-")},
                {"label": "页数", "value": document_info.get("page_count", "-")},
                {"label": "提取要点", "value": len(extraction_result.get("key_points", []))},
            ],
            "key_points": extraction_result.get("key_points", []),
            "issues": extraction_result.get("issues", [])
        }

        return self.generate_summary_report("文档分析报告", data, filename)


class AnimatedHTMLGenerator:
    """
    动画HTML生成器 - 生成带动画效果的可视化页面
    """

    ANIMATED_STYLE = """
        {base_style}

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-30px); }
            to { opacity: 1; transform: translateX(0); }
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        @keyframes countUp {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .animate-fade { animation: fadeIn 0.6s ease-out; }
        .animate-slide { animation: slideIn 0.5s ease-out; }
        .animate-pulse { animation: pulse 2s infinite; }

        .timeline { position: relative; padding-left: 30px; }
        .timeline::before {
            content: '';
            position: absolute;
            left: 10px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: linear-gradient(to bottom, #00d4ff, #7c3aed);
        }

        .timeline-item {
            position: relative;
            margin-bottom: 20px;
            padding-left: 20px;
        }

        .timeline-item::before {
            content: '';
            position: absolute;
            left: -24px;
            top: 5px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00d4ff;
            box-shadow: 0 0 10px #00d4ff;
        }

        .progress-ring {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: conic-gradient(#00d4ff {progress}%, rgba(255,255,255,0.1) 0%);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .progress-ring-inner {
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: #1a1a2e;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5em;
            font-weight: bold;
        }

        .flow-chart {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .flow-node {
            background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(124,58,237,0.2));
            border: 1px solid rgba(0,212,255,0.3);
            border-radius: 12px;
            padding: 15px 25px;
            text-align: center;
        }

        .flow-arrow {
            color: #00d4ff;
            font-size: 1.5em;
        }
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_animated_dashboard(
        self,
        title: str,
        metrics: List[Dict],
        flow_data: List[str] = None,
        filename: str = "dashboard.html"
    ) -> str:
        """
        生成带动画的数据仪表盘

        Args:
            title: 仪表盘标题
            metrics: 指标列表 [{"label": "...", "value": "...", "icon": "..."}]
            flow_data: 流程节点列表
            filename: 输出文件名
        """
        metrics_html = '<div class="metrics-grid">'
        for i, m in enumerate(metrics):
            metrics_html += f'''
            <div class="metric-card animate-fade" style="animation-delay: {i * 0.1}s">
                <div class="metric-icon">{m.get("icon", "📊")}</div>
                <div class="metric-value">{m.get("value", "-")}</div>
                <div class="metric-label">{m.get("label", "")}</div>
            </div>
            '''
        metrics_html += '</div>'

        flow_html = ""
        if flow_data:
            flow_html = '<div class="flow-section">'
            flow_html += '<h3 style="color:#00d4ff;margin-bottom:20px;">处理流程</h3>'
            flow_html += '<div class="flow-chart">'
            for i, node in enumerate(flow_data):
                flow_html += f'<div class="flow-node">{node}</div>'
                if i < len(flow_data) - 1:
                    flow_html += '<div class="flow-arrow">→</div>'
            flow_html += '</div></div>'

        style = self.ANIMATED_STYLE.format(
            base_style=HTMLReportGenerator.DEFAULT_STYLE
        )

        additional_css = '''
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s;
        }
        .metric-card:hover { transform: translateY(-5px); }
        .metric-icon { font-size: 2em; margin-bottom: 10px; }
        .metric-value { font-size: 2em; font-weight: bold; color: #00d4ff; }
        .metric-label { color: #a0a0a0; font-size: 0.85em; margin-top: 5px; }
        .flow-section { background: rgba(0,0,0,0.2); border-radius: 12px; padding: 25px; margin-top: 20px; }
        '''

        html = f'''
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                {style}
                {additional_css}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header animate-fade">
                    <h1>{title}</h1>
                    <p class="subtitle">实时数据展示</p>
                </div>

                <div class="content">
                    {metrics_html}
                    {flow_html}
                </div>

                <div class="footer">
                    <p>商飞离线AI文档处理平台 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
            </div>
        </body>
        </html>
        '''

        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return str(output_path)
