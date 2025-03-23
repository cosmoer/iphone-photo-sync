# -*- coding: utf-8 -*-

"""MTP设备文件同步工具"""

import argparse
import logging
import os
import re

from win32com.client import Dispatch
from win32com.propsys import propsys  # type: ignore
from win32com.shell import shell, shellcon  # type: ignore


def setup_logging():
    """配置日志
    - 同时输出到文件sync.log和控制台
    - 日志级别设置为INFO
    - 格式包含时间、日志级别和消息"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler("sync.log"), logging.StreamHandler()]
    )


def find_photo_path():
    """动态获取手机相册的图片文件夹路径"""
    try:
        logging.info("正在尝试通过 Shell.Application 枚举设备")
        shell_app = Dispatch("Shell.Application")
        namespace = shell_app.NameSpace(17)  # ssfDRIVES

        for item in namespace.Items():
            logging.debug(f"发现设备: {item.Name}")
            if "Apple iPhone" in item.Name:
                logging.info(f"找到iPhone设备: {item.Path}")
                return os.path.join(item.Path, "Internal Storage", "DCIM")

        raise Exception("在文件系统设备中未找到iPhone")

    except Exception as e:
        logging.error(f"新方法失败: {str(e)}")
        logging.info("回退到原始方法")
        # 原始方法作为回退方案
    folder = shell.SHGetDesktopFolder().BindToObject(
        pidl, None, shell.IID_IShellFolder)
    logging.debug(f"成功绑定到Shell Folder对象")
    enum = folder.EnumObjects(0, shellcon.SHCONTF_FOLDERS)
    logging.info(f"开始枚举设备列表...")
    while True:
        pidls = enum.Next(1)
        if not pidls:
            logging.debug("枚举结束")
            break
        pidl = pidls[0]
        name = folder.GetDisplayNameOf(pidl, shellcon.SHGDN_INFOLDER)
        logging.debug(f"发现设备项: {name}")
        if "Apple iPhone" in name:
            logging.info(f"找到疑似iPhone设备: {name}")
            dcim_path = folder.GetDisplayNameOf(
                pidl, shellcon.SHGDN_FORPARSING) + r"\Internal Storage\DCIM"
            logging.debug(f"生成完整DCIM路径: {dcim_path}")
            return dcim_path
    raise Exception("iPhone not found")


def sync_folder(folder, local_dir, file_types, dry_run):
    """递归同步文件夹核心算法
    1. 枚举当前文件夹所有对象(包含子文件夹和文件)
    2. 对文件夹：在本地创建对应目录并递归处理
    3. 对文件：检查扩展名匹配后执行复制操作
    4. dry-run模式仅记录不实际执行"""

    # SHCONTF标志组合：包含文件夹和非文件夹对象
    enum = folder.EnumObjects(
        0, shellcon.SHCONTF_FOLDERS | shellcon.SHCONTF_NONFOLDERS)
    logging.info(f"开始同步文件夹, 源目录: {folder}, 备份目录: {local_dir}")

    while True:
        pidls = enum.Next(1)
        if not pidls:
            break
        pidl = pidls[0]
        name = folder.GetDisplayNameOf(pidl, shellcon.SHGDN_INFOLDER)
        attrs = folder.GetAttributesOf([pidl], shellcon.SFGAO_FOLDER)
        if attrs & shellcon.SFGAO_FOLDER:
            subdir = os.path.join(local_dir, name)
            if not dry_run and not os.path.exists(subdir):
                os.makedirs(subdir)
            subfolder = folder.BindToObject(pidl, None, shell.IID_IShellFolder)
            sync_folder(subfolder, subdir, file_types, dry_run)
        else:
            ext = os.path.splitext(name)[1].lower()
            if ext in file_types:
                src_path = folder.GetDisplayNameOf(
                    pidl, shellcon.SHGDN_FORADDRESSBAR)
                dest_path = os.path.join(local_dir, name)
                if dry_run:
                    logging.info(
                        f"DRY-RUN: Would copy {src_path} to {dest_path}")
                    continue
                # 实际操作（非 dry-run 模式）
                result, aborted = shell.SHFileOperation(
                    0, shellcon.FO_COPY, src_path, dest_path, shellcon.FOF_NOCONFIRMMKDIR, None, None
                )
                if result == 0 and not aborted:
                    logging.info(f"Copied {src_path} to {dest_path}")
                else:
                    logging.error(f"Failed to copy {src_path}")


def calculate_folder_size(folder):
    """递归计算文件夹总大小"""
    total = 0
    try:
        # 获取枚举器并遍历
        enum = folder.EnumObjects(
            0, shellcon.SHCONTF_FOLDERS | shellcon.SHCONTF_NONFOLDERS)
        while True:
            pidls = enum.Next(1)
            if not pidls:
                break
            pidl = pidls[0]

            name = folder.GetDisplayNameOf(pidl, shellcon.SHGDN_INFOLDER)
            attrs = folder.GetAttributesOf([pidl], shellcon.SFGAO_FOLDER)
            if attrs & shellcon.SFGAO_FOLDER:
                # Create a subfolder object
                subfolder = item.BindToObject(
                    pidl, None, shell.IID_IShellFolder)
                # Pass the correct folder object
                total += calculate_folder_size(subfolder)
            else:
                # 将 IShellFolder 转换为 IShellFolder2
                folder2 = folder.QueryInterface(shell.IID_IShellFolder2)
                # 使用 GetDetailsEx 获取文件大小
                prop_key = propsys.PSGetPropertyKeyFromName("System.Size")
                size_str = folder2.GetDetailsEx(pidl, prop_key)
                if size_str:
                    total += convert_size_to_bytes(str(size_str))

    except Exception as e:
        logging.error(f"计算目录大小时出错: {folder} - {str(e)}", exc_info=True)
        raise
    return total


def convert_size_to_bytes(size_str):
    """将资源管理器显示的大小字符串转换为字节数"""
    size_str = size_str.strip().replace(',', '')
    units = {"TB": 1024**4, "GB": 1024**3, "MB": 1024**2, "KB": 1024}

    # 处理中文单位（如：千字节）
    cn_units = {"太字节": "TB", "千兆字节": "GB", "兆字节": "MB", "千字节": "KB"}
    for cn, en in cn_units.items():
        if cn in size_str:
            size_str = size_str.replace(cn, en)
            break

    # 分离数字和单位
    match = re.match(r"([\d.]+)\s*([TGMK]B)", size_str)
    if match:
        number, unit = match.groups()
        return int(float(number) * units[unit])

    # 纯数字情况（字节）
    if size_str.isdigit():
        return int(size_str)

    return 0


def list_directories_by_size(folder):
    """列出第一层目录并按大小排序"""
    # SHCONTF标志组合：包含文件夹和非文件夹对象
    enum = folder.EnumObjects(
        0, shellcon.SHCONTF_FOLDERS | shellcon.SHCONTF_NONFOLDERS)
    dirs = []
    while True:
        pidls = enum.Next(1)
        if not pidls:
            break
        pidl = pidls[0]
        name = folder.GetDisplayNameOf(pidl, shellcon.SHGDN_INFOLDER)
        attrs = folder.GetAttributesOf([pidl], shellcon.SFGAO_FOLDER)
        if attrs & shellcon.SFGAO_FOLDER:
            print(f"计算目录: {name} 的大小,", end="")
            subfolder = folder.BindToObject(pidl, None, shell.IID_IShellFolder)
            total_size = calculate_folder_size(
                subfolder.BindToObject(pidl, None, shell.IID_IShellFolder))
            print(f"大小: {total_size} bytes")
            dirs.append((name, total_size))

    # 按大小降序排序
    dirs.sort(key=lambda x: x[1], reverse=True)

    # 保持原有格式化输出
    print("\n目录大小排序:")
    for name, size in dirs:
        if size >= 1024**4:
            print(f"{name}: {size/1024**4:.2f} TB")
        elif size >= 1024**3:
            print(f"{name}: {size/1024**3:.2f} GB")
        elif size >= 1024**2:
            print(f"{name}: {size/1024**2:.2f} MB")
        elif size >= 1024:
            print(f"{name}: {size/1024:.2f} KB")
        else:
            print(f"{name}: {size} bytes")


def handle_list_command(dcim_folder):
    list_directories_by_size(dcim_folder)


def handle_sync_command(dcim_folder, args):
    sync_folder(dcim_folder, args.local_dir,
                set(args.file_types), args.dry_run)


def create_parser():
    parser = argparse.ArgumentParser(description="MTP 设备上的照片同步工具")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # list 子命令
    list_parser = subparsers.add_parser('list', help='列出目照片目录的存储空间占用情况')

    # sync 子命令
    sync_parser = subparsers.add_parser('sync', help='执行同步操作')
    sync_parser.add_argument("-d", "--local-dir", required=True, help="本地同步目录")
    sync_parser.add_argument("--file-types", nargs="*",
                             default=[".jpg", ".png", ".mov"],
                             help="要同步的文件类型")
    sync_parser.add_argument("--dry-run",
                             action="store_true",
                             help="启用 dry-run 模式")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    setup_logging()

    try:
        iphone_path = find_photo_path()
        logging.info(f"检测到 iPhone 路径: {iphone_path}")
    except Exception as ex:
        logging.error(f"获取MTP设备上的照片文件夹路径失败: {str(ex)}", exc_info=True)
        raise

    desktop = shell.SHGetDesktopFolder()
    pidl, _ = shell.SHParseDisplayName(iphone_path, 0)
    dcim_folder = desktop.BindToObject(pidl, None, shell.IID_IShellFolder)

    if args.command == 'list':
        handle_list_command(dcim_folder)
    elif args.command == 'sync':
        handle_sync_command(dcim_folder, args)


if __name__ == "__main__":
    main()
