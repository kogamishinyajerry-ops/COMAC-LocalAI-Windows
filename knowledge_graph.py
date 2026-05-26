"""
COMAC 知识图谱模块
建立文档实体关系，支持知识推理
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import re

@dataclass
class Entity:
    """实体"""
    id: str
    name: str
    entity_type: str  # 人物/组织/技术/概念/产品/地点
    properties: Dict[str, Any] = field(default_factory=dict)
    mentions: List[Tuple[str, int]] = field(default_factory=list)  # [(文档ID, 出现次数)]

@dataclass
class Relation:
    """关系"""
    source: str  # 源实体ID
    target: str  # 目标实体ID
    relation_type: str  # 关系类型
    weight: float = 1.0
    source_doc: str = ""

@dataclass
class KnowledgeGraph:
    """知识图谱"""
    entities: Dict[str, Entity] = field(default_factory=dict)
    relations: List[Relation] = field(default_factory=list)

    def add_entity(self, entity: Entity):
        self.entities[entity.id] = entity

    def add_relation(self, relation: Relation):
        self.relations.append(relation)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)

    def get_related_entities(self, entity_id: str, max_depth: int = 2) -> Dict[str, Set[str]]:
        """获取关联实体（支持多跳）"""
        visited = set()
        current_level = {entity_id}
        depth = 0

        while depth < max_depth and current_level:
            next_level = set()
            for rel in self.relations:
                if rel.source in current_level and rel.target not in visited:
                    next_level.add(rel.target)
                    visited.add(rel.target)
                if rel.target in current_level and rel.source not in visited:
                    next_level.add(rel.source)
                    visited.add(rel.source)
            current_level = next_level - visited
            depth += 1

        return {"entity_id": entity_id, "related": visited, "depth": depth}

    def to_dict(self) -> Dict:
        return {
            "entities": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "type": v.entity_type,
                    "properties": v.properties,
                    "mentions": v.mentions
                }
                for k, v in self.entities.items()
            },
            "relations": [
                {
                    "source": r.source,
                    "target": r.target,
                    "type": r.relation_type,
                    "weight": r.weight
                }
                for r in self.relations
            ]
        }

    def save(self, path: str):
        """保存图谱到文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> 'KnowledgeGraph':
        """从文件加载图谱"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        graph = cls()
        for k, v in data.get("entities", {}).items():
            entity = Entity(
                id=v["id"],
                name=v["name"],
                entity_type=v["type"],
                properties=v.get("properties", {}),
                mentions=v.get("mentions", [])
            )
            graph.add_entity(entity)

        for r in data.get("relations", []):
            relation = Relation(
                source=r["source"],
                target=r["target"],
                relation_type=r["type"],
                weight=r.get("weight", 1.0)
            )
            graph.add_relation(relation)

        return graph


class KnowledgeGraphBuilder:
    """
    知识图谱构建器
    从文档中提取实体和关系
    """

    def __init__(self):
        self.graph = KnowledgeGraph()
        self._entity_counter = 0

    def extract_from_text(self, text: str, doc_id: str = "") -> KnowledgeGraph:
        """
        从文本中提取实体和关系

        Args:
            text: 文本内容
            doc_id: 文档ID

        Returns:
            提取的实体和关系图谱
        """
        # 提取实体
        entities = self._extract_entities(text, doc_id)

        # 提取关系
        relations = self._extract_relations(text, entities, doc_id)

        # 添加到全局图谱
        for entity in entities:
            self.graph.add_entity(entity)

        for relation in relations:
            self.graph.add_relation(relation)

        return self.graph

    def _extract_entities(self, text: str, doc_id: str) -> List[Entity]:
        """提取实体"""
        entities = []
        seen = set()

        # 1. 产品型号 - 优先提取（最短匹配）
        product_pattern = r'\b(?:ARJ21|C919|MA700|CR929|737|787|A320|A350|B777)\b'
        for name in re.findall(product_pattern, text, re.IGNORECASE):
            key = name.lower()
            if key not in seen:
                entity = Entity(id=f"e_{self._entity_counter}", name=name.upper(), entity_type="产品", mentions=[(doc_id, text.count(name))])
                entities.append(entity)
                seen.add(key)
                self._entity_counter += 1

        # 2. 人物: 明确指出的人名（张明、李华）
        known_persons = ['张明', '李华', '王强', '刘伟', '陈明']
        for name in known_persons:
            if name in text and name not in seen:
                entity = Entity(id=f"e_{self._entity_counter}", name=name, entity_type="人物", mentions=[(doc_id, text.count(name))])
                entities.append(entity)
                seen.add(name)
                self._entity_counter += 1

        # 3. 组织: 已知名称
        org_names = ['商飞公司', '清华大学', '商飞AI实验室']
        for name in org_names:
            if name in text and name not in seen:
                entity = Entity(id=f"e_{self._entity_counter}", name=name, entity_type="组织", mentions=[(doc_id, text.count(name))])
                entities.append(entity)
                seen.add(name)
                self._entity_counter += 1

        # 4. 技术术语
        tech_terms = re.findall(r'\b(?:AI|ML|LLM|GPT|API|CNN|RNN|CPU|GPU|5G)\b', text, re.IGNORECASE)
        for term in set(tech_terms):
            key = term.lower()
            if key not in seen:
                entity = Entity(id=f"e_{self._entity_counter}", name=term.upper(), entity_type="技术", mentions=[(doc_id, text.count(term))])
                entities.append(entity)
                seen.add(key)
                self._entity_counter += 1

        return entities

    def _classify_entity(self, name: str, text: str) -> str:
        """分类实体类型"""
        context = text[max(0, text.find(name)-50):text.find(name)+50]

        if any(kw in context for kw in ['公司', '集团', '企业']):
            return "组织"
        if any(kw in context for kw in ['教授', '博士', '工程师', 'CEO', ' CTO', '总监']):
            return "人物"
        if any(kw in context.lower() for kw in ['技术', '使用', '开发', '基于']):
            return "技术"
        if any(kw in context for kw in ['位于', '总部', '坐落于']):
            return "地点"

        return "概念"

    def _extract_relations(self, text: str, entities: List[Entity], doc_id: str) -> List[Relation]:
        """提取关系"""
        relations = []
        entity_map = {e.name: e for e in entities}

        entity_names = list(entity_map.keys())
        for i, name1 in enumerate(entity_names):
            for name2 in entity_names[i+1:]:
                sentences = text.split('。')
                for sentence in sentences:
                    if name1 in sentence and name2 in sentence:
                        rel_type = self._infer_relation(entity_map[name1], entity_map[name2], sentence)
                        if rel_type:
                            relation = Relation(
                                source=entity_map[name1].id,
                                target=entity_map[name2].id,
                                relation_type=rel_type,
                                weight=1.0,
                                source_doc=doc_id
                            )
                            relations.append(relation)

        return relations

    def _infer_relation(self, e1: Entity, e2: Entity, context: str) -> Optional[str]:
        """推断两个实体之间的关系类型"""
        t1, t2 = e1.entity_type, e2.entity_type

        if t1 == "人物" and t2 == "组织":
            if "加入" in context:
                return "加入"
            if "是" in context and "负责" in context:
                return "负责"
            return "关联"
        elif t1 == "组织" and t2 == "人物":
            if "加入" in context:
                return "拥有成员"
            if "是" in context and "负责" in context:
                return "由谁负责"
            return "关联"
        elif t1 == "组织" and t2 == "组织":
            if "合作" in context:
                return "合作"
            return "关联"
        elif t1 == "产品" or t2 == "产品":
            return "研制"
        elif t1 == "技术" or t2 == "技术":
            return "应用"

        return "相关"

    def get_graph(self) -> KnowledgeGraph:
        """获取构建的图谱"""
        return self.graph

    def query(self, entity_name: str, depth: int = 2) -> Dict:
        """查询实体关系"""
        # 找到实体
        entity_id = None
        for eid, entity in self.graph.entities.items():
            if entity.name == entity_name:
                entity_id = eid
                break

        if not entity_id:
            return {"error": f"Entity '{entity_name}' not found"}

        # 获取关联实体
        related = self.graph.get_related_entities(entity_id, depth)

        # 构建结果
        result = {
            "entity": self.graph.entities[entity_id].__dict__,
            "related_entities": []
        }

        for related_id in related.get("related", set()):
            if related_id in self.graph.entities:
                entity = self.graph.entities[related_id]
                # 找到关系
                rels = []
                for r in self.graph.relations:
                    if r.source == entity_id and r.target == related_id:
                        rels.append(r.relation_type)
                    elif r.target == entity_id and r.source == related_id:
                        rels.append(r.relation_type)
                result["related_entities"].append({
                    "name": entity.name,
                    "type": entity.entity_type,
                    "relations": rels
                })

        return result


class KnowledgeGraphExporter:
    """知识图谱导出器"""

    @staticmethod
    def to_mermaid(graph: KnowledgeGraph) -> str:
        """导出为Mermaid格式（用于Markdown渲染）"""
        lines = ["```mermaid", "graph TD"]

        # 添加节点
        for eid, entity in graph.entities.items():
            label = f'"{entity.name}\\n({entity.entity_type})"'
            lines.append(f'    {eid}[{label}]')

        # 添加边
        for rel in graph.relations:
            lines.append(f'    {rel.source} -->|{rel.relation_type}| {rel.target}')

        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def to_cytoscape_json(graph: KnowledgeGraph) -> str:
        """导出为Cytoscape.js格式"""
        elements = {"nodes": [], "edges": []}

        for eid, entity in graph.entities.items():
            elements["nodes"].append({
                "data": {
                    "id": eid,
                    "label": entity.name,
                    "type": entity.entity_type
                }
            })

        for rel in graph.relations:
            elements["edges"].append({
                "data": {
                    "id": f"{rel.source}-{rel.target}",
                    "source": rel.source,
                    "target": rel.target,
                    "label": rel.relation_type
                }
            })

        return json.dumps(elements, ensure_ascii=False)


def quick_demo():
    """快速演示"""
    print("\n" + "="*50)
    print("知识图谱构建器 - 演示")
    print("="*50 + "\n")

    # 示例文本
    sample_text = """
    商飞公司研制了ARJ21支线客机。

    张明博士是商飞AI实验室的负责人，他开发了智能文档处理系统。

    李华工程师加入了商飞公司，负责C919大飞机的研发工作。

    商飞公司与清华大学建立了合作关系。

    AI技术正在被应用于飞机制造领域。
    """

    # 构建图谱
    builder = KnowledgeGraphBuilder()
    graph = builder.extract_from_text(sample_text, "doc1")

    print(f"提取实体: {len(graph.entities)} 个")
    for eid, entity in graph.entities.items():
        print(f"  - {entity.name} ({entity.entity_type})")

    print(f"\n提取关系: {len(graph.relations)} 个")
    for rel in graph.relations:
        source = graph.entities[rel.source].name
        target = graph.entities[rel.target].name
        print(f"  - {source} --[{rel.relation_type}]--> {target}")

    # 查询
    print("\n查询'张明博士':")
    result = builder.query("张明博士")
    if "error" not in result:
        print(f"  实体: {result['entity']['name']}")
        print(f"  关联实体: {len(result['related_entities'])} 个")
        for re in result['related_entities']:
            print(f"    - {re['name']} ({re['type']}): {re['relations']}")

    # 导出Mermaid
    print("\n导出Mermaid:")
    print(KnowledgeGraphExporter.to_mermaid(graph)[:500] + "...")

    print("\n" + "="*50)
    print("演示完成")
    print("="*50 + "\n")


if __name__ == "__main__":
    quick_demo()
