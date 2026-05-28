"""
COMAC 轻量级RAG引擎
使用纯Ollama实现，无需LlamaIndex

功能：
- 文档分块
- Embedding生成（使用ollama嵌入模型）
- 向量相似度搜索
- RAG问答
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import re

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from ollama_client import OllamaClient, MODEL_DOC


@dataclass
class Chunk:
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float] = None


@dataclass
class Document:
    path: str
    chunks: List[Chunk]
    content_hash: str


class SimpleVectorStore:
    """
    简单的向量存储（基于JSON + 内存）
    对于离线环境，无需额外依赖
    """

    def __init__(self, index_path: str = "./vector_index"):
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.documents: Dict[str, Document] = {}
        self.chunks: Dict[str, Chunk] = {}
        self._load_index()

    def _load_index(self):
        index_file = self.index_path / "index.json"
        if index_file.exists():
            try:
                with open(index_file) as f:
                    data = json.load(f)
                    # 加载文档
                    for doc_id, doc_data in data.get("documents", {}).items():
                        chunks = []
                        for chunk_data in doc_data.get("chunks", []):
                            chunk = Chunk(
                                id=chunk_data["id"],
                                content=chunk_data["content"],
                                metadata=chunk_data.get("metadata", {}),
                                embedding=chunk_data.get("embedding")
                            )
                            chunks.append(chunk)
                            self.chunks[chunk.id] = chunk
                        self.documents[doc_id] = Document(
                            path=doc_data["path"],
                            chunks=chunks,
                            content_hash=doc_data.get("content_hash", "")
                        )
                print(f"[VectorStore] Loaded {len(self.chunks)} chunks from index")
            except Exception as e:
                print(f"[VectorStore] Failed to load index: {e}")

    def _save_index(self):
        index_file = self.index_path / "index.json"
        data = {
            "documents": {
                doc_id: {
                    "path": doc.path,
                    "content_hash": doc.content_hash,
                    "chunks": [
                        {
                            "id": c.id,
                            "content": c.content,
                            "metadata": c.metadata,
                            "embedding": c.embedding
                        }
                        for c in doc.chunks
                    ]
                }
                for doc_id, doc in self.documents.items()
            }
        }
        with open(index_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_chunk(self, chunk: Chunk, doc_id: str):
        self.chunks[chunk.id] = chunk
        if doc_id not in self.documents:
            self.documents[doc_id] = Document(
                path=doc_id,
                chunks=[],
                content_hash=""
            )
        self.documents[doc_id].chunks.append(chunk)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """搜索最相似的chunk"""
        if not NUMPY_AVAILABLE:
            return self._search_naive(query_embedding, top_k)

        scores = []
        query_vec = np.array(query_embedding)
        for chunk_id, chunk in self.chunks.items():
            if chunk.embedding is None:
                continue
            chunk_vec = np.array(chunk.embedding)
            similarity = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec) + 1e-10
            )
            scores.append((chunk, float(similarity)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _search_naive(self, query_embedding: List[float], top_k: int) -> List[Tuple[Chunk, float]]:
        """朴素搜索（无numpy时）"""
        if not self.chunks:
            return []

        # 简单的余弦相似度计算
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot / (norm_a * norm_b + 1e-10)

        scores = []
        for chunk in self.chunks.values():
            if chunk.embedding:
                score = cosine_similarity(query_embedding, chunk.embedding)
                scores.append((chunk, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def clear(self):
        self.documents.clear()
        self.chunks.clear()
        self._save_index()


class OllamaRAG:
    """
    基于Ollama的轻量级RAG引擎

    使用方式：

    rag = OllamaRAG(
        embed_model="nomic-embed-text"  # Ollama嵌入模型
    )

    # 索引文档
    rag.index_documents("./docs")

    # RAG问答
    response = rag.query("总结这份文档的主要内容")
    """

    def __init__(
        self,
        embed_model: str = "nomic-embed-text",
        llm_model: str = MODEL_DOC,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.embed_model = embed_model
        self.llm_model = llm_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._embed_client = OllamaClient(embed_model)
        self._llm_client = OllamaClient(llm_model)
        self._embed_available = self._check_embed_model()
        self.vector_store = SimpleVectorStore()

    def _check_embed_model(self) -> bool:
        """检测 embedding 模型是否可用，不可用则用主模型替代"""
        try:
            models = self._embed_client.list_models()
            if self.embed_model in models:
                return True
            # embedding 模型不可用，尝试用主模型
            print(f"[RAG] Embedding model '{self.embed_model}' not available, "
                  f"will use main model '{self.llm_model}' for embeddings.")
            self._embed_client = OllamaClient(self.llm_model)
            return False
        except Exception:
            print(f"[RAG] Embedding model check failed, will use main model for embeddings.")
            print(f"[RAG] Tip: run 'ollama pull nomic-embed-text' to install dedicated embedding model for better performance.")
            return False

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的embedding（自动降级）"""
        try:
            response = self._embed_client.embeddings(text)
            # Ollama embeddings API返回 {'embedding': [...]}
            if isinstance(response, dict) and 'embedding' in response:
                return response['embedding']
            elif hasattr(response, 'embedding'):
                return response.embedding
            return response[:768] if isinstance(response, list) else []
        except Exception as e:
            print(f"[RAG] Embedding failed: {e}")
            return []

    def _chunk_text(self, text: str) -> List[str]:
        """将文本分块"""
        # 简单分块，可按段落或句子进一步优化
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        return [c for c in chunks if c]

    def _compute_hash(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def index_file(self, file_path: str) -> int:
        """索引单个文件"""
        path = Path(file_path)
        if not path.exists():
            print(f"[RAG] File not found: {file_path}")
            return 0

        # 读取文件
        try:
            if path.suffix == '.md':
                content = path.read_text(encoding='utf-8')
            elif path.suffix == '.txt':
                content = path.read_text(encoding='utf-8')
            elif path.suffix == '.pdf':
                try:
                    import pdfplumber
                    with pdfplumber.open(path) as pdf:
                        content = "\n".join([p.extract_text() or "" for p in pdf.pages])
                except Exception as e:
                    print(f"[RAG] PDF reading not available for {file_path}: {e}")
                    return 0
            else:
                try:
                    content = path.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"[RAG] Unsupported file type: {file_path}: {e}")
                    return 0
        except Exception as e:
            print(f"[RAG] Failed to read {file_path}: {e}")
            return 0

        # 检查是否已索引（通过hash）
        content_hash = self._compute_hash(content)
        if path in self.vector_store.documents:
            if self.vector_store.documents[path].content_hash == content_hash:
                print(f"[RAG] Skipping unchanged: {file_path}")
                return 0

        # 分块
        text_chunks = self._chunk_text(content)
        print(f"[RAG] Processing {len(text_chunks)} chunks from {path.name}")

        # 为每个chunk生成embedding并存储
        chunk_count = 0
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{path}:{i}"
            embedding = self._get_embedding(chunk_text)

            if embedding:
                chunk = Chunk(
                    id=chunk_id,
                    content=chunk_text,
                    metadata={"source": str(path), "index": i},
                    embedding=embedding
                )
                self.vector_store.add_chunk(chunk, str(path))
                chunk_count += 1

        # 更新文档hash
        if str(path) in self.vector_store.documents:
            self.vector_store.documents[str(path)].content_hash = content_hash

        self.vector_store._save_index()
        print(f"[RAG] Indexed {chunk_count} chunks from {path.name}")
        return chunk_count

    def index_documents(self, path: str, recursive: bool = True) -> int:
        """
        索引目录下的所有文档

        Args:
            path: 目录路径
            recursive: 是否递归

        Returns:
            索引的chunk数量
        """
        dir_path = Path(path)
        if not dir_path.exists():
            print(f"[RAG] Path not found: {path}")
            return 0

        total_chunks = 0

        if dir_path.is_file():
            return self.index_file(str(dir_path))

        # 遍历目录
        patterns = ['*.md', '*.txt', '*.pdf']
        for pattern in patterns:
            if recursive:
                files = dir_path.rglob(pattern)
            else:
                files = dir_path.glob(pattern)

            for file_path in files:
                # 跳过隐藏文件和敏感目录（跨平台路径安全检查）
                file_path_str = str(file_path)
                # 同时检查 Unix 风格和 Windows 风格的路径遍历特征
                if ('/.' in file_path_str or '\\..\\' in file_path_str
                        or '\\.' in file_path_str or '..' in Path(file_path).parts
                        or 'AI-Processed' in file_path_str
                        or file_path_str.startswith('.')):
                    continue
                # 额外验证：解析真实路径，确保不在敏感区域内
                try:
                    resolved = file_path.resolve()
                    forbidden = ['Windows', 'System32', 'Program Files', 'ProgramData',
                                '.config', '.ssh', '.aws']
                    if any(f in resolved.parts for f in forbidden):
                        continue
                except Exception:
                    continue
                total_chunks += self.index_file(str(file_path))

        print(f"[RAG] Total indexed: {total_chunks} chunks")
        return total_chunks

    def query(self, question: str, top_k: int = 3, context_mode: str = "combined") -> str:
        """
        RAG问答

        Args:
            question: 问题
            top_k: 检索的chunk数量
            context_mode: 'combined' 或 'individual'

        Returns:
            AI回答
        """
        # 获取问题的embedding
        query_embedding = self._get_embedding(question)
        if not query_embedding:
            return "无法生成查询向量，请检查Ollama服务是否正常。"

        # 检索相似chunk
        results = self.vector_store.search(query_embedding, top_k=top_k)

        if not results:
            return "知识库为空，请先索引文档。"

        # 构建上下文
        if context_mode == "combined":
            context = "\n\n".join([f"[文档{i+1}]\n{c.content}" for i, (c, _) in enumerate(results)])
        else:
            context = "\n\n---\n\n".join([c.content for c, _ in results])

        # 构建prompt
        prompt = f"""基于以下上下文信息，回答问题。如果上下文中没有相关信息，请说明。

上下文：
{context}

问题：{question}

回答："""

        try:
            response = self._llm_client.generate(prompt, temperature=0.3)
            return response
        except Exception as e:
            return f"生成回答失败: {e}"

    def sync_index(self, path: str, recursive: bool = True) -> Dict[str, int]:
        """
        增量同步索引 - 只索引新增或变更的文件

        Args:
            path: 目录路径
            recursive: 是否递归

        Returns:
            包含 indexed/skipped/deleted 数量的字典
        """
        dir_path = Path(path)
        if not dir_path.exists():
            return {"indexed": 0, "skipped": 0, "deleted": 0}

        stats = {"indexed": 0, "skipped": 0, "deleted": 0}

        # 获取当前索引的文件集合
        indexed_files = set(self.vector_store.documents.keys())

        # 遍历目录
        patterns = ['*.md', '*.txt', '*.pdf']
        current_files = set()

        for pattern in patterns:
            if recursive:
                files = dir_path.rglob(pattern)
            else:
                files = dir_path.glob(pattern)

            for file_path in files:
                file_path_str = str(file_path)
                if ('/.' in file_path_str or '\\..\\' in file_path_str
                        or '\\.' in file_path_str or '..' in Path(file_path).parts
                        or 'AI-Processed' in file_path_str
                        or file_path_str.startswith('.')):
                    continue
                try:
                    resolved = file_path.resolve()
                    forbidden = ['Windows', 'System32', 'Program Files', 'ProgramData',
                                '.config', '.ssh', '.aws']
                    if any(f in resolved.parts for f in forbidden):
                        continue
                except Exception:
                    continue
                current_files.add(str(file_path))

        # 索引新增或变更的文件
        for file_path in current_files:
            if file_path in indexed_files:
                # 已索引，检查是否变更
                doc = self.vector_store.documents[file_path]
                try:
                    current_hash = self._compute_hash(Path(file_path).read_text())
                    if current_hash != doc.content_hash:
                        # 文件已变更，删除旧索引并重新索引
                        self._remove_from_index(file_path)
                        indexed = self.index_file(file_path)
                        stats["indexed"] += indexed
                    else:
                        stats["skipped"] += 1
                except Exception:
                    stats["skipped"] += 1
            else:
                # 新文件，索引
                indexed = self.index_file(file_path)
                stats["indexed"] += indexed

        # 清理已删除的文件
        for file_path in indexed_files - current_files:
            self._remove_from_index(file_path)
            stats["deleted"] += 1

        print(f"[RAG] Sync: {stats['indexed']} indexed, {stats['skipped']} skipped, {stats['deleted']} deleted")
        return stats

    def _remove_from_index(self, file_path: str):
        """从索引中移除文件"""
        if file_path in self.vector_store.documents:
            doc = self.vector_store.documents[file_path]
            for chunk in doc.chunks:
                if chunk.id in self.vector_store.chunks:
                    del self.vector_store.chunks[chunk.id]
            del self.vector_store.documents[file_path]
            self.vector_store._save_index()

    def rebuild_index(self, path: str) -> int:
        """
        重建索引 - 删除所有索引并重新索引

        Args:
            path: 目录路径

        Returns:
            索引的chunk数量
        """
        print("[RAG] Rebuilding index...")
        self.vector_store.clear()
        return self.index_documents(path)

    def get_stats(self) -> Dict:
        """获取索引统计"""
        return {
            "total_documents": len(self.vector_store.documents),
            "total_chunks": len(self.vector_store.chunks),
            "embed_model": self.embed_model,
            "llm_model": self.llm_model,
            "chunk_size": self.chunk_size
        }


