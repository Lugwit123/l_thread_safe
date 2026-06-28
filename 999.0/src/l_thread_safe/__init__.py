#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
线程安全库 (ThreadSafe Library)
===============================

🎯 **库功能**
- 线程安全的UI操作
- 跨线程回调调度
- 线程间数据同步
- 线程池管理
- 锁机制封装

📦 **核心模块**
- dispatcher: 回调函数调度器
- helper: 线程安全UI Helper基类
- sync: 数据同步工具
- pool: 线程池管理
- locks: 锁机制封装

🚀 **快速开始**
```python
# 导入库
from l_thread_safe import CallbackDispatcher, ThreadSafeUIHelper

# 方式1：使用 CallbackDispatcher（函数式）
dispatcher = CallbackDispatcher()

# 在任何线程中安全调用UI更新
def update_ui(data):
    ui.label.setText(data)

dispatcher.dispatch(update_ui, "新数据")

# 方式2：使用 ThreadSafeUIHelper（面向对象）
class MyHelper(ThreadSafeUIHelper):
    def update_display(self, text):
        # 自动线程安全（内部使用 CallbackDispatcher）
        self.label.setText(text)
```

📋 **版本信息**
- Version: 1.1.0 (统一线程调度实现)
- Author: Assistant
- License: MIT
"""

# === 版本信息 ===
__version__ = "1.1.0"
__author__ = "Assistant"
__license__ = "MIT"
__description__ = "线程安全库 - 提供跨线程安全操作的工具集"

# === 核心模块导入 ===
import os as _os

if _os.environ.get("L_DISABLE_THREAD_SAFE") == "1":
    _DISABLED = True
    _DISPATCHER_AVAILABLE = False
    _HELPER_AVAILABLE = False
    _SYNC_AVAILABLE = False
    _POOL_AVAILABLE = False
    _LOCKS_AVAILABLE = False
    print("[ThreadSafe库] 已通过 L_DISABLE_THREAD_SAFE=1 禁用")
else:
    _DISABLED = False

    # 回调调度器
    from .dispatcher import CallbackDispatcher
    _DISPATCHER_AVAILABLE = True

    # 线程安全UI Helper
    from .helper import ThreadSafeUIHelper, thread_safe
    _HELPER_AVAILABLE = True

    # 数据同步工具
    from .sync import ThreadSafeData, ThreadSafeQueue, ThreadSafeDict, ThreadSafeList
    _SYNC_AVAILABLE = True

    # 线程池管理
    from .pool import ThreadPoolManager, WorkerThread
    _POOL_AVAILABLE = True

    # 锁机制封装
    from .locks import SmartLock, ReadWriteLock, TimeoutLock
    _LOCKS_AVAILABLE = True

# === 库状态检查 ===

def get_library_status():
    """
    获取库的可用状态
    
    Returns:
        dict: 各模块的可用状态
    """
    return {
        'dispatcher': _DISPATCHER_AVAILABLE,
        'helper': _HELPER_AVAILABLE,
        'sync': _SYNC_AVAILABLE,
        'pool': _POOL_AVAILABLE,
        'locks': _LOCKS_AVAILABLE,
        'version': __version__
    }

def check_dependencies():
    """
    检查库的依赖是否满足
    
    Returns:
        tuple: (是否完整可用, 缺失的依赖列表)
    """
    missing = []
    
    if not _DISPATCHER_AVAILABLE:
        missing.append("dispatcher (回调调度器)")
    if not _HELPER_AVAILABLE:
        missing.append("helper (线程安全Helper)")
    if not _SYNC_AVAILABLE:
        missing.append("sync (数据同步工具)")
    if not _POOL_AVAILABLE:
        missing.append("pool (线程池管理)")
    if not _LOCKS_AVAILABLE:
        missing.append("locks (锁机制)")
    
    return len(missing) == 0, missing

# === 便捷工厂函数 ===

def create_ui_safe_environment(main_window=None):
    """
    创建UI安全环境
    
    Args:
        main_window: 主窗口实例
    
    Returns:
        dict: 包含dispatcher和helper基类的字典
    """
    if not _DISPATCHER_AVAILABLE or not _HELPER_AVAILABLE:
        raise ImportError("创建UI安全环境需要dispatcher和helper模块都可用")
    
    dispatcher = CallbackDispatcher(main_window)
    
    return {
        'dispatcher': dispatcher,
        'helper_class': ThreadSafeUIHelper
    }

def create_data_sync_environment():
    """
    创建数据同步环境
    
    Returns:
        dict: 包含各种线程安全数据结构的字典
    """
    if not _SYNC_AVAILABLE:
        raise ImportError("创建数据同步环境需要sync模块可用")
    
    return {
        'data': ThreadSafeData,
        'queue': ThreadSafeQueue,
        'dict': ThreadSafeDict,
        'list': ThreadSafeList
    }

def create_thread_pool_environment(max_workers=4):
    """
    创建线程池环境
    
    Args:
        max_workers: 最大工作线程数
    
    Returns:
        ThreadPoolManager: 线程池管理器实例
    """
    if not _POOL_AVAILABLE:
        raise ImportError("创建线程池环境需要pool模块可用")
    
    return ThreadPoolManager(max_workers=max_workers)

def create_complete_thread_safe_system(main_window=None, max_workers=4):
    """
    创建完整的线程安全系统
    
    Args:
        main_window: 主窗口实例
        max_workers: 最大工作线程数
    
    Returns:
        dict: 包含所有组件的完整系统
    """
    is_complete, missing = check_dependencies()
    if not is_complete:
        raise ImportError(f"创建完整系统需要所有模块都可用，缺失: {', '.join(missing)}")
    
    # 创建各个组件
    ui_env = create_ui_safe_environment(main_window)
    data_env = create_data_sync_environment()
    pool_manager = create_thread_pool_environment(max_workers)
    
    return {
        'ui': ui_env,
        'data': data_env,
        'pool': pool_manager,
        'locks': {
            'smart': SmartLock,
            'read_write': ReadWriteLock,
            'timeout': TimeoutLock
        }
    }

# === 装饰器工具 ===

def thread_safe_method(func):
    """
    线程安全方法装饰器
    
    Args:
        func: 要装饰的方法
    
    Returns:
        装饰后的线程安全方法
    
    Note:
        由于ThreadSafeWrapper未实现，此装饰器当前只返回原函数
    """
    # TODO: 实现ThreadSafeWrapper或使用其他线程安全机制
    return func

def ui_thread_only(func):
    """
    仅UI线程执行装饰器
    
    Args:
        func: 要装饰的方法
    
    Returns:
        装饰后的方法，只能在UI线程执行
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            from PySide6 import QtCore
            from PySide6.QtWidgets import QApplication
            if QApplication.instance() and QApplication.instance().thread() != QtCore.QThread.currentThread():
                raise RuntimeError(f"方法 {func.__name__} 只能在UI线程中执行")
        except ImportError:
            pass  # 如果没有Qt，跳过检查
        
        return func(*args, **kwargs)
    
    return wrapper

