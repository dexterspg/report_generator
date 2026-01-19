#!/usr/bin/env python3
"""
Test script to debug the company code filtering issue
"""

import requests
import sys
import os

# Configuration
BASE_URL = "http://localhost:8000"
TEST_FILE_PATH = sys.argv[1] if len(sys.argv) > 1 else None

if not TEST_FILE_PATH or not os.path.exists(TEST_FILE_PATH):
    print("Usage: python test_upload.py <path_to_excel_file>")
    sys.exit(1)

def test_extract_company_codes():
    """Test extracting company codes from the file"""
    print("\n1. Testing company code extraction...")
    
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {'file': (os.path.basename(TEST_FILE_PATH), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {'input_header_start': '27'}
        
        response = requests.post(f"{BASE_URL}/extract-company-codes", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Found {result['total_count']} company codes: {result['company_codes']}")
            return result['company_codes']
        else:
            print(f"✗ Error: {response.text}")
            return []

def test_upload_with_filter(company_code):
    """Test uploading with a specific company code filter"""
    print(f"\n2. Testing upload with company code filter: '{company_code}'...")
    
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {'file': (os.path.basename(TEST_FILE_PATH), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'input_header_start': '27',
            'input_data_start': '28',
            'template_header_start': '1',
            'template_data_start': '2',
            'company_code': company_code
        }
        
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Upload successful. Job ID: {result['job_id']}")
            return result['job_id']
        else:
            print(f"✗ Error: {response.text}")
            return None

def test_upload_without_filter():
    """Test uploading without company code filter"""
    print(f"\n3. Testing upload without company code filter...")
    
    with open(TEST_FILE_PATH, 'rb') as f:
        files = {'file': (os.path.basename(TEST_FILE_PATH), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'input_header_start': '27',
            'input_data_start': '28',
            'template_header_start': '1',
            'template_data_start': '2'
        }
        
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Upload successful. Job ID: {result['job_id']}")
            return result['job_id']
        else:
            print(f"✗ Error: {response.text}")
            return None

def check_job_status(job_id):
    """Check the status of a processing job"""
    print(f"\n4. Checking job status for: {job_id}")
    
    import time
    max_attempts = 30
    
    for i in range(max_attempts):
        response = requests.get(f"{BASE_URL}/status/{job_id}")
        
        if response.status_code == 200:
            status = response.json()
            print(f"   Status: {status['status']}")
            
            if status['status'] == 'completed':
                print("✓ Processing completed successfully!")
                if status.get('result'):
                    print(f"   Result: {status['result']}")
                return True
            elif status['status'] == 'failed':
                print(f"✗ Processing failed: {status.get('error', 'Unknown error')}")
                return False
            else:
                time.sleep(1)
        else:
            print(f"✗ Error checking status: {response.text}")
            return False
    
    print("✗ Timeout waiting for job to complete")
    return False

def main():
    print(f"Testing with file: {TEST_FILE_PATH}")
    print("=" * 60)
    
    # Test 1: Extract company codes
    company_codes = test_extract_company_codes()
    
    if company_codes:
        # Test 2: Upload with first company code
        first_code = company_codes[0]
        job_id = test_upload_with_filter(first_code)
        
        if job_id:
            check_job_status(job_id)
    
    # Test 3: Upload without filter
    job_id = test_upload_without_filter()
    if job_id:
        check_job_status(job_id)

if __name__ == "__main__":
    main()