def quick_demo():
    """快速演示"""
    print("\n" + "="*50)
    print("COMAC 轻量级RAG引擎 - 演示")
    print("="*50 + "\n")

    rag = OllamaRAG()

    print("系统统计:")
    stats = rag.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 创建测试文档
    test_dir = Path("./temp/test_rag")
    test_dir.mkdir(parents=True, exist_ok=True)

    test_doc = test_dir / "test.md"
    test_doc.write_text("""# 人工智能概述

人工智能（AI）是计算机科学的一个分支，旨在创造能够模拟人类智能的机器。

## 机器学习

机器学习是AI的一个子领域，通过数据训练模型来实现预测和决策。

## 深度学习

深度学习使用神经网络来学习数据的层次化表示，在图像识别、自然语言处理等领域取得突破。

## 总结

AI技术正在深刻改变我们的生活和工作方式。
""")

    print(f"\n索引文档: {test_doc}")
    rag.index_documents(str(test_dir))

    print("\n统计:")
    stats = rag.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 测试问答
    print("\n问答测试:")
    questions = [
        "什么是人工智能？",
        "深度学习是什么？",
    ]

    for q in questions:
        print(f"\nQ: {q}")
        answer = rag.query(q)
        print(f"A: {answer[:200]}...")

    # 清理测试文件
    import shutil
    shutil.rmtree(test_dir)

    print("\n" + "="*50)
    print("演示完成")
    print("="*50 + "\n")


if __name__ == "__main__":
    quick_demo()
