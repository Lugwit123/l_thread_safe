# -*- coding: utf-8 -*-

name = "l_thread_safe"
version = "999.0"
description = "线程安全库 - 提供跨线程安全操作的工具集"
authors = ["Lugwit Team"]

requires = [
    "python-3.12+<3.13",
    "pyside6",
]

build_command = False
cachable = True
relocatable = True


def commands():
    env.PYTHONPATH.prepend("{root}/src")
