# Palopedix

Palopedix is an advanced save parser and database viewer for Palworld. It provides an interactive web interface and a robust backend to parse your Palworld save files (`Level.sav`) and display comprehensive details about your save game, including:

- **Paldex Database:** View detailed statistics, traits, and elements of all Pals.
- **Save Game Viewer:** Explore all Pals currently in your save, filterable by species, level, and passives.
- **Base Camps Manager:** View all your active base camps, the Pals currently deployed as workers, and a complete inventory of built structures in each camp.
- **Breeding Calculator:** Plan out your Pal breeding lines to get exactly the Pal you want.

## Project Structure

- `palengine/`: The core Python backend, which handles reading and decoding `Level.sav` files using a tolerant save parser compatible with Palworld v1.0+.
- `ui/`: The React-based frontend web interface, built with Vite and vanilla CSS for a modern, glassmorphic aesthetic.

## Running the Application

To run the full stack, you need to start both the Python backend and the React frontend.

1. **Start the backend server:**
   ```bash
   python -m uvicorn palengine.api.main:app --reload --port 8000
   ```
2. **Start the frontend UI:**
   ```bash
   cd ui
   npm run dev
   ```

Then, open your browser to the URL provided by the Vite server (typically `http://localhost:5173`).
