#!/usr/bin/env node

/**
 * Watch and Build Script for CTR Mapper
 * 
 * This script watches for changes in the Vue frontend and automatically
 * rebuilds when files change, so the desktop app reflects updates.
 */

const { spawn } = require('child_process');
const chokidar = require('chokidar');
const path = require('path');

console.log('🔄 Starting CTR Mapper Development Watch Mode');
console.log('=' .repeat(60));

let isBuilding = false;
let buildQueue = [];

function runBuild() {
    if (isBuilding) {
        buildQueue.push(() => runBuild());
        return;
    }
    
    isBuilding = true;
    console.log('🏗️  Building frontend...');
    
    const build = spawn('npm', ['run', 'build'], {
        cwd: path.join(__dirname, 'frontend-vue'),
        stdio: 'pipe',
        shell: true
    });
    
    build.stdout.on('data', (data) => {
        process.stdout.write(data);
    });
    
    build.stderr.on('data', (data) => {
        process.stderr.write(data);
    });
    
    build.on('close', (code) => {
        isBuilding = false;
        if (code === 0) {
            console.log('✅ Build completed successfully!');
            console.log('🔄 Refresh your browser to see changes');
        } else {
            console.log('❌ Build failed!');
        }
        
        // Process queued builds
        if (buildQueue.length > 0) {
            const nextBuild = buildQueue.shift();
            setTimeout(nextBuild, 1000); // Debounce
        }
    });
}

// Watch Vue files for changes
const watcher = chokidar.watch([
    'frontend-vue/src/**/*.vue',
    'frontend-vue/src/**/*.js',
    'frontend-vue/src/**/*.ts',
    'frontend-vue/src/**/*.css',
    'frontend-vue/src/**/*.scss'
], {
    ignored: /node_modules/,
    persistent: true,
    ignoreInitial: true
});

let buildTimeout;

watcher.on('change', (filePath) => {
    console.log(`📝 Changed: ${filePath}`);
    
    // Debounce builds - wait 500ms for more changes
    clearTimeout(buildTimeout);
    buildTimeout = setTimeout(runBuild, 500);
});

watcher.on('ready', () => {
    console.log('👀 Watching for changes...');
    console.log('');
    console.log('📋 Instructions:');
    console.log('1. Keep this terminal running');
    console.log('2. Make changes to Vue files');
    console.log('3. Files will auto-build');
    console.log('4. Refresh your browser to see changes');
    console.log('');
    console.log('💡 For instant hot reload, use: npm run dev in frontend-vue/');
    console.log('Press Ctrl+C to stop watching');
    
    // Initial build
    runBuild();
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n👋 Stopping file watcher...');
    watcher.close();
    process.exit(0);
});