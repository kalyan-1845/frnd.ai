import os
import subprocess
import fnmatch
import config

# Get the current user's home directory (e.g., C:\Users\prsnl)
USER_HOME = os.path.expanduser("~")

# Auto-detect Desktop path (OneDrive may redirect it)
_DESKTOP_STANDARD = os.path.join(USER_HOME, "Desktop")
_DESKTOP_ONEDRIVE = os.path.join(USER_HOME, "OneDrive", "Desktop")
# Use OneDrive Desktop if standard doesn't exist
DESKTOP_PATH = _DESKTOP_STANDARD if os.path.exists(_DESKTOP_STANDARD) else _DESKTOP_ONEDRIVE

# Auto-detect Documents path
_DOCS_STANDARD = os.path.join(USER_HOME, "Documents")
_DOCS_ONEDRIVE = os.path.join(USER_HOME, "OneDrive", "Documents")
DOCUMENTS_PATH = _DOCS_STANDARD if os.path.exists(_DOCS_STANDARD) else _DOCS_ONEDRIVE

COMMON_DIRS = {
    "downloads": os.path.join(USER_HOME, "Downloads"),
    "download": os.path.join(USER_HOME, "Downloads"),
    "documents": DOCUMENTS_PATH,
    "document": DOCUMENTS_PATH,
    "desktop": DESKTOP_PATH,
    "pictures": os.path.join(USER_HOME, "Pictures"),
    "picture": os.path.join(USER_HOME, "Pictures"),
    "photos": os.path.join(USER_HOME, "Pictures"),
    "videos": os.path.join(USER_HOME, "Videos"),
    "video": os.path.join(USER_HOME, "Videos"),
    "music": os.path.join(USER_HOME, "Music"),
    "onedrive": os.path.join(USER_HOME, "OneDrive"),
}


def open_folder(folder_name):
    """
    Opens a standard Windows folder. Supports common names, 
    OneDrive paths, and will search for the folder if not immediately found.
    Returns (success: bool, message: str)
    """
    folder_name = folder_name.lower().strip()

    # 1. Check known shortcuts (exact match)
    if folder_name in COMMON_DIRS:
        path = COMMON_DIRS[folder_name]
        if os.path.exists(path):
            print(f"[File Manager] Opening Folder: {path}")
            os.startfile(path)
            return True, f"Opened {folder_name}"

    # 2. Try directly under home directory
    path = os.path.join(USER_HOME, folder_name)
    if os.path.exists(path):
        print(f"[File Manager] Opening Folder: {path}")
        os.startfile(path)
        return True, f"Opened {folder_name}"

    # 3. Try under Desktop
    path = os.path.join(USER_HOME, "Desktop", folder_name)
    if os.path.exists(path):
        print(f"[File Manager] Opening Folder: {path}")
        os.startfile(path)
        return True, f"Opened {folder_name} from Desktop"

    # 4. Try under Documents
    path = os.path.join(USER_HOME, "Documents", folder_name)
    if os.path.exists(path):
        print(f"[File Manager] Opening Folder: {path}")
        os.startfile(path)
        return True, f"Opened {folder_name} from Documents"

    # 5. Try under OneDrive Desktop (since user has OneDrive)
    onedrive_desktop = os.path.join(USER_HOME, "OneDrive", "Desktop", folder_name)
    if os.path.exists(onedrive_desktop):
        print(f"[File Manager] Opening Folder: {onedrive_desktop}")
        os.startfile(onedrive_desktop)
        return True, f"Opened {folder_name} from OneDrive Desktop"

    # 6. Search top-level directories for a partial match
    search_roots = [USER_HOME, os.path.join(USER_HOME, "Desktop"),
                    os.path.join(USER_HOME, "Documents")]
    for root in search_roots:
        if os.path.exists(root):
            try:
                for item in os.listdir(root):
                    if folder_name in item.lower() and os.path.isdir(os.path.join(root, item)):
                        full_path = os.path.join(root, item)
                        print(f"[File Manager] Found matching folder: {full_path}")
                        os.startfile(full_path)
                        return True, f"Opened {item}"
            except PermissionError:
                continue

    print(f"[Error] Folder not found: {folder_name}")
    return False, f"Sorry, I couldn't find a folder called '{folder_name}'"


