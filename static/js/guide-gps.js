// Guide GPS Tracking Module
class GuideGPSTracker {
    constructor() {
        this.gpsEnabled = false;
        this.developerMode = false;
        this.watchId = null;
        this.guideMarker = null;
        this.lastUpdate = 0;
        this.updateThreshold = 10000; // 10 seconds minimum between updates
        this.accuracyThreshold = 100; // Only use positions with < 100m accuracy
        this.isUpdating = false;
        
        // Manual movement properties
        this.currentLat = null;
        this.currentLon = null;
        this.moveStep = 0.001; // Approximately 111 meters
        
        this.initializeControls();
    }
    
    initializeControls() {
        // Initialize GPS controls with null checks
        const toggleBackground = document.getElementById('toggleBackground');
        const gpsToggle = document.getElementById('gpsToggle');
        const updateLocationBtn = document.getElementById('updateLocationBtn');
        
        // Initialize developer mode controls
        const devModeBackground = document.getElementById('devModeBackground');
        const devModeToggle = document.getElementById('devModeToggle');
        
        if (toggleBackground) {
            toggleBackground.addEventListener('click', () => this.toggleGPS());
        }
        
        if (gpsToggle) {
            gpsToggle.addEventListener('change', () => this.toggleGPS());
        }
        
        if (updateLocationBtn) {
            updateLocationBtn.addEventListener('click', () => this.manualLocationUpdate());
        }
        
        if (devModeBackground) {
            devModeBackground.addEventListener('click', () => this.toggleDeveloperMode());
        }
        
        if (devModeToggle) {
            devModeToggle.addEventListener('change', () => this.toggleDeveloperMode());
        }
        
        // Initialize arrow controls
        this.initializeArrowControls();
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => this.stopGPSTracking());
        
        // Log initialization status
        console.log('Guide GPS controls initialized:', {
            toggleBackground: !!toggleBackground,
            gpsToggle: !!gpsToggle,
            updateLocationBtn: !!updateLocationBtn,
            devModeBackground: !!devModeBackground,
            devModeToggle: !!devModeToggle
        });
        
