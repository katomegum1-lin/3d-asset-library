"""
批量把 FBX / OBJ / STL / DAE / GLTF 转成 GLB（在 Blender 无界面模式下运行）

用法（一般由 batch-convert.bat 调用，不需要手动跑）：
    blender -b -P batch-convert.py -- "输入文件夹" "输出文件夹"

特点：
  - 原文件只读，不做任何修改
  - 每个文件独立处理，单个失败不影响其他文件
  - 输出 CSV 报告（文件名 / 状态 / 面数 / 体积）
  - 兼容不同 Blender 版本的导入操作符（会依次尝试）
"""
import bpy
import os
import sys
import csv
import time

# ---------- 参数 ----------
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []

if len(argv) < 2:
    print("[错误] 用法: blender -b -P batch-convert.py -- <输入文件夹> <输出文件夹>")
    sys.exit(1)

SRC_DIR = os.path.abspath(argv[0])
OUT_DIR = os.path.abspath(argv[1])
REPORT = os.path.join(OUT_DIR, "_report.csv")

SUPPORTED = (".fbx", ".obj", ".stl", ".dae", ".glb", ".gltf")

# 各格式的导入方式，按顺序尝试（不同 Blender 版本操作符名字不同）
IMPORTERS = {
    ".fbx": [("import_scene", "fbx", {})],
    ".obj": [("wm", "obj_import", {}), ("import_scene", "obj", {})],
    ".stl": [("wm", "stl_import", {}), ("import_mesh", "stl", {})],
    ".dae": [("wm", "collada_import", {})],
    ".glb": [("import_scene", "gltf", {})],
    ".gltf": [("import_scene", "gltf", {})],
}


def reset_scene():
    """清空场景，避免上一个模型的残留"""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_file(path, ext):
    """按格式尝试导入，返回 (成功?, 错误信息)"""
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
        except Exception as e:
            last_error = str(e)
    return False, locals().get("last_error", "找不到可用的导入操作符")


def export_glb(out_path):
    """导出 GLB，Y 轴向上（glTF 标准）"""
    try:
        bpy.ops.export_scene.gltf(
            filepath=out_path,
            export_format="GLB",
            export_apply=True,   # 应用修改器
            export_yup=True,     # Z-up 转 Y-up
        )
        return True, ""
    except TypeError:
        # 老版本参数名不同，退化到最少参数
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
        mesh.calc_loop_triangles()
        total += len(mesh.loop_triangles)
    return total


def main():
    if not os.path.isdir(SRC_DIR):
        print("[错误] 输入文件夹不存在:", SRC_DIR)
        sys.exit(1)

    files = [f for f in sorted(os.listdir(SRC_DIR)) if f.lower().endswith(SUPPORTED)]
    if not files:
        print("[提示] 该文件夹里没有可转换的文件")
        print("       支持:", ", ".join(SUPPORTED))
        sys.exit(0)

    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 60)
    print("源文件夹:", SRC_DIR)
    print("输出到  :", OUT_DIR)
    print("共 %d 个文件" % len(files))
    print("=" * 60)

    rows = []
    ok_count = 0
    start_all = time.time()

    for idx, name in enumerate(files, 1):
        src = os.path.join(SRC_DIR, name)
        ext = os.path.splitext(name)[1].lower()
        stem = os.path.splitext(name)[0]
        dst = os.path.join(OUT_DIR, stem + ".glb")

        print("\n[%d/%d] %s" % (idx, len(files), name))

        reset_scene()

        ok, err = import_file(src, ext)
        if not ok:
            print("   ✗ 导入失败:", err)
            rows.append([name, "导入失败", 0, 0, 0, err])
            continue

        tris = count_triangles()
        ok, err = export_glb(dst)
        if not ok:
            print("   ✗ 导出失败:", err)
            rows.append([name, "导出失败", tris, 0, 0, err])
            continue

        src_kb = os.path.getsize(src) / 1024
        dst_kb = os.path.getsize(dst) / 1024 if os.path.exists(dst) else 0
        print("   ✓ %d 面  %.1f KB → %.1f KB" % (tris, src_kb, dst_kb))

        rows.append([name, "成功", tris, round(src_kb, 1), round(dst_kb, 1), ""])
        ok_count += 1

    # ---------- 报告 ----------
    with open(REPORT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["文件名", "状态", "三角面数", "源体积KB", "输出体积KB", "备注"])
        writer.writerows(rows)

    elapsed = time.time() - start_all
    print("\n" + "=" * 60)
    print("完成：成功 %d / 共 %d，用时 %.1f 秒" % (ok_count, len(files), elapsed))
    print("报告：", REPORT)
    print("=" * 60)


main()