def find_file(filename):
    """
    Searches for a file by name (supports partial matching and wildcards).
    Searches Desktop, Documents, Downloads, and OneDrive Desktop.
    Returns (success: bool, message: str)
    """
    filename = filename.strip()
    print(f"[File Manager] Searching for '{filename}'... (This may take a moment)")

    # Directories to search (prioritized)
    search_dirs = [
        COMMON_DIRS.get("desktop", ""),
        COMMON_DIRS.get("documents", ""),
        COMMON_DIRS.get("downloads", ""),
        os.path.join(USER_HOME, "OneDrive", "Desktop"),
    ]
    # Remove non-existent dirs
    search_dirs = [d for d in search_dirs if d and os.path.exists(d)]

    results = []
    filename_lower = filename.lower()

    for search_path in search_dirs:
        try:
            for root, dirs, files in os.walk(search_path):
                # Skip hidden/system dirs for speed
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in (
                    '__pycache__', '.git', 'node_modules', '.venv', 'venv', 
                    'AppData', 'Program Files', 'Windows', '$RECYCLE.BIN'
                )]
                
                for f in files:
                    f_lower = f.lower()
                    # Exact match (case-insensitive)
                    if f_lower == filename_lower:
                        results.append(os.path.join(root, f))
                    # Partial match (filename contains search term)
                    elif filename_lower in f_lower:
                        results.append(os.path.join(root, f))
                    # Wildcard match
                    elif '*' in filename or '?' in filename:
                        if fnmatch.fnmatch(f_lower, filename_lower):
                            results.append(os.path.join(root, f))
                
                # Limit results to prevent long searches
                if len(results) >= 5:
                    break
        except PermissionError:
            continue
        
        if len(results) >= 5:
            break

    if results:
        # Open the best match (first result = most likely exact match)
        best = results[0]
        print(f"[Success] Found: {best}")
        try:
            os.startfile(best)
        except Exception as e:
            print(f"[Warning] Couldn't open file directly: {e}")
            # Try opening the containing folder instead
            os.startfile(os.path.dirname(best))

        if len(results) > 1:
            msg = f"Found {len(results)} matches. Opening the best match: {os.path.basename(best)}"
            for r in results[1:]:
                print(f"  Also found: {r}")
        else:
            msg = f"Found and opened: {os.path.basename(best)}"
        return True, msg
    
    print(f"[Failed] Could not find '{filename}'")
    return False, f"Sorry, I couldn't find any file matching '{filename}'"


def create_folder(folder_name, location="desktop"):
    """
    Creates a new folder at the specified location.
    Returns (success: bool, message: str)
    """
    location = location.lower().strip()
    base = COMMON_DIRS.get(location, os.path.join(USER_HOME, "Desktop"))
    path = os.path.join(base, folder_name)

    try:
        os.makedirs(path, exist_ok=True)
        print(f"[File Manager] Created folder: {path}")
        return True, f"Created folder '{folder_name}' on {location}"
    except Exception as e:
        print(f"[Error] Failed to create folder: {e}")
        return False, f"Failed to create folder: {e}"


def create_file(filename, content="", location="desktop"):
    """
    Creates a new file with optional content.
    Returns (success: bool, message: str)
    """
    location = location.lower().strip()
    # Default to Desktop if location unknown
    base = COMMON_DIRS.get(location, DESKTOP_PATH)
    path = os.path.join(base, filename)

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[File Manager] Created file: {path}")
        return True, f"Created {filename} on {location}."
    except Exception as e:
        print(f"[Error] Failed to create file: {e}")
        return False, f"Failed to create file: {e}"


import shutil

def move_file(source, destination_folder="desktop"):
    """
    Moves a file to a new location.
    Returns (success, message)
    """
    if not os.path.exists(source):
        return False, f"Source file does not exist: {source}"
    
    dest_base = COMMON_DIRS.get(destination_folder.lower(), os.path.join(USER_HOME, destination_folder))
    dest_path = os.path.join(dest_base, os.path.basename(source))
    
    try:
        os.makedirs(dest_base, exist_ok=True)
        shutil.move(source, dest_path)
        return True, f"Moved {os.path.basename(source)} to {destination_folder}"
    except Exception as e:
        return False, f"Failed to move file: {e}"

