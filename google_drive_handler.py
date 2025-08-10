"""
Google Drive Handler for WATW
Handles all Google Drive operations with OAuth2 authentication
"""

import os
import io
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import mimetypes

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:
    print("⚠️ Google API libraries not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

class GoogleDriveHandler:
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.authenticated = False
        
    def authenticate(self) -> bool:
        """Authenticate with Google Drive using OAuth2"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    return False
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('drive', 'v3', credentials=creds)
            self.authenticated = True
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def list_files(self, folder_path: str = '/') -> Dict[str, Any]:
        """List files in a Google Drive folder"""
        if not self.authenticated:
            return {'error': 'Not authenticated with Google Drive'}
        
        try:
            # Find folder by path
            folder_id = self._get_folder_id_by_path(folder_path)
            if not folder_id:
                return {'error': f'Folder not found: {folder_path}'}
            
            # List files in folder
            query = f"'{folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, createdTime)",
                orderBy='name'
            ).execute()
            
            items = results.get('files', [])
            
            # Format response
            files = []
            folders = []
            
            for item in items:
                file_info = {
                    'id': item['id'],
                    'name': item['name'],
                    'type': self._get_file_type(item['mimeType']),
                    'size': self._format_size(item.get('size', 0)),
                    'modified': item.get('modifiedTime', ''),
                    'created': item.get('createdTime', '')
                }
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    folders.append(file_info)
                else:
                    files.append(file_info)
            
            return {
                'success': True,
                'path': folder_path,
                'folders': folders,
                'files': files,
                'total_items': len(folders) + len(files)
            }
            
        except HttpError as e:
            return {'error': f'Google Drive API error: {e}'}
        except Exception as e:
            return {'error': f'Unexpected error: {e}'}
    
    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """Delete a file from Google Drive"""
        if not self.authenticated:
            return {'error': 'Not authenticated with Google Drive'}
        
        try:
            file_id = self._get_file_id_by_path(file_path)
            if not file_id:
                return {'error': f'File not found: {file_path}'}
            
            # Move to trash (safer than permanent delete)
            self.service.files().update(fileId=file_id, body={'trashed': True}).execute()
            
            return {
                'success': True,
                'message': f'File moved to trash: {file_path}',
                'file_path': file_path
            }
            
        except HttpError as e:
            return {'error': f'Google Drive API error: {e}'}
        except Exception as e:
            return {'error': f'Unexpected error: {e}'}
    
    def move_file(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        """Move a file to a different folder"""
        if not self.authenticated:
            return {'error': 'Not authenticated with Google Drive'}
        
        try:
            # Get source file ID
            file_id = self._get_file_id_by_path(source_path)
            if not file_id:
                return {'error': f'Source file not found: {source_path}'}
            
            # Get destination folder ID
            dest_folder_id = self._get_folder_id_by_path(destination_path)
            if not dest_folder_id:
                return {'error': f'Destination folder not found: {destination_path}'}
            
            # Get current parents
            file = self.service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents'))
            
            # Move file
            self.service.files().update(
                fileId=file_id,
                addParents=dest_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            return {
                'success': True,
                'message': f'File moved from {source_path} to {destination_path}',
                'source_path': source_path,
                'destination_path': destination_path
            }
            
        except HttpError as e:
            return {'error': f'Google Drive API error: {e}'}
        except Exception as e:
            return {'error': f'Unexpected error: {e}'}
    
    def get_file_content(self, file_path: str) -> Dict[str, Any]:
        """Download and return file content for AI processing"""
        if not self.authenticated:
            return {'error': 'Not authenticated with Google Drive'}
        
        try:
            file_id = self._get_file_id_by_path(file_path)
            if not file_id:
                return {'error': f'File not found: {file_path}'}
            
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            mime_type = file_metadata.get('mimeType')
            
            # Handle different file types
            if mime_type == 'application/pdf':
                return self._extract_pdf_content(file_id, file_path)
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return self._extract_docx_content(file_id, file_path)
            elif mime_type.startswith('text/'):
                return self._extract_text_content(file_id, file_path)
            elif mime_type.startswith('application/vnd.google-apps'):
                return self._extract_google_doc_content(file_id, file_path, mime_type)
            else:
                return {'error': f'Unsupported file type: {mime_type}'}
                
        except HttpError as e:
            return {'error': f'Google Drive API error: {e}'}
        except Exception as e:
            return {'error': f'Unexpected error: {e}'}
    
    def _get_folder_id_by_path(self, path: str) -> Optional[str]:
        """Get folder ID by path"""
        if path == '/' or path == 'root':
            return 'root'
        
        # Split path and traverse
        parts = [p for p in path.strip('/').split('/') if p]
        current_id = 'root'
        
        for part in parts:
            query = f"name='{part}' and '{current_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(q=query, fields="files(id)").execute()
            items = results.get('files', [])
            
            if not items:
                return None
            current_id = items[0]['id']
        
        return current_id
    
    def _get_file_id_by_path(self, file_path: str) -> Optional[str]:
        """Get file ID by full path"""
        path_parts = file_path.strip('/').split('/')
        if len(path_parts) < 1:
            return None
            
        filename = path_parts[-1]
        folder_path = '/' + '/'.join(path_parts[:-1]) if len(path_parts) > 1 else '/'
        
        folder_id = self._get_folder_id_by_path(folder_path)
        if not folder_id:
            return None
        
        query = f"name='{filename}' and '{folder_id}' in parents and trashed = false"
        results = self.service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        return items[0]['id'] if items else None
    
    def _extract_text_content(self, file_id: str, file_path: str) -> Dict[str, Any]:
        """Extract content from text files"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            content = file_io.getvalue().decode('utf-8')
            
            return {
                'success': True,
                'file_path': file_path,
                'content': content,
                'type': 'text',
                'size': len(content)
            }
            
        except Exception as e:
            return {'error': f'Failed to extract text content: {e}'}
    
    def _extract_pdf_content(self, file_id: str, file_path: str) -> Dict[str, Any]:
        """Extract content from PDF files"""
        # For now, return placeholder - would need PyPDF2 or similar
        return {
            'success': True,
            'file_path': file_path,
            'content': '[PDF content extraction requires additional libraries]',
            'type': 'pdf',
            'note': 'PDF extraction requires PyPDF2 or similar library'
        }
    
    def _extract_docx_content(self, file_id: str, file_path: str) -> Dict[str, Any]:
        """Extract content from DOCX files"""
        # For now, return placeholder - would need python-docx
        return {
            'success': True,
            'file_path': file_path,
            'content': '[DOCX content extraction requires additional libraries]',
            'type': 'docx',
            'note': 'DOCX extraction requires python-docx library'
        }
    
    def _extract_google_doc_content(self, file_id: str, file_path: str, mime_type: str) -> Dict[str, Any]:
        """Extract content from Google Docs"""
        try:
            # Export as plain text
            request = self.service.files().export_media(fileId=file_id, mimeType='text/plain')
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            content = file_io.getvalue().decode('utf-8')
            
            return {
                'success': True,
                'file_path': file_path,
                'content': content,
                'type': 'google_doc',
                'size': len(content)
            }
            
        except Exception as e:
            return {'error': f'Failed to extract Google Doc content: {e}'}
    
    def _get_file_type(self, mime_type: str) -> str:
        """Get user-friendly file type"""
        type_mapping = {
            'application/vnd.google-apps.folder': '📁 Folder',
            'application/vnd.google-apps.document': '📝 Google Doc',
            'application/vnd.google-apps.spreadsheet': '📊 Google Sheet',
            'application/vnd.google-apps.presentation': '📺 Google Slides',
            'application/pdf': '📄 PDF',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📝 Word Doc',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊 Excel',
            'text/plain': '📄 Text',
            'image/jpeg': '🖼️ Image',
            'image/png': '🖼️ Image',
        }
        
        return type_mapping.get(mime_type, '📄 File')
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if not size_bytes or size_bytes == 0:
            return '0 B'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

# Test function
def test_google_drive():
    """Test Google Drive functionality"""
    handler = GoogleDriveHandler()
    
    print("🔐 Testing Google Drive Authentication...")
    if handler.authenticate():
        print("✅ Authentication successful!")
        
        # Test listing root folder
        result = handler.list_files('/')
        print(f"📁 Root folder contents: {result}")
        
    else:
        print("❌ Authentication failed!")
        print("Make sure you have credentials.json file")

if __name__ == "__main__":
    test_google_drive()
