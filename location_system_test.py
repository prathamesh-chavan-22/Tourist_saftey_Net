#!/usr/bin/env python3
"""
Simplified Location Tracking System Tests using available tools
"""

import json
import sys
import os
from datetime import datetime

def test_html_structure():
    """Test HTML template structure for GPS controls"""
    print("🧪 Testing Guide Dashboard GPS Controls Structure")
    
    try:
        with open('templates/guide_dashboard.html', 'r') as f:
            guide_template = f.read()
        
        # Test for GPS control elements
        gps_elements = [
            ('id="gpsToggle"', 'GPS Toggle Checkbox'),
            ('id="toggleBackground"', 'Toggle Background'),
            ('id="statusIndicator"', 'Status Indicator'),
            ('id="statusText"', 'Status Text'),
            ('id="updateLocationBtn"', 'Manual Update Button'),
            ('id="currentLocationDisplay"', 'Current Location Display'),
            ('id="currentLat"', 'Latitude Display'),
            ('id="currentLon"', 'Longitude Display'),
            ('id="lastUpdated"', 'Last Updated Display'),
            ('id="accuracy"', 'Accuracy Display'),
        ]
        
        results = []
        for element_id, description in gps_elements:
            if element_id in guide_template:
                results.append(f"✅ {description}: Found")
            else:
                results.append(f"❌ {description}: Missing")
        
        return results
        
    except FileNotFoundError:
        return ["❌ Guide dashboard template not found"]

def test_javascript_structure():
    """Test JavaScript GPS functionality"""
    print("🧪 Testing Guide GPS JavaScript Implementation")
    
    try:
        with open('static/js/guide-gps.js', 'r') as f:
            gps_js = f.read()
        
        # Test for key functions and features
        js_features = [
            ('class GuideGPSTracker', 'GPS Tracker Class'),
            ('validateCoordinates', 'Coordinate Validation Function'),
            ('toggleGPS', 'GPS Toggle Function'),
            ('updateLocationDisplay', 'Location Display Update'),
            ('manualLocationUpdate', 'Manual Location Update'),
            ('startGPSTracking', 'GPS Tracking Start'),
            ('stopGPSTracking', 'GPS Tracking Stop'),
            ('updateGuideLocation', 'Guide Location Update'),
            ('updateGPSStatus', 'GPS Status Update'),
            ('showLocationError', 'Error Display Function'),
            ('navigator.geolocation', 'Geolocation API Usage'),
            ('/guide/update_location', 'API Endpoint Reference'),
        ]
        
        results = []
        for feature, description in js_features:
            if feature in gps_js:
                results.append(f"✅ {description}: Implemented")
            else:
                results.append(f"❌ {description}: Missing")
        
        return results
        
    except FileNotFoundError:
        return ["❌ Guide GPS JavaScript file not found"]

def test_map_structure():
    """Test tourist map template structure"""
    print("🧪 Testing Tourist Map Structure")
    
    try:
        with open('templates/map.html', 'r') as f:
            map_template = f.read()
        
        # Test for guide visibility elements
        guide_elements = [
            ('id="guideInfoPanel"', 'Guide Information Panel'),
            ('id="guideName"', 'Guide Name Display'),
            ('id="guideStatus"', 'Guide Status Display'),
            ('id="guideCoordinates"', 'Guide Coordinates Display'),
            ('id="guideUpdated"', 'Guide Last Updated Display'),
            ('purple "G" marker', 'Purple Guide Marker Reference'),
            ('guide_location_update', 'Guide Location Update Handler'),
        ]
        
        results = []
        for element, description in guide_elements:
            if element in map_template:
                results.append(f"✅ {description}: Found")
            else:
                results.append(f"❌ {description}: Missing")
        
        return results
        
    except FileNotFoundError:
        return ["❌ Map template not found"]

def test_websocket_structure():
    """Test WebSocket implementation structure"""
    print("🧪 Testing WebSocket Implementation")
    
    try:
        with open('websocket_manager.py', 'r') as f:
            ws_content = f.read()
        
        # Test WebSocket features
        ws_features = [
            ('class ConnectionManager', 'Connection Manager Class'),
            ('async def connect', 'Connection Method'),
            ('async def broadcast_location_update', 'Location Broadcast'),
            ('async def send_to_trip', 'Trip-specific Messaging'),
            ('AuthenticatedConnection', 'Authenticated Connection Class'),
            ('guide_location_update', 'Guide Location Update Type'),
        ]
        
        results = []
        for feature, description in ws_features:
            if feature in ws_content:
                results.append(f"✅ {description}: Implemented")
            else:
                results.append(f"❌ {description}: Missing")
        
        return results
        
    except FileNotFoundError:
        return ["❌ WebSocket manager file not found"]

