module.exports = {
  "env": {
    "browser": true,
    "es2021": true
  },
  "extends": "eslint:recommended",
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module"
  },
  "rules": {
    "no-undef": "off" // Turn off undefined variable warnings
  },
  "globals": {
    // Add any global variables your templates use
    "L": "readonly", // Leaflet
    "map": "writable"
  }
};
