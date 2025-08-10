#!/usr/bin/env python3
"""
Validation script for Drive webhook setup
Tests folder access and service account permissions
"""
import sys
from pathlib import Path

# Add parent directory to path to import watch_setup
sys.path.append(str(Path(__file__).parent.parent))

from tests.watch_setup import USERS, create_drive_service, verify_folder_access

def main():
    """Validate setup before deployment"""
    print("🔍 Validating Drive webhook setup...")
    
    errors = []
    
    # Check service account file exists
    if not Path("service_account.json").exists():
        errors.append("❌ service_account.json not found")
    else:
        print("✅ Service account file exists")
    
    # Test each user/folder combination
    for user, folder_id in USERS.items():
        print(f"\n👤 Testing user: {user}")
        print(f"📁 Folder ID: {folder_id}")
        
        try:
            # Test service creation
            service = create_drive_service(user)
            print("✅ Drive service created successfully")
            
            # Test folder access
            if verify_folder_access(user, folder_id):
                print("✅ Folder access verified")
            else:
                errors.append(f"❌ Cannot access folder {folder_id} for {user}")
                
        except Exception as e:
            errors.append(f"❌ Service creation failed for {user}: {e}")
    
    # Summary
    print("\n" + "="*50)
    if errors:
        print(f"❌ Validation failed with {len(errors)} errors:")
        for error in errors:
            print(f"   {error}")
        sys.exit(1)
    else:
        print("✅ All validations passed! Ready for deployment.")

if __name__ == "__main__":
    main()