"""
COMAC 知识同步引擎
实现 Obsidian Vault ↔ AI处理系统 双向同步

架构：
1. Obsidian → AI: 监控Vault变化，自动索引新笔记到向量库
2. AI → Obsidian: 处理结果自动写入Vault指定文件夹
3. 双向同步: 通过文件Watcher + 事件队列实现
"""

import os
import json
import time
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, asdict
from enum import Enum
import re

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("[ObsidianSync] watchdog not installed, using polling mode")

from ollama_client import OllamaClient, MODEL_DOC

@dataclass
class SyncRecord:
    """同步记录"""
    file_path: str
    action: str  # 'created' | 'modified' | 'deleted'
    timestamp: str
    content_hash: str
    synced: bool = False

class SyncDirection(Enum):
    """同步方向"""
    OBSIDIAN_TO_AI = "obsidian_to_ai"   # Obsidian新笔记 → AI索引
    AI_TO_OBSIDIAN = "ai_to_obsidian"   # AI处理结果 → Obsidian
    BIDIRECTIONAL = "bidirectional"

@dataclass
class ProcessedNote:
    """处理后的笔记"""
    title: str
    content: str
    summary: str = ""
    tags: List[str] = None
    links: List[str] = None
    metadata: Dict = None
    source_file: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.links is None:
            self.links = []
        if self.metadata is None:
            self.metadata = {}

