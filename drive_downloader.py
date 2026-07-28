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
            # Lần thử đầu tiên trong mỗi vòng lặp: Cố gắng dùng cookies trước
            return gdown.download_folder(url, output=dest_folder, use_cookies=True, quiet=True)
        except Exception as e:
            err_str = str(e)
            if "FileURLRetrievalError" in err_str or "Cannot retrieve" in err_str:
                # Nếu dùng cookies bị lỗi (do cookies hết hạn, hoặc cookies sai định dạng)
                # Thử chuyển qua tải ẩn danh (Không dùng Cookies)
                try:
                    if log_callback:
                        log_callback("   [!] File Cookies gặp sự cố. Tự động chuyển qua tải Ẩn Danh (Bỏ qua Cookies)...")
                    return gdown.download_folder(url, output=dest_folder, use_cookies=False, quiet=True)
                except Exception as e2:
                    err2_str = str(e2)
                    if "FileURLRetrievalError" in err2_str or "Cannot retrieve" in err2_str:
                        # Nếu cả ẩn danh cũng bị chặn -> Đích thị là Rate Limit do IP tải quá nhiều
                        if attempt < max_retries - 1:
                            wait_time = 60 * (attempt + 1)
                            msg = f"   [!] Google Drive chặn tạm thời (Rate Limit). Đang nghỉ giải lao {wait_time} giây để thử lại (Lần {attempt + 1}/{max_retries - 1})..."
                            if log_callback:
                                log_callback(msg)
                            else:
                                print(msg)
                            time.sleep(wait_time)
                            continue
                    raise Exception(f"Lỗi tải thư mục Google Drive: {err2_str}")
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
