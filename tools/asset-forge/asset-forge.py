# -*- coding: utf-8 -*-
"""Asset Forge —— 资产转换工作台

把 Maya(.ma/.mb) / FBX / OBJ / STL / DAE / GLB 批量转成 FBX 和 GLB，
后端分别调用本机的 mayapy.exe 和 blender.exe 无界面运行。

启动方式：双击同目录的「启动 Asset Forge.bat」
依赖：Python 3 + tkinter；拖拽功能需要 tkinterdnd2（未安装时自动退化为按钮选文件夹）
"""
import glob
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ---------- 拖拽支持（可选） ----------
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    BaseTk = TkinterDnD.Tk
    HAS_DND = True
except Exception:
    BaseTk = tk.Tk
    HAS_DND = False

APP_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(APP_DIR)
ENGINE_DIR = os.path.join(APP_DIR, "engine")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

MAYA_ENGINE = os.path.join(ENGINE_DIR, "maya_export.py")
BLENDER_ENGINE = os.path.join(ENGINE_DIR, "blender_convert.py")

MAYA_EXTS = {".ma", ".mb"}
MODEL_EXTS = {".fbx", ".obj", ".stl", ".dae", ".glb", ".gltf"}
ALL_EXTS = MAYA_EXTS | MODEL_EXTS

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# ---------- 配色 ----------
BG = "#1e1f22"
PANEL = "#2b2d31"
PANEL2 = "#33353a"
FG = "#e8e8ea"
FG_DIM = "#9a9ca3"
ACCENT = "#4f9dff"
OK_COLOR = "#4caf50"
FAIL_COLOR = "#ef5350"
WARN_COLOR = "#ffb74d"


