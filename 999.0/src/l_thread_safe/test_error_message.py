#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试线程安全库优化后的错误信息
"""

import sys
import os

# 添加模块路径
sys.path.insert(0, r'd:\TD_Depot\Software\Lugwit_syncPlug\lugwit_insapp\trayapp\rez-package-source\l_thread_safe\999.0\src')

from l_thread_safe.helper import ThreadSafeUIHelper


class TestHelper(ThreadSafeUIHelper):
    """测试用的Helper类"""
    
    def __init__(self, main_window):
        super().__init__(main_window)
    
    def test_method(self):
        """测试方法"""
        print("测试方法被调用")


class MockMainWindow:
    """模拟主窗口"""
    pass


def test_error_message():
    """测试错误信息是否包含足够的调试信息"""
    print("=" * 60)
    print("测试线程安全库错误信息优化")
    print("=" * 60)
    
    # 创建实例
    mock_main = MockMainWindow()
    helper = TestHelper(mock_main)
    
    # 测试1: 访问不存在的属性
    print("\n[测试1] 访问不存在的普通属性:")
    try:
        _ = helper.non_existent_attr
    except AttributeError as e:
        print("捕获到 AttributeError:")
        print(str(e))
        print()
    
    # 测试2: 访问不存在的特殊属性（双下划线）
    print("[测试2] 访问不存在的特殊属性 (__name__):")
    try:
        _ = helper.__name__
    except AttributeError as e:
        print("捕获到 AttributeError:")
        print(str(e))
        print()
    
    # 测试3: 访问存在的方法
    print("[测试3] 访问存在的方法 (test_method):")
    try:
        method = helper.test_method
        print("成功获取方法:", method)
        method()
    except Exception as e:
        print("捕获到异常:", str(e))
        print()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_error_message()
