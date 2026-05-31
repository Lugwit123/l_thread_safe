#!/usr/bin/env python
# -*- coding: utf-8 -*-
u"""
回调函数调度器 - 确保回调函数在主线程安全执行

提供线程安全的回调函数调度机制，使用 Qt Signal + QueuedConnection
确保回调函数始终在主线程的事件循环中执行。

工作原理：
1. 使用 Signal(object) 接收 callable 对象
2. 通过 QueuedConnection 自动跨线程调度
3. 使用 functools.partial 绑定参数，避免闭包晚绑定问题
4. 在主线程的槽函数中执行 callable

使用示例：
    # 创建调度器（通常作为类的成员变量）
    dispatcher = CallbackDispatcher(parent=self)
    
    # 在任何线程中调度回调
    def on_complete(result):
        # 这里会在主线程执行
        self.ui.update_display(result)
    
    # 从子线程调用
    dispatcher.dispatch(on_complete, result_data)
    
    # 或者调度多参数回调
    dispatcher.dispatch(on_error, error_msg, error_code)

作者: AI Assistant
日期: 2025-10-05
"""

from __future__ import print_function, unicode_literals
from functools import partial
from typing import Callable, Any

from PySide6 import QtCore, QtWidgets


class CallbackDispatcher(QtCore.QObject):
    u"""
    回调函数调度器 - 线程安全的回调执行
    
    核心特性：
    1. 使用 Signal + QueuedConnection 跨线程调度（最可靠）
    2. 使用 functools.partial 绑定参数（避免闭包问题）
    3. 异常捕获和日志记录
    4. 主线程直接执行，子线程自动调度
    
    技术细节：
    - Signal 在类级别定义一次
    - QueuedConnection 确保跨线程安全
    - partial 在调用时立即绑定参数
    """
    
    # 类级别信号：接收一个 callable 对象
    _callback_signal = QtCore.Signal(object)
    
    def __init__(self, parent: QtCore.QObject = None, debug_mode: bool = False):
        u"""
        初始化回调调度器
        
        Args:
            parent: 父对象（通常是主窗口或执行器）
            debug_mode: 是否启用调试模式（打印调度信息）
        """
        super(CallbackDispatcher, self).__init__(parent)
        
        self._debug_mode = debug_mode
        self._signal_connected = False
        
        # 连接信号槽
        self._connect_signal()
    
    def _connect_signal(self):
        u"""连接调度信号到执行槽"""
        if not self._signal_connected:
            self._callback_signal.connect(
                self._execute_callback,
                QtCore.Qt.ConnectionType.QueuedConnection
            )
            self._signal_connected = True
            
            if self._debug_mode:
                print(u"[CallbackDispatcher] 调度信号已连接")
    
    def dispatch(self, callback: Callable, *args, **kwargs):
        u"""
        调度回调函数在主线程执行
        
        Args:
            callback: 要执行的回调函数
            *args: 回调函数的位置参数
            **kwargs: 回调函数的关键字参数
        
        Example:
            # 无参数回调
            dispatcher.dispatch(on_cancel)
            
            # 单参数回调
            dispatcher.dispatch(on_complete, result)
            
            # 多参数回调
            dispatcher.dispatch(on_error, error_msg, error_code)
            
            # 带关键字参数
            dispatcher.dispatch(on_progress, desc="loading", percent=50)
        """
        if callback is None:
            return
        
        # 检查当前线程
        current_thread = QtCore.QThread.currentThread()
        app = QtWidgets.QApplication.instance()
        
        if app is None:
            # 没有 QApplication，直接执行（测试场景）
            self._safe_execute(callback, *args, **kwargs)
            return
        
        main_thread = app.thread()
        
        # 如果已在主线程，直接执行
        if current_thread == main_thread:
            self._safe_execute(callback, *args, **kwargs)
            return
        
        # 在子线程，通过信号调度到主线程
        if self._debug_mode:
            thread_name = current_thread.objectName() or hex(id(current_thread))
            callback_name = getattr(callback, '__name__', str(callback))
            print(u"[CallbackDispatcher] 调度回调 {} 从线程 {} 到主线程".format(
                callback_name, thread_name
            ))
        
        # 使用 partial 立即绑定参数
        bound_callback = partial(callback, *args, **kwargs)
        
        # 通过信号发送到主线程
        self._callback_signal.emit(bound_callback)
    
    def _execute_callback(self, bound_callback: Callable):
        u"""
        在主线程中执行回调（槽函数）
        
        Args:
            bound_callback: 已绑定参数的 callable 对象
        """
        try:
            bound_callback()
        except Exception as e:
            print(u"[CallbackDispatcher] 回调执行出错: {}".format(str(e)))
            import traceback
            traceback.print_exc()
    
    def _safe_execute(self, callback: Callable, *args, **kwargs):
        u"""
        安全执行回调函数（捕获异常）
        
        Args:
            callback: 回调函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        try:
            callback(*args, **kwargs)
        except Exception as e:
            print(u"[CallbackDispatcher] 回调执行出错: {}".format(str(e)))
            import traceback
            traceback.print_exc()
    
    def enable_debug_mode(self):
        u"""启用调试模式"""
        self._debug_mode = True
    
    def disable_debug_mode(self):
        u"""禁用调试模式"""
        self._debug_mode = False
    
    def is_debug_mode(self) -> bool:
        u"""检查是否处于调试模式"""
        return self._debug_mode


# ==================== 便利函数 ====================

# 全局单例调度器（可选）
_global_dispatcher = None


def get_global_dispatcher() -> CallbackDispatcher:
    u"""
    获取全局单例调度器
    
    注意：需要在有 QApplication 的情况下调用
    
    Returns:
        CallbackDispatcher: 全局调度器实例
    """
    global _global_dispatcher
    
    if _global_dispatcher is None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            raise RuntimeError(u"必须先创建 QApplication 才能使用全局调度器")
        
        _global_dispatcher = CallbackDispatcher(parent=app)
    
    return _global_dispatcher


def dispatch_callback(callback: Callable, *args, **kwargs):
    u"""
    使用全局调度器调度回调（便利函数）
    
    Args:
        callback: 回调函数
        *args: 位置参数
        **kwargs: 关键字参数
    
    Example:
        from callback_dispatcher import dispatch_callback
        
        # 在任何线程调用
        dispatch_callback(on_complete, result)
    """
    dispatcher = get_global_dispatcher()
    dispatcher.dispatch(callback, *args, **kwargs)

