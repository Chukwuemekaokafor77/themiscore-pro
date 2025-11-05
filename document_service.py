import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO
from werkzeug.utils import secure_filename

class DocumentService:
    """Handles document storage and management."""
    
    def __init__(self, base_upload_folder: str = None):
        """
        Initialize the document service.
        
        Args:
            base_upload_folder: Base directory for storing uploaded files. 
                              Defaults to 'uploads' in the current directory.
        """
        self.base_upload_folder = base_upload_folder or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'uploads'
        )
        self._ensure_directory_exists(self.base_upload_folder)
    
    def _ensure_directory_exists(self, path: str) -> None:
        """Ensure a directory exists, create it if it doesn't."""
        os.makedirs(path, exist_ok=True)
    
    def _get_case_folder(self, case_id: int) -> str:
        """Get the folder path for a specific case."""
        return os.path.join(self.base_upload_folder, str(case_id))
    
    def save_document(
        self, 
        file_stream: BinaryIO, 
        filename: str, 
        case_id: int, 
        user_id: int,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Save an uploaded document.
        
        Args:
            file_stream: File-like object containing the file data
            filename: Original filename
            case_id: ID of the case this document belongs to
            user_id: ID of the user uploading the document
            metadata: Additional metadata to store with the document
            
        Returns:
            Dict containing document metadata
        """
        # Sanitize filename and generate a unique one
        original_filename = secure_filename(filename)
        file_ext = os.path.splitext(original_filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        
        # Create case-specific directory if it doesn't exist
        case_folder = self._get_case_folder(case_id)
        self._ensure_directory_exists(case_folder)
        
        # Save the file
        file_path = os.path.join(case_folder, unique_filename)
        with open(file_path, 'wb') as f:
            # Read the file in chunks to handle large files
            chunk_size = 4096
            while True:
                chunk = file_stream.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        
        # Prepare document metadata
        file_stat = os.stat(file_path)
        
        return {
            'original_filename': original_filename,
            'stored_filename': unique_filename,
            'file_path': file_path,
            'file_size': file_stat.st_size,
            'file_type': file_ext.lstrip('.').upper(),
            'uploaded_at': datetime.utcnow(),
            'uploaded_by': user_id,
            'case_id': case_id,
            'metadata': metadata or {}
        }
    
    def get_document_path(self, case_id: int, filename: str) -> Optional[str]:
        """
        Get the full path to a stored document.
        
        Args:
            case_id: ID of the case the document belongs to
            filename: Name of the file (as stored in the system)
            
        Returns:
            Full path to the document or None if not found
        """
        file_path = os.path.join(self._get_case_folder(case_id), filename)
        return file_path if os.path.exists(file_path) else None
    
    def delete_document(self, case_id: int, filename: str) -> bool:
        """
        Delete a document.
        
        Args:
            case_id: ID of the case the document belongs to
            filename: Name of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        file_path = self.get_document_path(case_id, filename)
        if not file_path:
            return False
            
        try:
            os.remove(file_path)
            return True
        except OSError:
            return False
    
    def list_case_documents(self, case_id: int) -> List[Dict]:
        """
        List all documents for a specific case.
        
        Args:
            case_id: ID of the case
            
        Returns:
            List of document metadata dictionaries
        """
        case_folder = self._get_case_folder(case_id)
        if not os.path.exists(case_folder):
            return []
            
        documents = []
        for filename in os.listdir(case_folder):
            file_path = os.path.join(case_folder, filename)
            if os.path.isfile(file_path):
                file_stat = os.stat(file_path)
                documents.append({
                    'filename': filename,
                    'original_filename': filename,  # In a real app, you'd get this from the database
                    'file_size': file_stat.st_size,
                    'created_at': datetime.fromtimestamp(file_stat.st_ctime),
                    'modified_at': datetime.fromtimestamp(file_stat.st_mtime)
                })
                
        return documents
    
    def get_document_metadata(self, case_id: int, filename: str) -> Optional[Dict]:
        """
        Get metadata for a specific document.
        
        Args:
            case_id: ID of the case the document belongs to
            filename: Name of the file
            
        Returns:
            Document metadata or None if not found
        """
        file_path = self.get_document_path(case_id, filename)
        if not file_path:
            return None
            
        file_stat = os.stat(file_path)
        
        return {
            'filename': filename,
            'original_filename': filename,  # In a real app, you'd get this from the database
            'file_path': file_path,
            'file_size': file_stat.st_size,
            'created_at': datetime.fromtimestamp(file_stat.st_ctime),
            'modified_at': datetime.fromtimestamp(file_stat.st_mtime),
            'file_type': os.path.splitext(filename)[1].lstrip('.').upper()
        }

# Create a singleton instance
document_service = DocumentService()
