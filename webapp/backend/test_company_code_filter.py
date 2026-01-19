#!/usr/bin/env python3
"""
Test script to verify company code filtering functionality
"""

import requests
import os
import json

# Test configuration
API_URL = "http://localhost:8000"
TEST_FILE = "test_upload.xlsx"  # Make sure you have a test file with multiple company codes

def test_company_code_filter():
    """Test the company code filtering functionality"""
    
    # Check if test file exists
    if not os.path.exists(TEST_FILE):
        print(f"Error: Test file '{TEST_FILE}' not found")
        print("Please ensure you have a test Excel file with multiple company codes")
        return
    
    print(f"Testing company code filtering with file: {TEST_FILE}")
    print("-" * 60)
    
    # Test 1: Upload without company code filter
    print("\n1. Testing upload WITHOUT company code filter:")
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (TEST_FILE, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'input_header_start': 27,
            'input_data_start': 28,
            'template_header_start': 1,
            'template_data_start': 2
        }
        
        response = requests.post(f"{API_URL}/upload", files=files, data=data)
        
    if response.status_code == 200:
        result = response.json()
        print(f"Success: Job ID = {result['job_id']}")
        print(f"Message: {result['message']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
    
    print("\n" + "-" * 60)
    
    # Test 2: Upload with company code filter
    print("\n2. Testing upload WITH company code filter (Company Code = '1000'):")
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (TEST_FILE, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'input_header_start': 27,
            'input_data_start': 28,
            'template_header_start': 1,
            'template_data_start': 2,
            'company_code': '1000'  # Add company code filter
        }
        
        response = requests.post(f"{API_URL}/upload", files=files, data=data)
        
    if response.status_code == 200:
        result = response.json()
        job_id = result['job_id']
        print(f"Success: Job ID = {job_id}")
        print(f"Message: {result['message']}")
        
        # Wait a moment and check job status
        import time
        time.sleep(2)
        
        status_response = requests.get(f"{API_URL}/status/{job_id}")
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"\nJob Status: {status['status']}")
            if status.get('result'):
                print(f"Result details:")
                for key, value in status['result'].items():
                    print(f"  - {key}: {value}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
    
    print("\n" + "-" * 60)
    
    # Test 3: Extract company codes
    print("\n3. Testing extract company codes endpoint:")
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (TEST_FILE, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {'input_header_start': 27}
        
        response = requests.post(f"{API_URL}/extract-company-codes", files=files, data=data)
        
    if response.status_code == 200:
        result = response.json()
        print(f"Success: Found {result['total_count']} company codes")
        print(f"Company codes: {result['company_codes']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("Company Code Filter Test Script")
    print("=" * 60)
    test_company_code_filter()