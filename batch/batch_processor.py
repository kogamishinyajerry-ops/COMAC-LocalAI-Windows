from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Callable, Any, Optional
from enum import Enum
import time

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class Task:
    task_id: str
    input_path: str
    output_path: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

@dataclass
class BatchResult:
    total: int
    success: int
    failed: int
    tasks: List[Task]
    duration: float

class BatchProcessor:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.tasks: List[Task] = []

    def add_task(self, input_path: str, output_path: str = None) -> Task:
        task_id = f"task_{len(self.tasks) + 1}"
        task = Task(
            task_id=task_id,
            input_path=input_path,
            output_path=output_path
        )
        self.tasks.append(task)
        return task

    def process(self, process_func: Callable[[str, str], Any]) -> BatchResult:
        start_time = time.time()
        success_count = 0
        failed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(process_func, task.input_path, task.output_path): task
                for task in self.tasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                task.start_time = time.time()

                try:
                    task.result = future.result()
                    task.status = TaskStatus.SUCCESS
                    success_count += 1
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    failed_count += 1

                task.end_time = time.time()

        duration = time.time() - start_time

        return BatchResult(
            total=len(self.tasks),
            success=success_count,
            failed=failed_count,
            tasks=self.tasks,
            duration=duration
        )

    def get_progress(self) -> dict:
        total = len(self.tasks)
        if total == 0:
            return {"total": 0, "completed": 0, "progress": 0}

        completed = sum(1 for t in self.tasks if t.status in [TaskStatus.SUCCESS, TaskStatus.FAILED])

        return {
            "total": total,
            "completed": completed,
            "progress": int(completed / total * 100)
        }
