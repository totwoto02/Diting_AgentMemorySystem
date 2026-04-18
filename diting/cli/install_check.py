"""
Diting 安装验证工具

用法：diting-check-install
"""

import sys
import os


def check_python_version():
    """检查 Python 版本"""
    print(f"Python 版本：{sys.version}")
    if sys.version_info < (3, 11):
        print("❌ Python 版本过低，需要 3.11+")
        return False
    print("✅ Python 版本符合要求")
    return True


def check_diting_import():
    """检查 MFS 是否可导入"""
    try:
        from diting import __version__
        print(f"Diting 版本：{__version__}")
        print("✅ Diting 可正常导入")
        return True
    except ImportError as e:
        print(f"❌ Diting 导入失败：{e}")
        return False


def check_mcp_registration():
    """检查 MCP 是否已注册到 OpenClaw"""
    # 检查 OpenClaw 配置目录
    config_paths = [
        os.path.expanduser("~/.openclaw/mcp_config.json"),
        os.path.expanduser("~/.config/openclaw/mcp_config.json"),
        "/etc/openclaw/mcp_config.json",
    ]

    for config_path in config_paths:
        if os.path.exists(config_path):
            print(f"✅ 找到 OpenClaw MCP 配置文件：{config_path}")
            # 检查是否包含 diting
            import json
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                mcp_servers = config.get("mcpServers", {})
                if "diting" in mcp_servers:
                    print("✅ Diting MCP Server 已注册到 OpenClaw")
                    return True
                else:
                    print("⚠️ Diting MCP Server 未注册到 OpenClaw")
                    print("   请手动添加配置或重新安装")
                    return False
            except Exception as e:
                print(f"⚠️ 读取配置文件失败：{e}")
                return False

    print("⚠️ 未找到 OpenClaw MCP 配置文件")
    print("   MFS 可能未正确安装或未配置 OpenClaw")
    return False


def check_dependencies():
    """检查依赖是否已安装"""
    required_packages = [
        "mcp",
        "sqlite3",
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")
            missing.append(package)

    if missing:
        print(f"\n请安装缺失的依赖：pip install {' '.join(missing)}")
        return False

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("Diting 安装验证工具")
    print("=" * 60)
    print()

    checks = [
        ("Python 版本", check_python_version),
        ("依赖检查", check_dependencies),
        ("Diting 导入", check_diting_import),
        ("MCP 注册", check_mcp_registration),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n正在检查：{name}")
        print("-" * 40)
        result = check_func()
        results.append((name, result))
        print()

    # 汇总结果
    print("=" * 60)
    print("检查结果汇总")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("🎉 所有检查通过！MFS 已正确安装。")
        print()
        print("使用方法:")
        print("  1. 在 OpenClaw 中自动识别 diting_read/diting_write/diting_search 工具")
        print("  2. 开始使用 MFS 管理记忆")
        return 0
    else:
        print("⚠️ 部分检查未通过，请参考上述错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
