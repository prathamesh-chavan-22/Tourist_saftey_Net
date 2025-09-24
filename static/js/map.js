// Global variables (to be set by template)
let tourist, geofence, currentUserRole, isAdmin;
let ws; // Global WebSocket variable

// Current position
let currentLat, currentLon;
const moveStep = 0.001; // Approximately 111 meters

// Map and markers
let map, geofenceCircle, touristMarker, guideMarker;

// Initialize map with provided data
function initializeMap(touristData, geofenceData, userRole) {
    tourist = touristData;
    geofence = geofenceData;
    currentUserRole = userRole;
    isAdmin = currentUserRole === "admin";
    
    currentLat = tourist.lat;
    currentLon = tourist.lon;

    // Initialize map
    map = L.map('map').setView([tourist.lat, tourist.lon], 15);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Add geofence circle using template data
    geofenceCircle = L.circle([geofence.centerLat, geofence.centerLon], {
        color: 'green',
        fillColor: '#90EE90',
        fillOpacity: 0.3,
        radius: geofence.radius,
        weight: 3
    }).addTo(map).bindPopup(`<b>Safe Zone</b><br>${geofence.name}<br>Radius: ${geofence.radius}m`);

    // Add tourist marker
    touristMarker = L.marker([tourist.lat, tourist.lon], {
        draggable: false
    }).addTo(map).bindPopup(`<b>${tourist.name}</b><br>Status: ${tourist.status}`);

    // Initialize WebSocket connection
    initializeWebSocket();
    
    // Initialize controls if not admin
    if (!isAdmin) {
        initializeControls();
    }
    
    // Initialize status display
    const insideFence = tourist.status === 'Safe';
    updateStatusDisplay(tourist.status, insideFence);

    // Set focus on window to capture keyboard events
    window.focus();
}