        // Debug logging for developer mode elements
        console.log('Developer mode elements check:', {
            devModeBackground: !!devModeBackground,
            devModeToggle: !!devModeToggle,
            devModeButton: !!document.getElementById('devModeButton'),
            gpsControls: !!document.getElementById('gpsControls'),
            manualControls: !!document.getElementById('manualControls'),
            modeIndicator: !!document.getElementById('modeIndicator'),
            modeText: !!document.getElementById('modeText')
        });
    }
    
    initializeArrowControls() {
        // Keyboard controls for manual movement
        document.addEventListener('keydown', (event) => {
            if (!this.developerMode) return;
            
            switch(event.key) {
                case 'ArrowUp':
                    event.preventDefault();
                    this.moveUp();
                    break;
                case 'ArrowDown':
                    event.preventDefault();
                    this.moveDown();
                    break;
                case 'ArrowLeft':
                    event.preventDefault();
                    this.moveLeft();
                    break;
                case 'ArrowRight':
                    event.preventDefault();
                    this.moveRight();
                    break;
            }
        });

        // Button controls for manual movement
        document.querySelectorAll('.arrow-key').forEach(button => {
            button.addEventListener('click', () => {
                if (!this.developerMode) return;
                
                const direction = button.getAttribute('data-direction');
                switch(direction) {
                    case 'up': this.moveUp(); break;
                    case 'down': this.moveDown(); break;
                    case 'left': this.moveLeft(); break;
                    case 'right': this.moveRight(); break;
                }
            });
        });
    }
    
    toggleDeveloperMode() {
        this.developerMode = !this.developerMode;
        
        const devModeToggle = document.getElementById('devModeToggle');
        const devModeBackground = document.getElementById('devModeBackground');
        const devModeButton = document.getElementById('devModeButton');
        const gpsControls = document.getElementById('gpsControls');
        const manualControls = document.getElementById('manualControls');
        const modeIndicator = document.getElementById('modeIndicator');
        const modeText = document.getElementById('modeText');
        
        if (devModeToggle) {
            devModeToggle.checked = this.developerMode;
        }
        
        if (devModeBackground && devModeButton) {
            if (this.developerMode) {
                devModeBackground.classList.remove('bg-gray-200');
                devModeBackground.classList.add('bg-guide-purple');
                devModeButton.style.transform = 'translateX(20px) translateY(2px)';
            } else {
                devModeBackground.classList.remove('bg-guide-purple');
                devModeBackground.classList.add('bg-gray-200');
                devModeButton.style.transform = 'translateX(2px) translateY(2px)';
            }
        }
        
        // Toggle control visibility
        if (gpsControls && manualControls) {
            if (this.developerMode) {
                gpsControls.classList.add('hidden');
                manualControls.classList.remove('hidden');
                // Stop GPS when entering developer mode
                if (this.gpsEnabled) {
                    this.toggleGPS();
                }
            } else {
                gpsControls.classList.remove('hidden');
                manualControls.classList.add('hidden');
            }
        }
        
        // Update mode indicator
        if (modeIndicator && modeText) {
            if (this.developerMode) {
                modeIndicator.classList.remove('bg-gray-400', 'bg-green-500');
                modeIndicator.classList.add('bg-guide-purple');
                modeText.textContent = 'Manual Mode';
            } else {
                modeIndicator.classList.remove('bg-guide-purple', 'bg-green-500');
                modeIndicator.classList.add('bg-gray-400');
                modeText.textContent = 'GPS Mode';
            }
        }
        
        console.log('Developer mode:', this.developerMode ? 'enabled' : 'disabled');
    }
    
    // Manual movement functions
    moveUp() { this.moveDirection(this.moveStep, 0); }
    moveDown() { this.moveDirection(-this.moveStep, 0); }
    moveLeft() { this.moveDirection(0, -this.moveStep); }
    moveRight() { this.moveDirection(0, this.moveStep); }
    
    moveDirection(latChange, lonChange) {
        // Initialize current position if not set
        if (this.currentLat === null || this.currentLon === null) {
            // Set default position (center of India)
            this.currentLat = 20.5937;
            this.currentLon = 78.9629;
        }
        
        this.currentLat += latChange;
        this.currentLon += lonChange;
        
        // Update location display and marker
        this.updateLocationDisplay(this.currentLat, this.currentLon);
        this.updateGuideMarkerOnMap(this.currentLat, this.currentLon);
        
        // Send location update to server
        this.updateGuideLocation(this.currentLat, this.currentLon);
    }
    
    // Coordinate validation utility for guides
    validateCoordinates(lat, lon) {
        if (lat == null || lon == null) {
            return "Location coordinates are missing";
        }
        
        if (isNaN(lat) || isNaN(lon)) {
            return "Location coordinates are invalid";
        }
        
        if (!isFinite(lat) || !isFinite(lon)) {
            return "Location coordinates are out of range";
        }
        
        if (lat < -90 || lat > 90) {
            return "Latitude must be between -90 and 90 degrees";
        }
        
        if (lon < -180 || lon > 180) {
            return "Longitude must be between -180 and 180 degrees";
        }
        
        return null; // Valid coordinates
    }

    async updateGuideLocation(latitude, longitude, accuracy = null) {
        // Validate coordinates before proceeding
        const validationError = this.validateCoordinates(latitude, longitude);
        if (validationError) {
            this.showLocationError(validationError);
            return false;
        }

        // Always update UI immediately (local map and display)
        this.updateLocationDisplay(latitude, longitude, accuracy);
        this.updateGuideMarkerOnMap(latitude, longitude);
        
        // Throttle server updates to prevent spam
        const now = Date.now();
        if (now - this.lastUpdate < this.updateThreshold) {
            console.log('Server update throttled - UI updated locally');
            return true;
        }
        
        // Filter server updates by accuracy if provided
        if (accuracy && accuracy > this.accuracyThreshold) {
            console.log(`Server update skipped due to low accuracy: ${accuracy}m - UI updated locally`);
            return true;
        }
        
        if (this.isUpdating) {
            console.log('Server update already in progress - UI updated locally');
            return true;
        }
        
        this.isUpdating = true;
        
        try {
            const response = await fetch('/guide/update_location', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude
                }),
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.lastUpdate = now;
                console.log('Guide location updated successfully on server');
                return true;
            } else if (response.status === 400) {
                // Handle validation errors from server
                const errorData = await response.json().catch(() => ({}));
                this.showLocationError(errorData.detail || 'Invalid location data');
                return false;
            } else if (response.status >= 500) {
                // Handle server errors
                this.showLocationError('Server temporarily unavailable. Please try again.');
                return false;
            } else {
                const error = await response.json().catch(() => ({}));
                console.error('Failed to update location on server:', error);
                this.showLocationError('Failed to update location: ' + (error.detail || 'Unknown error'));
                return false;
            }
        } catch (error) {
            console.error('Error updating location on server:', error);
            if (error.name === 'NetworkError' || error.message.includes('Failed to fetch')) {
                this.showLocationError('Connection lost. Please try again.');
            } else {
                this.showLocationError('Unexpected error occurred. Please try again.');
            }
            return false;
        } finally {
            this.isUpdating = false;
        }
    }
    
    updateLocationDisplay(lat, lon, accuracy) {
        const latSpan = document.getElementById('currentLat');
        const lonSpan = document.getElementById('currentLon');
        const lastUpdatedSpan = document.getElementById('lastUpdated');
        const accuracySpan = document.getElementById('accuracy');
        const display = document.getElementById('currentLocationDisplay');
        
        if (latSpan) latSpan.textContent = lat.toFixed(6);
        if (lonSpan) lonSpan.textContent = lon.toFixed(6);
        if (lastUpdatedSpan) lastUpdatedSpan.textContent = new Date().toLocaleTimeString();
        if (accuracySpan) accuracySpan.textContent = accuracy ? `±${Math.round(accuracy)}m` : 'Unknown';
        if (display) display.classList.remove('hidden');
    }
    
    updateGuideMarkerOnMap(lat, lon) {
        // Check if map and Leaflet are available
        if (typeof map === 'undefined' || typeof L === 'undefined') {
            console.warn('Map or Leaflet not available for guide marker update');
            return;
        }
        
        if (this.guideMarker) {
            // Update existing marker
            this.guideMarker.setLatLng([lat, lon]);
            this.guideMarker.setPopupContent(`<b>Your Location</b><br>Guide Position<br>Updated: ${new Date().toLocaleTimeString()}`);
        } else {
            // Check if there's already a guide marker in the global guideMarkers object
            // to avoid duplication (assuming current user ID is available)
            if (typeof guideMarkers !== 'undefined' && window.currentUserId && guideMarkers[window.currentUserId]) {
                // Reuse existing marker
                this.guideMarker = guideMarkers[window.currentUserId];
                this.guideMarker.setLatLng([lat, lon]);
                this.guideMarker.setPopupContent(`<b>Your Location</b><br>Guide Position<br>Updated: ${new Date().toLocaleTimeString()}`);
                console.log('Reusing existing guide marker');
            } else {
                // Create new guide marker with special styling for self
                const selfGuideIcon = L.divIcon({
                    html: '<div style="background: #DC3545; width: 26px; height: 26px; border-radius: 50%; border: 3px solid white; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">G</div>',
                    className: 'guide-self-marker',
                    iconSize: [32, 32],
                    iconAnchor: [16, 16]
                });
                
                // Add to guideLayer if available, otherwise directly to map
                const targetMap = (typeof guideLayer !== 'undefined') ? guideLayer : map;
                this.guideMarker = L.marker([lat, lon], {icon: selfGuideIcon})
                    .addTo(targetMap)
                    .bindPopup('<b>Your Location</b><br>Guide Position<br>Updated: ' + new Date().toLocaleTimeString());
                    
                // Register marker to prevent future duplication
                if (typeof guideMarkers !== 'undefined' && window.currentUserId) {
                    guideMarkers[window.currentUserId] = this.guideMarker;
                }
                    
                // Center map on guide's location when first created
                if (map.getZoom() < 13) {
                    map.setView([lat, lon], 13);
                }
                
                console.log('Created new guide self-marker');
            }
        }
    }
    
    updateGPSStatus(status, color, text) {
        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        if (indicator) {
            indicator.className = `w-3 h-3 rounded-full ${color}`;
            if (status === 'active') {
                indicator.classList.add('animate-pulse');
            } else {
                indicator.classList.remove('animate-pulse');
            }
        }
        
        if (statusText) {
            statusText.textContent = text;
        }
    }
    
    toggleGPS() {
        const toggle = document.getElementById('gpsToggle');
        const background = document.getElementById('toggleBackground');
        const button = document.getElementById('toggleButton');
        
        this.gpsEnabled = !this.gpsEnabled;
        if (toggle) toggle.checked = this.gpsEnabled;
        
        if (this.gpsEnabled) {
            // Enable GPS tracking
            if (background) {
                background.classList.remove('bg-gray-200');
                background.classList.add('bg-green-500');
            }
            if (button) {
                button.classList.remove('translate-x-0.5');
                button.classList.add('translate-x-5');
            }
            
            this.startGPSTracking();
        } else {
            // Disable GPS tracking
            if (background) {
                background.classList.remove('bg-green-500');
                background.classList.add('bg-gray-200');
            }
            if (button) {
                button.classList.remove('translate-x-5');
                button.classList.add('translate-x-0.5');
            }
            
            this.stopGPSTracking();
        }
    }
    
    startGPSTracking() {
        if (!navigator.geolocation) {
            this.showNotification('Geolocation is not supported by this browser', 'error');
            this.updateGPSStatus('error', 'bg-red-500', 'Not Supported');
            return;
        }
        
        this.updateGPSStatus('active', 'bg-green-500', 'Active');
        
        const options = {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 30000 // 30 seconds
        };
        
        // Get initial position
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const accuracy = position.coords.accuracy;
                
                this.updateGuideLocation(lat, lon, accuracy);
                this.showNotification('GPS tracking started successfully', 'success');
                
                // Start continuous tracking after successful initial position
                this.startContinuousTracking(options);
            },
            (error) => {
                this.handleGeolocationError(error);
                // Properly reset without creating infinite loop
                this.resetGPSState();
            },
            options
        );
    }
    
    startContinuousTracking(options) {
        if (!this.gpsEnabled) return;
        
        this.watchId = navigator.geolocation.watchPosition(
            (position) => {
                if (!this.gpsEnabled) return; // Double check
                
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const accuracy = position.coords.accuracy;
                
                this.updateGuideLocation(lat, lon, accuracy);
            },
            (error) => {
                console.error('GPS watch error:', error);
                this.updateGPSStatus('error', 'bg-red-500', 'Error');
                
                // Don't stop tracking for minor errors, just log them
                if (error.code === 1) { // Permission denied - stop tracking
                    this.resetGPSState();
                    this.showNotification('Location permission denied', 'error');
                }
            },
            {
                ...options,
                timeout: 30000 // Longer timeout for continuous tracking
            }
        );
    }
    
    stopGPSTracking() {
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
        this.gpsEnabled = false;
        this.updateGPSStatus('inactive', 'bg-gray-400', 'Inactive');
        this.showNotification('GPS tracking stopped', 'info');
    }
    
    resetGPSState() {
        // Stop any active tracking
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
        
        // Reset state
        this.gpsEnabled = false;
        
        // Reset UI elements safely
        const toggle = document.getElementById('gpsToggle');
        const background = document.getElementById('toggleBackground');
        const button = document.getElementById('toggleButton');
        
        if (toggle) toggle.checked = false;
        if (background) {
            background.classList.remove('bg-green-500');
            background.classList.add('bg-gray-200');
        }
        if (button) {
            button.classList.remove('translate-x-5');
            button.classList.add('translate-x-0.5');
        }
        
        this.updateGPSStatus('inactive', 'bg-gray-400', 'Inactive');
    }
    
    manualLocationUpdate() {
        if (!navigator.geolocation) {
            this.showNotification('Geolocation is not supported by this browser', 'error');
            return;
        }
        
        const button = document.getElementById('updateLocationBtn');
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
        }
        
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const accuracy = position.coords.accuracy;
                
                this.updateGuideLocation(lat, lon, accuracy).then((success) => {
                    if (button) {
                        button.disabled = false;
                        button.innerHTML = '<i class="fas fa-crosshairs"></i> Update Location Now';
                    }
                    
                    if (success) {
                        this.showNotification('Location updated successfully', 'success');
                    }
                });
            },
            (error) => {
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-crosshairs"></i> Update Location Now';
                }
                this.handleGeolocationError(error);
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0 // Force fresh location
            }
        );
    }
    
    handleGeolocationError(error) {
        console.error('Geolocation error:', error);
        let message = 'Location access failed';
        
        switch (error.code) {
            case 1:
                message = 'Location access denied by user';
                break;
            case 2:
                message = 'Location unavailable';
                break;
            case 3:
                message = 'Location request timeout';
                break;
            default:
                message = 'Unknown location error';
        }
        
        this.showNotification(message, 'error');
        this.updateGPSStatus('error', 'bg-red-500', 'Error');
    }
    
    showLocationError(message) {
        // Use the existing notification system for location errors
        this.showNotification(`📍 Location Error: ${message}`, 'error');
    }

    showNotification(message, type = 'info') {
        // Remove any existing notifications
        const existingNotifications = document.querySelectorAll('.gps-notification');
        existingNotifications.forEach(n => n.remove());
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'gps-notification fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full max-w-sm';
        
        const colors = {
            success: 'bg-green-500 text-white',
            error: 'bg-red-500 text-white',
            info: 'bg-blue-500 text-white',
            warning: 'bg-yellow-500 text-black'
        };
        
        notification.className += ` ${colors[type] || colors.info}`;
        notification.innerHTML = `
            <div class="flex items-center gap-2">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'}"></i>
                <span class="text-sm">${message}</span>
                <button class="ml-2 text-current opacity-70 hover:opacity-100" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.classList.add('translate-x-full');
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 5000);
    }
}

// Initialize GPS tracker when DOM is ready
let guideGPS = null;

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the guide dashboard
    if (document.getElementById('gpsToggle')) {
        guideGPS = new GuideGPSTracker();
        console.log('Guide GPS tracker initialized');
    }
});