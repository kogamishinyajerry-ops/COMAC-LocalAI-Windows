"""
任务管理器 - 支持任务取消和中断
"""

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import time


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskInfo:
    task_id: str
    description: str
    agent: str
    state: TaskState = TaskState.PENDING
    progress: int = 0
    result: Any = None
    error: str = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime = None
    completed_at: datetime = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def cancel(self):
        self.cancel_event.set()
        self.state = TaskState.CANCELLED


class TaskManager:
    """
    全局任务管理器
    支持任务追踪、取消、打断
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._tasks: Dict[str, TaskInfo] = {}
        self._current_task_id: Optional[str] = None
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()

    def create_task(self, description: str, agent: str) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._tasks[task_id] = TaskInfo(
                task_id=task_id,
                description=description,
                agent=agent
            )
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务信息。

        Args:
            task_id: 任务ID

        Returns:
            任务信息对象，如果不存在则返回None
        """
        return self._tasks.get(task_id)

    def get_current_task_id(self) -> Optional[str]:
        return self._current_task_id

    def set_current_task(self, task_id: str):
        self._current_task_id = task_id

    def clear_current_task(self):
        self._current_task_id = None

    def update_progress(self, task_id: str, progress: int, state: TaskState = None):
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.progress = progress
                if state:
                    task.state = state
                if state == TaskState.RUNNING and task.started_at is None:
                    task.started_at = datetime.now()

    def complete_task(self, task_id: str, result: Any = None, error: str = None):
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.result = result
                task.error = error
                task.completed_at = datetime.now()
                if error:
                    task.state = TaskState.FAILED
                else:
                    task.state = TaskState.COMPLETED

                if self._current_task_id == task_id:
                    self._current_task_id = None

    def cancel_task(self, task_id: str):
        """
        取消指定任务。

        Args:
            task_id: 要取消的任务ID
        """
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.cancel()
                if self._current_task_id == task_id:
                    self._current_task_id = None

    def cancel_current_task(self):
        """取消当前正在执行的任务"""
        if self._current_task_id:
            self.cancel_task(self._current_task_id)

    def get_all_tasks(self) -> List[TaskInfo]:
        with self._lock:
            return list(self._tasks.values())

    def get_active_tasks(self) -> List[TaskInfo]:
        with self._lock:
            return [t for t in self._tasks.values()
                   if t.state in [TaskState.PENDING, TaskState.RUNNING]]

    def clear_completed(self):
        with self._lock:
            self._tasks = {
                k: v for k, v in self._tasks.items()
                if v.state in [TaskState.PENDING, TaskState.RUNNING]
            }

    def is_cancelled(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task:
            return task.is_cancelled()
        return False


# 全局实例
task_manager = TaskManager()
