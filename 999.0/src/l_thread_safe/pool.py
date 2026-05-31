#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
线程池管理模块
=============

提供高级的线程池管理功能，包括工作线程、任务调度、资源管理等。

🎯 **主要功能**
- 智能线程池管理
- 任务优先级调度
- 线程生命周期管理
- 资源监控和统计

📦 **核心类**
- ThreadPoolManager: 线程池管理器
- WorkerThread: 工作线程
- TaskInfo: 任务信息
- PoolStats: 池统计信息

🚀 **使用示例**
```python
# 创建线程池
pool = ThreadPoolManager(max_workers=4)

# 提交任务
future = pool.submit(my_function, arg1, arg2)
result = future.result()

# 批量提交任务
futures = pool.map(process_item, item_list)
results = [f.result() for f in futures]

# 关闭线程池
pool.shutdown()
```
"""

import threading
import queue
import time
import concurrent.futures
from typing import Any, Callable, List, Optional, Dict, Union
from dataclasses import dataclass
from enum import Enum

# 日志函数
import Lugwit_Module as LM
lprint = LM.lprint


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class WorkerState(Enum):
    """工作线程状态"""
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    submit_time: float
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[Exception] = None
    worker_id: Optional[str] = None


@dataclass
class PoolStats:
    """线程池统计信息"""
    total_workers: int
    active_workers: int
    idle_workers: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    pending_tasks: int
    average_task_time: float
    pool_utilization: float


class WorkerThread(threading.Thread):
    """
    工作线程
    
    负责从任务队列中获取任务并执行。
    """
    
    def __init__(self, worker_id: str, task_queue: queue.PriorityQueue, 
                 stats_callback: Callable = None):
        """
        初始化工作线程
        
        Args:
            worker_id: 工作线程ID
            task_queue: 任务队列
            stats_callback: 统计回调函数
        """
        super().__init__(name=f"Worker-{worker_id}")
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.stats_callback = stats_callback
        self.state = WorkerState.IDLE
        self.current_task = None
        self.total_tasks = 0
        self.daemon = True
        self._stop_event = threading.Event()
        
        lprint(f"[线程池] 工作线程 {worker_id} 已创建")
    
    def run(self):
        """线程主循环"""
        lprint(f"[线程池] 工作线程 {self.worker_id} 开始运行")
        
        while not self._stop_event.is_set():
            try:
                # 获取任务（带超时，以便检查停止信号）
                try:
                    priority, task_info = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                if task_info is None:  # 毒丸，停止信号
                    break
                
                self.current_task = task_info
                self.state = WorkerState.RUNNING
                
                # 执行任务
                self._execute_task(task_info)
                
                self.current_task = None
                self.state = WorkerState.IDLE
                self.total_tasks += 1
                
                # 标记任务完成
                self.task_queue.task_done()
                
            except Exception as e:
                lprint(f"[线程池] 工作线程 {self.worker_id} 异常: {e}")
                if self.current_task:
                    self.current_task.error = e
                    self.current_task.end_time = time.time()
        
        self.state = WorkerState.STOPPED
        lprint(f"[线程池] 工作线程 {self.worker_id} 已停止")
    
    def _execute_task(self, task_info: TaskInfo):
        """
        执行任务
        
        Args:
            task_info: 任务信息
        """
        task_info.start_time = time.time()
        task_info.worker_id = self.worker_id
        
        try:
            lprint(f"[线程池] 工作线程 {self.worker_id} 开始执行任务 {task_info.task_id}")
            
            # 执行任务函数
            result = task_info.func(*task_info.args, **task_info.kwargs)
            task_info.result = result
            task_info.end_time = time.time()
            
            # 统计回调
            if self.stats_callback:
                self.stats_callback('task_completed', task_info)
            
            lprint(f"[线程池] 任务 {task_info.task_id} 执行完成")
            
        except Exception as e:
            task_info.error = e
            task_info.end_time = time.time()
            
            if self.stats_callback:
                self.stats_callback('task_failed', task_info)
            
            lprint(f"[线程池] 任务 {task_info.task_id} 执行失败: {e}")
    
    def stop(self):
        """停止工作线程"""
        self.state = WorkerState.STOPPING
        self._stop_event.set()
    
    def is_idle(self):
        """检查是否空闲"""
        return self.state == WorkerState.IDLE
    
    def is_running(self):
        """检查是否正在运行"""
        return self.state == WorkerState.RUNNING


class ThreadPoolManager:
    """
    线程池管理器
    
    提供高级的线程池管理功能，包括任务调度、资源监控等。
    """
    
    def __init__(self, max_workers: int = 4, queue_size: int = 0):
        """
        初始化线程池管理器
        
        Args:
            max_workers: 最大工作线程数
            queue_size: 任务队列大小，0表示无限制
        """
        self.max_workers = max_workers
        self.task_queue = queue.PriorityQueue(maxsize=queue_size)
        self.workers = {}
        self.task_futures = {}
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'task_times': []
        }
        self._shutdown = False
        self._lock = threading.RLock()
        
        # 创建工作线程
        self._create_workers()
        
        lprint(f"[线程池] 线程池管理器已创建，工作线程数: {max_workers}")
    
    def _create_workers(self):
        """创建工作线程"""
        for i in range(self.max_workers):
            worker_id = f"worker-{i+1}"
            worker = WorkerThread(worker_id, self.task_queue, self._stats_callback)
            self.workers[worker_id] = worker
            worker.start()
    
    def _stats_callback(self, event_type: str, task_info: TaskInfo):
        """统计回调"""
        with self._lock:
            if event_type == 'task_completed':
                self.stats['completed_tasks'] += 1
                if task_info.start_time and task_info.end_time:
                    task_time = task_info.end_time - task_info.start_time
                    self.stats['task_times'].append(task_time)
            elif event_type == 'task_failed':
                self.stats['failed_tasks'] += 1
    
    def submit(self, func: Callable, *args, priority: TaskPriority = TaskPriority.NORMAL, 
               task_id: str = None, **kwargs) -> concurrent.futures.Future:
        """
        提交任务
        
        Args:
            func: 任务函数
            *args: 位置参数
            priority: 任务优先级
            task_id: 任务ID
            **kwargs: 关键字参数
        
        Returns:
            Future: 任务的Future对象
        """
        if self._shutdown:
            raise RuntimeError("线程池已关闭")
        
        if task_id is None:
            task_id = f"task-{int(time.time()*1000)}-{id(func)}"
        
        # 创建任务信息
        task_info = TaskInfo(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            submit_time=time.time()
        )
        
        # 创建Future
        future = concurrent.futures.Future()
        self.task_futures[task_id] = (future, task_info)
        
        # 将任务加入队列（优先级越高，数值越小）
        priority_value = 5 - priority.value  # 转换为队列优先级
        self.task_queue.put((priority_value, task_info))
        
        with self._lock:
            self.stats['total_tasks'] += 1
        
        # 启动监控线程（如果还没启动）
        self._start_monitor_thread()
        
        lprint(f"[线程池] 任务 {task_id} 已提交，优先级: {priority.name}")
        return future
    
    def _start_monitor_thread(self):
        """启动监控线程"""
        if not hasattr(self, '_monitor_thread') or not self._monitor_thread.is_alive():
            self._monitor_thread = threading.Thread(target=self._monitor_tasks, daemon=True)
            self._monitor_thread.start()
    
    def _monitor_tasks(self):
        """监控任务执行"""
        while not self._shutdown:
            completed_tasks = []
            
            with self._lock:
                for task_id, (future, task_info) in self.task_futures.items():
                    if task_info.end_time:  # 任务已完成
                        if task_info.error:
                            future.set_exception(task_info.error)
                        else:
                            future.set_result(task_info.result)
                        completed_tasks.append(task_id)
            
            # 清理已完成的任务
            for task_id in completed_tasks:
                del self.task_futures[task_id]
            
            time.sleep(0.1)  # 避免过度占用CPU
    
    def map(self, func: Callable, iterable, priority: TaskPriority = TaskPriority.NORMAL) -> List[concurrent.futures.Future]:
        """
        批量提交任务
        
        Args:
            func: 任务函数
            iterable: 参数列表
            priority: 任务优先级
        
        Returns:
            List[Future]: Future对象列表
        """
        futures = []
        for i, item in enumerate(iterable):
            task_id = f"map-task-{i}"
            future = self.submit(func, item, priority=priority, task_id=task_id)
            futures.append(future)
        return futures
    
    def shutdown(self, wait: bool = True, timeout: float = None):
        """
        关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
            timeout: 等待超时时间
        """
        lprint("[线程池] 开始关闭线程池...")
        
        self._shutdown = True
        
        if wait:
            # 等待队列中的任务完成
            if timeout:
                start_time = time.time()
                while not self.task_queue.empty():
                    if time.time() - start_time > timeout:
                        lprint("[线程池] 等待超时，强制关闭")
                        break
                    time.sleep(0.1)
            else:
                self.task_queue.join()
        
        # 发送停止信号给所有工作线程
        for _ in self.workers:
            self.task_queue.put((0, None))  # 毒丸
        
        # 等待所有工作线程停止
        for worker in self.workers.values():
            worker.stop()
            if wait:
                worker.join(timeout=5.0)
        
        lprint("[线程池] 线程池已关闭")
    
    def get_stats(self) -> PoolStats:
        """
        获取线程池统计信息
        
        Returns:
            PoolStats: 统计信息
        """
        with self._lock:
            active_workers = sum(1 for w in self.workers.values() if w.is_running())
            idle_workers = sum(1 for w in self.workers.values() if w.is_idle())
            
            avg_task_time = 0.0
            if self.stats['task_times']:
                avg_task_time = sum(self.stats['task_times']) / len(self.stats['task_times'])
            
            utilization = active_workers / self.max_workers if self.max_workers > 0 else 0.0
            
            return PoolStats(
                total_workers=self.max_workers,
                active_workers=active_workers,
                idle_workers=idle_workers,
                total_tasks=self.stats['total_tasks'],
                completed_tasks=self.stats['completed_tasks'],
                failed_tasks=self.stats['failed_tasks'],
                pending_tasks=self.task_queue.qsize(),
                average_task_time=avg_task_time,
                pool_utilization=utilization
            )
    
    def get_worker_info(self) -> Dict[str, Dict]:
        """
        获取工作线程信息
        
        Returns:
            Dict: 工作线程信息字典
        """
        info = {}
        for worker_id, worker in self.workers.items():
            info[worker_id] = {
                'state': worker.state.value,
                'total_tasks': worker.total_tasks,
                'current_task': worker.current_task.task_id if worker.current_task else None,
                'is_alive': worker.is_alive()
            }
        return info
    
    def resize(self, new_size: int):
        """
        调整线程池大小
        
        Args:
            new_size: 新的线程池大小
        """
        if new_size == self.max_workers:
            return
        
        lprint(f"[线程池] 调整线程池大小: {self.max_workers} -> {new_size}")
        
        if new_size > self.max_workers:
            # 增加工作线程
            for i in range(self.max_workers, new_size):
                worker_id = f"worker-{i+1}"
                worker = WorkerThread(worker_id, self.task_queue, self._stats_callback)
                self.workers[worker_id] = worker
                worker.start()
        else:
            # 减少工作线程
            workers_to_remove = list(self.workers.keys())[new_size:]
            for worker_id in workers_to_remove:
                worker = self.workers[worker_id]
                worker.stop()
                del self.workers[worker_id]
        
        self.max_workers = new_size
    
    def clear_queue(self):
        """清空任务队列"""
        cleared_count = 0
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
                cleared_count += 1
            except queue.Empty:
                break
        
        lprint(f"[线程池] 已清空 {cleared_count} 个待处理任务")
        return cleared_count


# === 便捷函数 ===

def create_thread_pool(max_workers: int = 4, queue_size: int = 0) -> ThreadPoolManager:
    """
    创建线程池
    
    Args:
        max_workers: 最大工作线程数
        queue_size: 任务队列大小
    
    Returns:
        ThreadPoolManager: 线程池管理器
    """
    return ThreadPoolManager(max_workers, queue_size)


def execute_in_thread_pool(func: Callable, args_list: List, max_workers: int = 4) -> List[Any]:
    """
    在线程池中执行函数列表
    
    Args:
        func: 要执行的函数
        args_list: 参数列表
        max_workers: 最大工作线程数
    
    Returns:
        List[Any]: 结果列表
    """
    pool = create_thread_pool(max_workers)
    try:
        futures = pool.map(func, args_list)
        results = [future.result() for future in futures]
        return results
    finally:
        pool.shutdown()


# === 导出列表 ===

__all__ = [
    'ThreadPoolManager',
    'WorkerThread',
    'TaskInfo',
    'PoolStats',
    'TaskPriority',
    'WorkerState',
    'create_thread_pool',
    'execute_in_thread_pool'
]
