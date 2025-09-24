// Initialize map centered on India
const map = L.map('map').setView([20.5937, 78.9629], 5);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Add all Indian tourist places
const touristPlaces = [
    {id: 1, name: "Taj Mahal, Agra", lat: 27.1751, lon: 78.0421, radius: 500},
    {id: 2, name: "Red Fort, Delhi", lat: 28.6562, lon: 77.2410, radius: 400},
    {id: 3, name: "Gateway of India, Mumbai", lat: 18.9220, lon: 72.8347, radius: 300},
    {id: 4, name: "Hawa Mahal, Jaipur", lat: 26.9239, lon: 75.8267, radius: 300},
    {id: 5, name: "Golden Temple, Amritsar", lat: 31.6200, lon: 74.8765, radius: 400},
    {id: 6, name: "India Gate, New Delhi", lat: 28.6129, lon: 77.2295, radius: 400},
    {id: 7, name: "Mysore Palace, Mysore", lat: 12.3051, lon: 76.6551, radius: 400}
];

// Add geofence circles for all tourist places
touristPlaces.forEach(place => {
    L.circle([place.lat, place.lon], {
        color: 'green',
        fillColor: '#90EE90',
        fillOpacity: 0.2,
        radius: place.radius
    }).addTo(map).bindPopup(`<b>${place.name}</b><br>Safe Zone: ${place.radius}m radius`);
});

// Add tourist and guide markers - this will be populated by template data
const touristMarkers = {};
const guideMarkers = {};

// Create custom icons for different marker types
const touristIcon = L.divIcon({
    html: '<div style="background: #007BFF; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px;">T</div>',
    className: 'custom-div-icon',
    iconSize: [24, 24],
    iconAnchor: [12, 12]
});

const guideIcon = L.divIcon({
    html: '<div style="background: #6C5CE7; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px;">G</div>',
    className: 'custom-div-icon',
    iconSize: [24, 24],
    iconAnchor: [12, 12]
});

// Create layer groups for tourists and guides
const touristLayer = L.layerGroup().addTo(map);
const guideLayer = L.layerGroup().addTo(map);

// Layer control
const overlayMaps = {
    "Tourists": touristLayer,
    "Guides": guideLayer
};
L.control.layers(null, overlayMaps).addTo(map);

// Function to initialize tourist markers from template data
function initializeTouristMarkers(tourists) {
    tourists.forEach(tourist => {
        const marker = L.marker([tourist.last_lat, tourist.last_lon], {icon: touristIcon})
            .addTo(touristLayer)
            .bindPopup(`<b>${tourist.name}</b><br>Status: ${tourist.status}<br>Trip ID: ${tourist.trip_id}`);
        // Use tourist.id but store it as the same key that WebSocket updates will use
        touristMarkers[tourist.id] = marker;
        console.log(`Initialized tourist marker for ID: ${tourist.id}`);
    });
}

// Function to initialize guide markers from template data
function initializeGuideMarkers(guides) {
    guides.forEach(guide => {
        const marker = L.marker([guide.last_lat, guide.last_lon], {icon: guideIcon})
            .addTo(guideLayer)
            .bindPopup(`<b>${guide.name}</b><br>Role: Guide<br>Assigned Tourists: ${guide.assigned_tourist_count}<br>Updated: ${new Date(guide.updated_at).toLocaleTimeString()}`);
        guideMarkers[guide.id] = marker;
        console.log(`Initialized guide marker for ID: ${guide.id}`);
    });
}