def test_coordinate_validation_schemas():
    """Test coordinate validation in schemas"""
    print("🧪 Testing Coordinate Validation Schemas")
    
    try:
        with open('schemas.py', 'r') as f:
            schemas_content = f.read()
        
        # Test validation features
        validation_features = [
            ('class GuideLocationUpdate', 'Guide Location Update Schema'),
            ('def validate_coordinates', 'Coordinate Validation Method'),
            ('math.isnan', 'NaN Check'),
            ('math.isinf', 'Infinity Check'),
            ('-90 <= self.latitude <= 90', 'Latitude Range Check'),
            ('-180 <= self.longitude <= 180', 'Longitude Range Check'),
            ('ValueError', 'Error Handling'),
        ]
        
        results = []
        for feature, description in validation_features:
            if feature in schemas_content:
                results.append(f"✅ {description}: Implemented")
            else:
                results.append(f"❌ {description}: Missing")
        
        return results
        
    except FileNotFoundError:
        return ["❌ Schemas file not found"]

def test_guide_routes():
    """Test guide routing implementation"""
    print("🧪 Testing Guide Route Implementation")
    
    try:
        with open('routers/guide.py', 'r') as f:
            guide_routes = f.read()
        
        # Test route features
        route_features = [
            ('@router.post("/update_location")', 'Location Update Endpoint'),
            ('GuideLocationUpdate', 'Schema Usage'),
            ('validate_coordinates()', 'Validation Call'),
            ('WebSocket', 'WebSocket Integration'),
            ('require_guide', 'Guide Authentication'),
            ('GuideLocation', 'Database Model Usage'),
        ]
        
        results = []
        for feature, description in route_features:
            if feature in guide_routes:
                results.append(f"✅ {description}: Implemented")
            else:
                results.append(f"❌ {description}: Missing")
        
        return results
        
    except FileNotFoundError:
        return ["❌ Guide routes file not found"]

def generate_comprehensive_report():
    """Generate comprehensive test report"""
    print("🚀 COMPREHENSIVE LOCATION TRACKING SYSTEM TEST REPORT")
    print("=" * 80)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    test_results = {}
    
    # Run all tests
    test_functions = [
        ('Guide Dashboard GPS Controls', test_html_structure),
        ('Guide GPS JavaScript', test_javascript_structure),
        ('Tourist Map Structure', test_map_structure),
        ('WebSocket Implementation', test_websocket_structure),
        ('Coordinate Validation', test_coordinate_validation_schemas),
        ('Guide Routes', test_guide_routes),
    ]
    
    for test_name, test_func in test_functions:
        print(f"\n{test_name.upper()}")
        print("-" * len(test_name))
        results = test_func()
        test_results[test_name] = results
        
        for result in results:
            print(f"  {result}")
    
    # Generate summary
    print(f"\n{'SUMMARY REPORT'.center(80, '=')}")
    
    total_tests = 0
    total_passed = 0
    
    for test_name, results in test_results.items():
        passed = sum(1 for r in results if r.startswith('✅'))
        total = len(results)
        total_tests += total
        total_passed += passed
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        print(f"{test_name}: {passed}/{total} ({pass_rate:.1f}%)")
    
    overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"\nOVERALL: {total_passed}/{total_tests} ({overall_pass_rate:.1f}%)")
    
    # Detailed findings
    print(f"\n{'DETAILED FINDINGS'.center(80, '=')}")
    
    print("\n🎯 KEY STRENGTHS IDENTIFIED:")
    for test_name, results in test_results.items():
        passed_items = [r for r in results if r.startswith('✅')]
        if passed_items:
            print(f"\n{test_name}:")
            for item in passed_items[:3]:  # Show top 3
                print(f"  {item}")
    
    print("\n⚠️ AREAS NEEDING ATTENTION:")
    for test_name, results in test_results.items():
        failed_items = [r for r in results if r.startswith('❌')]
        if failed_items:
            print(f"\n{test_name}:")
            for item in failed_items:
                print(f"  {item}")
    
    return {
        'total_tests': total_tests,
        'total_passed': total_passed,
        'pass_rate': overall_pass_rate,
        'results': test_results
    }

if __name__ == "__main__":
    report = generate_comprehensive_report()
    
    # Export detailed report
    with open('location_tracking_test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: location_tracking_test_report.json")
    
    # Exit with appropriate code
    exit_code = 0 if report['pass_rate'] > 80 else 1
    sys.exit(exit_code)