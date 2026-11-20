# -*- coding: utf-8 -*-
"""Asset Forge —— Blender 转换引擎

由主程序用 blender.exe -b 调用，把各种模型格式批量转成 GLB。

    blender.exe -b -P blender_convert.py -- <清单.json> <输出文件夹>

清单格式：
    {"files": [{"path": "绝对路径", "name": "显示用文件名"}, ...]}

也兼容传一个目录（自动扫描该目录下的模型文件）。

与界面通信的协议：
    ##PROGRESS|当前序号|总数|文件名
    ##DONE|文件名|ok|三角面数|备注
    ##TOTAL|总数
    ##FINISH|成功数|总数
    ##ERROR|错误信息
"""
import json
import os
import sys
import traceback

import bpy

SUPPORTED = (".fbx", ".obj", ".stl", ".dae", ".glb", ".gltf")

# 各格式的导入方式，按顺序尝试（不同 Blender 版本操作符名字不同）
IMPORTERS = {
    ".fbx": [("import_scene", "fbx", {"use_selection": False})],
    ".obj": [("wm", "obj_import", {}), ("import_scene", "obj", {})],
    ".stl": [("wm", "stl_import", {}), ("import_mesh", "stl", {})],
    ".dae": [("wm", "collada_import", {})],
    ".glb": [("import_scene", "gltf", {})],
    ".gltf": [("import_scene", "gltf", {})],
}


def emit(line):
    sys.stdout.write(str(line) + "\n")
    sys.stdout.flush()


def collect_entries(target):
    """清单文件或目录，统一返回 [{"path":..., "name":...}]"""
    if os.path.isdir(target):
        names = sorted(f for f in os.listdir(target) if f.lower().endswith(SUPPORTED))
        return [{"path": os.path.join(target, n), "name": n} for n in names]

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("files", [])


def unique_path(folder, stem, ext):
    """重名自动加序号，不覆盖已有文件"""
    dst = os.path.join(folder, stem + ext)
    if not os.path.exists(dst):
        return dst
    i = 1
    while True:
        dst = os.path.join(folder, "%s_%d%s" % (stem, i, ext))
        if not os.path.exists(dst):
            return dst
        i += 1


def reset_scene():
    """清空场景，避免上一个模型的残留"""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_file(path, ext):
    """按格式尝试导入，返回 (成功?, 错误信息)"""
    last_error = "找不到可用的导入操作符"
    for module_name, op_name, kwargs in IMPORTERS.get(ext, []):
        module = getattr(bpy.ops, module_name, None)
        if module is None:
            continue
        op = getattr(module, op_name, None)
        if op is None:
            continue
        try:
            op(filepath=path, **kwargs)
            return True, ""
        except TypeError:
            try:
                op(filepath=path)
                return True, ""
            except Exception as e:
                last_error = str(e)
        except Exception as e:
            last_error = str(e)
    return False, last_error


def export_glb(out_path):
    """导出 GLB。新版本可能移除了部分参数，失败时退化"""
    try:
        bpy.ops.export_scene.gltf(
            filepath=out_path,
            export_format="GLB",
            export_apply=True,   # 应用修改器
        )
        return True, ""
    except TypeError:
        try:
            bpy.ops.export_scene.gltf(filepath=out_path, export_format="GLB")
            return True, ""
        except Exception as e:
            return False, str(e)
    except Exception as e:
        return False, str(e)


def count_triangles():
    """统计场景里的三角面数"""
    total = 0
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        try:
            mesh.calc_loop_triangles()
            total += len(mesh.loop_triangles)
        except Exception:
            pass
    return total


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    if len(argv) < 2:
        emit("##ERROR|用法: blender -b -P blender_convert.py -- <清单.json 或 目录> <输出文件夹>")
        return 2

    target, out_dir = argv[0], os.path.abspath(argv[1])

    if not os.path.exists(target):
        emit("##ERROR|输入不存在: %s" % target)
        return 2

    try:
        entries = collect_entries(target)
    except Exception as e:
        emit("##ERROR|清单读取失败: %s" % e)
        return 2

    if not entries:
        emit("##TOTAL|0")
        emit("##FINISH|0|0")
        return 0

    os.makedirs(out_dir, exist_ok=True)
    emit("Blender 转 GLB：%d 个文件" % len(entries))
    emit("##TOTAL|%d" % len(entries))

    ok_count = 0
    for idx, entry in enumerate(entries, 1):
        src = entry.get("path", "")
        name = entry.get("name") or os.path.basename(src)
        ext = os.path.splitext(src)[1].lower()
        stem = os.path.splitext(os.path.basename(src))[0]
        dst = unique_path(out_dir, stem, ".glb")

        emit("##PROGRESS|%d|%d|%s" % (idx, len(entries), name))

        if not os.path.isfile(src):
            emit("##DONE|%s|fail|0|源文件不存在" % name)
            continue

        reset_scene()

        ok, err = import_file(src, ext)
        if not ok:
            emit("##DONE|%s|fail|0|导入失败: %s" % (name, err))
            continue

        tris = count_triangles()
        ok, err = export_glb(dst)
        if not ok:
            emit("##DONE|%s|fail|%d|导出失败: %s" % (name, tris, err))
            continue

        emit("##DONE|%s|ok|%d|%s" % (name, tris, dst))
        ok_count += 1

    emit("##FINISH|%d|%d" % (ok_count, len(entries)))
    return 0


try:
    code = main()
except Exception:
    emit("##ERROR|引擎异常")
    emit(traceback.format_exc())
    code = 1

sys.stdout.flush()
sys.exit(code)
