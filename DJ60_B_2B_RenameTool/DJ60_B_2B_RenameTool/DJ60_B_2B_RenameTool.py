import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re

# --- フォルダ選択 ---
def select_folder():
    path = filedialog.askdirectory()
    if path:
        entry_path.delete(0, tk.END)
        entry_path.insert(0, path)
        rebuild_tree(tree_left, path)
        rebuild_tree(tree_right, path)
        update_all_visuals()

# --- プレビュー更新 ---
def update_all_visuals(*args):
    update_tree_visuals(tree_left, sv_old_name.get(), is_preview=False)
    update_tree_visuals(tree_right, sv_old_name.get(), is_preview=True)

# --- ツリー再構築 ---
def rebuild_tree(tree, root_path):
    for i in tree.get_children(): tree.delete(i)
    if not os.path.exists(root_path): return
    tree.original_names = {}
    
    if not hasattr(root, 'global_excluded_paths'):
        root.global_excluded_paths = set()

    def add_nodes(parent_node, current_path):
        try:
            items = os.listdir(current_path)
            dirs = sorted([i for i in items if os.path.isdir(os.path.join(current_path, i))])
            files = sorted([i for i in items if not os.path.isdir(os.path.join(current_path, i))])
            for item in (dirs + files):
                full_p = os.path.normpath(os.path.join(current_path, item))
                is_dir = os.path.isdir(full_p)
                img = icon_folder if is_dir else icon_file
                node = tree.insert(parent_node, "end", text=" " + item, image=img, open=False)
                tree.original_names[node] = {"name": item, "full_path": full_p, "is_dir": is_dir}
                if is_dir:
                    add_nodes(node, full_p)
        except Exception: pass

    root_name = os.path.basename(root_path)
    root_node = tree.insert("", "end", text=" " + root_name, image=icon_folder, open=True)
    tree.original_names[root_node] = {"name": root_name, "full_path": os.path.normpath(root_path), "is_dir": True}
    add_nodes(root_node, root_path)

# --- フォルダ展開の同期ロジック ---
def sync_expansion(event):
    source_tree = event.widget
    target_tree = tree_right if source_tree == tree_left else tree_left
    item_id = source_tree.focus()
    if not item_id: return

    def get_index_path(tree, item):
        path = []
        while item:
            parent = tree.parent(item)
            if parent:
                path.insert(0, tree.index(item))
            item = parent
        return path

    def find_item_by_path(tree, path):
        root_children = tree.get_children("")
        if not root_children: return None
        node = root_children[0]
        for idx in path:
            children = tree.get_children(node)
            if idx < len(children):
                node = children[idx]
            else: return None
        return node

    path = get_index_path(source_tree, item_id)
    target_item = find_item_by_path(target_tree, path)
    if target_item:
        is_open = source_tree.item(item_id, "open")
        target_tree.item(target_item, open=is_open)

# --- 除外切り替え ---
def toggle_exclusion(event):
    tree = event.widget
    element = tree.identify_element(event.x, event.y)
    if element != "text" and element != "image": return

    item = tree.identify_row(event.y)
    if not item: return
    data = tree.original_names.get(item)
    if not data: return
    
    path = data["full_path"]
    if path in root.global_excluded_paths:
        root.global_excluded_paths.remove(path)
    else:
        root.global_excluded_paths.add(path)
    update_all_visuals()

# --- 名前生成 ---
def get_renamed_name(orig_name, old_target, new_target, is_dir):
    if not old_target or old_target not in orig_name:
        return orig_name
    if is_dir:
        return orig_name.replace(old_target, new_target)
    else:
        base, ext = os.path.splitext(orig_name)
        new_base = base.replace(old_target, new_target)
        return new_base + ext

