import os
import shutil
import logging
import datetime

# Setup Logging
logger = logging.getLogger(__name__)

# File Categories
FILE_CATEGORIES = {
    "Images": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp", ".webp"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt", ".xlsx", ".xls", ".hwp", ".csv", ".md"],
    "Installers": [".exe", ".msi", ".bat", ".sh", ".apk"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Media": [".mp4", ".mp3", ".mov", ".avi", ".wav", ".mkv"],
    "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".json"]
}

def organize_directory(target_path):
    """
    Organizes files in the target directory into subfolders based on their extensions.
    """
    if not os.path.exists(target_path):
        logger.error(f"Directory not found: {target_path}")
        return f"Error: Directory not found ({target_path})"

    logger.info(f"Starting organization of: {target_path}")
    moved_count = 0
    
    try:
        # Get all files in the directory
        files = [f for f in os.listdir(target_path) if os.path.isfile(os.path.join(target_path, f))]
        
        for filename in files:
            # Skip hidden files
            if filename.startswith('.'):
                continue
                
            file_path = os.path.join(target_path, filename)
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            # Find category
            category = "Others"
            for cat, exts in FILE_CATEGORIES.items():
                if ext in exts:
                    category = cat
                    break
            
            # Create category directory
            category_dir = os.path.join(target_path, category)
            os.makedirs(category_dir, exist_ok=True)
            
            # Move file
            dest_path = os.path.join(category_dir, filename)
            
            # Handle duplicates
            if os.path.exists(dest_path):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}_{timestamp}{ext}"
                dest_path = os.path.join(category_dir, new_filename)
            
            shutil.move(file_path, dest_path)
            moved_count += 1
            action_log = f"Moved: {filename} -> {category}/"
            logger.info(action_log)
            # Add to a global list or return it? For now, let's return a summary.

        result_msg = f"Organization Complete. Moved {moved_count} files."
        logger.info(result_msg)
        return result_msg

    except Exception as e:
        error_msg = f"Error during organization: {e}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    # Test with a dummy folder if needed
    logging.basicConfig(level=logging.INFO)
    print("File Manager Module Ready")