def background_thread_only(func):
    """
    仅后台线程执行装饰器
    
    Args:
        func: 要装饰的方法
    
    Returns:
        装饰后的方法，只能在后台线程执行
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            from PySide6 import QtCore
            from PySide6.QtWidgets import QApplication
            if QApplication.instance() and QApplication.instance().thread() == QtCore.QThread.currentThread():
                raise RuntimeError(f"方法 {func.__name__} 不能在UI线程中执行")
        except ImportError:
            pass  # 如果没有Qt，跳过检查
        
        return func(*args, **kwargs)
    
    return wrapper

# === 公共接口导出 ===

__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    '__license__',
    '__description__',
    
    # 核心类
    'CallbackDispatcher',
    'ThreadSafeUIHelper',
    'thread_safe',
    'ThreadSafeData',
    'ThreadSafeQueue',
    'ThreadSafeDict',
    'ThreadSafeList',
    'ThreadPoolManager',
    'WorkerThread',
    'SmartLock',
    'ReadWriteLock',
    'TimeoutLock',
    
    # 工厂函数
    'create_ui_safe_environment',
    'create_data_sync_environment',
    'create_thread_pool_environment',
    'create_complete_thread_safe_system',
    
    # 装饰器
    'thread_safe_method',
    'ui_thread_only',
    'background_thread_only',
    
    # 状态检查
    'get_library_status',
    'check_dependencies',
]

# === 库初始化日志 ===

def _print_library_info():
    """打印库信息"""
    status = get_library_status()
    is_complete, missing = check_dependencies()
    
    print(f"[ThreadSafe库] 版本 {__version__} 初始化完成")
    print(f"[ThreadSafe库] 模块状态: Dispatcher={status['dispatcher']}, Helper={status['helper']}, Sync={status['sync']}, Pool={status['pool']}, Locks={status['locks']}")
    
    if not is_complete:
        print(f"[ThreadSafe库] 警告: 缺失模块 - {', '.join(missing)}")
    else:
        print("[ThreadSafe库] 所有模块加载成功")

# 初始化时打印信息
if not _DISABLED:
    _print_library_info()
