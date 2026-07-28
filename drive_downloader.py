import gdown
import os
import shutil
import time

def download_drive_folder(url, dest_folder, log_callback=None):
    """
    Downloads a public Google Drive folder to dest_folder.
    Returns the path to the downloaded folder.
    """
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
        
    if log_callback:
        log_callback(f"Downloading from {url} to {dest_folder}...")
    else:
        print(f"Downloading from {url} to {dest_folder}...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Bước 1: Quét cấu trúc thư mục ẩn danh (không cookies) để tránh bị mù do tài khoản đăng nhập
            if log_callback:
                log_callback("   [+] Đang quét cấu trúc thư mục (Chế độ Ẩn Danh)...")
                
            files_to_download = gdown.download_folder(url, output=dest_folder, use_cookies=False, quiet=True, skip_download=True)
            if not files_to_download:
                raise Exception("Không tìm thấy file nào trong thư mục này.")
                
            downloaded_paths = []
            
            # Bước 2: Tải từng file. Bật cookies=True để tận dụng Cookies (nếu có) lách Rate Limit
            if log_callback:
                log_callback(f"   [+] Tìm thấy {len(files_to_download)} files. Đang tiến hành tải xuống...")
                
            for f in files_to_download:
                if os.path.splitext(f.local_path)[1]:
                    download_output = f.local_path
                else:
                    download_output = os.path.dirname(f.local_path) + os.sep
                    
                # Thử tải với cookies=True trước (để chống Rate Limit nếu đã nạp Cookies)
                try:
                    downloaded = gdown.download(id=f.id, output=download_output, use_cookies=True, quiet=True)
                    if not downloaded:
                        raise Exception("Downloaded path is empty")
                    downloaded_paths.append(downloaded)
                except Exception as e1:
                    # Nếu cookies hết hạn hoặc bị lỗi, tự động chuyển về ẩn danh
                    err1_str = str(e1)
                    if log_callback and ("FileURLRetrievalError" in err1_str or "Cannot retrieve" in err1_str):
                        log_callback(f"       [!] Lỗi Cookies khi tải file {f.id}, chuyển sang tải Ẩn Danh...")
                        
                    downloaded = gdown.download(id=f.id, output=download_output, use_cookies=False, quiet=True)
                    if downloaded:
                        downloaded_paths.append(downloaded)
                    else:
                        raise Exception(f"Không thể tải file {f.id} ẩn danh.")
                        
            return downloaded_paths
            
        except Exception as e:
            err_str = str(e)
            if "FileURLRetrievalError" in err_str or "Cannot retrieve" in err_str:
                if attempt < max_retries - 1:
                    wait_time = 60 * (attempt + 1)
                    msg = f"   [!] Google Drive chặn tạm thời (Rate Limit). Đang nghỉ giải lao {wait_time} giây để thử lại (Lần {attempt + 1}/{max_retries - 1})..."
                    if log_callback:
                        log_callback(msg)
                    else:
                        print(msg)
                    time.sleep(wait_time)
                    continue
            raise Exception(f"Lỗi tải thư mục Google Drive: {err_str}")

def get_files_from_folder(folder_path):
    """
    Scans the folder and returns a tuple (docx_path, image_paths_list)
    """
    docx_file = None
    images = []
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)
            if ext == '.docx':
                if not docx_file: # Just take the first docx found
                    docx_file = full_path
            elif ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                images.append(full_path)
                
    return docx_file, images