# --- 見た目反映 ---
def update_tree_visuals(tree, search_text, is_preview=False):
    if not hasattr(tree, 'original_names'): return
    new_text = sv_new_name.get()

    def update_item(item):
        data = tree.original_names.get(item, {})
        orig_name = data.get("name", "")
        full_path = data.get("full_path", "")
        is_dir = data.get("is_dir", False)
        if not orig_name: return
        
        display_text = orig_name
        tag = ()
        mark_l, mark_r = " 【 ", " 】 "
        is_excluded = full_path in root.global_excluded_paths
        target_part = orig_name if is_dir else os.path.splitext(orig_name)[0]
        has_match = search_text and search_text in target_part

        if is_excluded:
            display_text = f" (除外) {orig_name}"
            tag = ("excluded",)
        elif has_match:
            if is_preview and new_text:
                res_name = get_renamed_name(orig_name, search_text, new_text, is_dir)
                display_text = res_name.replace(new_text, f"{mark_l}{new_text}{mark_r}", 1)
            else:
                base_display = target_part.replace(search_text, f"{mark_l}{search_text}{mark_r}", 1)
                display_text = base_display + (os.path.splitext(orig_name)[1] if not is_dir else "")
            tag = ("highlight",)
        
        tree.item(item, text=" " + display_text, tags=tag)
        for child in tree.get_children(item): update_item(child)

    for root_item in tree.get_children(''): update_item(root_item)

# --- スクロール同期 ---
def on_tree_scroll(*args):
    tree_left.yview_set(*args)
    tree_right.yview_set(*args)

def on_mouse_wheel(event):
    delta = int(-1*(event.delta/120)) if event.delta else 0
    tree_left.yview_scroll(delta, "units")
    tree_right.yview_scroll(delta, "units")
    return "break"

# --- 新規フォルダ ---
def create_new_folder():
    root_path = entry_path.get()
    if not root_path or not os.path.exists(root_path):
        messagebox.showwarning("警告", "先にフォルダを選択してください。"); return
    new_dir_path = os.path.join(root_path, "新しいフォルダー")
    counter = 2
    temp_path = new_dir_path
    while os.path.exists(temp_path):
        temp_path = f"{new_dir_path} ({counter})"; counter += 1
    os.makedirs(temp_path)
    rebuild_tree(tree_left, root_path); rebuild_tree(tree_right, root_path); update_all_visuals()

# --- リネーム実行 ---
def execute_rename():
    root_path = entry_path.get()
    old_target = sv_old_name.get().strip(); new_target = sv_new_name.get().strip()
    if not root_path or not os.path.exists(root_path): return
    if not old_target or not new_target:
        messagebox.showerror("入力エラー", "名称を入力してください。"); return
    confirm = messagebox.askyesno("確認", "リネームを実行しますか？")
    if not confirm: return
    count = 0
    try:
        for root_dir, dirs, files in os.walk(root_path, topdown=False):
            for name in dirs + files:
                full_p = os.path.normpath(os.path.join(root_dir, name))
                if full_p in root.global_excluded_paths: continue
                is_dir = os.path.isdir(full_p)
                new_name = get_renamed_name(name, old_target, new_target, is_dir)
                if new_name != name:
                    os.rename(full_p, os.path.join(root_dir, new_name)); count += 1
        messagebox.showinfo("完了", f"{count} 件リネーム完了")
        root.global_excluded_paths.clear()
        rebuild_tree(tree_left, root_path); rebuild_tree(tree_right, root_path); update_all_visuals()
    except Exception as e:
        messagebox.showerror("エラー", f"失敗: {e}")

# --- GUI ---
root = tk.Tk()
root.title("一括リネームツール")
root.geometry("820x720")
root.global_excluded_paths = set()

# スタイルの設定（選択時の青色を無効化）
style = ttk.Style()
# mapメソッドで、selected状態の背景色を通常時と同じ（あるいは透明）に上書きします
style.map("Treeview", 
          background=[("selected", "white")], 
          foreground=[("selected", "black")])

icon_folder = tk.PhotoImage(width=16, height=16)
icon_folder.put(("#FFD700",), to=(2, 4, 14, 14)); icon_folder.put(("#FFD700",), to=(2, 2, 8, 4))
icon_file = tk.PhotoImage(width=16, height=16)
icon_file.put(("#FFFFFF",), to=(4, 2, 12, 14)); icon_file.put(("#555555",), to=(4, 2, 12, 3)); icon_file.put(("#555555",), to=(4, 2, 5, 14)); icon_file.put(("#555555",), to=(11, 2, 12, 14)); icon_file.put(("#555555",), to=(4, 13, 12, 14))

root.columnconfigure(0, weight=1); root.rowconfigure(2, weight=1)

