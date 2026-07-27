import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import tempfile
import shutil
import traceback
import os
import sys
import io

# Fix cho Pyinstaller Windowed mode (sys.stdout bị None làm gdown/tqdm văng lỗi)
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from wp_api import get_categories, upload_media, create_post
from drive_downloader import download_drive_folder, get_files_from_folder
from docx_parser import parse_docx

# Thiết lập chế độ giao diện
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class GinContentPostApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- Thiết lập Theme & Font chữ chung ---
        self.title("GinContent Post")
        self.geometry("900x700")
        self.minsize(900, 650)
        
        # Font chữ hiện đại
        self.MAIN_FONT = ("Product Sans", 14)
        self.TITLE_FONT = ("Product Sans", 28, "bold")
        self.BOLD_FONT = ("Product Sans", 14, "bold")
        self.LOG_FONT = ("Consolas", 12)
        
        # Bảng màu phong cách Simulated Glassmorphism / Acrylic Dark
        self.BG_MAIN = "#09090e"           # Nền rất tối (gần đen)
        self.BG_CARD = "#15151e"           # Nền card sáng hơn 1 chút
        self.BORDER_COLOR = "#2a2a35"      # Viền sáng tạo cảm giác kính
        self.PRIMARY = "#8b5cf6"           # Tím gradient
        self.PRIMARY_HOVER = "#7c3aed"
        self.ACCENT = "#00f2fe"            # Xanh Cyan rực
        self.TEXT_MAIN = "#ffffff"         
        self.TEXT_MUTED = "#8e8e9e"        
        
        self.configure(fg_color=self.BG_MAIN)
        
        self.categories_data = [] # List of dicts
        self.temp_dir = None
        
        # Layout tổng: Không có sidebar, 1 cột chính giữa
        self.grid_columnconfigure(0, weight=1) 
        self.grid_rowconfigure(2, weight=1)
        
        self.create_widgets()
        
    def create_widgets(self):
        # ================= HEADER =================
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 10))
        
        ctk.CTkLabel(header_frame, text="GinContent", font=self.TITLE_FONT, text_color=self.TEXT_MAIN).pack(side="left")
        ctk.CTkLabel(header_frame, text="Post", font=("Product Sans", 28), text_color=self.ACCENT).pack(side="left", padx=(5, 10))
        ctk.CTkLabel(header_frame, text="Tự động đồng bộ nội dung từ Google Drive", font=self.MAIN_FONT, text_color=self.TEXT_MUTED).pack(side="left", pady=(8, 0))

        # ================= MAIN CONTENT GRID (2 Cột) =================
        content_grid = ctk.CTkFrame(self, fg_color="transparent")
        content_grid.grid(row=1, column=0, sticky="nsew", padx=40, pady=10)
        content_grid.grid_columnconfigure(0, weight=1)
        content_grid.grid_columnconfigure(1, weight=1)

        # Chung style cho các thẻ (Giả lập Glass)
        card_kwargs = {"fg_color": self.BG_CARD, "corner_radius": 15, "border_width": 1, "border_color": self.BORDER_COLOR}
        entry_kwargs = {"height": 40, "font": self.MAIN_FONT, "border_width": 1, "border_color": "#2a2a35", "fg_color": "#0d0d12", "text_color": self.TEXT_MAIN}

        # --- 1. WP Config Card ---
        wp_frame = ctk.CTkFrame(content_grid, **card_kwargs)
        wp_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        wp_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(wp_frame, text="Cấu Hình WordPress", font=self.BOLD_FONT, text_color=self.TEXT_MAIN).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        
        ctk.CTkLabel(wp_frame, text="URL Website:", font=self.MAIN_FONT, text_color=self.TEXT_MUTED).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        self.entry_url = ctk.CTkEntry(wp_frame, placeholder_text="https://", **entry_kwargs)
        self.entry_url.grid(row=1, column=1, padx=(0, 20), pady=(0, 10), sticky="ew")
        self.entry_url.insert(0, "https://")
        
        ctk.CTkLabel(wp_frame, text="Username:", font=self.MAIN_FONT, text_color=self.TEXT_MUTED).grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")
        self.entry_user = ctk.CTkEntry(wp_frame, **entry_kwargs)
        self.entry_user.grid(row=2, column=1, padx=(0, 20), pady=(0, 10), sticky="ew")
        
        ctk.CTkLabel(wp_frame, text="App Password:", font=self.MAIN_FONT, text_color=self.TEXT_MUTED).grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")
        self.entry_pass = ctk.CTkEntry(wp_frame, show="•", **entry_kwargs)
        self.entry_pass.grid(row=3, column=1, padx=(0, 20), pady=(0, 10), sticky="ew")
        
        self.btn_get_cats = ctk.CTkButton(wp_frame, text="Tải Danh Mục", font=self.BOLD_FONT, command=self.fetch_categories, height=40, fg_color="#2a2a35", hover_color="#3b3b4a", text_color=self.TEXT_MAIN, corner_radius=8)
        self.btn_get_cats.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="w")
        
        self.combo_cats = ctk.CTkComboBox(wp_frame, values=["(Chưa có danh mục)"], height=40, font=self.MAIN_FONT, dropdown_font=self.MAIN_FONT, border_color="#2a2a35", button_color="#2a2a35", fg_color="#0d0d12", text_color=self.TEXT_MAIN)
        self.combo_cats.grid(row=4, column=1, padx=(0, 20), pady=(10, 20), sticky="ew")
        
        # --- 2. Drive Links Card ---
        links_frame = ctk.CTkFrame(content_grid, **card_kwargs)
        links_frame.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        links_frame.grid_columnconfigure(0, weight=1)
        links_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(links_frame, text="Link Google Drive (Mỗi link 1 dòng)", font=self.BOLD_FONT, text_color=self.TEXT_MAIN).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.text_drive = ctk.CTkTextbox(links_frame, font=self.MAIN_FONT, border_width=1, border_color="#2a2a35", fg_color="#0d0d12", text_color=self.TEXT_MAIN, border_spacing=10, corner_radius=8)
        self.text_drive.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="nsew")
        
        # Căn giữa nút bấm
        btn_container = ctk.CTkFrame(links_frame, fg_color="transparent")
        btn_container.grid(row=2, column=0, pady=(0, 20))
        
        self.btn_start = ctk.CTkButton(btn_container, text="Bắt Đầu Đăng Bài", command=self.start_posting, font=self.BOLD_FONT, height=45, width=220, fg_color=self.PRIMARY, hover_color=self.PRIMARY_HOVER, text_color="white", corner_radius=22) # Bo tròn nhiều hơn
        self.btn_start.pack()
        
        # ================= LOGS AREA =================
        log_frame = ctk.CTkFrame(self, **card_kwargs)
        log_frame.grid(row=2, column=0, padx=40, pady=(10, 30), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(log_frame, text="Trạng Thái Hoạt Động", font=self.BOLD_FONT, text_color=self.TEXT_MUTED).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.log_area = ctk.CTkTextbox(log_frame, state="disabled", font=self.LOG_FONT, fg_color="#09090e", text_color=self.ACCENT, border_width=1, border_color="#2a2a35", corner_radius=8)
        self.log_area.grid(row=1, column=0, padx=20, pady=(5, 20), sticky="nsew")

    def log(self, message):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")
        self.update_idletasks()

    def fetch_categories(self):
        url = self.entry_url.get().strip()
        user = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        
        if not url or not user or not password:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập URL, Username và App Password trước.")
            return
            
        self.btn_get_cats.configure(state="disabled")
        self.log("Đang lấy danh mục từ WordPress...")
        
        def run():
            try:
                cats = get_categories(url, user, password)
                self.categories_data = cats
                cat_names = [c['name'] for c in cats]
                
                self.after(0, lambda: self.update_combo(cat_names))
                self.after(0, lambda: self.log("Đã lấy danh mục thành công."))
            except Exception as e:
                self.after(0, lambda: self.log(f"Lỗi: {str(e)}"))
                self.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
            finally:
                self.after(0, lambda: self.btn_get_cats.configure(state="normal"))
                
        threading.Thread(target=run, daemon=True).start()

    def update_combo(self, cat_names):
        if cat_names:
            self.combo_cats.configure(values=cat_names)
            self.combo_cats.set(cat_names[0])
        else:
            self.combo_cats.configure(values=["(Trống)"])

    def start_posting(self):
        drive_text = self.text_drive.get("1.0", "end").strip()
        if not drive_text:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập ít nhất 1 link thư mục Google Drive.")
            return
            
        cat_name = self.combo_cats.get()
        if not cat_name or cat_name in ["(Chưa có danh mục)", "(Trống)"]:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn Category hợp lệ.")
            return
            
        # Lấy danh sách link (bỏ dòng trống)
        links = [line.strip() for line in drive_text.split('\n') if line.strip()]
        if not links:
            return
            
        self.btn_start.configure(state="disabled")
        self.log("\n==================================")
        self.log(f"BẮT ĐẦU QUÁ TRÌNH ĐĂNG {len(links)} BÀI")
        self.log("==================================")
        
        threading.Thread(target=self.process_bulk_posts, args=(links, cat_name), daemon=True).start()

    def process_bulk_posts(self, links, cat_name):
        url = self.entry_url.get().strip()
        user = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        
        cat_id = None
        for c in self.categories_data:
            if c['name'] == cat_name:
                cat_id = c['id']
                break
                
        success_count = 0
        error_count = 0

        for i, drive_url in enumerate(links, 1):
            self.log(f"\n---> [Bài {i}/{len(links)}] Đang xử lý link: {drive_url}")
            try:
                # 1. Download
                self.temp_dir = tempfile.mkdtemp()
                self.log(f"   [+] Tải thư mục Drive...")
                download_drive_folder(drive_url, self.temp_dir)
                
                # 2. Get files
                docx_file, images = get_files_from_folder(self.temp_dir)
                if not docx_file:
                    raise Exception("Không tìm thấy file .docx.")
                    
                self.log(f"   [+] Phân tích Docx và Tải ảnh ({len(images)} ảnh)...")
                
                # 3. Parse docx
                def wp_upload_callback(file_path, alt_text):
                    self.log(f"       -> Upload ảnh: {alt_text}")
                    res = upload_media(url, user, password, file_path, alt_text)
                    return res['url']
                    
                title, meta_desc, body_html = parse_docx(docx_file, images, wp_upload_callback)
                
                # 4. Create Post
                self.log(f"   [+] Đăng bài: {title}")
                post_res = create_post(url, user, password, title, body_html, cat_id, meta_desc)
                
                self.log(f"   [V] THÀNH CÔNG! Link nháp: {post_res.get('link')}")
                success_count += 1
                
            except Exception as e:
                err_msg = str(e)
                trace = traceback.format_exc()
                self.log(f"   [X] LỖI: {err_msg}")
                print(trace)
                error_count += 1
            finally:
                # Cleanup temp dir for this link
                if self.temp_dir and os.path.exists(self.temp_dir):
                    try:
                        shutil.rmtree(self.temp_dir)
                    except:
                        pass
        
        self.log("\n==================================")
        self.log(f"HOÀN TẤT ĐĂNG HÀNG LOẠT!")
        self.log(f"Thành công: {success_count} bài | Lỗi: {error_count} bài.")
        self.log("==================================")
        self.after(0, lambda: self.btn_start.configure(state="normal"))
        self.after(0, lambda: messagebox.showinfo("Hoàn tất", f"Đã chạy xong danh sách!\nThành công: {success_count}\nLỗi: {error_count}"))

if __name__ == "__main__":
    app = GinContentPostApp()
    app.mainloop()
