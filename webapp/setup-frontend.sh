#!/bin/bash

echo "Setting up Vue.js frontend..."

# Navigate to frontend directory
cd frontend-vue

# Install dependencies
echo "Installing npm dependencies..."
npm install

# Build for production
echo "Building for production..."
npm run build

echo "Frontend setup complete!"
echo "Built files are in ../frontend-dist/"