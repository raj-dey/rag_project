"""
firebase_client.py
------------------
Singleton Firebase Admin SDK initializer.
Exposes helpers for Firestore and Firebase Storage.

Set FIREBASE_ENABLED=true in .env along with credentials to activate.
Falls back gracefully (returns None) when Firebase is not configured.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_firebase_app = None
_firestore_client = None
_storage_bucket = None


def _initialize_firebase():
    """Initializes the Firebase Admin SDK exactly once."""
    global _firebase_app, _firestore_client, _storage_bucket

    if _firebase_app is not None:
        return True

    from backend.core.config import settings

    if not settings.FIREBASE_ENABLED:
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage

        # Build credential from inline JSON or file path
        cred_obj = None
        if settings.FIREBASE_SERVICE_ACCOUNT_JSON:
            service_account_info = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            cred_obj = credentials.Certificate(service_account_info)
        elif settings.FIREBASE_SERVICE_ACCOUNT_PATH:
            cred_obj = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
        else:
            logger.error("[Firebase] FIREBASE_ENABLED=true but no credentials provided. "
                         "Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON.")
            return False

        # Avoid re-initialization if already done (e.g. hot-reload)
        if not firebase_admin._apps:
            _firebase_app = firebase_admin.initialize_app(
                cred_obj,
                {"storageBucket": settings.FIREBASE_STORAGE_BUCKET}
            )
        else:
            _firebase_app = firebase_admin.get_app()

        _firestore_client = firestore.client()
        _storage_bucket = storage.bucket()

        logger.info(f"[Firebase] Initialized successfully. Project: {settings.FIREBASE_PROJECT_ID}, "
                    f"Bucket: {settings.FIREBASE_STORAGE_BUCKET}")
        return True

    except ImportError:
        logger.error("[Firebase] 'firebase-admin' package not installed. Run: pip install firebase-admin")
        return False
    except Exception as e:
        logger.error(f"[Firebase] Initialization failed: {e}")
        return False


def get_firestore_client():
    """Returns the Firestore client, or None if Firebase is not enabled/configured."""
    global _firestore_client
    if _firestore_client is None:
        _initialize_firebase()
    return _firestore_client


def get_storage_bucket():
    """Returns the Firebase Storage bucket, or None if Firebase is not enabled/configured."""
    global _storage_bucket
    if _storage_bucket is None:
        _initialize_firebase()
    return _storage_bucket


def is_firebase_enabled() -> bool:
    """Returns True if Firebase was successfully initialized."""
    from backend.core.config import settings
    if not settings.FIREBASE_ENABLED:
        return False
    return _initialize_firebase()