// WebSocket connection for live updates
function initializeDashboardWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    
    // Use cookie-based authentication (no token in URL for security)
    const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/location`);

    ws.onopen = function(event) {
        console.log('WebSocket connection established for dashboard');
    };

    ws.onmessage = function(event) {
        console.log('Dashboard WebSocket message received:', event.data);
        const data = JSON.parse(event.data);
        if (data.type === 'location_update') {
            console.log('Updating tourist on dashboard:', data);
            updateTouristOnMap(data);
            updateTouristInTable(data);
        } else if (data.type === 'tourist_status_change') {
            console.log('Tourist status change:', data);
            handleTouristStatusChange(data);
        } else if (data.type === 'guide_location_update') {
            console.log('Updating guide location on dashboard:', data);
            updateGuideOnMap(data);
        }
    };

    ws.onerror = function(error) {
        console.error('Dashboard WebSocket error:', error);
    };

    ws.onclose = function(event) {
        console.log('Dashboard WebSocket connection closed:', event.code, event.reason);
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
            console.log('Attempting to reconnect dashboard WebSocket...');
            initializeDashboardWebSocket();
        }, 3000);
    };
}

// Initialize WebSocket connection
initializeDashboardWebSocket();

function updateTouristOnMap(data) {
    if (touristMarkers[data.tourist_id]) {
        touristMarkers[data.tourist_id].setLatLng([data.latitude, data.longitude]);
        touristMarkers[data.tourist_id].setPopupContent(`<b>${data.name}</b><br>Status: ${data.status}<br>Trip ID: ${data.trip_id}`);
    } else {
        const marker = L.marker([data.latitude, data.longitude], {icon: touristIcon})
            .addTo(touristLayer)
            .bindPopup(`<b>${data.name}</b><br>Status: ${data.status}<br>Trip ID: ${data.trip_id}`);
        touristMarkers[data.tourist_id] = marker;
    }
}

function updateGuideOnMap(data) {
    if (guideMarkers[data.guide_id]) {
        // Update existing guide marker
        guideMarkers[data.guide_id].setLatLng([data.latitude, data.longitude]);
        guideMarkers[data.guide_id].setPopupContent(
            `<b>${data.guide_name}</b><br>Role: Guide<br>Updated: ${new Date(data.timestamp).toLocaleTimeString()}`
        );
    } else {
        // Create new guide marker
        const marker = L.marker([data.latitude, data.longitude], {icon: guideIcon})
            .addTo(guideLayer)
            .bindPopup(`<b>${data.guide_name}</b><br>Role: Guide<br>Updated: ${new Date(data.timestamp).toLocaleTimeString()}`);
        guideMarkers[data.guide_id] = marker;
        console.log(`Added new guide marker for ID: ${data.guide_id}`);
    }
}

function updateTouristInTable(data) {
    // Look for existing row in both active and inactive tables
    const activeTable = document.getElementById('activeTouristsTable');
    const inactiveTable = document.getElementById('inactiveTouristsTable');
    
    let existingRow = null;
    let currentTable = null;
    
    // Check active table first
    if (activeTable) {
        existingRow = activeTable.querySelector(`tr[data-tourist-id="${data.tourist_id}"]`);
        if (existingRow) {
            currentTable = 'active';
        }
    }
    
    // If not found in active table, check inactive table
    if (!existingRow && inactiveTable) {
        existingRow = inactiveTable.querySelector(`tr[data-tourist-id="${data.tourist_id}"]`);
        if (existingRow) {
            currentTable = 'inactive';
        }
    }
    
    if (existingRow && currentTable === 'active') {
        // Update the active tourist row (status and coordinates)
        existingRow.children[3].textContent = data.status;
        existingRow.children[3].className = `status-${data.status.toLowerCase()}`;
        existingRow.children[4].textContent = `${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}`;
    }
    // Note: Inactive tourists don't receive location updates as they don't have active trips
}

function handleTouristStatusChange(data) {
    if (data.action === 'trip_started') {
        // Tourist became active - move from inactive to active table and add marker
        moveTouristToActiveTable(data);
        addTouristToMap(data);
    } else if (data.action === 'trip_ended') {
        // Tourist became inactive - move from active to inactive table and remove marker
        moveTouristToInactiveTable(data);
        removeTouristFromMap(data);
    }
}

function moveTouristToActiveTable(data) {
    const activeTable = document.getElementById('activeTouristsTable');
    const inactiveTable = document.getElementById('inactiveTouristsTable');
    
    if (!activeTable || !inactiveTable) return;
    
    // Remove from inactive table if it exists there
    const inactiveRow = inactiveTable.querySelector(`tr[data-tourist-id="${data.tourist_id}"]`);
    if (inactiveRow) {
        inactiveRow.remove();
    }
    
    // Add to active table
    const tbody = activeTable.getElementsByTagName('tbody')[0];
    const newRow = tbody.insertRow();
    newRow.setAttribute('data-tourist-id', data.tourist_id);
    
    newRow.innerHTML = `
        <td>${data.name}</td>
        <td>${data.trip_id}</td>
        <td>${data.location_name}</td>
        <td class="status-${data.status.toLowerCase()}">${data.status}</td>
        <td>${data.last_lat.toFixed(4)}, ${data.last_lon.toFixed(4)}</td>
        <td><a href="/trip/${data.trip_id}" class="tourist-link">View Map</a></td>
    `;
    
    // Update header counts if elements exist
    updateTableCounts();
}

function moveTouristToInactiveTable(data) {
    const activeTable = document.getElementById('activeTouristsTable');
    const inactiveTable = document.getElementById('inactiveTouristsTable');
    
    if (!activeTable || !inactiveTable) return;
    
    // Remove from active table
    const activeRow = activeTable.querySelector(`tr[data-tourist-id="${data.tourist_id}"]`);
    if (activeRow) {
        activeRow.remove();
    }
    
    // Add to inactive table
    const tbody = inactiveTable.getElementsByTagName('tbody')[0];
    const newRow = tbody.insertRow();
    newRow.setAttribute('data-tourist-id', data.tourist_id);
    
    newRow.innerHTML = `
        <td>${data.name}</td>
        <td>${data.email}</td>
        <td>${data.contact_number}</td>
        <td>${data.age}</td>
        <td class="status-inactive">No Active Trip</td>
    `;
    
    // Update header counts if elements exist
    updateTableCounts();
}

function addTouristToMap(data) {
    // Add tourist marker to map
    const marker = L.marker([data.last_lat, data.last_lon])
        .addTo(map)
        .bindPopup(`<b>${data.name}</b><br>Status: ${data.status}`);
    touristMarkers[data.tourist_id] = marker;
}

function removeTouristFromMap(data) {
    // Remove tourist marker from map
    if (touristMarkers[data.tourist_id]) {
        map.removeLayer(touristMarkers[data.tourist_id]);
        delete touristMarkers[data.tourist_id];
    }
}

function updateTableCounts() {
    // Update the count in table headers by finding h3 elements that contain the specific text
    const allH3s = document.querySelectorAll('h3');
    
    allH3s.forEach(h3 => {
        if (h3.textContent.includes('Active Tourists')) {
            const activeCount = document.querySelectorAll('#activeTouristsTable tbody tr').length;
            h3.textContent = `📋 Active Tourists (${activeCount})`;
        } else if (h3.textContent.includes('Inactive Tourists')) {
            const inactiveCount = document.querySelectorAll('#inactiveTouristsTable tbody tr').length;
            h3.textContent = `👥 Inactive Tourists (${inactiveCount})`;
        }
    });
}