import gdown
import os
import shutil

def download_drive_folder(url, dest_folder):
    """
    Downloads a public Google Drive folder to dest_folder.
    Returns the path to the downloaded folder.
    """
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
        
    print(f"Downloading from {url} to {dest_folder}...")
    
    # gdown download_folder normally downloads directly into current directory or specified output
    # but the API can be a bit tricky depending on the version. 
    # Let's try gdown.download_folder
    
    # download_folder downloads into a folder named as the Drive folder name inside output
    # or directly into output if it's already a folder
    try:
        downloaded_paths = gdown.download_folder(url, output=dest_folder, use_cookies=False, quiet=True)
        return downloaded_paths
    except Exception as e:
        raise Exception(f"Lỗi tải thư mục Google Drive: {str(e)}")

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
