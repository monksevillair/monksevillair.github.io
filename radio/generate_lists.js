const fs = require('fs');
const path = require('path');

// Read songs directory
const songs = fs.readdirSync(path.join(__dirname, 'songs'))
    .filter(file => file.endsWith('.mp3'));

// Read broadcasts directory
const broadcasts = fs.readdirSync(path.join(__dirname, 'broadcasts'))
    .filter(file => file.endsWith('.mp3'));

// Write to JSON files
fs.writeFileSync('songs.json', JSON.stringify(songs, null, 2));
fs.writeFileSync('broadcasts.json', JSON.stringify(broadcasts, null, 2));

console.log('Generated songs.json and broadcasts.json'); 
