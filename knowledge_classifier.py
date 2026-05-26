"""
COMAC 知识分类器
自动为文档打标签、分类整理
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import re

from ollama_client import OllamaClient, MODEL_DOC

@dataclass
class Category:
    """知识分类"""
    name: str
    keywords: Set[str]
    subcategories: List['Category'] = None

class KnowledgeClassifier:
    """
    知识分类器 - 自动为文档打标签和分类

    使用方式：

    classifier = KnowledgeClassifier()

    # 自动分类
    result = classifier.classify("这是一份关于人工智能的技术报告...")
    print(result['category'])  # "技术/AI"
    print(result['tags'])     # ["人工智能", "机器学习", "深度学习"]

    # 批量处理
    results = classifier.batch_classify(documents)
    """

    # 预定义分类体系
    CATEGORIES = [
        Category(
            name="技术/AI",
            keywords={"人工智能", "AI", "机器学习", "深度学习", "神经网络", "大模型", "LLM", "GPT", "自然语言处理", "NLP", "计算机视觉", "CV"},
            subcategories=[
                Category(name="机器学习", keywords={"机器学习", "监督学习", "无监督学习", "强化学习", "ML"}),
                Category(name="深度学习", keywords={"深度学习", "CNN", "RNN", "Transformer", "BERT", "GAN"}),
                Category(name="大模型", keywords={"大模型", "LLM", "GPT", "Claude", "Qwen", "DeepSeek", "RAG", "Embedding"}),
            ]
        ),
        Category(
            name="技术/软件",
            keywords={"软件", "编程", "代码", "开发", "Python", "Java", "JavaScript", "API", "框架", "架构"},
            subcategories=[
                Category(name="编程语言", keywords={"Python", "Java", "C++", "Go", "Rust", "JavaScript", "TypeScript"}),
                Category(name="框架", keywords={"Django", "Flask", "Spring", "React", "Vue", "Angular"}),
            ]
        ),
        Category(
            name="技术/基础设施",
            keywords={"服务器", "网络", "云", "Docker", "Kubernetes", "K8S", "Linux", "运维", "DevOps", "CI/CD"},
            subcategories=[
                Category(name="云计算", keywords={"AWS", "Azure", "GCP", "阿里云", "腾讯云", "云原生"}),
                Category(name="容器化", keywords={"Docker", "Kubernetes", "K8S", "容器", "镜像"}),
            ]
        ),
        Category(
            name="业务/文档",
            keywords={"文档", "报告", "方案", "规范", "标准", "流程", "制度", "手册", "操作手册"},
            subcategories=[
                Category(name="技术文档", keywords={"技术文档", "API文档", "接口文档", "设计文档"}),
                Category(name="商务文档", keywords={"合同", "协议", "报价", "方案书", "投标"}),
            ]
        ),
        Category(
            name="安全/合规",
            keywords={"安全", "加密", "隐私", "合规", "GDPR", "网络安全", "防火墙", "渗透测试", "漏洞"},
            subcategories=[
                Category(name="信息安全", keywords={"信息安全", "等级保护", "ISO27001"}),
                Category(name="数据安全", keywords={"数据安全", "脱敏", "加密", "备份"}),
            ]
        ),
        Category(
            name="管理/组织",
            keywords={"管理", "组织", "团队", "项目", "OKR", "KPI", "敏捷", "Scrum"},
            subcategories=[
                Category(name="项目管理", keywords={"项目管理", "PM", "PMP", "敏捷", "Scrum", "看板"}),
                Category(name="团队管理", keywords={"团队管理", "领导力", "绩效", "OKR"}),
            ]
        ),
        Category(
            name="行业/航空",
            keywords={"航空", "商飞", "COMAC", "ARJ21", "C919", "MA700", "飞机", "民航", "适航"},
            subcategories=[
                Category(name="飞机制造", keywords={"飞机制造", "机体", "装配", "复合材料"}),
                Category(name="航空技术", keywords={"航空技术", "发动机", "航电", "飞控", "材料"}),
            ]
        ),
    ]

    def __init__(self, llm_model: str = MODEL_DOC):
        self.llm_model = llm_model
        self._client = OllamaClient(llm_model)
        self._tag_cache: Dict[str, List[str]] = {}

    def classify(self, text: str, top_k: int = 3) -> Dict:
        """
        对文本进行分类

        Args:
            text: 要分类的文本
            top_k: 返回的标签数量

        Returns:
            包含category、tags、confidence的字典
        """
        if not text or not text.strip():
            return {"category": "未分类", "tags": [], "confidence": 0.0}

        # 1. 基于关键词的快速分类
        keyword_result = self._keyword_classify(text)
        category = keyword_result["category"]
        keywords_found = keyword_result["keywords"]

        # 2. 使用LLM进行细化和验证
        llm_tags = self._llm_extract_tags(text, top_k)

        # 3. 合并结果
        all_tags = list(set(keywords_found + llm_tags))[:top_k]

        return {
            "category": category,
            "tags": all_tags,
            "confidence": min(1.0, len(all_tags) / top_k),
            "method": "hybrid"
        }

    def _keyword_classify(self, text: str) -> Dict:
        """基于关键词的快速分类"""
        text_lower = text.lower()
        best_category = "其他"
        best_score = 0
        keywords_found = []

        for category in self.CATEGORIES:
            score = 0
            category_keywords = []

            for keyword in category.keywords:
                if keyword.lower() in text_lower:
                    score += 1
                    category_keywords.append(keyword)

            # 检查子分类
            if category.subcategories:
                for subcat in category.subcategories:
                    for keyword in subcat.keywords:
                        if keyword.lower() in text_lower:
                            score += 0.5
                            if keyword not in category_keywords:
                                category_keywords.append(keyword)

            if score > best_score:
                best_score = score
                best_category = category.name
                keywords_found = category_keywords

        return {
            "category": best_category,
            "keywords": keywords_found,
            "score": best_score
        }

    def _llm_extract_tags(self, text: str, top_k: int) -> List[str]:
        """使用LLM提取标签"""
        # 缓存检查
        cache_key = text[:100]
        if cache_key in self._tag_cache:
            return self._tag_cache[cache_key][:top_k]

        prompt = f"""从以下文本中提取{top_k}个最相关的标签（关键词）。

