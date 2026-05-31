#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
锁机制封装模块
=============

提供各种高级锁机制的封装，包括智能锁、读写锁、超时锁等。

🎯 **主要功能**
- 智能锁管理
- 读写锁实现
- 超时锁机制
- 死锁检测
- 锁统计和监控

📦 **核心类**
- SmartLock: 智能锁，自动管理锁的获取和释放
- ReadWriteLock: 读写锁，支持多读单写
- TimeoutLock: 超时锁，支持超时获取
- DeadlockDetector: 死锁检测器

🚀 **使用示例**
```python
# 智能锁
with SmartLock() as lock:
    # 临界区代码
    shared_resource += 1

# 读写锁
rw_lock = ReadWriteLock()
with rw_lock.read_lock():
    # 读操作
    value = shared_data

with rw_lock.write_lock():
    # 写操作
    shared_data = new_value

# 超时锁
timeout_lock = TimeoutLock(timeout=5.0)
if timeout_lock.acquire():
    try:
        # 临界区代码
        pass
    finally:
        timeout_lock.release()
```
"""

import threading
import time
import weakref
from typing import Optional, Dict, Set, Any, List
from contextlib import contextmanager
from collections import defaultdict

# 日志函数
import Lugwit_Module as LM
lprint = LM.lprint


class SmartLock:
    """
    智能锁
    
    提供自动管理的锁机制，支持上下文管理器、重入、统计等功能。
    """
    
    def __init__(self, name: str = None, reentrant: bool = True):
        """
        初始化智能锁
        
        Args:
            name: 锁名称
            reentrant: 是否支持重入
        """
        self.name = name or f"SmartLock-{id(self)}"
        self.reentrant = reentrant
        
        if reentrant:
            self._lock = threading.RLock()
        else:
            self._lock = threading.Lock()
        
        self._stats = {
            'acquire_count': 0,
            'wait_time_total': 0.0,
            'hold_time_total': 0.0,
            'max_wait_time': 0.0,
            'max_hold_time': 0.0,
            'current_holder': None,
            'acquire_time': None
        }
        self._stats_lock = threading.Lock()
    
    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        """
        获取锁
        
        Args:
            blocking: 是否阻塞
            timeout: 超时时间
        
        Returns:
            bool: 是否成功获取锁
        """
        start_time = time.time()
        
        try:
            if timeout >= 0:
                success = self._lock.acquire(blocking, timeout)
            else:
                success = self._lock.acquire(blocking)
            
            if success:
                wait_time = time.time() - start_time
                
                with self._stats_lock:
                    self._stats['acquire_count'] += 1
                    self._stats['wait_time_total'] += wait_time
                    self._stats['max_wait_time'] = max(self._stats['max_wait_time'], wait_time)
                    self._stats['current_holder'] = threading.current_thread().name
                    self._stats['acquire_time'] = time.time()
            
            return success
            
        except Exception as e:
            lprint(f"[智能锁] {self.name} 获取锁异常: {e}")
            return False
    
    def release(self):
        """释放锁"""
        try:
            with self._stats_lock:
                if self._stats['acquire_time']:
                    hold_time = time.time() - self._stats['acquire_time']
                    self._stats['hold_time_total'] += hold_time
                    self._stats['max_hold_time'] = max(self._stats['max_hold_time'], hold_time)
                
                self._stats['current_holder'] = None
                self._stats['acquire_time'] = None
            
            self._lock.release()
            
        except Exception as e:
            lprint(f"[智能锁] {self.name} 释放锁异常: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取锁统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
            
            # 计算平均时间
            if stats['acquire_count'] > 0:
                stats['avg_wait_time'] = stats['wait_time_total'] / stats['acquire_count']
                stats['avg_hold_time'] = stats['hold_time_total'] / stats['acquire_count']
            else:
                stats['avg_wait_time'] = 0.0
                stats['avg_hold_time'] = 0.0
            
            return stats
    
    def is_locked(self) -> bool:
        """检查锁是否被持有"""
        return self._stats['current_holder'] is not None


class ReadWriteLock:
    """
    读写锁
    
    支持多个读者同时访问，但写者独占访问。
    """
    
    def __init__(self, name: str = None):
        """
        初始化读写锁
        
        Args:
            name: 锁名称
        """
        self.name = name or f"ReadWriteLock-{id(self)}"
        self._read_ready = threading.Condition(threading.RLock())
        self._readers = 0
        self._writers = 0
        self._write_ready = threading.Condition(threading.RLock())
        self._current_writer = None
        
        self._stats = {
            'read_count': 0,
            'write_count': 0,
            'max_concurrent_readers': 0,
            'total_read_time': 0.0,
            'total_write_time': 0.0
        }
        self._stats_lock = threading.Lock()
    
    @contextmanager
    def read_lock(self):
        """读锁上下文管理器"""
        self.acquire_read()
        start_time = time.time()
        try:
            yield
        finally:
            read_time = time.time() - start_time
            with self._stats_lock:
                self._stats['total_read_time'] += read_time
            self.release_read()
    
    @contextmanager
    def write_lock(self):
        """写锁上下文管理器"""
        self.acquire_write()
        start_time = time.time()
        try:
            yield
        finally:
            write_time = time.time() - start_time
            with self._stats_lock:
                self._stats['total_write_time'] += write_time
            self.release_write()
    
    def acquire_read(self):
        """获取读锁"""
        with self._read_ready:
            while self._writers > 0:
                self._read_ready.wait()
            self._readers += 1
            
            with self._stats_lock:
                self._stats['read_count'] += 1
                self._stats['max_concurrent_readers'] = max(
                    self._stats['max_concurrent_readers'], self._readers
                )
    
    def release_read(self):
        """释放读锁"""
        with self._read_ready:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notifyAll()
    
    def acquire_write(self):
        """获取写锁"""
        with self._write_ready:
            while self._writers > 0 or self._readers > 0:
                self._write_ready.wait()
            self._writers += 1
            self._current_writer = threading.current_thread().name
            
            with self._stats_lock:
                self._stats['write_count'] += 1
    
    def release_write(self):
        """释放写锁"""
        with self._write_ready:
            self._writers -= 1
            self._current_writer = None
            self._write_ready.notifyAll()
        
        with self._read_ready:
            self._read_ready.notifyAll()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取读写锁统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
            stats['current_readers'] = self._readers
            stats['current_writers'] = self._writers
            stats['current_writer_thread'] = self._current_writer
            
            # 计算平均时间
            if stats['read_count'] > 0:
                stats['avg_read_time'] = stats['total_read_time'] / stats['read_count']
            else:
                stats['avg_read_time'] = 0.0
            
            if stats['write_count'] > 0:
                stats['avg_write_time'] = stats['total_write_time'] / stats['write_count']
            else:
                stats['avg_write_time'] = 0.0
            
            return stats


class TimeoutLock:
    """
    超时锁
    
    支持超时获取的锁机制。
    """
    
    def __init__(self, timeout: float = 5.0, name: str = None):
        """
        初始化超时锁
        
        Args:
            timeout: 默认超时时间
            name: 锁名称
        """
        self.default_timeout = timeout
        self.name = name or f"TimeoutLock-{id(self)}"
        self._lock = threading.Lock()
        self._holder = None
        self._acquire_time = None
        
        self._stats = {
            'acquire_attempts': 0,
            'acquire_success': 0,
            'acquire_timeout': 0,
            'total_wait_time': 0.0,
            'max_wait_time': 0.0
        }
        self._stats_lock = threading.Lock()
    
    def acquire(self, timeout: float = None) -> bool:
        """
        获取锁
        
        Args:
            timeout: 超时时间，None使用默认值
        
        Returns:
            bool: 是否成功获取锁
        """
        if timeout is None:
            timeout = self.default_timeout
        
        start_time = time.time()
        
        with self._stats_lock:
            self._stats['acquire_attempts'] += 1
        
        try:
            success = self._lock.acquire(timeout=timeout)
            wait_time = time.time() - start_time
            
            with self._stats_lock:
                self._stats['total_wait_time'] += wait_time
                self._stats['max_wait_time'] = max(self._stats['max_wait_time'], wait_time)
                
                if success:
                    self._stats['acquire_success'] += 1
                    self._holder = threading.current_thread().name
                    self._acquire_time = time.time()
                else:
                    self._stats['acquire_timeout'] += 1
            
            return success
            
        except Exception as e:
            lprint(f"[超时锁] {self.name} 获取锁异常: {e}")
            return False
    
    def release(self):
        """释放锁"""
        try:
            with self._stats_lock:
                self._holder = None
                self._acquire_time = None
            
            self._lock.release()
            
        except Exception as e:
            lprint(f"[超时锁] {self.name} 释放锁异常: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        if not self.acquire():
            raise TimeoutError(f"获取锁 {self.name} 超时")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取超时锁统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()
            stats['current_holder'] = self._holder
            stats['acquire_time'] = self._acquire_time
            
            # 计算成功率和平均等待时间
            if stats['acquire_attempts'] > 0:
                stats['success_rate'] = stats['acquire_success'] / stats['acquire_attempts']
                stats['avg_wait_time'] = stats['total_wait_time'] / stats['acquire_attempts']
            else:
                stats['success_rate'] = 0.0
                stats['avg_wait_time'] = 0.0
            
            return stats


class DeadlockDetector:
    """
    死锁检测器
    
    检测和报告潜在的死锁情况。
    """
    
    def __init__(self):
        """初始化死锁检测器"""
        self._lock_graph = defaultdict(set)  # 锁依赖图
        self._thread_locks = defaultdict(set)  # 线程持有的锁
        self._waiting_for = {}  # 线程等待的锁
        self._detector_lock = threading.Lock()
    
    def register_lock_acquire(self, thread_id: str, lock_id: str):
        """
        注册锁获取
        
        Args:
            thread_id: 线程ID
            lock_id: 锁ID
        """
        with self._detector_lock:
            # 检查是否会形成死锁
            if self._would_cause_deadlock(thread_id, lock_id):
                lprint(f"[死锁检测] 警告: 线程 {thread_id} 获取锁 {lock_id} 可能导致死锁")
            
            self._thread_locks[thread_id].add(lock_id)
            
            # 更新锁依赖图
            if thread_id in self._waiting_for:
                waiting_lock = self._waiting_for[thread_id]
                self._lock_graph[waiting_lock].add(lock_id)
                del self._waiting_for[thread_id]
    
    def register_lock_wait(self, thread_id: str, lock_id: str):
        """
        注册锁等待
        
        Args:
            thread_id: 线程ID
            lock_id: 锁ID
        """
        with self._detector_lock:
            self._waiting_for[thread_id] = lock_id
    
    def register_lock_release(self, thread_id: str, lock_id: str):
        """
        注册锁释放
        
        Args:
            thread_id: 线程ID
            lock_id: 锁ID
        """
        with self._detector_lock:
            self._thread_locks[thread_id].discard(lock_id)
            
            # 清理空的线程记录
            if not self._thread_locks[thread_id]:
                del self._thread_locks[thread_id]
    
    def _would_cause_deadlock(self, thread_id: str, lock_id: str) -> bool:
        """
        检查获取锁是否会导致死锁
        
        Args:
            thread_id: 线程ID
            lock_id: 锁ID
        
        Returns:
            bool: 是否会导致死锁
        """
        # 简化的死锁检测：检查是否存在循环等待
        visited = set()
        
        def has_cycle(current_lock):
            if current_lock in visited:
                return True
            
            visited.add(current_lock)
            
            for next_lock in self._lock_graph[current_lock]:
                if has_cycle(next_lock):
                    return True
            
            visited.remove(current_lock)
            return False
        
        # 检查从当前锁开始是否存在循环
        return has_cycle(lock_id)
    
    def get_deadlock_report(self) -> Dict[str, Any]:
        """
        获取死锁检测报告
        
        Returns:
            Dict: 死锁检测报告
        """
        with self._detector_lock:
            return {
                'lock_graph': dict(self._lock_graph),
                'thread_locks': dict(self._thread_locks),
                'waiting_for': dict(self._waiting_for),
                'potential_deadlocks': self._find_potential_deadlocks()
            }
    
    def _find_potential_deadlocks(self) -> List[List[str]]:
        """查找潜在的死锁循环"""
        cycles = []
        visited = set()
        
        def dfs(lock, path):
            if lock in path:
                # 找到循环
                cycle_start = path.index(lock)
                cycle = path[cycle_start:] + [lock]
                cycles.append(cycle)
                return
            
            if lock in visited:
                return
            
            visited.add(lock)
            path.append(lock)
            
            for next_lock in self._lock_graph[lock]:
                dfs(next_lock, path)
            
            path.pop()
        
        for lock in self._lock_graph:
            if lock not in visited:
                dfs(lock, [])
        
        return cycles


# === 便捷函数 ===

def create_smart_lock(name: str = None, reentrant: bool = True) -> SmartLock:
    """
    创建智能锁
    
    Args:
        name: 锁名称
        reentrant: 是否支持重入
    
    Returns:
        SmartLock: 智能锁实例
    """
    return SmartLock(name, reentrant)


def create_read_write_lock(name: str = None) -> ReadWriteLock:
    """
    创建读写锁
    
    Args:
        name: 锁名称
    
    Returns:
        ReadWriteLock: 读写锁实例
    """
    return ReadWriteLock(name)


def create_timeout_lock(timeout: float = 5.0, name: str = None) -> TimeoutLock:
    """
    创建超时锁
    
    Args:
        timeout: 超时时间
        name: 锁名称
    
    Returns:
        TimeoutLock: 超时锁实例
    """
    return TimeoutLock(timeout, name)


# 全局死锁检测器实例
_global_deadlock_detector = DeadlockDetector()


def get_deadlock_detector() -> DeadlockDetector:
    """获取全局死锁检测器"""
    return _global_deadlock_detector


# === 导出列表 ===

__all__ = [
    'SmartLock',
    'ReadWriteLock',
    'TimeoutLock',
    'DeadlockDetector',
    'create_smart_lock',
    'create_read_write_lock',
    'create_timeout_lock',
    'get_deadlock_detector'
]
