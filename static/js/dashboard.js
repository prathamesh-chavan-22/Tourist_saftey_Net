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

// Add tourist markers - this will be populated by template data
const touristMarkers = {};

// Function to initialize tourist markers from template data
function initializeTouristMarkers(tourists) {
    tourists.forEach(tourist => {
        const marker = L.marker([tourist.last_lat, tourist.last_lon])
            .addTo(map)
            .bindPopup(`<b>${tourist.name}</b><br>Status: ${tourist.status}`);
        touristMarkers[tourist.id] = marker;
    });
}

// WebSocket connection for live updates
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsHost = window.location.host;
const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/location`);

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'location_update') {
        updateTouristOnMap(data);
        updateTouristInTable(data);
    }
};

function updateTouristOnMap(data) {
    if (touristMarkers[data.tourist_id]) {
        touristMarkers[data.tourist_id].setLatLng([data.latitude, data.longitude]);
        touristMarkers[data.tourist_id].setPopupContent(`<b>${data.name}</b><br>Status: ${data.status}`);
    } else {
        const marker = L.marker([data.latitude, data.longitude])
            .addTo(map)
            .bindPopup(`<b>${data.name}</b><br>Status: ${data.status}`);
        touristMarkers[data.tourist_id] = marker;
    }
}

function updateTouristInTable(data) {
    // Update existing row or add new one
    const table = document.getElementById('touristsTable').getElementsByTagName('tbody')[0];
    const existingRow = document.querySelector(`tr[data-tourist-id="${data.tourist_id}"]`);
    
    if (existingRow) {
        existingRow.children[3].textContent = data.status;
        existingRow.children[3].className = `status-${data.status.toLowerCase()}`;
        existingRow.children[4].textContent = `${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}`;
    }
}