// WebSocket connection
function initializeWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    
    // Use cookie-based authentication (no token in URL for security)
    ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/location`);
    
    ws.onopen = function(event) {
        console.log('WebSocket connection established for tourist map');
    };
    
    ws.onmessage = function(event) {
        console.log('WebSocket message received:', event.data);
        const data = JSON.parse(event.data);
        
        if (data.type === 'location_update' && data.tourist_id === tourist.id) {
            console.log('Updating tourist status via WebSocket:', data);
            updateStatus(data);
            
            // Also update coordinates display and marker position
            currentLat = data.latitude;
            currentLon = data.longitude;
            touristMarker.setLatLng([data.latitude, data.longitude]);
            map.setView([data.latitude, data.longitude]);
            document.getElementById('coordinates').textContent = 
                `${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}`;
        } else if (data.type === 'guide_location_update') {
            console.log('Received guide location update:', data);
            updateGuideLocation(data);
        }
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = function(event) {
        console.log('WebSocket connection closed:', event.code, event.reason);
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
            console.log('Attempting to reconnect WebSocket...');
            initializeWebSocket();
        }, 3000);
    };
}

// Movement functions
function moveUp() { moveDirection(moveStep, 0); }
function moveDown() { moveDirection(-moveStep, 0); }
function moveLeft() { moveDirection(0, -moveStep); }
function moveRight() { moveDirection(0, moveStep); }

function moveDirection(latChange, lonChange) {
    currentLat += latChange;
    currentLon += lonChange;
    
    // Update marker position
    touristMarker.setLatLng([currentLat, currentLon]);
    map.setView([currentLat, currentLon]);
    
    // Update coordinates display
    document.getElementById('coordinates').textContent = 
        `${currentLat.toFixed(4)}, ${currentLon.toFixed(4)}`;
    
    // Send location update to server
    updateLocation();
}

// Coordinate validation utility
function validateCoordinates(lat, lon) {
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

async function updateLocation() {
    // Validate coordinates before sending
    const validationError = validateCoordinates(currentLat, currentLon);
    if (validationError) {
        showLocationError(validationError);
        return;
    }
    
    try {
        const response = await fetch('/update_location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tourist_id: tourist.id,
                latitude: currentLat,
                longitude: currentLon
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            updateStatusDisplay(result.status, result.inside_fence);
            hideLocationError(); // Hide any previous errors
        } else if (response.status === 403) {
            // Handle 403 Forbidden - Admin trying to update location
            showAdminErrorMessage();
        } else if (response.status === 400) {
            // Handle validation errors from server
            const errorData = await response.json().catch(() => ({}));
            showLocationError(errorData.detail || 'Invalid location data');
        } else if (response.status >= 500) {
            // Handle server errors
            showLocationError('Server temporarily unavailable. Please try again.');
        } else {
            console.error('Failed to update location:', response.status, response.statusText);
            showLocationError('Failed to update location. Please try again.');
        }
    } catch (error) {
        console.error('Error updating location:', error);
        if (error.name === 'NetworkError' || error.message.includes('Failed to fetch')) {
            showLocationError('Connection lost. Attempting to reconnect...');
            // Attempt reconnection
            setTimeout(() => updateLocation(), 3000);
        } else {
            showLocationError('Unexpected error occurred. Please refresh the page.');
        }
    }
}

function showAdminErrorMessage() {
    // Create or show error message for admin users
    let errorDiv = document.getElementById('adminError');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'adminError';
        errorDiv.className = 'alert alert-warning';
        errorDiv.innerHTML = '⚠️ <strong>Access Denied:</strong> Admin users cannot control tourist movement.';
        document.getElementById('alertContainer').appendChild(errorDiv);
    }
    errorDiv.style.display = 'block';
    
    // Hide error after 5 seconds
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

function showLocationError(message) {
    // Create or show location error message
    let errorDiv = document.getElementById('locationError');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'locationError';
        errorDiv.className = 'alert alert-warning';
        document.getElementById('alertContainer').appendChild(errorDiv);
    }
    errorDiv.innerHTML = `🚨 <strong>Location Error:</strong> ${message}`;
    errorDiv.style.display = 'block';
    
    // Auto-hide informational errors after 8 seconds
    if (!message.includes('Connection lost') && !message.includes('Server temporarily unavailable')) {
        setTimeout(() => {
            hideLocationError();
        }, 8000);
    }
}

function hideLocationError() {
    const errorDiv = document.getElementById('locationError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
}

function updateStatus(data) {
    updateStatusDisplay(data.status, data.inside_fence);
    touristMarker.setPopupContent(`<b>${data.name}</b><br>Status: ${data.status}`);
}

function updateStatusDisplay(status, insideFence) {
    const statusElement = document.getElementById('status');
    statusElement.textContent = status;
    statusElement.className = `status-${status.toLowerCase()}`;
    
    // Show/hide alerts
    const warningAlert = document.getElementById('warningAlert');
    const safeAlert = document.getElementById('safeAlert');
    
    if (insideFence) {
        warningAlert.style.display = 'none';
        safeAlert.style.display = 'block';
    } else {
        warningAlert.style.display = 'block';
        safeAlert.style.display = 'none';
    }
}

// Initialize controls for non-admin users
function initializeControls() {
    // Keyboard controls
    document.addEventListener('keydown', function(event) {
        switch(event.key) {
            case 'ArrowUp':
                event.preventDefault();
                moveUp();
                break;
            case 'ArrowDown':
                event.preventDefault();
                moveDown();
                break;
            case 'ArrowLeft':
                event.preventDefault();
                moveLeft();
                break;
            case 'ArrowRight':
                event.preventDefault();
                moveRight();
                break;
        }
    });

    // Button controls
    document.querySelectorAll('.arrow-key').forEach(button => {
        button.addEventListener('click', function() {
            const direction = this.getAttribute('data-direction');
            switch(direction) {
                case 'up': moveUp(); break;
                case 'down': moveDown(); break;
                case 'left': moveLeft(); break;
                case 'right': moveRight(); break;
            }
        });
    });
}

// Guide location update function
function updateGuideLocation(data) {
    if (data.latitude == null || data.longitude == null) {
        console.warn('Invalid guide location data:', data);
        return;
    }
    
    // Update guide info panel if it exists
    updateGuideInfoPanel(data);
    
    if (guideMarker) {
        // Update existing guide marker
        guideMarker.setLatLng([data.latitude, data.longitude]);
        guideMarker.setPopupContent(
            `<b>${data.guide_name}</b><br>Role: Your Guide<br>Updated: ${new Date(data.timestamp).toLocaleTimeString()}`
        );
    } else {
        // Create new guide marker with special styling
        const guideIcon = L.divIcon({
            html: '<div style="background: #6C5CE7; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">G</div>',
            className: 'guide-marker',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
        
        guideMarker = L.marker([data.latitude, data.longitude], {icon: guideIcon})
            .addTo(map)
            .bindPopup(`<b>${data.guide_name}</b><br>Role: Your Guide<br>Updated: ${new Date(data.timestamp).toLocaleTimeString()}`);
            
        console.log('Created guide marker for:', data.guide_name);
    }
}

// Update guide info panel
function updateGuideInfoPanel(data) {
    const guideNameElement = document.getElementById('guideName');
    const guideStatusElement = document.getElementById('guideStatus');
    const guideCoordinatesElement = document.getElementById('guideCoordinates');
    const guideUpdatedElement = document.getElementById('guideUpdated');
    const guideInfoPanel = document.getElementById('guideInfoPanel');
    
    if (guideNameElement) guideNameElement.textContent = data.guide_name;
    if (guideStatusElement) guideStatusElement.textContent = 'Active';
    if (guideCoordinatesElement) {
        guideCoordinatesElement.textContent = `${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}`;
    }
    if (guideUpdatedElement) {
        guideUpdatedElement.textContent = new Date(data.timestamp).toLocaleTimeString();
    }
    if (guideInfoPanel) {
        guideInfoPanel.style.display = 'block';
    }
}