文本：
{text[:2000]}

要求：
1. 每个标签2-4个字
2. 只返回标签，用逗号分隔
3. 不要解释

标签："""

        try:
            response = self._client.generate(prompt, temperature=0.3)
            # 解析标签
            tags = [t.strip() for t in response.split(',') if t.strip()]
            self._tag_cache[cache_key] = tags
            return tags[:top_k]
        except Exception:
            return []

    def batch_classify(self, documents: List[Dict[str, str]]) -> List[Dict]:
        """
        批量分类文档

        Args:
            documents: 文档列表，格式为 [{"id": "...", "title": "...", "content": "..."}]

        Returns:
            每个文档的分类结果列表
        """
        results = []

        for doc in documents:
            text = doc.get("content", doc.get("title", ""))
            title = doc.get("title", "")

            # 组合标题和内容
            full_text = f"{title}\n\n{text}" if title else text

            classification = self.classify(full_text)
            classification["id"] = doc.get("id", "")
            classification["title"] = title

            results.append(classification)

        return results

    def get_category_tree(self) -> Dict:
        """获取分类树"""
        def build_tree(category: Category) -> Dict:
            node = {
                "name": category.name,
                "keywords": list(category.keywords)[:10]
            }
            if category.subcategories:
                node["children"] = [build_tree(sub) for sub in category.subcategories]
            return node

        return {
            "categories": [build_tree(cat) for cat in self.CATEGORIES]
        }


class KnowledgeOrganizer:
    """
    知识整理器 - 将分类结果组织成结构化文档
    """

    def __init__(self, classifier: KnowledgeClassifier = None):
        self.classifier = classifier or KnowledgeClassifier()

    def organize_document(
        self,
        title: str,
        content: str,
        source: str = "",
        metadata: Dict = None
    ) -> Dict:
        """
        整理文档

        Args:
            title: 文档标题
            content: 文档内容
            source: 来源
            metadata: 额外元数据

        Returns:
            结构化的知识条目
        """
        # 分类
        classification = self.classifier.classify(content)

        # 提取摘要
        summary = self._extract_summary(content)

        # 提取关键实体
        entities = self._extract_entities(content)

        return {
            "title": title,
            "content": content,
            "summary": summary,
            "category": classification["category"],
            "tags": classification["tags"],
            "entities": entities,
            "source": source,
            "metadata": metadata or {},
            "word_count": len(content),
            "char_count": len(content.replace(" ", "")),
        }

    def _extract_summary(self, content: str, max_length: int = 200) -> str:
        """提取摘要"""
        if len(content) <= max_length:
            return content

        prompt = f"""请总结以下文档的要点，字数控制在{max_length}字以内：

