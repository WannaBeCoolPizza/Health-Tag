# Heart Tag

RFID-based patient lookup system for healthcare workers. An ESP32 reads a patient's RFID tag, pulls their data, and uses Gemini AI + Google TTS to give a spoken briefing. A MERN web app lets staff look up and manage patient records.

## Quick Start

```bash
npm install
npm install --prefix server
npm install --prefix client
cp server/.env.example server/.env   # add your MongoDB URI
npm run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:5000

## Secrets

| File | How to configure |
|---|---|
| `server/.env` | Copy from `server/.env.example` |
| `.env` | Copy from `.env.example` — set `GEMINI_API_KEY` |
| `RFID_Code/DoorUnit/secrets.h` | Copy from `secrets.h.example` — set WiFi + API keys |
