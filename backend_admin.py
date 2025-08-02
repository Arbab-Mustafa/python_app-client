#!/usr/bin/env python3
"""
Backend Admin Interface for Texas School Psychology Assistant
Provides secure file upload and management capabilities for both local and GCP deployment
"""

import os
import sys
import argparse
import logging
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import hashlib
from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

class BackendAdmin:
    """Backend administration class for file management"""
    
    def __init__(self):
        self.pdfs_dir = "pdfs"
        self.backup_dir = "backups"
        self.logs_dir = "logs"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        for directory in [self.pdfs_dir, self.backup_dir, self.logs_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def upload_pdf(self, file_path: str, description: str = "") -> Dict:
        """Upload a PDF file to the backend"""
        try:
            # Validate file
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not file_path.lower().endswith('.pdf'):
                raise ValueError("Only PDF files are allowed")
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > config.MAX_FILE_SIZE:
                raise ValueError(f"File too large: {file_size} bytes (max: {config.MAX_FILE_SIZE})")
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = os.path.basename(file_path)
            file_hash = self._calculate_file_hash(file_path)
            new_filename = f"{timestamp}_{file_hash[:8]}_{original_name}"
            destination_path = os.path.join(self.pdfs_dir, new_filename)
            
            # Copy file
            shutil.copy2(file_path, destination_path)
            
            # Create metadata
            metadata = {
                "original_name": original_name,
                "uploaded_name": new_filename,
                "uploaded_at": datetime.now().isoformat(),
                "file_size": file_size,
                "file_hash": file_hash,
                "description": description,
                "uploaded_by": "backend_admin"
            }
            
            # Save metadata
            metadata_file = destination_path.replace('.pdf', '_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"PDF uploaded successfully: {new_filename}")
            return {
                "success": True,
                "filename": new_filename,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error uploading PDF: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def upload_multiple_pdfs(self, file_paths: List[str], descriptions: List[str] = None) -> Dict:
        """Upload multiple PDF files"""
        if descriptions is None:
            descriptions = [""] * len(file_paths)
        
        results = []
        for file_path, description in zip(file_paths, descriptions):
            result = self.upload_pdf(file_path, description)
            results.append(result)
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        return {
            "total_files": len(file_paths),
            "successful": len(successful),
            "failed": len(failed),
            "results": results
        }
    
    def list_pdfs(self) -> List[Dict]:
        """List all PDF files in the backend"""
        pdfs = []
        for file_path in Path(self.pdfs_dir).glob("*.pdf"):
            metadata_file = file_path.with_suffix('').with_suffix('_metadata.json')
            
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            pdfs.append({
                "filename": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                "metadata": metadata
            })
        
        return sorted(pdfs, key=lambda x: x["modified"], reverse=True)
    
    def delete_pdf(self, filename: str) -> Dict:
        """Delete a PDF file from the backend"""
        try:
            file_path = os.path.join(self.pdfs_dir, filename)
            metadata_file = file_path.replace('.pdf', '_metadata.json')
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF not found: {filename}")
            
            # Create backup before deletion
            backup_path = os.path.join(self.backup_dir, f"deleted_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
            shutil.copy2(file_path, backup_path)
            
            # Delete files
            os.remove(file_path)
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            
            logger.info(f"PDF deleted successfully: {filename}")
            return {
                "success": True,
                "message": f"PDF deleted: {filename}",
                "backup_created": backup_path
            }
            
        except Exception as e:
            logger.error(f"Error deleting PDF: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def backup_pdfs(self, backup_name: str = None) -> Dict:
        """Create a backup of all PDF files"""
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_path = os.path.join(self.backup_dir, backup_name)
            os.makedirs(backup_path, exist_ok=True)
            
            # Copy all PDFs and metadata
            pdf_count = 0
            for file_path in Path(self.pdfs_dir).glob("*.pdf"):
                shutil.copy2(file_path, backup_path)
                metadata_file = file_path.with_suffix('').with_suffix('_metadata.json')
                if metadata_file.exists():
                    shutil.copy2(metadata_file, backup_path)
                pdf_count += 1
            
            # Create backup manifest
            manifest = {
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "pdf_count": pdf_count,
                "source_directory": self.pdfs_dir
            }
            
            manifest_file = os.path.join(backup_path, "backup_manifest.json")
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"Backup created successfully: {backup_name} ({pdf_count} PDFs)")
            return {
                "success": True,
                "backup_name": backup_name,
                "backup_path": backup_path,
                "pdf_count": pdf_count
            }
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def restore_backup(self, backup_name: str) -> Dict:
        """Restore PDFs from a backup"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_name)
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup not found: {backup_name}")
            
            # Read backup manifest
            manifest_file = os.path.join(backup_path, "backup_manifest.json")
            if os.path.exists(manifest_file):
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
            
            # Restore PDFs
            restored_count = 0
            for file_path in Path(backup_path).glob("*.pdf"):
                shutil.copy2(file_path, self.pdfs_dir)
                metadata_file = file_path.with_suffix('').with_suffix('_metadata.json')
                if metadata_file.exists():
                    shutil.copy2(metadata_file, self.pdfs_dir)
                restored_count += 1
            
            logger.info(f"Backup restored successfully: {backup_name} ({restored_count} PDFs)")
            return {
                "success": True,
                "backup_name": backup_name,
                "restored_count": restored_count
            }
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_system_info(self) -> Dict:
        """Get system information"""
        pdfs = self.list_pdfs()
        total_size = sum(pdf["size"] for pdf in pdfs)
        
        return {
            "pdf_count": len(pdfs),
            "total_size": total_size,
            "pdfs_directory": os.path.abspath(self.pdfs_dir),
            "backup_directory": os.path.abspath(self.backup_dir),
            "logs_directory": os.path.abspath(self.logs_dir),
            "max_file_size": config.MAX_FILE_SIZE,
            "allowed_file_types": config.ALLOWED_FILE_TYPES
        }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

def main():
    """Main backend admin interface"""
    parser = argparse.ArgumentParser(
        description="Backend Admin Interface for Texas School Psychology Assistant"
    )
    parser.add_argument(
        'command',
        choices=['upload', 'upload-multiple', 'list', 'delete', 'backup', 'restore', 'info'],
        help='Command to execute'
    )
    parser.add_argument(
        '--files', '-f',
        nargs='+',
        help='File paths for upload/delete operations'
    )
    parser.add_argument(
        '--descriptions', '-d',
        nargs='+',
        help='Descriptions for uploaded files'
    )
    parser.add_argument(
        '--backup-name', '-b',
        help='Backup name for backup/restore operations'
    )
    
    args = parser.parse_args()
    
    admin = BackendAdmin()
    
    print(f"🔧 Backend Admin Interface - Texas School Psychology Assistant")
    print(f"Command: {args.command}")
    
    if args.command == 'upload':
        if not args.files or len(args.files) != 1:
            print("❌ Please provide exactly one file path")
            sys.exit(1)
        
        description = args.descriptions[0] if args.descriptions else ""
        result = admin.upload_pdf(args.files[0], description)
        print(json.dumps(result, indent=2))
        
    elif args.command == 'upload-multiple':
        if not args.files:
            print("❌ Please provide file paths")
            sys.exit(1)
        
        result = admin.upload_multiple_pdfs(args.files, args.descriptions)
        print(json.dumps(result, indent=2))
        
    elif args.command == 'list':
        pdfs = admin.list_pdfs()
        print(f"📚 Found {len(pdfs)} PDF files:")
        for pdf in pdfs:
            print(f"  - {pdf['filename']} ({pdf['size']} bytes)")
            if pdf['metadata']:
                print(f"    Description: {pdf['metadata'].get('description', 'N/A')}")
        
    elif args.command == 'delete':
        if not args.files or len(args.files) != 1:
            print("❌ Please provide exactly one filename to delete")
            sys.exit(1)
        
        result = admin.delete_pdf(args.files[0])
        print(json.dumps(result, indent=2))
        
    elif args.command == 'backup':
        result = admin.backup_pdfs(args.backup_name)
        print(json.dumps(result, indent=2))
        
    elif args.command == 'restore':
        if not args.backup_name:
            print("❌ Please provide backup name")
            sys.exit(1)
        
        result = admin.restore_backup(args.backup_name)
        print(json.dumps(result, indent=2))
        
    elif args.command == 'info':
        info = admin.get_system_info()
        print(json.dumps(info, indent=2))

if __name__ == "__main__":
    main() 