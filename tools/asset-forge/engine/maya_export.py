# -*- coding: utf-8 -*-
"""Asset Forge —— Maya 导出引擎

由主程序用 mayapy.exe 调用，把 .ma / .mb 批量导出成 FBX。

    mayapy.exe maya_export.py <清单.json> <输出文件夹>

清单格式（由界面生成，避免中文路径和分批拷贝的问题）：
    {"files": [{"path": "绝对路径", "name": "显示用文件名"}, ...]}

与界面通信的协议（每行一条，界面按前缀解析）：
    ##PROGRESS|当前序号|总数|文件名
    ##DONE|文件名|ok|体积KB|备注
    ##TOTAL|总数
    ##FINISH|成功数|总数
    ##ERROR|错误信息
"""
import json
import os
import sys
import traceback

import maya.standalone

maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402  必须在 initialize 之后导入


def emit(line):
    """输出协议行并立即刷新，保证界面能实时收到"""
    sys.stdout.write(str(line) + "\n")
    sys.stdout.flush()


def load_manifest(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("files", [])


def unique_path(folder, stem, ext):
    """输出文件重名时自动加序号，绝不覆盖已有文件"""
    dst = os.path.join(folder, stem + ext)
    if not os.path.exists(dst):
        return dst
    i = 1
    while True:
        dst = os.path.join(folder, "%s_%d%s" % (stem, i, ext))
        if not os.path.exists(dst):
            return dst
        i += 1


def ensure_fbx_plugin():
    try:
        if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
            cmds.loadPlugin("fbxmaya", quiet=True)
        return True
    except Exception:
        return False


def setup_export():
    """FBX 导出设置，参数名不同版本有差异，失败就跳过"""
    try:
        cmds.FBXResetExport()
    except Exception:
        pass

    settings = [
        ("FBXExportUpAxis", "y"),         # Y 轴向上，与 glTF 一致
        ("FBXExportSmoothingGroups", 1),  # 保留平滑组
        ("FBXExportEmbedMedia", 1),       # 内嵌贴图
        ("FBXExportInAscii", 0),          # 二进制，体积小
    ]
    for name, value in settings:
        try:
            getattr(cmds, name)(value)
        except Exception:
            pass


def export_fbx(dst):
    """导出当前场景为 FBX

    实测坑（Maya 2022 + mayapy standalone）：
      1. cmds.file(type="FBX export") 不生成文件
      2. FBXExport 的 -s 表示"只导出选中物体"；不加 -s 才是整场景。
         写成 FBXExport("-f", dst, "-s") 且无选择时会导出空场景。
    """
    try:
        cmds.FBXExport("-f", dst)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return True, ""
    except Exception as e:
        first_error = str(e)
    else:
        first_error = "导出后文件不存在或为空"

    # 兜底：全选后用 file 命令只导选择
    try:
        cmds.select(cmds.ls(type="transform"), replace=True)
        cmds.file(
            dst,
            force=True,
            options="v=0",
            type="FBX export",
            exportSelected=True,
            prompt=False,
        )
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return True, ""
        return False, "导出后文件不存在或为空"
    except Exception as e:
        return False, "%s / %s" % (first_error, e)


def main():
    argv = sys.argv[1:]
    if len(argv) < 2:
        emit("##ERROR|用法: maya_export.py <清单.json> <输出文件夹>")
        return 2

    manifest_path, out_dir = argv[0], argv[1]
    if not os.path.isfile(manifest_path):
        emit("##ERROR|清单文件不存在: %s" % manifest_path)
        return 2

    try:
        entries = load_manifest(manifest_path)
    except Exception as e:
        emit("##ERROR|清单读取失败: %s" % e)
        return 2

    if not entries:
        emit("##TOTAL|0")
        emit("##FINISH|0|0")
        return 0

    os.makedirs(out_dir, exist_ok=True)

    if not ensure_fbx_plugin():
        emit("##ERROR|无法加载 FBX 插件 fbxmaya，导出可能失败")

    emit("Maya 导出：%d 个文件" % len(entries))
    emit("##TOTAL|%d" % len(entries))

    ok_count = 0
    for idx, entry in enumerate(entries, 1):
        src = entry.get("path", "")
        name = entry.get("name") or os.path.basename(src)
        stem = os.path.splitext(os.path.basename(src))[0]
        dst = unique_path(out_dir, stem, ".fbx")

        emit("##PROGRESS|%d|%d|%s" % (idx, len(entries), name))

        try:
            cmds.file(src, open=True, force=True, prompt=False)
        except Exception as e:
            emit("##DONE|%s|fail|0|打开失败: %s" % (name, e))
            continue

        setup_export()
        ok, err = export_fbx(dst)

        if ok:
            size_kb = round(os.path.getsize(dst) / 1024.0, 1)
            emit("##DONE|%s|ok|%s|%s" % (name, size_kb, dst))
            ok_count += 1
        else:
            emit("##DONE|%s|fail|0|%s" % (name, err))

    emit("##FINISH|%d|%d" % (ok_count, len(entries)))
    return 0


try:
    code = main()
except Exception:
    emit("##ERROR|引擎异常")
    emit(traceback.format_exc())
    code = 1

sys.stdout.flush()
sys.stderr.flush()
os._exit(code)
