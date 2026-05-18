import os
import sys
import json
import shutil
import threading
import webbrowser
import ctypes
import platform
import urllib.request
import subprocess
import tarfile
from io import BytesIO
from zipfile import ZipFile
import tkinter as tk
from tkinter import ttk, filedialog
from yt_dlp import YoutubeDL
from PIL import Image, ImageOps, ImageTk

CURRENT_VERSION = "v1.0.6d"

try:
    if platform.system() == "Windows":
        myappid = 'clipperlight.app'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".clipper_dl_config.json")

if platform.system() == "Windows":
    FFMPEG_DIR = "C:\\ytdl"
    FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    FFMPEG_BINARY = "ffmpeg.exe"
    FFPROBE_BINARY = "ffprobe.exe"
else:
    FFMPEG_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "clipper-ffmpeg")
    FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
    FFMPEG_BINARY = "ffmpeg"
    FFPROBE_BINARY = "ffprobe"

BASE_PATH = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
ICON_FILE = os.path.join(BASE_PATH, "app_icon.ico")

class VideoDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Clipper")
        self.root.withdraw()
        self.root.geometry("480x370")
        self.root.resizable(False, False)
        
        self.style = ttk.Style()
        
        self.themes = {
            "light": {
                "bg": "#f0f0f0", "fg": "#000000", "frame_bg": "#f0f0f0",
                "entry_bg": "#ffffff", "entry_fg": "#000000", "accent": "#333333",
                "link": "#0066cc", "title_bar": 0x00F0F0F0, "progress_bar": "#000000"
            },
            "dark": {
                "bg": "#1e1e1e", "fg": "#ffffff", "frame_bg": "#1e1e1e",
                "entry_bg": "#2d2d2d", "entry_fg": "#ffffff", "accent": "#aaaaaa",
                "link": "#4da6ff", "title_bar": 0x001E1E1E, "progress_bar": "#ffffff"
            }
        }
        
        self.center_window(self.root, 480, 370)
        self.load_settings()
        self.generate_native_icon()
        
        self.init_frame = tk.Frame(self.root)
        self.main_frame = tk.Frame(self.root)
        self.missing_frame = tk.Frame(self.root)
        self.download_frame = tk.Frame(self.root)
        self.manual_frame = tk.Frame(self.root)
        self.update_frame = tk.Frame(self.root)
        
        self.build_init_screen()
        self.build_missing_screen()
        self.build_download_screen()
        self.build_main_screen()
        self.build_manual_screen()
        self.build_update_screen()
        self.build_footer_navigation()
        
        self.apply_theme()
        
        self.show_screen(self.init_frame, footer=False)
        self.root.deiconify()
        self.root.after(500, self.run_startup_checks)

    def center_window(self, target, width, height):
        target.update_idletasks()
        x = (target.winfo_screenwidth() // 2) - (width // 2)
        y = (target.winfo_screenheight() // 2) - (height // 2)
        target.geometry(f'{width}x{height}+{x}+{y}')

    def generate_native_icon(self):
        try:
            target_path = ICON_FILE if os.path.exists(ICON_FILE) else "app_icon.ico"
            if os.path.exists(target_path):
                img = Image.open(target_path).convert("RGBA")
                r, g, b, a = img.split()
                rgb_img = Image.merge("RGB", (r, g, b))
                
                if self.theme_var.get() == "light":
                    inverted_rgb = ImageOps.invert(rgb_img)
                    final_img = Image.merge("RGBA", (*inverted_rgb.split(), a))
                else:
                    final_img = img
                
                self.tk_icon = ImageTk.PhotoImage(final_img)
                if platform.system() == "Windows":
                    self.root.wm_iconphoto(False, self.tk_icon)
                else:
                    self.root.iconphoto(True, self.tk_icon)
        except Exception:
            pass

    def update_windows_title_bar(self, window_handle, color_hex_int):
        if platform.system() != "Windows":
            return
        try:
            DWMWA_CAPTION_COLOR = 35
            hwnd = ctypes.windll.user32.GetParent(window_handle.winfo_id())
            if hwnd == 0:
                hwnd = window_handle.winfo_id()
            color = ctypes.c_int(color_hex_int)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(color), ctypes.sizeof(color)
            )
        except Exception:
            pass

    def run_startup_checks(self):
        threading.Thread(target=self.check_updates_and_environment, daemon=True).start()

    def check_updates_and_environment(self):
        update_target_url = None
        
        try:
            api_url = "https://api.github.com/repos/justrainlol/clipper/releases/latest"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Clipper-Update-Checker'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode())
                target_tag = data.get("tag_name", "")
                
                if target_tag and target_tag != CURRENT_VERSION:
                    assets = data.get("assets", [])
                    if assets:
                        for asset in assets:
                            asset_name = asset.get("name", "")
                            if platform.system() == "Windows" and "win" in asset_name:
                                update_target_url = asset.get("browser_download_url")
                                break
                            elif platform.system() != "Windows" and "linux" in asset_name:
                                update_target_url = asset.get("browser_download_url")
                                break
                        if not update_target_url and assets:
                            update_target_url = assets[0].get("browser_download_url")
                    else:
                        update_target_url = data.get("zipball_url")
        except Exception:
            pass

        if update_target_url:
            self.root.after(0, lambda: self.show_screen(self.update_frame, footer=False))
            self.root.after(0, lambda: self.update_progress_bar_custom(self.update_canvas, 0))
            threading.Thread(target=self.download_and_install_update, args=(update_target_url,), daemon=True).start()
            return

        self.verify_local_environment()

    def download_and_install_update(self, download_url):
        try:
            req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', 0))
                bytes_so_far = 0
                buffer = BytesIO()
                chunk_size = 1024 * 64
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    bytes_so_far += len(chunk)
                    buffer.write(chunk)
                    if total_size > 0:
                        percent = int((bytes_so_far / total_size) * 100)
                        self.root.after(0, lambda p=percent: self.update_progress_bar_custom(self.update_canvas, p))
            
            buffer.seek(0)
            current_executable = os.path.abspath(sys.argv[0])
            temp_dir = os.path.dirname(CONFIG_FILE)
            new_executable_path = os.path.join(temp_dir, "Clipper_update_temp" + (".exe" if platform.system() == "Windows" else ""))
            
            if download_url.endswith(".zip"):
                with ZipFile(buffer) as zip_file:
                    for member in zip_file.namelist():
                        if "win" in member or member.endswith(".exe"):
                            with zip_file.open(member) as source, open(new_executable_path, "wb") as target:
                                target.write(source.read())
                            break
            else:
                with open(new_executable_path, "wb") as target:
                    target.write(buffer.read())
                    
            if platform.system() != "Windows":
                os.chmod(new_executable_path, 0o755)

            if platform.system() == "Windows":
                batch_script_path = os.path.join(os.environ.get("TEMP", temp_dir), "clipper_updater.bat")
                with open(batch_script_path, "w") as f:
                    f.write(f'@echo off\n'
                            f'timeout /t 1 /nobreak >nul\n'
                            f':wait\n'
                            f'tasklist | findstr /i "{os.path.basename(current_executable)}" >nul\n'
                            f'if %errorlevel% equ 0 (\n'
                            f'    taskkill /f /im "{os.path.basename(current_executable)}" >nul 2>&1\n'
                            f'    timeout /t 1 /nobreak >nul\n'
                            f'    goto wait\n'
                            f')\n'
                            f'move /y "{new_executable_path}" "{current_executable}" >nul\n'
                            f'start "" "{current_executable}"\n'
                            f'del "%~f0"\n')
                
                subprocess.Popen(
                    f'cmd.exe /c start /b "" "{batch_script_path}"', 
                    shell=True, 
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS
                )
            else:
                shell_script_path = os.path.join(temp_dir, "updater.sh")
                with open(shell_script_path, "w") as f:
                    f.write(f'#!/bin/sh\n'
                            f'sleep 1\n'
                            f'cp -f "{new_executable_path}" "{current_executable}"\n'
                            f'chmod +x "{current_executable}"\n'
                            f'"{current_executable}" &\n'
                            f'rm -- "$0"\n')
                os.chmod(shell_script_path, 0o755)
                subprocess.Popen(["/bin/sh", shell_script_path], start_new_session=True)
                
            self.root.after(0, lambda: self.root.destroy())
        except Exception:
            self.root.after(0, self.verify_local_environment)

    def verify_local_environment(self):
        system_has_ffmpeg = False
        try:
            if shutil.which(FFMPEG_BINARY) and shutil.which(FFPROBE_BINARY):
                system_has_ffmpeg = True
        except Exception:
            pass

        has_ffmpeg = system_has_ffmpeg or (os.path.exists(os.path.join(FFMPEG_DIR, FFMPEG_BINARY)) and os.path.exists(os.path.join(FFMPEG_DIR, FFPROBE_BINARY)))
        has_dir = os.path.exists(self.dir_var.get())
        
        if has_ffmpeg and has_dir:
            self.root.after(0, lambda: self.show_screen(self.main_frame))
        else:
            if not has_ffmpeg:
                self.root.after(0, lambda: self.show_screen(self.missing_frame, footer=False))
            elif not has_dir:
                self.root.after(0, lambda: self.show_screen(self.init_frame, footer=False))
                self.root.after(1000, self.auto_fix_missing_directory)

    def check_environment(self):
        threading.Thread(target=self.verify_local_environment, daemon=True).start()
        return True

    def show_screen(self, target_frame, footer=True):
        self.init_frame.pack_forget()
        self.missing_frame.pack_forget()
        self.download_frame.pack_forget()
        self.main_frame.pack_forget()
        self.manual_frame.pack_forget()
        self.update_frame.pack_forget()
        
        if footer:
            self.footer_frame.pack(side="bottom", fill="x", padx=10, pady=5)
            target_frame.pack(fill="both", expand=True, pady=(0, 45))
        else:
            self.footer_frame.pack_forget()
            target_frame.pack(fill="both", expand=True)

    def auto_fix_missing_directory(self):
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(default_dir, exist_ok=True)
        self.dir_var.set(default_dir)
        self.save_settings()
        self.check_environment()

    def build_clickable_link(self, parent, text, url, font_cfg=("Arial", 9)):
        lbl = tk.Label(parent, text=text, font=font_cfg, cursor="hand2")
        lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
        return lbl

    def apply_theme(self):
        mode = self.theme_var.get()
        colors = self.themes[mode]
        
        self.root.config(bg=colors["bg"])
        self.update_windows_title_bar(self.root, colors["title_bar"])
        self.generate_native_icon()
        
        for frame in [self.main_frame, self.init_frame, self.missing_frame, self.download_frame, self.manual_frame, self.update_frame, self.footer_frame]:
            frame.config(bg=colors["bg"])
            for child in frame.winfo_children():
                if isinstance(child, tk.Frame):
                    child.config(bg=colors["bg"])
                    for sub_child in child.winfo_children():
                        if isinstance(sub_child, (tk.Label, tk.Checkbutton)):
                            if hasattr(sub_child, "_is_hyperlink") and sub_child._is_hyperlink:
                                sub_child.config(bg=colors["bg"], fg=colors["link"])
                            else:
                                sub_child.config(bg=colors["bg"], fg=colors["fg"])
                            if isinstance(sub_child, tk.Checkbutton):
                                sub_child.config(selectcolor=colors["entry_bg"], activebackground=colors["bg"], activeforeground=colors["fg"])
                elif isinstance(child, (tk.Label, tk.Checkbutton)):
                    if hasattr(child, "_is_hyperlink") and child._is_hyperlink:
                        child.config(bg=colors["bg"], fg=colors["link"])
                    else:
                        child.config(bg=colors["bg"], fg=colors["fg"])
                    if isinstance(child, tk.Checkbutton):
                        child.config(selectcolor=colors["entry_bg"], activebackground=colors["bg"], activeforeground=colors["fg"])
                elif isinstance(child, tk.Entry):
                    child.config(bg=colors["entry_bg"], fg=colors["entry_fg"], insertbackground=colors["fg"])
                elif isinstance(child, tk.Canvas):
                    child.config(bg=colors["bg"])
        
        self.update_progress_bar_custom(self.progress_canvas, 0)
        self.update_progress_bar_custom(self.update_canvas, 0)
        
        theme_icon = "☀️" if mode == "light" else "🌙"
        self.theme_btn.config(text=theme_icon, bg=colors["bg"], fg=colors["fg"], activebackground=colors["bg"])
        self.info_btn.config(bg=colors["bg"], fg=colors["fg"], activebackground=colors["bg"])

    def toggle_theme(self):
        self.theme_var.set("dark" if self.theme_var.get() == "light" else "light")
        self.save_settings()
        self.apply_theme()

    def build_init_screen(self):
        lbl = tk.Label(self.init_frame, text="🪶", font=("Arial", 36))
        lbl.pack(expand=True)

    def build_missing_screen(self):
        icon = tk.Label(self.missing_frame, text="🪶", font=("Arial", 36))
        icon.pack(pady=(60, 5))
        
        msg = tk.Label(self.missing_frame, text="Missing framework tools (FFmpeg).", font=("Arial", 10, "bold"))
        msg.pack(pady=10)
        
        btn_frame = tk.Frame(self.missing_frame)
        btn_frame.pack(pady=15)
        
        self.auto_btn = ttk.Button(btn_frame, text="Auto Setup", command=self.start_auto_download, width=16)
        self.auto_btn.grid(row=0, column=0, padx=10)
        
        self.manual_btn = ttk.Button(btn_frame, text="Manual Setup", command=lambda: self.show_screen(self.manual_frame), width=16)
        self.manual_btn.grid(row=0, column=1, padx=10)

    def build_update_screen(self):
        icon = tk.Label(self.update_frame, text="🪶", font=("Arial", 36))
        icon.pack(pady=(80, 5))
        
        update_msg = tk.Label(self.update_frame, text="Downloading app update...", font=("Arial", 10, "bold"))
        update_msg.pack(pady=5)
        
        self.update_canvas = tk.Canvas(self.update_frame, width=280, height=8, highlightthickness=0, bd=0)
        self.update_canvas.pack(pady=5)
        
        restart_notice = tk.Label(self.update_frame, text="App will restart after update completes.", font=("Arial", 9, "italic"))
        restart_notice.pack(pady=5)

    def build_download_screen(self):
        icon = tk.Label(self.download_frame, text="🪶", font=("Arial", 36))
        icon.pack(pady=(110, 15))
        
        self.progress_canvas = tk.Canvas(self.download_frame, width=280, height=8, highlightthickness=0, bd=0)
        self.progress_canvas.pack(pady=5)

    def update_progress_bar_custom(self, canvas_widget, percentage):
        if not canvas_widget:
            return
        canvas_widget.delete("all")
        mode = self.theme_var.get()
        colors = self.themes[mode]
        bar_color = colors.get("progress_bar", "#000000")
        bg_color = "#e0e0e0" if mode == "light" else "#333333"
        
        canvas_widget.create_rectangle(0, 0, 280, 8, fill=bg_color, outline="")
        fill_width = int((percentage / 100) * 280)
        if fill_width > 0:
            canvas_widget.create_rectangle(0, 0, fill_width, 8, fill=bar_color, outline="")
        self.root.update_idletasks()

    def build_manual_screen(self):
        tk.Label(self.manual_frame, text="🪶 Manual Setup", font=("Arial", 12, "bold")).pack(pady=(25, 15))
        
        steps = [
            "1. Open up browser and head over to ffmpeg.org/download.html",
            f"2. Download archive file containing '{FFMPEG_BINARY}' and '{FFPROBE_BINARY}'",
            f"3. Place both extraction files inside folder path: {FFMPEG_DIR}"
        ]
        
        for step in steps:
            tk.Label(self.manual_frame, text=step, font=("Arial", 10), justify="left").pack(anchor="w", padx=45, pady=4)
            
        ttk.Button(self.manual_frame, text="Check Installation", command=self.check_environment, width=20).pack(pady=25)

    def build_footer_navigation(self):
        self.footer_frame = tk.Frame(self.root)
        self.footer_frame.pack_propagate(False)
        self.footer_frame.config(height=30)
        
        self.info_btn = tk.Button(self.footer_frame, text="Info", font=("Arial", 9), borderwidth=0, cursor="hand2", command=self.open_info_window)
        self.info_btn.pack(side="left", padx=5)
        
        theme_container = tk.Frame(self.footer_frame, width=30, height=30)
        theme_container.pack(side="right", padx=5)
        theme_container.pack_propagate(False)
        
        self.theme_btn = tk.Button(theme_container, text="☀️", font=("Arial", 11), borderwidth=0, cursor="hand2", command=self.toggle_theme)
        self.theme_btn.pack(fill="both", expand=True)

        self.version_lbl = tk.Label(self.footer_frame, text=CURRENT_VERSION, font=("Arial", 9, "italic"))
        self.version_lbl.pack(side="bottom", pady=5)

    def open_info_window(self):
        info_win = tk.Toplevel(self.root)
        info_win.withdraw()
        info_win.title("About")
        info_win.geometry("300x350")
        info_win.resizable(False, False)
        info_win.transient(self.root)
        info_win.grab_set()
         
        self.center_window(info_win, 300, 350)
        
        mode = self.theme_var.get()
        colors = self.themes[mode]
        info_win.config(bg=colors["bg"])
        
        if hasattr(self, 'tk_icon') and self.tk_icon:
            if platform.system() == "Windows":
                info_win.wm_iconphoto(False, self.tk_icon)
            else:
                info_win.iconphoto(True, self.tk_icon)
                
        self.update_windows_title_bar(info_win, colors["title_bar"])
        
        tk.Label(info_win, text="🪶 Clipper Resources", font=("Arial", 10, "bold"), bg=colors["bg"], fg=colors["fg"]).pack(pady=(12, 6))
        
        row1 = tk.Frame(info_win, bg=colors["bg"])
        row1.pack(pady=2)
        tk.Label(row1, text="Documentation: ", font=("Arial", 9), bg=colors["bg"], fg=colors["fg"]).pack(side="left")
        lnk1 = self.build_clickable_link(row1, "ffmpeg.org", "https://ffmpeg.org")
        lnk1._is_hyperlink = True
        lnk1.config(fg=colors["link"], bg=colors["bg"])
        lnk1.pack(side="left")
        
        row2 = tk.Frame(info_win, bg=colors["bg"])
        row2.pack(pady=2)
        tk.Label(row2, text="Engine Core: ", font=("Arial", 9), bg=colors["bg"], fg=colors["fg"]).pack(side="left")
        lnk2 = self.build_clickable_link(row2, "github.com/yt-dlp", "https://github.com/yt-dlp/yt-dlp")
        lnk2._is_hyperlink = True
        lnk2.config(fg=colors["link"], bg=colors["bg"])
        lnk2.pack(side="left")
        
        tk.Label(info_win, text="Supported Links", font=("Arial", 9, "bold"), bg=colors["bg"], fg=colors["fg"]).pack(pady=(10, 2))
        
        credits_frame = tk.Frame(info_win, bg=colors["bg"])
        credits_frame.pack(side="bottom", fill="x", pady=(5, 10))
        
        tk.Frame(credits_frame, height=1, width=240, bg=colors["accent"]).pack(pady=(0, 5))
        tk.Label(credits_frame, text="Credits:", font=("Arial", 8, "bold"), bg=colors["bg"], fg=colors["fg"]).pack()
        tk.Label(credits_frame, text="etx.rain & common.ui", font=("Arial", 9, "italic"), bg=colors["bg"], fg=colors["fg"]).pack()

        list_container = tk.Frame(info_win, bg=colors["entry_bg"], bd=1, relief="solid")
        list_container.pack(padx=25, pady=5, fill="both", expand=True)
        
        canvas = tk.Canvas(list_container, bg=colors["entry_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=colors["entry_bg"])
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
        canvas.bind_all("<MouseWheel>", on_mouse_wheel)
         
        def clean_close():
            canvas.unbind_all("<MouseWheel>")
            info_win.destroy()
        info_win.protocol("WM_DELETE_WINDOW", clean_close)
        
        platforms = [
            "YouTube & YouTube Shorts", "Twitch (Clips & VODs)", "TikTok Videos", 
            "Twitter / X Media", "Instagram Reels & Posts", "Reddit Video Links", 
            "SoundCloud Tracks", "Vimeo Collections", "Facebook Videos", 
            "Streamable Links", "Bandcamp Audio"
        ]
        for p in platforms:
            lbl = tk.Label(scroll_frame, text=f" • {p}", font=("Arial", 8), bg=colors["entry_bg"], fg=colors["entry_fg"], anchor="w")
            lbl.pack(fill="x", padx=5, pady=2)
            
        info_win.deiconify()

    def start_auto_download(self):
        self.show_screen(self.download_frame, footer=False)
        self.update_progress_bar_custom(self.progress_canvas, 0)
        threading.Thread(target=self.download_and_extract_ffmpeg, daemon=True).start()

    def download_and_extract_ffmpeg(self):
        try:
            os.makedirs(FFMPEG_DIR, exist_ok=True)
            req = urllib.request.Request(FFMPEG_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', 0))
                bytes_so_far = 0
                buffer = BytesIO()
                chunk_size = 1024 * 64
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    bytes_so_far += len(chunk)
                    buffer.write(chunk)
                    
                    if total_size > 0:
                        percent = int((bytes_so_far / total_size) * 100)
                        self.root.after(0, lambda p=percent: self.update_progress_bar_custom(self.progress_canvas, p))
            
            buffer.seek(0)
            
            if FFMPEG_URL.endswith(".zip"):
                with ZipFile(buffer) as zip_file:
                    for member in zip_file.namelist():
                        filename = os.path.basename(member)
                        if filename in [FFMPEG_BINARY, FFPROBE_BINARY]:
                            with zip_file.open(member) as source, open(os.path.join(FFMPEG_DIR, filename), "wb") as target:
                                target.write(source.read())
            else:
                with tarfile.open(fileobj=buffer, mode="r:xz") as tar_file:
                    for member in tar_file.getmembers():
                        filename = os.path.basename(member.name)
                        if filename in [FFMPEG_BINARY, FFPROBE_BINARY]:
                            source = tar_file.extractfile(member)
                            if source:
                                with open(os.path.join(FFMPEG_DIR, filename), "wb") as target:
                                    target.write(source.read())
            
            if platform.system() != "Windows":
                for binary in [FFMPEG_BINARY, FFPROBE_BINARY]:
                    full_path = os.path.join(FFMPEG_DIR, binary)
                    if os.path.exists(full_path):
                        os.chmod(full_path, 0o755)

            self.root.after(0, self.check_environment)
        except Exception:
            self.root.after(0, lambda: self.show_screen(self.missing_frame, footer=False))

    def build_main_screen(self):
        self.url_label = tk.Label(self.main_frame, text="URL Link:", font=("Arial", 10, "bold"))
        self.url_label.pack(pady=(12, 2))
        
        self.url_entry = tk.Entry(self.main_frame, width=50, font=("Arial", 10))
        self.url_entry.pack(pady=2, padx=20)
        self.url_entry.focus()

        options_frame = tk.Frame(self.main_frame)
        options_frame.pack(pady=8, fill="x", padx=40)

        self.video_var = tk.BooleanVar(value=self.saved_settings.get("video_on", True))
        self.video_chk = tk.Checkbutton(options_frame, text="Video", variable=self.video_var, command=self.toggle_states)
        self.video_chk.grid(row=0, column=0, sticky="w", pady=4)
        
        self.v_qual_var = tk.StringVar(value=self.saved_settings.get("video_quality", "1080p"))
        v_options = ["4K (2160p)", "2K (1440p)", "1080p", "720p", "480p", "360p", "240p", "144p"]
        self.v_qual_combo = ttk.Combobox(options_frame, textvariable=self.v_qual_var, values=v_options, width=12, state="readonly")
        self.v_qual_combo.grid(row=0, column=1, padx=20, sticky="w")

        self.audio_var = tk.BooleanVar(value=self.saved_settings.get("audio_on", False))
        self.audio_chk = tk.Checkbutton(options_frame, text="Audio", variable=self.audio_var, command=self.toggle_states)
        self.audio_chk.grid(row=1, column=0, sticky="w", pady=4)
      
        self.a_qual_var = tk.StringVar(value=self.saved_settings.get("audio_quality", "320kbps"))
        a_options = ["320kbps", "256kbps", "192kbps", "128kbps", "96kbps"]
        self.a_qual_combo = ttk.Combobox(options_frame, textvariable=self.a_qual_var, values=a_options, width=12, state="readonly")
        self.a_qual_combo.grid(row=1, column=1, padx=20, sticky="w")

        self.gif_var = tk.BooleanVar(value=self.saved_settings.get("gif_on", False))
        self.gif_chk = tk.Checkbutton(options_frame, text="GIF", variable=self.gif_var, command=self.toggle_states)
        self.gif_chk.grid(row=2, column=0, sticky="w", pady=4)
        
        self.g_qual_var = tk.StringVar(value=self.saved_settings.get("gif_quality", "480p"))
        g_options = ["720p", "480p", "360p", "240p"]
        self.g_qual_combo = ttk.Combobox(options_frame, textvariable=self.g_qual_var, values=g_options, width=12, state="readonly")
        self.g_qual_combo.grid(row=2, column=1, padx=20, sticky="w")

        self.best_var = tk.BooleanVar(value=self.saved_settings.get("always_best", False))
        self.best_chk = tk.Checkbutton(self.main_frame, text="Always use best quality", variable=self.best_var, command=self.toggle_states)
        self.best_chk.pack(pady=4)

        folder_frame = tk.Frame(self.main_frame)
        folder_frame.pack(pady=4, fill="x", padx=40)
        self.folder_title = tk.Label(folder_frame, text="Folder:", font=("Arial", 9, "bold"))
        self.folder_title.grid(row=0, column=0, sticky="w")
        
        self.dir_label = tk.Label(folder_frame, textvariable=self.dir_var, font=("Arial", 8, "italic"), width=34, anchor="w")
        self.dir_label.grid(row=0, column=1, padx=10, sticky="w")
        ttk.Button(folder_frame, text="Browse...", command=self.browse_directory, width=9).grid(row=0, column=2, sticky="e")

        self.download_btn = ttk.Button(self.main_frame, text="Download", command=self.start_download_thread, width=28)
        self.download_btn.pack(pady=(12, 2))
         
        self.toggle_states()

    def load_settings(self):
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.saved_settings = {
            "video_on": True, "video_quality": "1080p", "audio_on": False, 
            "audio_quality": "320kbps", "gif_on": False, "gif_quality": "480p", 
            "always_best": False, "download_directory": default_dir, "theme_mode": "light"
        }
    
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.saved_settings.update(json.load(f))
            except:
                pass
        self.dir_var = tk.StringVar(value=self.saved_settings.get("download_directory", default_dir))
        self.theme_var = tk.StringVar(value=self.saved_settings.get("theme_mode", "light"))

    def save_settings(self):
        settings = {
            "video_on": self.video_var.get(),
            "video_quality": self.v_qual_var.get(),
            "audio_on": self.audio_var.get(),
            "audio_quality": self.a_qual_var.get(),
            "gif_on": self.gif_var.get(),
            "gif_quality": self.g_qual_var.get(),
            "always_best": self.best_var.get(),
            "download_directory": self.dir_var.get(),
            "theme_mode": self.theme_var.get()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(settings, f)
        except:
             pass

    def browse_directory(self):
        selected = filedialog.askdirectory(initialdir=self.dir_var.get())
        if selected:
            self.dir_var.set(os.path.normpath(selected))
            self.save_settings()
            self.check_environment()

    def toggle_states(self):
        if self.best_var.get():
            self.v_qual_combo.config(state="disabled")
            self.a_qual_combo.config(state="disabled")
            self.g_qual_combo.config(state="disabled")
        else:
            self.v_qual_combo.config(state="readonly" if self.video_var.get() else "disabled")
            self.a_qual_combo.config(state="readonly" if self.audio_var.get() else "disabled")
            self.g_qual_combo.config(state="readonly" if self.gif_var.get() else "disabled")

    def reset_button_text(self):
        self.download_btn.config(text="Download", state="normal")

    def start_download_thread(self):
        url = self.url_entry.get().strip()
        if not url.startswith(("http://", "https://")):
            self.download_btn.config(text="Invalid URL link provided.")
            self.root.after(3000, self.reset_button_text)
            return
            
        if not (self.video_var.get() or self.audio_var.get() or self.gif_var.get()):
            self.download_btn.config(text="Select a download format.")
            self.root.after(3000, self.reset_button_text)
            return

        self.download_btn.config(state="disabled", text="Processing download...")
        self.save_settings()
        
        threading.Thread(target=self.process_batch_download, args=(url,), daemon=True).start()

    def process_batch_download(self, url):
        target_dir = self.dir_var.get()
        base_opts = {
            'outtmpl': os.path.join(target_dir, '%(title)s.%(ext)s'), 
            'quiet': True, 
            'no_warnings': True,
            'nocheckcertificate': True
        }
        
        if not (shutil.which(FFMPEG_BINARY) and shutil.which(FFPROBE_BINARY)):
            base_opts['ffmpeg_location'] = FFMPEG_DIR
            
        is_best = self.best_var.get()
        
        try:
            if self.video_var.get():
                opts = base_opts.copy()
                opts['merge_output_format'] = 'mp4'
                opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
                if is_best:
                    opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    qual = self.v_qual_var.get()
                    height = "2160" if "4K" in qual else "1440" if "2K" in qual else qual.replace("p", "")
                    opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}]/best'
                with YoutubeDL(opts) as ydl: ydl.download([url])

            if self.audio_var.get():
                opts = base_opts.copy()
                opts['format'] = 'bestaudio/best'
                bitrate = "320" if is_best else self.a_qual_var.get().replace("kbps", "")
                opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate}]
                with YoutubeDL(opts) as ydl: ydl.download([url])

            if self.gif_var.get():
                opts = base_opts.copy()
                height = "720" if is_best else self.g_qual_var.get().replace("p", "")
                opts['format'] = f'bestvideo[height<={height}]'
                opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'gif'}]
                with YoutubeDL(opts) as ydl: ydl.download([url])

            self.root.after(0, self.download_success)
        except Exception:
            self.root.after(0, self.download_error)

    def download_success(self):
        self.url_entry.delete(0, tk.END)
        self.download_btn.config(text="Completed successfully!")
        self.root.after(3000, self.reset_button_text)

    def download_error(self):
        self.download_btn.config(text="Download error encountered.")
        self.root.after(3000, self.reset_button_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloaderGUI(root)
    root.mainloop()
