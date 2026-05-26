"""
演示文稿生成包
包含HTML报告、PPT、动画MG生成器
"""

from .html_report_generator import HTMLReportGenerator, AnimatedHTMLGenerator
from .ppt_generator import PPTGenerator, PPTOptimizer
from .animated_generator import Animated展示Generator, create_sample_presentation

__all__ = [
    "HTMLReportGenerator",
    "AnimatedHTMLGenerator",
    "PPTGenerator",
    "PPTOptimizer",
    "Animated展示Generator",
    "create_sample_presentation",
]