# 上部エリア
frame_top = tk.Frame(root); frame_top.grid(row=0, column=0, sticky="ew", padx=20, pady=10); frame_top.columnconfigure(1, weight=1)
tk.Label(frame_top, text="フォルダパス:").grid(row=0, column=0, sticky="w")
entry_path = tk.Entry(frame_top); entry_path.grid(row=0, column=1, padx=5, sticky="ew")
tk.Button(frame_top, text="選択", command=select_folder, width=8).grid(row=0, column=2)

sv_old_name = tk.StringVar(); sv_old_name.trace_add("write", update_all_visuals)
tk.Label(frame_top, text="リネーム前:").grid(row=1, column=0, sticky="w", pady=5)
tk.Entry(frame_top, textvariable=sv_old_name).grid(row=1, column=1, columnspan=2, sticky="ew")

sv_new_name = tk.StringVar(); sv_new_name.trace_add("write", update_all_visuals)
tk.Label(frame_top, text="リネーム後:").grid(row=2, column=0, sticky="w", pady=5)
tk.Entry(frame_top, textvariable=sv_new_name).grid(row=2, column=1, columnspan=2, sticky="ew")

# ラベル
label_frame = tk.Frame(root); label_frame.grid(row=1, column=0, sticky="ew", padx=20)
label_frame.columnconfigure(0, weight=1); label_frame.columnconfigure(2, weight=1)
tk.Label(label_frame, text="[リネーム前]").grid(row=0, column=0, sticky="w")
tk.Label(label_frame, text="[リネーム後]").grid(row=0, column=2, sticky="w")

# 中央ツリーエリア
container = tk.Frame(root); container.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
container.columnconfigure(0, weight=1); container.columnconfigure(1, minsize=20); container.columnconfigure(2, weight=1); container.rowconfigure(0, weight=1)

tree_left = ttk.Treeview(container, show="tree")
tree_right = ttk.Treeview(container, show="tree")

# タグの設定（水色：リネーム対象、グレー：除外対象）
tree_left.tag_configure("highlight", background="#E1F5FE")
tree_right.tag_configure("highlight", background="#E1F5FE")
tree_left.tag_configure("excluded", foreground="#888888", background="#F0F0F0")
tree_right.tag_configure("excluded", foreground="#888888", background="#F0F0F0")

sc_common = ttk.Scrollbar(container, orient="vertical", command=on_tree_scroll)
tree_left.configure(yscrollcommand=sc_common.set); tree_right.configure(yscrollcommand=sc_common.set)

tree_left.grid(row=0, column=0, sticky="nsew")
tk.Frame(container, width=20).grid(row=0, column=1) 
tree_right.grid(row=0, column=2, sticky="nsew")
sc_common.grid(row=0, column=3, sticky="ns")

# バインド
tree_left.bind("<MouseWheel>", on_mouse_wheel); tree_right.bind("<MouseWheel>", on_mouse_wheel)
tree_left.bind("<ButtonRelease-1>", toggle_exclusion); tree_right.bind("<ButtonRelease-1>", toggle_exclusion)
tree_left.bind("<<TreeviewOpen>>", sync_expansion); tree_left.bind("<<TreeviewClose>>", sync_expansion)
tree_right.bind("<<TreeviewOpen>>", sync_expansion); tree_right.bind("<<TreeviewClose>>", sync_expansion)

# --- 注意書きエリア ---
frame_info = tk.LabelFrame(root, text=" ツールのご案内 ", padx=10, pady=5, fg="#555555")
frame_info.grid(row=3, column=0, sticky="ew", padx=20, pady=5)
info_text = (
    "● 水色の行：リネーム対象です。　● グレーの行：除外対象です（リネームされません）。\n"
    "● 除外方法：リスト内の文字またはアイコンをクリックしてください。\n"
    "● 拡張子の保護：ファイル名の本体のみを書き換えます。拡張子は変更されません。"
)
tk.Label(frame_info, text=info_text, justify="left", fg="#666666", font=("", 9)).pack(anchor="w")

# 下部ボタン
frame_bot = tk.Frame(root); frame_bot.grid(row=4, column=0, sticky="ew", padx=20, pady=10)
tk.Button(frame_bot, text="新規フォルダ", command=create_new_folder, width=15).pack(side="left")
tk.Button(frame_bot, text="一括リネームを実行", command=execute_rename, width=20, bg="#e1e1e1").pack(side="right")

root.mainloop()