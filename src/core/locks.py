"""
Distributed locking system using Firestore transactions.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from google.cloud import firestore
from google.cloud.firestore_v1 import Transaction

logger = logging.getLogger(__name__)


class FileLock:
    """
    Distributed file-level lock using Firestore transactions.
    
    Lock key format: {repoId}:{filePath} (NO commit SHA in lock key)
    """
    
    def __init__(self, repo_id: str, file_path: str, ttl_seconds: int = 300):
        """
        Initialize file lock.
        
        Args:
            repo_id: Repository identifier
            file_path: Relative path within repository
            ttl_seconds: Lock TTL in seconds (default: 5 minutes)
        """
        self.repo_id = repo_id
        self.file_path = file_path
        self.lock_key = f"{repo_id}:{file_path}"
        self.ttl_seconds = ttl_seconds
        self.acquired_at: Optional[datetime] = None
        self.lock_doc_ref: Optional[firestore.DocumentReference] = None
        self._firestore_client: Optional[firestore.Client] = None
        
    async def acquire(self, firestore_client: firestore.Client) -> bool:
        """
        Acquire the file lock atomically using Firestore transaction.
        
        Args:
            firestore_client: Firestore client instance
            
        Returns:
            True if lock acquired, False otherwise
        """
        self._firestore_client = firestore_client
        self.lock_doc_ref = firestore_client.collection('file_locks').document(self.lock_key)
        
        try:
            # Use transaction to atomically acquire lock
            transaction = firestore_client.transaction()
            success = await self._acquire_in_transaction(transaction)
            
            if success:
                self.acquired_at = datetime.utcnow()
                logger.info(f"Lock acquired: {self.lock_key}")
            else:
                logger.warning(f"Failed to acquire lock: {self.lock_key}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error acquiring lock {self.lock_key}: {e}")
            return False
    
    async def _acquire_in_transaction(self, transaction: Transaction) -> bool:
        """Acquire lock within a Firestore transaction."""
        try:
            # Get current lock state
            lock_doc = self.lock_doc_ref.get(transaction=transaction)
            
            now = datetime.utcnow()
            lock_expires_at = now + timedelta(seconds=self.ttl_seconds)
            
            if not lock_doc.exists:
                # No existing lock, create new one
                transaction.set(self.lock_doc_ref, {
                    'repo_id': self.repo_id,
                    'file_path': self.file_path,
                    'acquired_at': now,
                    'expires_at': lock_expires_at,
                    'lock_key': self.lock_key,
                    'status': 'acquired'
                })
                return True
            
            # Check if existing lock is expired
            existing_data = lock_doc.to_dict()
            existing_expires_at = existing_data.get('expires_at')
            
            if existing_expires_at and existing_expires_at < now:
                # Lock expired, acquire it
                transaction.update(self.lock_doc_ref, {
                    'acquired_at': now,
                    'expires_at': lock_expires_at,
                    'status': 'acquired'
                })
                return True
            
            # Lock is still valid
            return False
            
        except Exception as e:
            logger.error(f"Transaction error acquiring lock {self.lock_key}: {e}")
            return False
    
    async def release(self) -> bool:
        """
        Release the file lock.
        
        Returns:
            True if lock released, False otherwise
        """
        if not self.acquired_at or not self.lock_doc_ref:
            logger.warning(f"Cannot release lock that was never acquired: {self.lock_key}")
            return False
        
        try:
            # Delete the lock document
            self.lock_doc_ref.delete()
            self.acquired_at = None
            logger.info(f"Lock released: {self.lock_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing lock {self.lock_key}: {e}")
            return False
    
    async def is_locked(self) -> bool:
        """
        Check if the file is currently locked.
        
        Returns:
            True if locked, False otherwise
        """
        if not self.lock_doc_ref:
            return False
            
        try:
            lock_doc = self.lock_doc_ref.get()
            
            if not lock_doc.exists:
                return False
            
            # Check if lock is expired
            lock_data = lock_doc.to_dict()
            expires_at = lock_data.get('expires_at')
            
            if expires_at and expires_at < datetime.utcnow():
                # Lock expired, clean it up
                await self._cleanup_expired_lock()
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking lock status {self.lock_key}: {e}")
            return False
    
    async def _cleanup_expired_lock(self):
        """Clean up expired lock."""
        try:
            self.lock_doc_ref.delete()
            logger.info(f"Cleaned up expired lock: {self.lock_key}")
        except Exception as e:
            logger.error(f"Error cleaning up expired lock {self.lock_key}: {e}")
    
    async def extend_ttl(self, additional_seconds: int) -> bool:
        """
        Extend the lock TTL.
        
        Args:
            additional_seconds: Additional seconds to add to TTL
            
        Returns:
            True if TTL extended, False otherwise
        """
        if not self.acquired_at or not self.lock_doc_ref:
            return False
        
        try:
            new_expires_at = datetime.utcnow() + timedelta(seconds=additional_seconds)
            
            self.lock_doc_ref.update({
                'expires_at': new_expires_at
            })
            
            logger.info(f"Extended TTL for lock {self.lock_key} by {additional_seconds} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Error extending TTL for lock {self.lock_key}: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry (synchronous)."""
        raise RuntimeError("FileLock must be used with async context manager")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (synchronous)."""
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not self._firestore_client:
            raise RuntimeError("Firestore client must be provided before using context manager")
        
        success = await self.acquire(self._firestore_client)
        if not success:
            raise RuntimeError(f"Failed to acquire lock: {self.lock_key}")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()
    
    @property
    def is_acquired(self) -> bool:
        """Check if lock is currently acquired."""
        return self.acquired_at is not None
    
    @property
    def time_remaining(self) -> Optional[float]:
        """Get remaining time until lock expires in seconds."""
        if not self.acquired_at:
            return None
        
        expires_at = self.acquired_at + timedelta(seconds=self.ttl_seconds)
        remaining = (expires_at - datetime.utcnow()).total_seconds()
        return max(0, remaining)
