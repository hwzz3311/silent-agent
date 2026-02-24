#!/usr/bin/env python3
"""
Neurone Native Messaging Host 安装脚本

安装步骤:
1. 加载 Chrome 扩展，获取 extension ID
2. 更新 native_host_manifest.json 中的 allowed_origins
3. 将 manifest 复制到 Chrome 的 Native Messaging 目录
4. 设置正确的执行权限

注意: 需要在加载扩展后运行此脚本
"""

import json
import os
import shutil
import stat
import sys
import subprocess


def get_chrome_user_data_dir() -> str:
    """获取 Chrome 用户数据目录"""
    platform = sys.platform

    if platform == "darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/Google/Chrome")
    elif platform == "linux":
        return os.path.expanduser("~/.config/google-chrome")
    elif platform == "win32":
        return os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
    else:
        raise OSError(f"Unsupported platform: {platform}")


def get_chrome_native_messaging_dir() -> str:
    """获取 Chrome Native Messaging 目录"""
    platform = sys.platform

    if platform == "darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/Google/Chrome/NativeMessagingHosts")
    elif platform == "linux":
        return os.path.expanduser("~/.config/google-chrome/NativeMessagingHosts")
    elif platform == "win32":
        return os.path.expanduser(r"~\AppData\Local\Google\Chrome\NativeMessagingHosts")
    else:
        raise OSError(f"Unsupported platform: {platform}")


def find_extension_id() -> str:
    """
    查找 Neurone 扩展的 ID

    尝试方法:
    1. 从 Chrome API 获取 (需要扩展已加载)
    2. 扫描扩展目录
    """
    # 方法 1: 尝试使用 chromium 查找
    # 注意: 这需要扩展已安装且有权限访问 management API

    # 方法 2: 从扩展目录查找
    # Chrome 扩展目录在用户数据目录下

    # 返回 None，提示用户手动输入
    return None


def update_manifest_with_extension_id(manifest_path: str, extension_id: str) -> str:
    """更新 manifest 文件中的 extension ID"""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # 更新 allowed_origins
    origin = f"chrome-extension://{extension_id}/"
    manifest["allowed_origins"] = [origin]

    # 写回临时文件
    temp_path = manifest_path + ".tmp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    return temp_path


def install_native_host(manifest_path: str) -> bool:
    """安装 Native Messaging Host"""
    native_messaging_dir = get_chrome_native_messaging_dir()

    # 创建目录
    os.makedirs(native_messaging_dir, exist_ok=True)

    # 复制 manifest 文件
    dest_path = os.path.join(native_messaging_dir, "com.neurone.host.json")
    shutil.copy2(manifest_path, dest_path)

    # 设置执行权限
    os.chmod(dest_path, stat.S_IRWXU)

    print(f"Native Messaging Host installed to: {dest_path}")
    return True


def main():
    """安装主流程"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_dir = os.path.join(project_root, "python")

    print("=" * 50)
    print("Neurone Native Messaging Host Installation")
    print("=" * 50)

    # 检查 Chrome 是否运行
    print("\n步骤 1: 确认 Chrome 以调试模式运行")
    print("请先启动 Chrome:")
    print("  macOS:   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
    print("  Linux:   google-chrome --remote-debugging-port=9222")
    print("  Windows: chrome --remote-debugging-port=9222")
    print()

    # 获取扩展 ID
    print("步骤 2: 获取扩展 ID")
    print("请访问 chrome://extensions/ 并复制 Neurone 扩展的 ID")
    print("ID 格式类似: a1b2c3d4e5f6g7h8i9j0")
    extension_id = input("\n请输入扩展 ID (直接回车跳过，可稍后手动更新): ").strip()

    if not extension_id:
        print("\n跳过安装。可稍后手动配置:")
        print(f"  1. 编辑 {os.path.join(python_dir, 'native_host_manifest.json')}")
        print("  2. 将 'chrome-extension://__EXTENSION_ID__/' 替换为实际扩展 ID")
        print("  3. 复制到 Native Messaging 目录")
        return

    # 更新 manifest
    manifest_path = os.path.join(python_dir, "native_host_manifest.json")
    temp_manifest = update_manifest_with_extension_id(manifest_path, extension_id)

    # 安装
    print("\n步骤 3: 安装 Native Messaging Host")
    try:
        install_native_host(temp_manifest)
        print("\n安装成功!")
    except Exception as e:
        print(f"\n安装失败: {e}")
        return

    # 清理临时文件
    os.remove(temp_manifest)

    print("\n后续步骤:")
    print("1. 重启 Chrome 浏览器")
    print("2. 重新加载 Neurone 扩展")
    print("3. 运行 demo: python python/demo.py")


if __name__ == "__main__":
    main()