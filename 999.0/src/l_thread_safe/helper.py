#!/usr/bin/env python
# -*- coding: utf-8 -*-
u"""
线程安全 UI Helper 基类模块

提供线程安全的 UI Helper 基类，使用装饰器方式让子类的指定方法支持跨线程调用。

工作原理：
1. 不劫持所有属性访问，避免性能开销和调试困难
2. 使用 @thread_safe 装饰器显式标记需要线程安全的方法
3. 如果在主线程调用，直接执行原方法
4. 如果在子线程调用，通过 CallbackDispatcher 调度到主线程执行

使用示例：
    from l_thread_safe import ThreadSafeUIHelper, thread_safe
    
    class ProjectHelper(ThreadSafeUIHelper):
        def __init__(self, main_window):
            super().__init__(main_window)
            self.combo = main_window.project_combobox
        
        @thread_safe
        def update_project_list(self, projects):
            # 这个方法线程安全
            self.combo.clear()
            for p in projects:
                self.combo.addItem(p.name)
        
        def normal_method(self):
            # 这个方法不线程安全，没有额外开销
            pass

作者: AI Assistant
日期: 2025-10-05
"""

from __future__ import print_function, unicode_literals
from functools import wraps
from typing import Callable, Any

from PySide6 import QtCore, QtWidgets

# 导入 CallbackDispatcher 用于线程调度
from .dispatcher import CallbackDispatcher

# Qt 内部方法白名单 - 这些方法不应该被包装
QT_INTERNAL_METHODS = {
    'parent', 'thread', 'moveToThread', 'metaObject', 'sender', 
    'receivers', 'staticMetaObject', 'deleteLater', 'destroyed',
    'objectName', 'setObjectName', 'property', 'setProperty',
    'blockSignals', 'signalsBlocked', 'dumpObjectInfo', 'dumpObjectTree',
    'disconnect', 'connect', 'inherits', 'isWidgetType', 'isWindowType',
    'findChild', 'findChildren', 'installEventFilter', 'removeEventFilter'
}


def thread_safe(func: Callable) -> Callable:
    u"""
    线程安全方法装饰器
    
    使用示例：
        class MyHelper(ThreadSafeUIHelper):
            @thread_safe
            def update_ui(self, data):
                # 这个方法会自动线程安全
                self.label.setText(data)
    
    Args:
        func: 要装饰的方法
    
    Returns:
        包装后的线程安全方法
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 获取当前线程和主线程
        current_thread = QtCore.QThread.currentThread()
        app = QtWidgets.QApplication.instance()
        
        if app is None:
            # 没有 QApplication，直接执行（测试场景）
            return func(self, *args, **kwargs)
        
        main_thread = app.thread()
        
        # 在主线程，直接执行
        if current_thread == main_thread:
            return func(self, *args, **kwargs)
        
        # 在子线程，使用 dispatcher 调度到主线程
        if hasattr(self, '_dispatcher'):
            dispatcher = self._dispatcher
            debug_mode = getattr(self, '_debug_mode', False)
            
            if debug_mode:
                thread_name = current_thread.objectName() or hex(id(current_thread))
                class_name = self.__class__.__name__
                module_name = self.__class__.__module__
                func_name = getattr(func, '__name__', 'unknown')
                print(u"[ThreadSafe] {}.{}.{} 从线程 {} 切换到主线程".format(
                    module_name, class_name, func_name, thread_name
                ))
            
            # 使用 CallbackDispatcher 调度
            dispatcher.dispatch(func, self, *args, **kwargs)
            return None
        else:
            # 如果没有 dispatcher，直接执行
            return func(self, *args, **kwargs)
    
    return wrapper


class ThreadSafeUIHelper(QtCore.QObject):
    u"""
    线程安全的 UI Helper 基类
    
    设计原则：
    1. 不劫持所有属性访问，避免性能开销和调试困难
    2. 使用 @thread_safe 装饰器显式标记需要线程安全的方法
    3. 子类可以自由选择哪些方法需要线程安全
    
    使用示例：
        class ProjectHelper(ThreadSafeUIHelper):
            def __init__(self, main_window):
                super().__init__(main_window)
                self.combo = main_window.project_combobox
            
            @thread_safe
            def update_project_list(self, projects):
                # 这个方法线程安全
                self.combo.clear()
                for p in projects:
                    self.combo.addItem(p.name)
            
            def normal_method(self):
                # 这个方法不线程安全，没有额外开销
                pass
    """
    
    def __init__(self, main_window, debug_mode=False):
        u"""
        初始化线程安全 UI Helper
        
        Args:
            main_window: 主窗口引用
            debug_mode: 是否启用调试模式（打印线程切换信息）
        """
        super(ThreadSafeUIHelper, self).__init__(main_window)
        
        # 使用 __dict__ 直接设置属性，避免与 QObject 的 __setattr__ 冲突
        self.__dict__['main_window'] = main_window
        self.__dict__['_debug_mode'] = debug_mode
        
        # 创建 CallbackDispatcher 用于线程调度
        self.__dict__['_dispatcher'] = CallbackDispatcher(parent=self, debug_mode=debug_mode)
    
    def enable_debug_mode(self):
        u"""启用调试模式，打印线程切换信息"""
        self.__dict__['_debug_mode'] = True
    
    def disable_debug_mode(self):
        u"""禁用调试模式"""
        self.__dict__['_debug_mode'] = False
    
    def is_debug_mode(self) -> bool:
        u"""检查是否处于调试模式"""
        return object.__getattribute__(self, '_debug_mode')