class ObsidianSyncEngine:
    """
    Obsidian双向同步引擎

    使用方式：
    engine = ObsidianSyncEngine(
        vault_path="/path/to/vault",
        ai_index_path="./vector_index"
    )

    # 启动监控
    engine.start_watch()

    # 手动同步
    engine.sync_to_obsidian(title="新文档", content="内容", folder="AI-Generated")
    """

    FRONT_MATTER_TEMPLATE = """---
date: {date}
title: {title}
tags: [{tags}]
source: ai-processed
processed: {timestamp}
---

"""

    def __init__(
        self,
        vault_path: str,
        ai_index_path: str = "./vector_index",
        sync_folder: str = "AI-Processed",
        watch_enabled: bool = True,
        poll_interval: float = 5.0
    ):
        self.vault_path = Path(vault_path).resolve()
        self.ai_index_path = Path(ai_index_path)
        self.sync_folder = sync_folder
        self.watch_enabled = watch_enabled and WATCHDOG_AVAILABLE
        self.poll_interval = poll_interval

        # 确保目录存在
        self.ai_folder = self.vault_path / sync_folder
        self.ai_folder.mkdir(parents=True, exist_ok=True)

        # 同步状态
        self._sync_records: Dict[str, SyncRecord] = {}
        self._observer: Optional[Observer] = None
        self._watch_thread: Optional[threading.Thread] = None
        self._running = False
        self._file_hashes: Dict[str, str] = {}

        # AI客户端
        self._ai_client: Optional[OllamaClient] = None

        # 回调函数
        self._on_new_file: Optional[Callable] = None
        self._on_sync_complete: Optional[Callable] = None

        # 加载历史记录
        self._load_sync_state()

        print(f"[ObsidianSync] Initialized")
        print(f"  Vault: {self.vault_path}")
        print(f"  AI Folder: {self.ai_folder}")
        print(f"  Watch: {'Enabled' if self.watch_enabled else 'Disabled (polling)'}")
        print(f"  Mode: Bidirectional")

    @property
    def ai_client(self) -> OllamaClient:
        if self._ai_client is None:
            self._ai_client = OllamaClient(MODEL_DOC)
        return self._ai_client

    def _load_sync_state(self):
        """加载同步状态"""
        state_file = self.ai_index_path / ".sync_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self._sync_records[k] = SyncRecord(**v)
            except Exception as e:
                print(f"[ObsidianSync] Failed to load state: {e}")

    def _save_sync_state(self):
        """保存同步状态"""
        state_file = self.ai_index_path / ".sync_state.json"
        self.ai_index_path.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self._sync_records.items()}
        with open(state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _compute_hash(self, file_path: Path) -> str:
        """计算文件内容hash"""
        if file_path.exists() and file_path.is_file():
            content = file_path.read_bytes()
            return hashlib.md5(content).hexdigest()
        return ""

    def _should_process(self, file_path: Path) -> bool:
        """检查文件是否需要处理"""
        file_str = str(file_path)

        # 忽略系统文件
        if file_path.name.startswith('.'):
            return False
        if file_path.suffix not in ['.md', '.txt']:
            return False

        # 检查变化
        current_hash = self._compute_hash(file_path)
        if file_str in self._file_hashes:
            return self._file_hashes[file_str] != current_hash

        self._file_hashes[file_str] = current_hash
        return True

    def _extract_front_matter(self, content: str) -> tuple[dict, str]:
        """提取并解析YAML前置元数据"""
        fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if fm_match:
            fm_content = fm_match.group(1)
            body = content[fm_match.end():]
            fm = {}
            for line in fm_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    fm[key.strip()] = value.strip().strip('"').strip("'")
            return fm, body
        return {}, content

    def _create_front_matter(self, title: str, tags: List[str], extra: dict = None) -> str:
        """创建YAML前置元数据"""
        date = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().isoformat()
        tags_str = ', '.join(tags) if tags else 'untagged'

        fm = f"""---
date: {date}
title: {title}
tags: [{tags_str}]
source: ai-processed
processed: {timestamp}
"""
        if extra:
            for k, v in extra.items():
                fm += f"{k}: {v}\n"
        fm += "---\n\n"
        return fm

    def _process_markdown(self, content: str) -> ProcessedNote:
        """用AI处理Markdown内容"""
        # 提取前置元数据
        fm, body = self._extract_front_matter(content)

        # 提取wikilinks和外部链接
        wikilinks = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', body)
        ext_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', body)
        links = wikilinks + [l[1] for l in ext_links]

        # 提取标题
        title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
        title = title_match.group(1) if title_match else fm.get('title', 'Untitled')

        # AI生成摘要
        summary = ""
        if len(body) > 500:
            try:
                prompt = f"""请总结以下文档的要点，字数控制在100字以内：

标题：{title}

内容：
{body[:3000]}
"""
                summary = self.ai_client.generate(prompt).strip()
            except Exception as e:
                print(f"[ObsidianSync] AI summary failed: {e}")

        # 提取标签
        md_tags = re.findall(r'#([a-zA-Z0-9_-]+)', body)
        tags = list(set(md_tags + fm.get('tags', '').split(',')))
        tags = [t.strip() for t in tags if t.strip()]

        return ProcessedNote(
            title=title,
            content=body,
            summary=summary,
            tags=tags,
            links=links,
            metadata=fm
        )

    def set_on_new_file_callback(self, callback: Callable[[Path], None]):
        """设置新文件回调"""
        self._on_new_file = callback

    def set_on_sync_complete_callback(self, callback: Callable[[str, str], None]):
        """设置同步完成回调"""
        self._on_sync_complete = callback

    def sync_to_obsidian(
        self,
        title: str,
        content: str,
        folder: str = None,
        tags: List[str] = None,
        source: str = "ai-processed"
    ) -> Path:
        """
        将AI处理结果写入Obsidian Vault

        Args:
            title: 文档标题
            content: 文档内容（支持Markdown）
            folder: 存储文件夹（相对于Vault根目录）
            tags: 标签列表
            source: 来源标识

        Returns:
            写入的文件路径
        """
        if tags is None:
            tags = [source]
        if folder is None:
            folder = self.sync_folder

        # 路径安全验证 - 防止路径遍历攻击
        # 拒绝包含 .. 的路径
        if '..' in folder:
            raise ValueError(f"Path traversal detected: {folder}")

        # 拒绝绝对路径
        if folder.startswith('/') or folder.startswith('\\'):
            raise ValueError(f"Absolute path not allowed: {folder}")

        # 清理危险字符
        safe_folder = folder.replace('..', '').strip()
        if not safe_folder or safe_folder in ['.', '/', '\\']:
            safe_folder = self.sync_folder

        # 创建文件夹（确保在vault内部）
        target_folder = self.vault_path / safe_folder
        target_folder = target_folder.resolve()

        # 验证目标在vault内部
        vault_resolved = self.vault_path.resolve()
        if not str(target_folder).startswith(str(vault_resolved) + '/'):
            raise ValueError(f"Path traversal blocked: {folder}")

        target_folder.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)[:50]
        filename = f"{timestamp}-{safe_title}.md"
        filepath = target_folder / filename

        # 添加前置元数据
        fm = self._create_front_matter(title, tags, {"source": source})
        full_content = fm + content

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)

        # 记录同步
        record = SyncRecord(
            file_path=str(filepath),
            action="created",
            timestamp=datetime.now().isoformat(),
            content_hash=self._compute_hash(filepath),
            synced=True
        )
        self._sync_records[str(filepath)] = record
        self._save_sync_state()

        print(f"[ObsidianSync] Written: {filepath.relative_to(self.vault_path)}")

        if self._on_sync_complete:
            self._on_sync_complete(str(filepath), "ai_to_obsidian")

        return filepath

    def sync_file_to_ai(self, file_path: Path) -> Optional[ProcessedNote]:
        """
        将Obsidian文件同步到AI处理

        Args:
            file_path: .md文件路径

        Returns:
            处理后的笔记对象
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            note = self._process_markdown(content)

            # 记录同步
            record = SyncRecord(
                file_path=str(file_path),
                action="modified",
                timestamp=datetime.now().isoformat(),
                content_hash=self._compute_hash(file_path)
            )
            self._sync_records[str(file_path)] = record
            self._save_sync_state()

            if self._on_new_file:
                self._on_new_file(file_path)

            return note

        except Exception as e:
            print(f"[ObsidianSync] Failed to process {file_path}: {e}")
            return None

    def get_all_notes(self, folder: str = None) -> List[Path]:
        """获取Vault中的所有笔记"""
        if folder:
            search_path = self.vault_path / folder
        else:
            search_path = self.vault_path

        return list(search_path.rglob("*.md"))

    def search_vault(self, query: str, limit: int = 10) -> List[Path]:
        """搜索Vault中的笔记"""
        results = []
        query_lower = query.lower()

        for md_file in self.get_all_notes():
            try:
                content = md_file.read_text(encoding='utf-8').lower()
                if query_lower in content or query_lower in md_file.stem.lower():
                    results.append(md_file)
                    if len(results) >= limit:
                        break
            except Exception:
                continue

        return results

    def _watch_loop(self):
        """监控循环（polling模式）"""
        print(f"[ObsidianSync] Watch loop started (polling every {self.poll_interval}s)")

        while self._running:
            try:
                for md_file in self.vault_path.rglob("*.md"):
                    if self._should_process(md_file):
                        print(f"[ObsidianSync] Detected change: {md_file.name}")
                        self.sync_file_to_ai(md_file)
            except Exception as e:
                print(f"[ObsidianSync] Watch error: {e}")

            time.sleep(self.poll_interval)

    def start_watch(self):
        """启动文件监控"""
        if self._running:
            return

        self._running = True

        if self.watch_enabled:
            # 使用watchdog
            class ObsidianHandler(FileSystemEventHandler):
                def __init__(self, parent):
                    super().__init__()
                    self._parent = parent

                def on_any_event(self, event: FileSystemEvent):
                    if event.is_directory:
                        return
                    if event.src_path.endswith('.md'):
                        if event.event_type in ['created', 'modified']:
                            self._parent.sync_file_to_ai(Path(event.src_path))

            self._observer = Observer()
            self._observer.schedule(
                ObsidianHandler(self),
                str(self.vault_path),
                recursive=True
            )
            self._observer.start()
            print("[ObsidianSync] File watcher started (inotify)")
        else:
            # Polling模式
            self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._watch_thread.start()
            print(f"[ObsidianSync] File watcher started (polling)")

    def stop_watch(self):
        """停止文件监控"""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
        print("[ObsidianSync] File watcher stopped")

    def get_sync_status(self) -> dict:
        """获取同步状态"""
        return {
            "vault_path": str(self.vault_path),
            "ai_folder": str(self.ai_folder),
            "total_synced": len(self._sync_records),
            "pending": sum(1 for r in self._sync_records.values() if not r.synced),
            "watching": self._running,
            "watch_mode": "inotify" if self.watch_enabled else "polling"
        }

    def __enter__(self):
        self.start_watch()
        return self

    def __exit__(self, *args):
        self.stop_watch()


class LlamaIndexIntegration:
    """
    LlamaIndex集成层
    提供RAG能力给ObsidianSyncEngine
    """

    def __init__(self, index_path: str = "./vector_index"):
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self._index = None
        self._documents = []

    def load_documents(self, files: List[Path]):
        """加载文档到索引"""
        try:
            from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
            from llama_index.llms.ollama import Ollama
            from llama_index.core import Settings

            # 配置LLM
            llm = Ollama(model=MODEL_DOC, request_timeout=360)
            Settings.llm = llm

            # 读取文档
            docs = []
            for f in files:
                try:
                    content = f.read_text(encoding='utf-8')
                    from llama_index.core import Document
                    doc = Document(
                        text=content,
                        metadata={"source": str(f), "file_name": f.name}
                    )
                    docs.append(doc)
                except Exception as e:
                    print(f"[LlamaIndex] Failed to load {f}: {e}")

            if docs:
                # 构建索引
                self._index = VectorStoreIndex.from_documents(docs)
                self._index.storage_context.persist(str(self.index_path))
                print(f"[LlamaIndex] Indexed {len(docs)} documents")
                return True

        except ImportError as e:
            print(f"[LlamaIndex] Not available: {e}")
        except Exception as e:
            print(f"[LlamaIndex] Indexing failed: {e}")

        return False

    def query(self, question: str, limit: int = 5) -> str:
        """查询索引"""
        if self._index is None:
            return "索引未初始化"

        try:
            query_engine = self._index.as_query_engine()
            response = query_engine.query(question)
            return str(response)
        except Exception as e:
            return f"查询失败: {e}"

    def get_index_stats(self) -> dict:
        """获取索引统计"""
        if self._index is None:
            return {"status": "not_initialized"}

        return {
            "status": "ready",
            "doc_count": len(self._documents),
            "index_path": str(self.index_path)
        }
