#!/usr/bin/env python
# -*- coding: utf-8 -*-
u"""
线程安全 UI Helper 基类模块

提供自动线程安全的 UI Helper 基类，让子类的公共方法自动支持跨线程调用。

工作原理：
1. 使用 __getattribute__ 拦截所有属性访问
2. 对于公共方法（不以_开头），创建线程安全的包装器
3. 如果在主线程调用，直接执行原方法
4. 如果在子线程调用，通过 CallbackDispatcher 调度到主线程执行

使用示例：
    class ProjectHelper(ThreadSafeUIHelper):
        def __init__(self, main_window):
            super().__init__(main_window)
            self.combo = main_window.project_combobox
        
        def update_project_list(self, projects):
            # 这个方法自动线程安全！
            self.combo.clear()
            for p in projects:
                self.combo.addItem(p.name)
    
    # 在任何线程调用都安全
    helper.update_project_list(projects)  # 自动处理线程切换

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


class ThreadSafeUIHelper(QtCore.QObject):
    u"""
    线程安全的 UI Helper 基类
    
    工作原理：
    1. 使用 __getattribute__ 拦截所有属性访问
    2. 对于公共方法（不以_开头），创建线程安全的包装器
    3. 如果在主线程调用，直接执行原方法
    4. 如果在子线程调用，通过 CallbackDispatcher 调度到主线程执行
    5. 包装后的方法会被缓存，避免重复创建
    
    使用示例：
        class ProjectHelper(ThreadSafeUIHelper):
            def __init__(self, main_window):
                super().__init__(main_window)
                self.combo = main_window.project_combobox
            
            def update_project_list(self, projects):
                # 这个方法自动线程安全！
                self.combo.clear()
                for p in projects:
                    self.combo.addItem(p.name)
        
        # 在任何线程调用都安全
        helper.update_project_list(projects)  # 自动处理线程切换
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
        self.__dict__['_wrapped_methods'] = {}
        
        # 创建 CallbackDispatcher 用于线程调度
        self.__dict__['_dispatcher'] = CallbackDispatcher(parent=self, debug_mode=debug_mode)
    
    def __getattribute__(self, name: str) -> Any:
        u"""
        拦截属性访问，自动为公共方法添加线程安全
        
        处理流程：
        1. 特殊属性和私有属性（_开头）直接返回
        2. Qt 内部方法直接返回，避免破坏 Qt 机制
        3. 非方法属性直接返回
        4. 检查缓存，如果已包装则直接返回
        5. 创建线程安全包装器并缓存
        
        Args:
            name: 属性名称
        
        Returns:
            属性值或包装后的方法
        """
        # 🚨 关键：避免无限递归，使用 object.__getattribute__
        
        # 1. 私有属性和特殊属性直接返回（简化过滤，避免重复）
        INTERNAL_METHODS = {'_create_thread_safe_wrapper', '_wrapped_methods', '_dispatcher', '_debug_mode'}
        if name.startswith('__') or name in QT_INTERNAL_METHODS or name in INTERNAL_METHODS:
            return object.__getattribute__(self, name)
        
        # 2. 获取原始属性
        try:
            attr = object.__getattribute__(self, name)
        except AttributeError:
            raise AttributeError(
                u"'{}' object has no attribute '{}'".format(self.__class__.__name__, name)
            )
        
        # 3. 非方法属性直接返回
        if not callable(attr):
            return attr
        
        # 检查是否是Qt信号对象(SignalInstance) - 信号是callable的，需要特殊处理
        if hasattr(attr, 'connect') and hasattr(attr, 'emit'):
            return attr
        
        # 4. 检查方法缓存
        wrapped_methods = object.__getattribute__(self, '_wrapped_methods')
        if name in wrapped_methods:
            return wrapped_methods[name]
        
        # 5. 创建线程安全的包装方法
        wrapped = self._create_thread_safe_wrapper(attr, name)
        wrapped_methods[name] = wrapped
        
        return wrapped
    
    def _create_thread_safe_wrapper(self, method: Callable, method_name: str) -> Callable:
        u"""
        创建线程安全的方法包装器
        
        使用 CallbackDispatcher 处理线程调度，避免重复实现。
        
        Args:
            method: 原始方法
            method_name: 方法名
        
        Returns:
            包装后的线程安全方法
        """
        @wraps(method)
        def thread_safe_wrapper(*args, **kwargs):
            # 获取当前线程和主线程
            current_thread = QtCore.QThread.currentThread()
            app = QtWidgets.QApplication.instance()
            
            if app is None:
                # 没有 QApplication，直接执行（测试场景）
                return method(*args, **kwargs)
            
            main_thread = app.thread()
            
            # 在主线程，直接执行
            if current_thread == main_thread:
                return method(*args, **kwargs)
            
            # 在子线程，使用 CallbackDispatcher 调度到主线程
            dispatcher = object.__getattribute__(self, '_dispatcher')
            debug_mode = object.__getattribute__(self, '_debug_mode')
            
            if debug_mode:
                thread_name = current_thread.objectName() or hex(id(current_thread))
                print(u"[ThreadSafe] {}.{} 从线程 {} 切换到主线程".format(
                    self.__class__.__name__, method_name, thread_name
                ))
            
            # 使用 CallbackDispatcher 调度
            dispatcher.dispatch(method, *args, **kwargs)
            
            # 异步调用，无返回值
            return None
        
        return thread_safe_wrapper
    
    def enable_debug_mode(self):
        u"""启用调试模式，打印线程切换信息"""
        self.__dict__['_debug_mode'] = True
    
    def disable_debug_mode(self):
        u"""禁用调试模式"""
        self.__dict__['_debug_mode'] = False
    
    def is_debug_mode(self) -> bool:
        u"""检查是否处于调试模式"""
        return object.__getattribute__(self, '_debug_mode')