def copy_file(source, destination_folder="desktop"):
    """
    Copies a file to a new location.
    Returns (success, message)
    """
    if not os.path.exists(source):
        return False, f"Source file does not exist: {source}"
    
    dest_base = COMMON_DIRS.get(destination_folder.lower(), os.path.join(USER_HOME, destination_folder))
    dest_path = os.path.join(dest_base, os.path.basename(source))
    
    try:
        os.makedirs(dest_base, exist_ok=True)
        if os.path.isdir(source):
            shutil.copytree(source, dest_path, dirs_exist_ok=True)
            return True, f"Copied folder {os.path.basename(source)} to {destination_folder}"
        else:
            shutil.copy2(source, dest_path)
            return True, f"Copied {os.path.basename(source)} to {destination_folder}"
    except Exception as e:
        return False, f"Failed to copy: {e}"

def delete_item(path):
    """
    Deletes a file or directory. High safety: check path first.
    Returns (success, message)
    """
    if not os.path.exists(path):
        return False, f"Path does not exist: {path}"
    
    # Safety: Don't delete system roots
    if path.lower() in [USER_HOME.lower(), "c:\\", "c:\\windows"]:
        return False, "Safety block: Cannot delete system/home directories."
        
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True, f"Deleted {os.path.basename(path)}"
    except Exception as e:
        return False, f"Failed to delete: {e}"

def write_to_file(filename, content, mode="w", location="desktop"):
    """
    Writes or appends content to a file.
    mode: 'w' (overwrite) or 'a' (append)
    """
    location = location.lower().strip()
    base = COMMON_DIRS.get(location, DESKTOP_PATH)
    path = os.path.join(base, filename)

    if not os.path.exists(path):
        # Search for it if not in immediate location
        print(f"[{config.ASSISTANT_NAME}] File {filename} not at {location}. Scanning system...")
        found, msg = find_file(filename)
        if not found:
            # If not found, create it
            return create_file(filename, content, location)
        return False, f"I found {filename} elsewhere, but I need explicit confirmation to edit non-standard locations."

    try:
        with open(path, mode, encoding='utf-8') as f:
            f.write(content)
        action = "Appended to" if mode == "a" else "Wrote to"
        print(f"[File Manager] {action} file: {path}")
        return True, f"{action} {filename}."
    except Exception as e:
        print(f"[Error] Failed to write to file: {e}")
        return False, f"Failed to write to file: {e}"


def rename_item(old_path, new_name):
    """Renames a file or folder."""
    try:
        if not os.path.exists(old_path):
            return False, f"Source not found: {old_path}"
        
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)
        
        os.rename(old_path, new_path)
        return True, f"Renamed to {new_name}"
    except Exception as e:
        return False, f"Rename failed: {e}"


def list_files(folder_name="desktop"):
    """Lists files in a specific folder."""
    try:
        folder_name = folder_name.lower().strip()
        path = COMMON_DIRS.get(folder_name, folder_name)
        
        if not os.path.exists(path):
            return False, f"Folder not found: {path}"
        
        items = os.listdir(path)
        if not items:
            return True, f"The folder '{folder_name}' is empty."
        
        file_list = "\n".join([f"- {item}" for item in items[:20]])
        if len(items) > 20:
            file_list += f"\n...and {len(items)-20} more."
            
        return True, f"Files in {folder_name}:\n{file_list}"
    except Exception as e:
        return False, f"Failed to list files: {e}"


def zip_item(item_path):
    """Compresses a file or folder into a ZIP archive."""
    try:
        if not os.path.exists(item_path):
            return False, f"Item not found: {item_path}"
        
        # Create zip at same location
        shutil.make_archive(item_path, 'zip', item_path if os.path.isdir(item_path) else os.path.dirname(item_path), 
                            os.path.basename(item_path) if not os.path.isdir(item_path) else None)
        return True, f"Created {os.path.basename(item_path)}.zip"
    except Exception as e:
        return False, f"Zip failed: {e}"


def unzip_item(zip_path):
    """Extracts a ZIP archive."""
    try:
        if not zip_path.endswith(".zip") or not os.path.exists(zip_path):
            return False, "Not a valid ZIP file path."
        
        extract_dir = zip_path.replace(".zip", "")
        os.makedirs(extract_dir, exist_ok=True)
        shutil.unpack_archive(zip_path, extract_dir)
        return True, f"Extracted to {os.path.basename(extract_dir)}"
    except Exception as e:
        return False, f"Unzip failed: {e}"
