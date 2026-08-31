import platform


if __name__ == "__main__":
    # 1. 操作系统信息
    print("操作系统:", platform.system())  # 例如: Windows, Linux, Darwin[reference:2][reference:3]
    print("系统版本:", platform.version())  # 详细的版本号[reference:4]
    print("系统发行版:", platform.release())  # 操作系统的发行版本[reference:5]

    # 2. 硬件架构信息
    print("机器类型:", platform.machine())  # 例如: AMD64[reference:6][reference:7]
    print("处理器名称:", platform.processor())  # 处理器信息[reference:8]
    print("架构:", platform.architecture())  # 例如: ('64bit', 'WindowsPE')[reference:9]

    # 3. Python环境信息
    print("Python版本:", platform.python_version())  # 例如: 3.9.7[reference:10]
    print("Python编译器:", platform.python_compiler())  # 编译器信息[reference:11]
    print("Python实现:", platform.python_implementation())  # 例如: CPython[reference:12]

    # 4. 网络与用户信息
    print("主机名:", platform.node())  # 计算机的网络名称[reference:13]
    # 注意：platform.getlogin() 在某些环境下可能失败，并非在所有平台都可靠[reference:14]
    # print("当前用户:", platform.getlogin())

    # 5. 综合信息
    print("平台完整信息:", platform.platform())  # 返回一个人类可读的字符串[reference:15][reference:16]