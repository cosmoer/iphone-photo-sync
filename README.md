# 手机照片同步工具

通过 Windows Shell API 实现 iPhone 照片/视频的快速同步，支持文件类型过滤和存储空间分析。

## 功能特性
- ✅ 递归同步指定文件类型（默认：jpg/png/mov）
- 📊 列出目录存储空间占用（支持 TB/GB/MB 单位转换）
- 🛡️ Dry-run 模式（模拟运行不实际操作）
- 📂 自动识别 MTP 设备路径

## 环境要求
- Windows 10/11
- Python 3.7+
- 依赖库：`pywin32`

## 实现原理
基于 Windows Shell API 实现，通过遍历指定目录下的文件，实现文件复制和移动操作。  
API 参考：https://pypi.org/project/pywin32/

## 安装步骤
### 安装依赖
```bash
pip install -r requirements.txt
```
### 列出照片目录里存储空间占用情况
```bash
python3 mtp-file-sync list
```
### 递归同步指定目录下的照片到指定目录
```bash
python3 mtp-file-sync sync --local-dir "D:\phone-backup\"
```