# ============================================================
#  配置与路径探测
# ============================================================
def load_config():
    data = {}
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    for key, default in (
        ("mayapy", ""),
        ("blender", ""),
        ("last_input", ""),
        ("last_output", ""),
        ("recursive", True),
    ):
        data.setdefault(key, default)
    return data


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def detect_mayapy():
    """按常见安装位置查找 mayapy.exe"""
    candidates = [
        r"F:\BaiduNetdiskDownload\Maya2022\bin\mayapy.exe",
        r"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe",
        r"C:\Program Files\Autodesk\Maya2023\bin\mayapy.exe",
        r"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe",
        r"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe",
        r"D:\Program Files\Autodesk\Maya2022\bin\mayapy.exe",
        r"F:\Program Files\Autodesk\Maya2022\bin\mayapy.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    for drive in ("C:", "D:", "E:", "F:"):
        for p in glob.glob(os.path.join(drive + os.sep, "**", "Autodesk", "Maya*", "bin", "mayapy.exe"), recursive=False):
            if os.path.isfile(p):
                return p
    found = shutil.which("mayapy")
    return found or ""


def detect_blender():
    """按常见安装位置查找 blender.exe"""
    candidates = [
        r"D:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    ]
    for drive in ("C:", "D:", "E:", "F:"):
        candidates.extend(
            sorted(
                glob.glob(os.path.join(drive + os.sep, "Program Files", "Blender Foundation", "Blender*", "blender.exe")),
                reverse=True,
            )
        )
    for p in candidates:
        if os.path.isfile(p):
            return p
    found = shutil.which("blender")
    return found or ""


def human_size(num_bytes):
    if num_bytes < 1024:
        return "%d B" % num_bytes
    if num_bytes < 1024 * 1024:
        return "%.1f KB" % (num_bytes / 1024.0)
    return "%.2f MB" % (num_bytes / 1024.0 / 1024.0)


class Toggle(ttk.Button):
    """自绘开关按钮。ttk 的 checkbox 在 clam 主题下指示器容易渲染成方框，
    直接做成按钮更稳，视觉效果也更接近现代桌面软件。"""

    def __init__(self, master, text, value=False, command=None, **kw):
        self._on = bool(value)
        self._label = text
        self._callback = command
        super().__init__(master, command=self._toggle, **kw)
        self._refresh()

    def _toggle(self):
        self._on = not self._on
        self._refresh()
        if self._callback:
            self._callback()

    def get(self):
        return self._on

    def set(self, value):
        self._on = bool(value)
        self._refresh()

    def _refresh(self):
        self.configure(
            text=("✓ " if self._on else "     ") + self._label,
            style="On.TButton" if self._on else "Off.TButton",
        )


# ============================================================
#  主窗口
# ============================================================
class AssetForge(BaseTk):
    def __init__(self):
        super().__init__()

        self.cfg = load_config()
        self.entries = []          # [{"path","name","ext","size","iid"}]
        self.name_to_iid = {}
        self.msg_queue = queue.Queue()
        self.worker_thread = None
        self.proc = None
        self.cancel_flag = False
        self.running = False

        self.title("Asset Forge — 资产转换工作台")
        self.configure(bg=BG)
        self.geometry("1040x760")
        self.minsize(860, 620)

        self._init_style()
        self._build_ui()

        if HAS_DND:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        self._autodetect_tools()
        self.after(80, self._pump_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- 样式 ----------
    def _init_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background=BG, foreground=FG, fieldbackground=PANEL2)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Panel.TLabel", background=PANEL, foreground=FG)
        style.configure("Dim.TLabel", background=BG, foreground=FG_DIM)
        style.configure("Title.TLabel", background=BG, foreground=FG, font=("Microsoft YaHei UI", 17, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=FG_DIM, font=("Microsoft YaHei UI", 9))
        style.configure("Stage.TLabel", background=BG, foreground=ACCENT, font=("Microsoft YaHei UI", 9, "bold"))

        style.configure(
            "TButton",
            background=PANEL2,
            foreground=FG,
            borderwidth=0,
            focusthickness=0,
            padding=(14, 7),
            font=("Microsoft YaHei UI", 9),
        )
        style.map("TButton", background=[("active", "#3d4046"), ("disabled", "#26282c")],
                  foreground=[("disabled", "#5c5e63")])

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#0b1220",
            font=("Microsoft YaHei UI", 10, "bold"),
            padding=(22, 9),
        )
        style.map("Accent.TButton", background=[("active", "#6fb1ff"), ("disabled", "#2f5f99")],
                  foreground=[("disabled", "#8ea4bf")])

        style.configure("Danger.TButton", background="#4a2a2c", foreground="#ff9a9a")
        style.map("Danger.TButton", background=[("active", "#5d3335")])

        # 自绘开关按钮（替代 checkbox，避免 clam 主题指示器缺字形）
        style.configure(
            "On.TButton",
            background="#24405f",
            foreground="#8fc2ff",
            font=("Microsoft YaHei UI", 9, "bold"),
            padding=(12, 6),
        )
        style.map("On.TButton", background=[("active", "#2d5076")])

        style.configure(
            "Off.TButton",
            background=PANEL2,
            foreground="#6b6d72",
            font=("Microsoft YaHei UI", 9),
            padding=(12, 6),
        )
        style.map("Off.TButton", background=[("active", "#3d4046")])

        style.configure(
            "TCheckbutton",
            background=BG,
            foreground=FG,
            font=("Microsoft YaHei UI", 9),
        )
        style.map("TCheckbutton", background=[("active", BG)], foreground=[("disabled", "#6b6d72")])

        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=FG,
            rowheight=25,
            borderwidth=0,
            font=("Microsoft YaHei UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=PANEL2,
            foreground=FG_DIM,
            relief="flat",
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        style.map("Treeview.Heading", background=[("active", PANEL2)])
        style.map("Treeview", background=[("selected", "#2f4f78")], foreground=[("selected", "#ffffff")])

        style.configure(
            "Horizontal.TProgressbar",
            background=ACCENT,
            troughcolor=PANEL2,
            borderwidth=0,
            thickness=8,
        )

        style.configure("TEntry", fieldbackground=PANEL2, foreground=FG, borderwidth=0, padding=6)

    # ---------- 界面 ----------
    def _build_ui(self):
        root = ttk.Frame(self, style="TFrame", padding=(16, 12, 16, 12))
        root.pack(fill="both", expand=True)

        # ===== 顶栏 =====
        top = ttk.Frame(root, style="TFrame")
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(top, text="Asset Forge", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="资产转换工作台", style="Sub.TLabel").pack(side="left", padx=(10, 0), pady=(7, 0))

        ttk.Button(top, text="⚙ 设置", command=self._open_settings).pack(side="right")

        self.env_label = ttk.Label(top, text="", style="Sub.TLabel")
        self.env_label.pack(side="right", padx=(0, 12))

        # ===== 输入行 =====
        row1 = ttk.Frame(root, style="TFrame")
        row1.pack(fill="x", pady=(0, 8))

        ttk.Button(row1, text="📁 选择文件夹", command=self._pick_folder).pack(side="left")
        ttk.Button(row1, text="清空", command=self._clear_list).pack(side="left", padx=(8, 0))

        self.recursive_toggle = Toggle(
            row1, "包含子文件夹", bool(self.cfg.get("recursive", True)),
            command=self._on_recursive_toggle,
        )
        self.recursive_toggle.pack(side="left", padx=(14, 0))

        self.hint_label = ttk.Label(
            row1,
            text="把文件夹拖进窗口" if HAS_DND else "（安装 tkinterdnd2 后可拖拽）",
            style="Sub.TLabel",
        )
        self.hint_label.pack(side="left", padx=(16, 0))

        self.path_label = ttk.Label(root, text="尚未选择文件夹", style="Dim.TLabel")
        self.path_label.pack(fill="x", pady=(0, 8))

        # ===== 文件列表 =====
        mid = ttk.Frame(root, style="TFrame")
        mid.pack(fill="both", expand=True)

        cols = ("name", "type", "size", "status")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("name", text="文件名")
        self.tree.heading("type", text="类型")
        self.tree.heading("size", text="大小")
        self.tree.heading("status", text="状态")
        self.tree.column("name", width=520, anchor="w")
        self.tree.column("type", width=80, anchor="center")
        self.tree.column("size", width=110, anchor="e")
        self.tree.column("status", width=150, anchor="center")

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.tag_configure("ok", foreground=OK_COLOR)
        self.tree.tag_configure("fail", foreground=FAIL_COLOR)
        self.tree.tag_configure("busy", foreground=WARN_COLOR)

        # ===== 选项行 =====
        opt = ttk.Frame(root, style="TFrame")
        opt.pack(fill="x", pady=(10, 6))

        ttk.Label(opt, text="输出", style="Dim.TLabel").pack(side="left")

        self.fbx_toggle = Toggle(opt, "FBX", True)
        self.fbx_toggle.pack(side="left", padx=(10, 0))

        self.glb_toggle = Toggle(opt, "GLB", True)
        self.glb_toggle.pack(side="left", padx=(6, 0))

        self.opt_toggle = Toggle(opt, "GLB 优化（减面 + 贴图降采样）", False)
        self.opt_toggle.pack(side="left", padx=(18, 0))

        # ===== 输出目录行 =====
        row2 = ttk.Frame(root, style="TFrame")
        row2.pack(fill="x", pady=(0, 10))

        ttk.Label(row2, text="输出目录", style="Dim.TLabel").pack(side="left")
        self.out_var = tk.StringVar(value=self.cfg.get("last_output", ""))
        ttk.Entry(row2, textvariable=self.out_var).pack(side="left", fill="x", expand=True, padx=(10, 8))
        ttk.Button(row2, text="浏览", command=self._pick_output).pack(side="left")

        # ===== 操作行 =====
        act = ttk.Frame(root, style="TFrame")
        act.pack(fill="x", pady=(0, 10))

        self.start_btn = ttk.Button(act, text="开始转换", style="Accent.TButton", command=self._start)
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(act, text="停止", style="Danger.TButton", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(10, 0))

        ttk.Button(act, text="打开输出目录", command=self._open_output).pack(side="left", padx=(10, 0))

        self.stage_label = ttk.Label(act, text="", style="Stage.TLabel")
        self.stage_label.pack(side="right")

        # ===== 进度条 =====
        self.progress = ttk.Progressbar(root, orient="horizontal", mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 6))

        self.progress_label = ttk.Label(root, text="就绪", style="Dim.TLabel")
        self.progress_label.pack(fill="x", pady=(0, 8))

        # ===== 日志 =====
        log_frame = ttk.Frame(root, style="TFrame")
        log_frame.pack(fill="both", expand=False)

        self.log = tk.Text(
            log_frame, height=9, bg="#141517", fg="#c9ccd1", insertbackground=FG,
            relief="flat", font=("Consolas", 9), wrap="word", padx=10, pady=8,
        )
        log_vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_vsb.set, state="disabled")
        self.log.pack(side="left", fill="both", expand=True)
        log_vsb.pack(side="right", fill="y")

        self.log.tag_configure("ok", foreground=OK_COLOR)
        self.log.tag_configure("fail", foreground=FAIL_COLOR)
        self.log.tag_configure("warn", foreground=WARN_COLOR)
        self.log.tag_configure("dim", foreground="#7c7f86")
        self.log.tag_configure("stage", foreground=ACCENT)

    # ---------- 环境探测 ----------
    def _autodetect_tools(self):
        changed = False
        if not self.cfg.get("mayapy") or not os.path.isfile(self.cfg["mayapy"]):
            found = detect_mayapy()
            if found:
                self.cfg["mayapy"] = found
                changed = True
        if not self.cfg.get("blender") or not os.path.isfile(self.cfg["blender"]):
            found = detect_blender()
            if found:
                self.cfg["blender"] = found
                changed = True
        if changed:
            save_config(self.cfg)
        self._refresh_env_label()

    def _refresh_env_label(self):
        maya = self.cfg.get("mayapy", "")
        blender = self.cfg.get("blender", "")
        maya_txt = "Maya ✓" if maya and os.path.isfile(maya) else "Maya ×"
        blender_txt = "Blender ✓" if blender and os.path.isfile(blender) else "Blender ×"
        self.env_label.configure(text="%s    %s" % (maya_txt, blender_txt))

    # ---------- 输入 ----------
    def _on_drop(self, event):
        try:
            paths = self.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        if paths:
            self._load_folder(paths[0])

    def _pick_folder(self):
        initial = self.cfg.get("last_input") or os.path.expanduser("~")
        folder = filedialog.askdirectory(title="选择包含模型的文件夹", initialdir=initial)
        if folder:
            self._load_folder(folder)

    def _on_recursive_toggle(self):
        self.cfg["recursive"] = bool(self.recursive_toggle.get())
        save_config(self.cfg)
        if self.cfg.get("last_input"):
            self._load_folder(self.cfg["last_input"])

    def _scan(self, folder, recursive):
        found = []
        if recursive:
            for dirpath, _dirnames, filenames in os.walk(folder):
                for fn in sorted(filenames):
                    if os.path.splitext(fn)[1].lower() in ALL_EXTS:
                        full = os.path.join(dirpath, fn)
                        rel = os.path.relpath(full, folder)
                        found.append((full, rel))
        else:
            for fn in sorted(os.listdir(folder)):
                full = os.path.join(folder, fn)
                if os.path.isfile(full) and os.path.splitext(fn)[1].lower() in ALL_EXTS:
                    found.append((full, fn))
        return found

    def _load_folder(self, folder):
        if self.running:
            self._log("转换进行中，请先停止再换文件夹", "warn")
            return
        if not os.path.isdir(folder):
            messagebox.showwarning("提示", "这不是一个文件夹：\n%s" % folder)
            return

        files = self._scan(folder, self.recursive_toggle.get())
        if not files:
            messagebox.showinfo(
                "没有找到模型文件",
                "该文件夹里没有支持的格式。\n\n支持：.ma .mb .fbx .obj .stl .dae .glb .gltf",
            )
            return

        self._clear_list()
        self.cfg["last_input"] = folder
        self.path_label.configure(text=folder)
        if not self.out_var.get():
            self.out_var.set(os.path.join(folder, "converted"))
        save_config(self.cfg)

        for idx, (full, rel) in enumerate(files):
            ext = os.path.splitext(full)[1].lower()
            size = os.path.getsize(full) if os.path.isfile(full) else 0
            iid = "row%d" % idx
            self.tree.insert(
                "", "end", iid=iid,
                values=(rel, ext.lstrip(".").upper(), human_size(size), "待转换"),
            )
            self.entries.append({"path": full, "name": rel, "ext": ext, "size": size, "iid": iid})
            self.name_to_iid[rel] = iid

        self._log("已载入 %d 个文件：%s" % (len(files), folder), "dim")
        self._set_progress(0, 100, "就绪，共 %d 个文件" % len(files))

    def _clear_list(self):
        if self.running:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.entries = []
        self.name_to_iid = {}
        self.path_label.configure(text="尚未选择文件夹")
        self._set_progress(0, 100, "就绪")

    # ---------- 输出目录 ----------
    def _pick_output(self):
        initial = self.out_var.get() or self.cfg.get("last_input") or os.path.expanduser("~")
        folder = filedialog.askdirectory(title="选择输出目录", initialdir=initial)
        if folder:
            self.out_var.set(folder)

    def _open_output(self):
        out = self.out_var.get().strip()
        if not out:
            messagebox.showinfo("提示", "还没有设置输出目录")
            return
        if not os.path.isdir(out):
            try:
                os.makedirs(out, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", "无法创建输出目录：\n%s" % e)
                return
        os.startfile(out)

    # ---------- 日志 / 进度 ----------
    def _log(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_progress(self, value, maximum, text=""):
        self.progress.configure(maximum=max(maximum, 1), value=value)
        if text:
            self.progress_label.configure(text=text)

    # ---------- 转换 ----------
    def _start(self):
        if self.running:
            return
        if not self.entries:
            messagebox.showinfo("提示", "先选择或拖入一个包含模型的文件夹")
            return

        out_dir = self.out_var.get().strip()
        if not out_dir:
            messagebox.showinfo("提示", "请先设置输出目录")
            return

        want_fbx = self.fbx_toggle.get()
        want_glb = self.glb_toggle.get()
        want_opt = self.opt_toggle.get()

        if not want_fbx and not want_glb:
            messagebox.showinfo("提示", "至少勾选一种输出格式（FBX 或 GLB）")
            return

        maya_entries = [e for e in self.entries if e["ext"] in MAYA_EXTS]
        if (want_fbx or want_glb) and maya_entries:
            mayapy = self.cfg.get("mayapy", "")
            if not mayapy or not os.path.isfile(mayapy):
                messagebox.showerror(
                    "找不到 Maya",
                    "有 .ma/.mb 文件需要 Maya 处理，但没有找到 mayapy.exe。\n\n请点右上角「设置」指定路径。",
                )
                return

        other_entries = [e for e in self.entries if e["ext"] in MODEL_EXTS]
        if want_glb and (other_entries or maya_entries):
            blender = self.cfg.get("blender", "")
            if not blender or not os.path.isfile(blender):
                messagebox.showerror(
                    "找不到 Blender",
                    "转 GLB 需要 Blender，但没有找到 blender.exe。\n\n请点右上角「设置」指定路径。",
                )
                return

        self.running = True
        self.cancel_flag = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._reset_status()

        self._log("─" * 56, "dim")
        self._log("开始转换 · 输出到 %s" % out_dir, "stage")

        args = (list(self.entries), out_dir, want_fbx, want_glb, want_opt)
        self.worker_thread = threading.Thread(target=self._worker, args=args, daemon=True)
        self.worker_thread.start()

    def _reset_status(self):
        for e in self.entries:
            self.tree.set(e["iid"], "status", "等待")
            self.tree.item(e["iid"], tags=())

    def _stop(self):
        if not self.running:
            return
        self.cancel_flag = True
        self._log("正在停止…", "warn")
        proc = self.proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        self.stop_btn.configure(state="disabled")

    # ---------- 工作线程 ----------
    def _worker(self, entries, out_dir, want_fbx, want_glb, want_opt):
        try:
            self._run_pipeline(entries, out_dir, want_fbx, want_glb, want_opt)
        except Exception:
            self.msg_queue.put(("log", "内部错误：" + traceback.format_exc(), "fail"))
            self.msg_queue.put(("finished", False, "转换中断"))
        finally:
            self.msg_queue.put(("state", False))

    def _run_pipeline(self, entries, out_dir, want_fbx, want_glb, want_opt):
        os.makedirs(out_dir, exist_ok=True)

        maya_entries = [e for e in entries if e["ext"] in MAYA_EXTS]
        other_entries = [e for e in entries if e["ext"] in MODEL_EXTS]

        fbx_dir = os.path.join(out_dir, "fbx") if want_fbx else os.path.join(out_dir, "_fbx_temp")
        glb_dir = os.path.join(out_dir, "glb")

        need_maya = bool(maya_entries) and (want_fbx or want_glb)
        fbx_count = len(maya_entries) if need_maya else 0
        glb_count = (len(other_entries) + fbx_count) if want_glb else 0
        opt_count = glb_count if (want_glb and want_opt) else 0

        total = fbx_count + glb_count + opt_count
        self.msg_queue.put(("total", total))

        done = 0

        # ---- 第 1 段：Maya -> FBX ----
        produced_fbx = []
        if need_maya:
            if self.cancel_flag:
                self.msg_queue.put(("finished", False, "已取消"))
                return
            self.msg_queue.put(("stage", "第 1 段 · Maya 导出 FBX"))
            manifest = self._write_manifest(out_dir, "_maya_manifest.json", maya_entries)
            if manifest is None:
                self.msg_queue.put(("finished", False, "清单写入失败"))
                return

            # 记录运行前的文件快照，避免把上次遗留的 FBX 当成这次的产物
            before = set(os.listdir(fbx_dir)) if os.path.isdir(fbx_dir) else set()

            cmd = [self.cfg["mayapy"], MAYA_ENGINE, manifest, fbx_dir]
            self._run_engine(cmd, "fbx", out_dir)
            done += fbx_count
            self.msg_queue.put(("done_inc", done, total))

            if os.path.isdir(fbx_dir):
                after = set(os.listdir(fbx_dir))
                produced_fbx = [
                    {"path": os.path.join(fbx_dir, f), "name": f}
                    for f in sorted(after - before)
                    if f.lower().endswith(".fbx")
                ]

        if self.cancel_flag:
            self.msg_queue.put(("finished", False, "已取消"))
            return

        # ---- 第 2 段：各种格式 -> GLB ----
        if want_glb:
            glb_inputs = list(other_entries) + produced_fbx
            if glb_inputs:
                self.msg_queue.put(("stage", "第 2 段 · Blender 转 GLB"))
                manifest = self._write_manifest(out_dir, "_glb_manifest.json", glb_inputs)
                if manifest is None:
                    self.msg_queue.put(("finished", False, "清单写入失败"))
                    return
                cmd = [self.cfg["blender"], "-b", "-P", BLENDER_ENGINE, "--", manifest, glb_dir]
                self._run_engine(cmd, "glb", out_dir)
                done += glb_count
                self.msg_queue.put(("done_inc", done, total))
            else:
                done += glb_count

        if self.cancel_flag:
            self.msg_queue.put(("finished", False, "已取消"))
            return

        # ---- 第 3 段：优化 ----
        if want_glb and want_opt:
            opt_out = os.path.join(out_dir, "optimized")
            glbs = sorted(
                f for f in os.listdir(glb_dir)
                if f.lower().endswith(".glb")
            ) if os.path.isdir(glb_dir) else []
            if glbs:
                self.msg_queue.put(("stage", "第 3 段 · GLB 优化"))
                os.makedirs(opt_out, exist_ok=True)
                npx = shutil.which("npx")
                if not npx or not os.path.isdir(os.path.join(TOOLS_DIR, "node_modules")):
                    self.msg_queue.put(("log", "缺少 @gltf-transform/cli 依赖，跳过优化", "warn"))
                    done += opt_count
                else:
                    for i, name in enumerate(glbs, 1):
                        if self.cancel_flag:
                            break
                        src = os.path.join(glb_dir, name)
                        dst = os.path.join(opt_out, name)
                        self.msg_queue.put(("log", "  优化 %s (%d/%d)" % (name, i, len(glbs)), None))
                        ok = self._run_optimize(npx, src, dst)
                        self.msg_queue.put(("log", "  %s %s" % ("✓" if ok else "×", name),
                                           "ok" if ok else "fail"))
                        done += 1
                        self.msg_queue.put(("done_inc", done, total))

        # ---- 收尾 ----
        if want_fbx is False and os.path.isdir(fbx_dir):
            pass  # 临时 FBX 保留，方便排查，不自动删除

        self.msg_queue.put(("finished", True, "全部完成"))

    def _run_optimize(self, npx, src, dst):
        cmd = [npx, "--no-install", "@gltf-transform/cli", "optimize", src, dst,
               "--compress", "false", "--texture-size", "1024"]
        try:
            r = subprocess.run(
                cmd, cwd=TOOLS_DIR, creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", timeout=600,
            )
            return r.returncode == 0 and os.path.exists(dst)
        except Exception:
            return False

    def _write_manifest(self, out_dir, filename, entries):
        path = os.path.join(out_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"files": [{"path": e["path"], "name": e["name"]} for e in entries]},
                          f, ensure_ascii=False, indent=1)
            return path
        except Exception as e:
            self.msg_queue.put(("log", "清单写入失败：%s" % e, "fail"))
            return None

    def _run_engine(self, cmd, kind, out_dir):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception as e:
            self.msg_queue.put(("log", "启动引擎失败：%s" % e, "fail"))
            return

        for raw in self.proc.stdout:
            line = raw.rstrip("\n").rstrip("\r")
            if not line:
                continue
            self._handle_engine_line(line, kind)

        self.proc.wait()

    def _handle_engine_line(self, line, kind):
        if line.startswith("##"):
            parts = line[2:].split("|")
            head = parts[0]

            if head == "PROGRESS":
                idx, total, name = parts[1], parts[2], "|".join(parts[3:])
                self.msg_queue.put(("busy", name))
                self.msg_queue.put(("log", "▶ %s/%s  %s" % (idx, total, name), None))

            elif head == "DONE":
                name = parts[1]
                status = parts[2]
                value = parts[3] if len(parts) > 3 else ""
                note = "|".join(parts[4:]) if len(parts) > 4 else ""
                if status == "ok":
                    extra = ("%s 面" % value) if kind == "glb" else ("%s KB" % value)
                    self.msg_queue.put(("row", name, "✓ 完成 %s" % extra, "ok"))
                    self.msg_queue.put(("log", "   ✓ %s  %s" % (name, extra), "ok"))
                else:
                    self.msg_queue.put(("row", name, "× 失败", "fail"))
                    self.msg_queue.put(("log", "   × %s  %s" % (name, note), "fail"))

            elif head == "FINISH":
                ok, total = parts[1], parts[2]
                self.msg_queue.put(("log", "—— 本段完成：成功 %s / %s ——" % (ok, total), "dim"))

            elif head == "ERROR":
                self.msg_queue.put(("log", "❗ " + "|".join(parts[1:]), "fail"))

            elif head == "TOTAL":
                pass

        else:
            low = line.lower()
            # Maya / Arnold 启动时的底层噪音，对用户没有意义
            noise = ("ntdll.dll", "rtlraiseexception", "stack trace", "kernel32.dll", "at <")
            if any(n in low for n in noise):
                return
            if any(k in low for k in ("error", "traceback", "exception", "错误", "失败", "警告")):
                self.msg_queue.put(("log", "   " + line.strip(), "warn"))
            elif line.startswith(("Maya 导出", "Blender 转 GLB", "源目录", "输出到")):
                self.msg_queue.put(("log", "   " + line.strip(), "dim"))

    # ---------- 队列泵 ----------
    def _pump_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                kind = msg[0]

                if kind == "log":
                    self._log(msg[1], msg[2])
                elif kind == "total":
                    self._set_progress(0, max(msg[1], 1), "准备中，共 %d 个任务" % msg[1])
                elif kind == "done_inc":
                    done, total = msg[1], msg[2]
                    self._set_progress(done, max(total, 1), "%d / %d" % (done, total))
                elif kind == "row":
                    _, name, text, tag = msg
                    iid = self.name_to_iid.get(name)
                    if iid and self.tree.exists(iid):
                        self.tree.set(iid, "status", text)
                        self.tree.item(iid, tags=(tag,))
                elif kind == "busy":
                    _, name = msg
                    iid = self.name_to_iid.get(name)
                    if iid and self.tree.exists(iid):
                        self.tree.set(iid, "status", "转换中…")
                        self.tree.item(iid, tags=("busy",))
                        self.tree.see(iid)
                elif kind == "stage":
                    self.stage_label.configure(text=msg[1])
                elif kind == "finished":
                    self._on_finished(msg[1], msg[2])
                elif kind == "state":
                    self.running = False
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")

        except queue.Empty:
            pass

        self.after(80, self._pump_queue)

    def _on_finished(self, ok, text):
        if ok:
            self._set_progress(self.progress["maximum"], self.progress["maximum"], "完成")
            self._log("✔ " + text, "ok")
            self.stage_label.configure(text="完成")
        else:
            self.progress_label.configure(text=text)
            self._log("■ " + text, "warn")

    # ---------- 设置对话框 ----------
    def _open_settings(self):
        win = tk.Toplevel(self)
        win.title("设置")
        win.configure(bg=BG)
        win.geometry("760x260")
        win.transient(self)
        win.grab_set()

        frame = ttk.Frame(win, style="TFrame", padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="mayapy.exe（Maya 无界面 Python）", style="TLabel").pack(anchor="w")
        maya_var = tk.StringVar(value=self.cfg.get("mayapy", ""))
        row = ttk.Frame(frame, style="TFrame")
        row.pack(fill="x", pady=(4, 14))
        ttk.Entry(row, textvariable=maya_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="浏览", command=lambda: self._browse_exe(maya_var)).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="自动检测", command=lambda: maya_var.set(detect_mayapy())).pack(side="left", padx=(6, 0))

        ttk.Label(frame, text="blender.exe（Blender 主程序）", style="TLabel").pack(anchor="w")
        blend_var = tk.StringVar(value=self.cfg.get("blender", ""))
        row2 = ttk.Frame(frame, style="TFrame")
        row2.pack(fill="x", pady=(4, 16))
        ttk.Entry(row2, textvariable=blend_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="浏览", command=lambda: self._browse_exe(blend_var)).pack(side="left", padx=(8, 0))
        ttk.Button(row2, text="自动检测", command=lambda: blend_var.set(detect_blender())).pack(side="left", padx=(6, 0))

        ttk.Label(
            frame,
            text="提示：路径只需设置一次，会保存在 config.json 里。",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        btns = ttk.Frame(frame, style="TFrame")
        btns.pack(fill="x")

        def do_save():
            self.cfg["mayapy"] = maya_var.get().strip()
            self.cfg["blender"] = blend_var.get().strip()
            save_config(self.cfg)
            self._refresh_env_label()
            win.destroy()

        ttk.Button(btns, text="保存", style="Accent.TButton", command=do_save).pack(side="right")
        ttk.Button(btns, text="取消", command=win.destroy).pack(side="right", padx=(0, 8))

    def _browse_exe(self, var):
        path = filedialog.askopenfilename(
            title="选择可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
        )
        if path:
            var.set(path)

    # ---------- 关闭 ----------
    def _on_close(self):
        if self.running:
            if not messagebox.askyesno("确认", "转换还在进行，确定要退出吗？"):
                return
            self.cancel_flag = True
            proc = self.proc
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
        self.destroy()


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = AssetForge()
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = os.path.join(APP_DIR, "asset-forge-error.log")
        try:
            with open(err, "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
        raise
