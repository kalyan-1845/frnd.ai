import os
import shutil
import time
from core.logger import log_event, log_error

def organize_folder(folder_path):
    """
    Automatically sorts files in the given folder into category subfolders.
    """
    if not os.path.exists(folder_path):
        return False, f"Folder '{folder_path}' does not exist."

    categories = {
        "Documents": [".pdf", ".docx", ".txt", ".rtf", ".pptx", ".csv", ".xlsx"],
        "Media": [".mp3", ".wav", ".mp4", ".mkv", ".mov", ".avi"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"],
        "Scripts": [".py", ".js", ".sh", ".bat", ".html", ".css"],
        "Compressed": [".zip", ".rar", ".7z", ".tar", ".gz"],
        "Executables": [".exe", ".msi"]
    }

    files_moved = 0
    try:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue

            file_ext = os.path.splitext(filename)[1].lower()
            
            # Find matching category
            target_cat = "Others"
            for cat, extensions in categories.items():
                if file_ext in extensions:
                    target_cat = cat
                    break
            
            # Create category folder
            cat_folder = os.path.join(folder_path, target_cat)
            if not os.path.exists(cat_folder):
                os.makedirs(cat_folder)
            
            # Move file
            shutil.move(file_path, os.path.join(cat_folder, filename))
            files_moved += 1

        log_event("Workspace.Organize", f"Organized {files_moved} files in {folder_path}")
        return True, f"Successfully organized {files_moved} files into category folders."
    except Exception as e:
        log_error("Workspace.Organize", e)
        return False, f"Error organizing folder: {str(e)}"

def clean_temp_files():
    """
    Safely cleans common temporary junk files.
    """
    temp_dirs = [
        os.environ.get('TEMP'),
        os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
    ]
    
    files_deleted = 0
    bytes_freed = 0
    
    for tdir in temp_dirs:
        if not tdir or not os.path.exists(tdir):
            continue
            
        for filename in os.listdir(tdir):
            file_path = os.path.join(tdir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    fsize = os.path.getsize(file_path)
                    os.unlink(file_path)
                    files_deleted += 1
                    bytes_freed += fsize
                elif os.path.isdir(file_path):
                    fsize = sum(os.path.getsize(os.path.join(dirpath, f)) 
                               for dirpath, dirnames, filenames in os.walk(file_path) 
                               for f in filenames)
                    shutil.rmtree(file_path)
                    files_deleted += 1
                    bytes_freed += fsize
            except Exception:
                # Many temp files are in use, skip silently
                continue
                
    mb_freed = bytes_freed / (1024 * 1024)
    log_event("Workspace.Clean", f"Cleaned {files_deleted} files, freed {mb_freed:.2f} MB")
    return True, f"Cleaned {files_deleted} temporary files and freed {mb_freed:.1f} MB of space."
