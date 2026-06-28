#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新的线程安全设计 - 使用装饰器而非 __getattribute__
"""

import sys
import os

# 添加模块路径
sys.path.insert(0, r'd:\TD_Depot\Software\Lugwit_syncPlug\lugwit_insapp\trayapp\rez-package-source\l_thread_safe\999.0\src')

from l_thread_safe import ThreadSafeUIHelper, thread_safe


class TestHelper(ThreadSafeUIHelper):
    """测试用的Helper类"""
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.test_data = "test"
    
    @thread_safe
    def thread_safe_method(self):
        """线程安全方法"""
        print("线程安全方法被调用")
        return "success"
    
    def normal_method(self):
        """普通方法，不线程安全"""
        print("普通方法被调用")
        return "normal"


class MockMainWindow:
    """模拟主窗口"""
    pass


def test_new_design():
    """测试新设计"""
    print("=" * 60)
    print("测试新的线程安全设计（装饰器方式）")
    print("=" * 60)
    
    # 创建实例
    mock_main = MockMainWindow()
    helper = TestHelper(mock_main)
    
    # 测试1: 访问普通属性（不应该被劫持）
    print("\n[测试1] 访问普通属性 (test_data):")
    try:
        result = helper.test_data
        print("成功访问属性:", result)
    except Exception as e:
        print("访问属性出错:", str(e))
    
    # 测试2: 访问线程安全方法
    print("\n[测试2] 访问线程安全方法 (thread_safe_method):")
    try:
        method = helper.thread_safe_method
        print("成功获取方法:", method)
        result = method()
        print("方法执行结果:", result)
    except Exception as e:
        print("调用方法出错:", str(e))
    
    # 测试3: 访问普通方法
    print("\n[测试3] 访问普通方法 (normal_method):")
    try:
        method = helper.normal_method
        print("成功获取方法:", method)
        result = method()
        print("方法执行结果:", result)
    except Exception as e:
        print("调用方法出错:", str(e))
    
    # 测试4: 访问不存在的属性（应该有清晰的错误信息）
    print("\n[测试4] 访问不存在的属性 (non_existent):")
    try:
        _ = helper.non_existent
    except AttributeError as e:
        print("捕获到 AttributeError:")
        print(str(e))
    
    # 测试5: 访问特殊属性
    print("\n[测试5] 访问特殊属性 (__class__):")
    try:
        cls = helper.__class__
        print("成功访问 __class__:", cls)
    except Exception as e:
        print("访问特殊属性出错:", str(e))
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_new_design()
