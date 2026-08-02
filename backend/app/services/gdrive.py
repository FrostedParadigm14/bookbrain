import os
import re
import requests
import gdown
from pathlib import Path
from typing import Optional
from app.core.config import settings

class GoogleDriveService:
    @staticmethod
    def extract_file_id(url_or_id: str) -> str:
        """Extract Google Drive file ID from various URL patterns or raw ID string."""
        url_or_id = url_or_id.strip()
        
        # Pattern 1: https://drive.google.com/file/d/<FILE_ID>/view...
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url_or_id)
        if match:
            return match.group(1)
            
        # Pattern 2: https://drive.google.com/open?id=<FILE_ID> or uc?id=<FILE_ID>
        match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url_or_id)
        if match:
            return match.group(1)
            
        # Pattern 3: Direct File ID string
        if re.match(r'^[a-zA-Z0-9_-]{20,}$', url_or_id):
            return url_or_id
            
        raise ValueError(f"Could not parse a valid Google Drive file ID from input: {url_or_id}")

    @staticmethod
    def download_file(url_or_id: str) -> str:
        """Download Google Drive file (supporting both public & restricted/private links).
        Returns local destination path.
        """
        file_id = GoogleDriveService.extract_file_id(url_or_id)
        
        output_dir = os.path.join(os.getcwd(), "data", "uploads", "gdrive")
        os.makedirs(output_dir, exist_ok=True)
        
        # Look for existing downloaded cached file for this file_id
        for existing in os.listdir(output_dir):
            if existing.startswith(f"gdrive_{file_id}"):
                cached_path = os.path.join(output_dir, existing)
                print(f"[GDrive Service] Using existing cached file: {cached_path}")
                return cached_path
                
        dest_path = os.path.join(output_dir, f"gdrive_{file_id}.epub")
        print(f"[GDrive Service] Downloading Google Drive file ID: {file_id}...")
        
        # Auto-discover service account json file if not explicitly set in config
        sa_path = settings.GDRIVE_SERVICE_ACCOUNT_FILE
        if not sa_path or not os.path.exists(sa_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            for fname in os.listdir(backend_dir):
                if fname.endswith('.json') and not fname.startswith('.'):
                    full_p = os.path.join(backend_dir, fname)
                    try:
                        with open(full_p, 'r') as f:
                            data = f.read(500)
                            if '"type": "service_account"' in data or '"type":' in data and 'service_account' in data:
                                sa_path = full_p
                                print(f"[GDrive Service] Auto-discovered Google Service Account file: {sa_path}")
                                break
                    except:
                        pass
        
        # Strategy A: Use Google Drive Official Client if Service Account or API key configured
        if sa_path or settings.GDRIVE_API_KEY or settings.GDRIVE_OAUTH_TOKEN:
            try:
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaIoBaseDownload
                import io
                
                creds = None
                if sa_path and os.path.exists(sa_path):
                    from google.oauth2 import service_account
                    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
                    creds = service_account.Credentials.from_service_account_file(
                        sa_path, scopes=SCOPES
                    )
                elif settings.GDRIVE_OAUTH_TOKEN:
                    from google.oauth2.credentials import Credentials
                    creds = Credentials(settings.GDRIVE_OAUTH_TOKEN)

                if creds:
                    service = build('drive', 'v3', credentials=creds)
                elif settings.GDRIVE_API_KEY:
                    service = build('drive', 'v3', developerKey=settings.GDRIVE_API_KEY)
                else:
                    service = None

                if service:
                    # Get metadata to get file name & mime
                    file_meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
                    fname = file_meta.get("name", f"gdrive_{file_id}.epub")
                    ext = Path(fname).suffix.lower() or ".epub"
                    dest_path = os.path.join(output_dir, f"gdrive_{file_id}{ext}")
                    
                    request = service.files().get_media(fileId=file_id)
                    fh = io.FileIO(dest_path, 'wb')
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        print(f"[GDrive Auth Download] Progress: {int(status.progress() * 100)}%")
                    print(f"[GDrive Auth Download] Successfully downloaded to {dest_path}")
                    return dest_path
            except Exception as e:
                print(f"[GDrive Auth Download] Auth download attempt failed: {e}. Trying gdown/fallback...")

        # Strategy B: gdown download
        try:
            downloaded = gdown.download(id=file_id, output=dest_path, quiet=False, fuzzy=True, use_cookies=False)
            if downloaded and os.path.exists(downloaded) and os.path.getsize(downloaded) > 100:
                print(f"[GDrive Service] Successfully downloaded via gdown: {downloaded}")
                return downloaded
        except Exception as e:
            print(f"[GDrive Service] gdown attempt failed: {e}")

        # Strategy C: Direct requests fallback
        try:
            session = requests.Session()
            url = f"https://docs.google.com/uc?export=download&confirm=t&id={file_id}"
            response = session.get(url, stream=True)
            if response.status_code == 200:
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=32768):
                        if chunk:
                            f.write(chunk)
                if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100:
                    print(f"[GDrive Service] Direct download succeeded: {dest_path}")
                    return dest_path
        except Exception as e:
            print(f"[GDrive Service] Direct request download failed: {e}")
            
        raise RuntimeError(
            f"Failed to download Google Drive file (ID: {file_id}). "
            "If the file is restricted or private, please set GDRIVE_SERVICE_ACCOUNT_FILE or GDRIVE_API_KEY in backend/.env"
        )
