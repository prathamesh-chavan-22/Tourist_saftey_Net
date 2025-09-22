// Global variables (to be set by template)
let tourist, geofence, currentUserRole, isAdmin;

// Current position
let currentLat, currentLon;
const moveStep = 0.001; // Approximately 111 meters

// Map and markers
let map, geofenceCircle, touristMarker;

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
    const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/location`);
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'location_update' && data.tourist_id === tourist.id) {
            updateStatus(data);
        }
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

async function updateLocation() {
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
        } else if (response.status === 403) {
            // Handle 403 Forbidden - Admin trying to update location
            showAdminErrorMessage();
        } else {
            console.error('Failed to update location:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('Error updating location:', error);
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