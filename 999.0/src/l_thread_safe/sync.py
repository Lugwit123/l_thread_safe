#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
线程安全数据同步工具模块
======================

提供各种线程安全的数据结构和同步机制，确保多线程环境下的数据一致性。

🎯 **主要功能**
- 线程安全的数据容器
- 读写锁保护的数据结构
- 原子操作封装
- 条件变量同步

📦 **核心类**
- ThreadSafeData: 通用线程安全数据容器
- ThreadSafeQueue: 线程安全队列
- ThreadSafeDict: 线程安全字典
- ThreadSafeList: 线程安全列表

🚀 **使用示例**
```python
# 线程安全数据容器
data = ThreadSafeData(initial_value={"count": 0})
data.update(lambda d: d.update({"count": d["count"] + 1}))

# 线程安全队列
queue = ThreadSafeQueue()
queue.put("item1")
item = queue.get()

# 线程安全字典
safe_dict = ThreadSafeDict()
safe_dict["key"] = "value"
value = safe_dict.get("key")
```
"""

import threading
import queue
import time
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import contextmanager

# 日志函数
import Lugwit_Module as LM
lprint = LM.lprint


class ThreadSafeData:
    """
    通用线程安全数据容器
    
    使用读写锁保护数据，支持原子操作和条件等待。
    """
    
    def __init__(self, initial_value=None):
        """
        初始化线程安全数据容器
        
        Args:
            initial_value: 初始值
        """
        self._data = initial_value
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._version = 0  # 数据版本号，用于检测变化
    
    def get(self):
        """
        获取数据（读操作）
        
        Returns:
            当前数据的副本
        """
        with self._lock:
            return self._data
    
    def set(self, value):
        """
        设置数据（写操作）
        
        Args:
            value: 新值
        """
        with self._lock:
            self._data = value
            self._version += 1
            self._condition.notify_all()
    
    def update(self, func: Callable[[Any], Any]):
        """
        原子更新操作
        
        Args:
            func: 更新函数，接收当前数据，返回新数据
        
        Returns:
            更新后的数据
        """
        with self._lock:
            self._data = func(self._data)
            self._version += 1
            self._condition.notify_all()
            return self._data
    
    def compare_and_swap(self, expected, new_value):
        """
        比较并交换操作（CAS）
        
        Args:
            expected: 期望的当前值
            new_value: 新值
        
        Returns:
            bool: 是否成功交换
        """
        with self._lock:
            if self._data == expected:
                self._data = new_value
                self._version += 1
                self._condition.notify_all()
                return True
            return False
    
    def wait_for_condition(self, condition_func: Callable[[Any], bool], timeout=None):
        """
        等待条件满足
        
        Args:
            condition_func: 条件函数，接收数据，返回bool
            timeout: 超时时间（秒）
        
        Returns:
            bool: 条件是否满足（False表示超时）
        """
        with self._condition:
            return self._condition.wait_for(lambda: condition_func(self._data), timeout)
    
    def wait_for_change(self, timeout=None):
        """
        等待数据变化
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            bool: 是否有变化（False表示超时）
        """
        with self._condition:
            current_version = self._version
            return self._condition.wait_for(lambda: self._version != current_version, timeout)
    
    @contextmanager
    def lock(self):
        """
        获取锁的上下文管理器
        
        使用示例:
            with data.lock():
                # 在这里进行复杂的原子操作
                current = data._data
                data._data = process(current)
        """
        with self._lock:
            yield self
    
    def get_version(self):
        """获取数据版本号"""
        with self._lock:
            return self._version


class ThreadSafeQueue:
    """
    线程安全队列
    
    基于queue.Queue的封装，提供额外的功能。
    """
    
    def __init__(self, maxsize=0):
        """
        初始化线程安全队列
        
        Args:
            maxsize: 最大队列大小，0表示无限制
        """
        self._queue = queue.Queue(maxsize)
        self._stats = ThreadSafeData({
            'put_count': 0,
            'get_count': 0,
            'peak_size': 0
        })
    
    def put(self, item, block=True, timeout=None):
        """
        放入项目
        
        Args:
            item: 要放入的项目
            block: 是否阻塞
            timeout: 超时时间
        """
        self._queue.put(item, block, timeout)
        self._stats.update(lambda s: {
            **s,
            'put_count': s['put_count'] + 1,
            'peak_size': max(s['peak_size'], self.qsize())
        })
    
    def get(self, block=True, timeout=None):
        """
        获取项目
        
        Args:
            block: 是否阻塞
            timeout: 超时时间
        
        Returns:
            队列中的项目
        """
        item = self._queue.get(block, timeout)
        self._stats.update(lambda s: {**s, 'get_count': s['get_count'] + 1})
        return item
    
    def put_nowait(self, item):
        """非阻塞放入"""
        return self.put(item, block=False)
    
    def get_nowait(self):
        """非阻塞获取"""
        return self.get(block=False)
    
    def qsize(self):
        """获取队列大小"""
        return self._queue.qsize()
    
    def empty(self):
        """检查队列是否为空"""
        return self._queue.empty()
    
    def full(self):
        """检查队列是否已满"""
        return self._queue.full()
    
    def clear(self):
        """清空队列"""
        while not self.empty():
            try:
                self.get_nowait()
            except queue.Empty:
                break
    
    def get_stats(self):
        """获取统计信息"""
        return self._stats.get()
    
    def wait_for_item(self, timeout=None):
        """
        等待队列中有项目
        
        Args:
            timeout: 超时时间
        
        Returns:
            bool: 是否有项目可用
        """
        start_time = time.time()
        while self.empty():
            if timeout and (time.time() - start_time) > timeout:
                return False
            time.sleep(0.01)
        return True


class ThreadSafeDict:
    """
    线程安全字典
    
    提供字典的所有基本操作，并确保线程安全。
    """
    
    def __init__(self, initial_dict=None):
        """
        初始化线程安全字典
        
        Args:
            initial_dict: 初始字典数据
        """
        self._dict = dict(initial_dict) if initial_dict else {}
        self._lock = threading.RLock()
    
    def __getitem__(self, key):
        """获取项目"""
        with self._lock:
            return self._dict[key]
    
    def __setitem__(self, key, value):
        """设置项目"""
        with self._lock:
            self._dict[key] = value
    
    def __delitem__(self, key):
        """删除项目"""
        with self._lock:
            del self._dict[key]
    
    def __contains__(self, key):
        """检查键是否存在"""
        with self._lock:
            return key in self._dict
    
    def __len__(self):
        """获取字典长度"""
        with self._lock:
            return len(self._dict)
    
    def get(self, key, default=None):
        """安全获取值"""
        with self._lock:
            return self._dict.get(key, default)
    
    def pop(self, key, default=None):
        """弹出值"""
        with self._lock:
            return self._dict.pop(key, default)
    
    def keys(self):
        """获取所有键"""
        with self._lock:
            return list(self._dict.keys())
    
    def values(self):
        """获取所有值"""
        with self._lock:
            return list(self._dict.values())
    
    def items(self):
        """获取所有键值对"""
        with self._lock:
            return list(self._dict.items())
    
    def update(self, other):
        """更新字典"""
        with self._lock:
            self._dict.update(other)
    
    def clear(self):
        """清空字典"""
        with self._lock:
            self._dict.clear()
    
    def copy(self):
        """复制字典"""
        with self._lock:
            return dict(self._dict)
    
    def setdefault(self, key, default=None):
        """设置默认值"""
        with self._lock:
            return self._dict.setdefault(key, default)
    
    @contextmanager
    def lock(self):
        """获取锁的上下文管理器"""
        with self._lock:
            yield self._dict


class ThreadSafeList:
    """
    线程安全列表
    
    提供列表的所有基本操作，并确保线程安全。
    """
    
    def __init__(self, initial_list=None):
        """
        初始化线程安全列表
        
        Args:
            initial_list: 初始列表数据
        """
        self._list = list(initial_list) if initial_list else []
        self._lock = threading.RLock()
    
    def __getitem__(self, index):
        """获取项目"""
        with self._lock:
            return self._list[index]
    
    def __setitem__(self, index, value):
        """设置项目"""
        with self._lock:
            self._list[index] = value
    
    def __delitem__(self, index):
        """删除项目"""
        with self._lock:
            del self._list[index]
    
    def __len__(self):
        """获取列表长度"""
        with self._lock:
            return len(self._list)
    
    def __contains__(self, item):
        """检查项目是否存在"""
        with self._lock:
            return item in self._list
    
    def append(self, item):
        """添加项目"""
        with self._lock:
            self._list.append(item)
    
    def extend(self, items):
        """扩展列表"""
        with self._lock:
            self._list.extend(items)
    
    def insert(self, index, item):
        """插入项目"""
        with self._lock:
            self._list.insert(index, item)
    
    def remove(self, item):
        """移除项目"""
        with self._lock:
            self._list.remove(item)
    
    def pop(self, index=-1):
        """弹出项目"""
        with self._lock:
            return self._list.pop(index)
    
    def index(self, item, start=0, stop=None):
        """查找项目索引"""
        with self._lock:
            if stop is None:
                return self._list.index(item, start)
            else:
                return self._list.index(item, start, stop)
    
    def count(self, item):
        """计算项目数量"""
        with self._lock:
            return self._list.count(item)
    
    def sort(self, key=None, reverse=False):
        """排序列表"""
        with self._lock:
            self._list.sort(key=key, reverse=reverse)
    
    def reverse(self):
        """反转列表"""
        with self._lock:
            self._list.reverse()
    
    def clear(self):
        """清空列表"""
        with self._lock:
            self._list.clear()
    
    def copy(self):
        """复制列表"""
        with self._lock:
            return list(self._list)
    
    @contextmanager
    def lock(self):
        """获取锁的上下文管理器"""
        with self._lock:
            yield self._list


class ThreadSafeCounter:
    """
    线程安全计数器
    
    提供原子的计数操作。
    """
    
    def __init__(self, initial_value=0):
        """
        初始化计数器
        
        Args:
            initial_value: 初始值
        """
        self._value = initial_value
        self._lock = threading.Lock()
    
    def increment(self, delta=1):
        """
        增加计数
        
        Args:
            delta: 增加量
        
        Returns:
            int: 增加后的值
        """
        with self._lock:
            self._value += delta
            return self._value
    
    def decrement(self, delta=1):
        """
        减少计数
        
        Args:
            delta: 减少量
        
        Returns:
            int: 减少后的值
        """
        with self._lock:
            self._value -= delta
            return self._value
    
    def get(self):
        """获取当前值"""
        with self._lock:
            return self._value
    
    def set(self, value):
        """设置值"""
        with self._lock:
            self._value = value
    
    def reset(self):
        """重置为0"""
        with self._lock:
            self._value = 0


# === 便捷函数 ===

def create_shared_data(initial_value=None):
    """
    创建共享数据容器
    
    Args:
        initial_value: 初始值
    
    Returns:
        ThreadSafeData: 线程安全数据容器
    """
    return ThreadSafeData(initial_value)

def create_shared_queue(maxsize=0):
    """
    创建共享队列
    
    Args:
        maxsize: 最大队列大小
    
    Returns:
        ThreadSafeQueue: 线程安全队列
    """
    return ThreadSafeQueue(maxsize)

def create_shared_dict(initial_dict=None):
    """
    创建共享字典
    
    Args:
        initial_dict: 初始字典
    
    Returns:
        ThreadSafeDict: 线程安全字典
    """
    return ThreadSafeDict(initial_dict)

def create_shared_list(initial_list=None):
    """
    创建共享列表
    
    Args:
        initial_list: 初始列表
    
    Returns:
        ThreadSafeList: 线程安全列表
    """
    return ThreadSafeList(initial_list)

def create_counter(initial_value=0):
    """
    创建线程安全计数器
    
    Args:
        initial_value: 初始值
    
    Returns:
        ThreadSafeCounter: 线程安全计数器
    """
    return ThreadSafeCounter(initial_value)


# === 导出列表 ===

__all__ = [
    'ThreadSafeData',
    'ThreadSafeQueue', 
    'ThreadSafeDict',
    'ThreadSafeList',
    'ThreadSafeCounter',
    'create_shared_data',
    'create_shared_queue',
    'create_shared_dict',
    'create_shared_list',
    'create_counter'
]
