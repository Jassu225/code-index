"""
Firestore database layer for the Serverless Code Index System.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from google.cloud import firestore
from google.cloud.firestore import DocumentReference, CollectionReference, WriteBatch
from google.cloud.firestore_v1.base_document import DocumentSnapshot
from google.api_core import exceptions

from .config import get_settings
from ..models.repository import RepositoryMetadata
from ..models.file_index import FileIndex

logger = logging.getLogger(__name__)


class FirestoreDatabase:
    """Firestore database client for code index operations."""
    
    def __init__(self):
        """Initialize Firestore client."""
        self.settings = get_settings()
        self.client: Optional[firestore.Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Firestore client with proper configuration."""
        try:
            if self.settings.service_account_key_path:
                # Use service account key file
                self.client = firestore.Client.from_service_account_json(
                    self.settings.service_account_key_path,
                    project=self.settings.gcp_project_id,
                    database=self.settings.firestore_database_id or "(default)"
                )
            else:
                # Use application default credentials
                self.client = firestore.Client(
                    project=self.settings.gcp_project_id,
                    database=self.settings.firestore_database_id or "(default)"
                )
            
            logger.info(f"Firestore client initialized for project: {self.settings.gcp_project_id}, database: {self.settings.firestore_database_id or '(default)'}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise
    
    def _get_collection(self, collection_name: str) -> CollectionReference:
        """Get a Firestore collection reference."""
        if not self.client:
            raise RuntimeError("Firestore client not initialized")
        
        # Use prefix from settings, but handle empty prefix case
        prefix = self.settings.firestore_collection_prefix
        if prefix:
            collection_path = f"{prefix}_{collection_name}"
        else:
            collection_path = collection_name
            
        return self.client.collection(collection_path)
    
    def _get_document_ref(self, collection_name: str, doc_id: str) -> DocumentReference:
        """Get a Firestore document reference."""
        return self._get_collection(collection_name).document(doc_id)
    
    async def create_repository(self, repo_data: RepositoryMetadata) -> bool:
        """Create a new repository document in Firestore."""
        try:
            doc_ref = self._get_document_ref("repositories", repo_data.repoId)
            doc_ref.set(repo_data.model_dump())
            logger.info(f"Repository created: {repo_data.repoId}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create repository {repo_data.repoId}: {e}")
            return False
    
    async def get_repository(self, repo_url: str) -> Optional[RepositoryMetadata]:
        """Retrieve a repository document from Firestore."""
        try:
            doc_ref = self._get_document_ref("repositories", repo_url)
            doc_snapshot = doc_ref.get()
            
            if doc_snapshot.exists:
                data = doc_snapshot.to_dict()
                return RepositoryMetadata(**data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve repository {repo_url}: {e}")
            return None
    
    async def list_repositories(self) -> List[RepositoryMetadata]:
        """List all repository documents from Firestore."""
        try:
            collection = self._get_collection("repositories")
            docs = collection.stream()
            
            repositories = []
            for doc in docs:
                try:
                    repo_data = RepositoryMetadata(**doc.to_dict())
                    repositories.append(repo_data)
                except Exception as e:
                    logger.warning(f"Failed to parse repository document {doc.id}: {e}")
                    continue
            
            return repositories
            
        except Exception as e:
            logger.error(f"Failed to list repositories: {e}")
            return []
    
    async def update_repository(self, repo_url: str, updates: Dict[str, Any]) -> bool:
        """Update a repository document in Firestore."""
        try:
            doc_ref = self._get_document_ref("repositories", repo_url)
            
            # Add timestamp
            updates["lastUpdated"] = datetime.utcnow().isoformat() + "Z"
            
            doc_ref.update(updates)
            logger.info(f"Repository updated: {repo_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update repository {repo_url}: {e}")
            return False
    
    async def delete_repository(self, repo_url: str) -> bool:
        """Delete a repository document and all related file indexes from Firestore."""
        try:
            # Start a batch write
            batch = self.client.batch()
            
            # Delete repository document
            repo_doc_ref = self._get_document_ref("repositories", repo_url)
            batch.delete(repo_doc_ref)
            
            # Delete all file indexes for this repository
            file_indexes_collection = self._get_collection("file_indexes")
            file_indexes = file_indexes_collection.where("repoId", "==", repo_url).stream()
            
            for doc in file_indexes:
                batch.delete(doc.reference)
            
            # Commit the batch
            batch.commit()
            
            logger.info(f"Repository and file indexes deleted: {repo_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete repository {repo_url}: {e}")
            return False
    
    async def create_file_index(self, file_index: FileIndex) -> bool:
        """Create a new file index document in Firestore."""
        try:
            # Create a unique document ID using repo and file path
            doc_id = f"{file_index.repoId}_{file_index.filePath.replace('/', '_')}"
            doc_ref = self._get_document_ref("file_indexes", doc_id)
            doc_ref.set(file_index.model_dump())
            
            logger.info(f"File index created: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create file index: {e}")
            return False
    
    async def get_file_index(self, repo_url: str, file_path: str) -> Optional[FileIndex]:
        """Retrieve a file index document from Firestore."""
        try:
            doc_id = f"{repo_url}_{file_path.replace('/', '_')}"
            doc_ref = self._get_document_ref("file_indexes", doc_id)
            doc_snapshot = doc_ref.get()
            
            if doc_snapshot.exists:
                data = doc_snapshot.to_dict()
                return FileIndex(**data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve file index: {e}")
            return None
    
    async def list_file_indexes(self, repo_url: str) -> List[FileIndex]:
        """List all file indexes for a specific repository."""
        try:
            collection = self._get_collection("file_indexes")
            docs = collection.where("repoId", "==", repo_url).stream()
            
            file_indexes = []
            for doc in docs:
                try:
                    file_index_data = FileIndex(**doc.to_dict())
                    file_indexes.append(file_index_data)
                except Exception as e:
                    logger.warning(f"Failed to parse file index document {doc.id}: {e}")
                    continue
            
            return file_indexes
            
        except Exception as e:
            logger.error(f"Failed to list file indexes for repository {repo_url}: {e}")
            return []
    
    async def update_file_index(self, repo_url: str, file_path: str, updates: Dict[str, Any]) -> bool:
        """Update a file index document in Firestore."""
        try:
            doc_id = f"{repo_url}_{file_path.replace('/', '_')}"
            doc_ref = self._get_document_ref("file_indexes", doc_id)
            
            # Add timestamp
            updates["updatedAt"] = datetime.utcnow().isoformat() + "Z"
            
            doc_ref.update(updates)
            logger.info(f"File index updated: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update file index: {e}")
            return False
    
    async def delete_file_index(self, repo_url: str, file_path: str) -> bool:
        """Delete a file index document from Firestore."""
        try:
            doc_id = f"{repo_url}_{file_path.replace('/', '_')}"
            doc_ref = self._get_document_ref("file_indexes", doc_id)
            doc_ref.delete()
            
            logger.info(f"File index deleted: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file index: {e}")
            return False
    
    async def batch_write_file_indexes(self, file_indexes: List[FileIndex]) -> bool:
        """Write multiple file indexes in a batch operation."""
        try:
            if not file_indexes:
                return True
            
            batch = self.client.batch()
            
            for file_index in file_indexes:
                doc_id = f"{file_index.repoId}_{file_index.filePath.replace('/', '_')}"
                doc_ref = self._get_document_ref("file_indexes", doc_id)
                batch.set(doc_ref, file_index.model_dump())
            
            batch.commit()
            logger.info(f"Batch write completed for {len(file_indexes)} file indexes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to batch write file indexes: {e}")
            return False
    
    async def search_exports(self, repo_url: str, query: str, limit: int = 100) -> List[FileIndex]:
        """Search for exports containing the query string."""
        try:
            collection = self._get_collection("file_indexes")
            
            # Firestore doesn't support full-text search, so we'll do a basic query
            # In production, consider using Algolia or similar for better search
            docs = collection.where("repoId", "==", repo_url).limit(limit).stream()
            
            results = []
            for doc in docs:
                try:
                    file_index = FileIndex(**doc.to_dict())
                    # Filter by query in exports
                    matching_exports = [
                        export for export in file_index.exports
                        if query.lower() in export.name.lower()
                    ]
                    if matching_exports:
                        # Create a copy with only matching exports
                        filtered_index = file_index.model_copy()
                        filtered_index.exports = matching_exports
                        results.append(filtered_index)
                except Exception as e:
                    logger.warning(f"Failed to parse file index document {doc.id}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search exports: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            repo_count = len(await self.list_repositories())
            
            # Count total file indexes
            file_indexes_collection = self._get_collection("file_indexes")
            file_index_count = len(list(file_indexes_collection.stream()))
            
            return {
                "total_repositories": repo_count,
                "total_file_indexes": file_index_count,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {
                "total_repositories": 0,
                "total_file_indexes": 0,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e)
            }


# Global database instance
_db: Optional[FirestoreDatabase] = None


def get_database() -> FirestoreDatabase:
    """Get database instance."""
    global _db
    if _db is None:
        _db = FirestoreDatabase()
    return _db
