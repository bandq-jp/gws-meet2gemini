from __future__ import annotations
from fastapi import Depends
from app.infrastructure.supabase.client import get_supabase as _get_supabase

def get_supabase():
    return _get_supabase()