{content[:3000]}

摘要："""

        try:
            client = OllamaClient(MODEL_DOC)
            return client.generate(prompt, temperature=0.3).strip()
        except Exception:
            return content[:max_length] + "..."

    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """提取关键实体"""
        entities = {
            "人物": [],
            "组织": [],
            "地点": [],
            "技术": [],
            "产品": []
        }

        # 简单基于模式的提取
        patterns = {
            "人物": [r'([A-Z][a-z]+ [A-Z][a-z]+)'],  # 英文名
            "组织": [r'([A-Z][a-z]+(?:公司|集团|机构|组织))'],  # 中文组织
            "技术": [r'([A-Z]{2,})'],  # 大写缩写
        }

        for entity_type, regexes in patterns.items():
            for regex in regexes:
                matches = re.findall(regex, content)
                entities[entity_type] = list(set(matches))[:10]

        return entities

    def generate_obsidian_note(self, knowledge: Dict) -> str:
        """生成Obsidian格式的笔记"""
        from datetime import datetime

        tags_str = ", ".join([f'"{t}"' for t in knowledge["tags"]])
        date = datetime.now().strftime("%Y-%m-%d")

        note = f"""---
date: {date}
title: {knowledge['title']}
tags: [{tags_str}]
category: {knowledge['category']}
source: {knowledge.get('source', '')}
word_count: {knowledge['word_count']}
---

# {knowledge['title']}

## 摘要

{knowledge['summary']}

## 分类

- **类别**: {knowledge['category']}
- **标签**: {', '.join(knowledge['tags'])}

## 关键实体

"""

        if knowledge.get('entities'):
            for entity_type, entity_list in knowledge['entities'].items():
                if entity_list:
                    note += f"- **{entity_type}**: {', '.join(entity_list[:5])}\n"

        note += f"""
## 原文

{knowledge['content'][:1000]}{'...' if len(knowledge['content']) > 1000 else ''}

---
*整理时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

        return note


def quick_demo():
    """快速演示"""
    print("\n" + "="*50)
    print("知识分类器 - 演示")
    print("="*50 + "\n")

    classifier = KnowledgeClassifier()

    # 演示分类
    test_texts = [
        ("AI技术", "人工智能是当前技术发展的重要方向，机器学习和深度学习是其核心技术的关键。"),
        ("航空", "COMAC商飞生产的ARJ21支线客机已经商业运营多年，C919大型客机即将交付。"),
        ("文档", "本技术报告详细描述了系统架构设计和API接口规范。"),
        ("安全", "本次渗透测试发现了系统中存在的安全漏洞，需要立即修复。"),
    ]

    print("分类测试：")
    for title, text in test_texts:
        result = classifier.classify(text)
        print(f"\n  [{title}]")
        print(f"    分类: {result['category']}")
        print(f"    标签: {', '.join(result['tags'])}")
        print(f"    置信度: {result['confidence']:.2f}")

    # 演示知识整理
    print("\n\n知识整理演示：")
    organizer = KnowledgeOrganizer(classifier)

    knowledge = organizer.organize_document(
        title="AI技术发展趋势报告",
        content="人工智能技术正在快速发展，深度学习和强化学习等技术取得了突破性进展。",
        source="内部研究"
    )

    print(f"  标题: {knowledge['title']}")
    print(f"  分类: {knowledge['category']}")
    print(f"  标签: {', '.join(knowledge['tags'])}")
    print(f"  摘要: {knowledge['summary'][:100]}...")

    print("\n" + "="*50)
    print("演示完成")
    print("="*50 + "\n")


if __name__ == "__main__":
    quick_demo()
