# Healthcare Guiding Badge (MERN Stack)

A full-stack MERN application for RFID-based patient lookup and data management, with ESP32 txt file integration.

---

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Clone & Setup](#clone--setup)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Project Structure](#project-structure)
7. [Code Explanations](#code-explanations)
8. [Available Commands](#available-commands)
9. [Features](#features)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you start, ensure you have:

- **Node.js** (v14+) and **npm** (v6+) installed
  - Download from: https://nodejs.org/
  - Verify: `node --version` and `npm --version`
- **Git** installed (to clone the repo)
  - Download from: https://git-scm.com/
- **MongoDB Atlas account** (optional but recommended for cloud database)
  - Sign up free at: https://www.mongodb.com/cloud/atlas
- A code editor like **VS Code**

---

## Clone & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/WannaBeCoolPizza/Healthcare-Guiding-Badge.git
cd Healthcare-Guiding-Badge
```

**What this does:**
- Downloads the entire project to your computer
- `cd` navigates into the project folder

### Step 2: Verify Project Structure

After cloning, you should see:
```
Healthcare-Guiding-Badge/
├── client/                    # React + TypeScript frontend
│   ├── src/
│   │   ├── pages/            # LookupPage.tsx, PatientTxtWriterPage.tsx
│   │   ├── components/       # Navbar.tsx, InfoField.tsx
│   │   ├── services/         # api.ts (fetch functions)
│   │   ├── types.ts          # TypeScript interfaces
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   └── package.json
├── server/                    # Express + Mongoose backend
│   ├── src/
│   │   ├── models/           # Patient.js (MongoDB schema)
│   │   ├── routes/           # patients.js (API endpoints)
│   │   ├── services/         # rfidTxtSync.js (auto-sync service)
│   │   ├── utils/            # patientTransform.js (helpers)
│   │   └── index.js          # Server entry point
│   ├── scripts/              # sync-rfid-txt.js (manual sync CLI)
│   ├── .env.example
│   └── package.json
├── RFID Code/                # RFID patient txt files
├── ProcessVoice/
├── 3d Files/
└── README.md
```

---

## Installation

### Step 1: Install Root Dependencies

```bash
npm install
```

**What this does:**
- Installs packages needed for the entire project (like `concurrently` for running multiple servers)
- Creates `node_modules/` folder
- Updates `package-lock.json`

### Step 2: Install Backend Dependencies

```bash
npm install --prefix server
```

**What this does:**
- Installs backend packages: `express`, `mongoose`, `cors`, `dotenv`, etc.
- Located in `server/node_modules/`

### Step 3: Install Frontend Dependencies

```bash
npm install --prefix client
```

**What this does:**
- Installs frontend packages: `react`, `react-dom`, `react-router-dom`, `typescript`, `vite`, etc.
- Located in `client/node_modules/`

---

## Configuration

### Step 1: Create Backend `.env` File

1. Navigate to the `server/` folder
2. Copy `.env.example` to `.env`:
   ```bash
   cp server/.env.example server/.env
   ```
   (On Windows: `copy server\.env.example server\.env`)

3. Edit `server/.env` and configure:
   ```
   PORT=5000
   MONGODB_URI=mongodb+srv://Whale:hardware@cluster0.eza5foh.mongodb.net/heart_tag?retryWrites=true&w=majority&appName=Cluster0
   ```

**Important:**
- `PORT`: Backend server port (default: 5000)
- `MONGODB_URI`: Your MongoDB connection string
  - **Option A (Cloud):** Use MongoDB Atlas (recommended):
    - Sign up at https://www.mongodb.com/cloud/atlas
    - Create a cluster and get your connection string
    - Format: `mongodb+srv://username:password@cluster.mongod.net/database_name?...`
  - **Option B (Local):** Use local MongoDB:
    - Install MongoDB locally
    - Use: `mongodb://localhost:27017/heart_tag`
  - **Replace `heart_tag`** with your desired database name (or use the default)

### Step 2: Verify Configuration

After creating `.env`, verify the backend can connect:

```bash
npm run sync:txt
```

**Expected output:**
```
MongoDB connected.
TXT sync completed.
Synced: X, Skipped: 0
```

---

## Running the Application

### Option 1: Run Both Frontend & Backend Together (Recommended)

```bash
npm run dev
```

**What this does (under the hood):**
- Uses `concurrently` to start frontend and backend simultaneously
- **Backend** runs on `http://localhost:5000` (Express)
- **Frontend** runs on `http://localhost:5173` (Vite dev server)
- Both are watched for file changes (hot reload)

**Open your browser to:**
```
http://localhost:5173
```

### Option 2: Run Backend and Frontend Separately

**Terminal 1 (Backend):**
```bash
npm run dev:server
```
- Starts Express on port 5000
- Uses Nodemon to auto-restart on file changes

**Terminal 2 (Frontend):**
```bash
npm run dev:client
```
- Starts Vite on port 5173
- Hot reloads on React changes

---

## Project Structure

### Frontend (`client/`)

**Entry Point:** `client/src/main.tsx`
```typescript
// Mounts React app to <div id="root">
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
```

**App Router:** `client/src/App.tsx`
```typescript
<Routes>
  <Route path="/" element={<LookupPage />} />
  <Route path="/patient-txt-writer" element={<PatientTxtWriterPage />} />
</Routes>
```
- Route `/` = Patient RFID Lookup
- Route `/patient-txt-writer` = Create Patient TXT Form

**Pages:**

1. **LookupPage.tsx** - Search for patients by RFID
   - Input field to enter RFID number
   - Fetches patient data from backend API
   - Displays allergies, medications, conditions, etc.

2. **PatientTxtWriterPage.tsx** - Create new patient records
   - Form with fields: RFID, Name, DOB, Gender, Height, Weight, etc.
   - Array inputs for allergies (with severity level)
   - Array inputs for symptoms
   - On submit: generates `.txt` file AND saves to MongoDB

**TypeScript Types:** `client/src/types.ts`
```typescript
interface Patient {
  id: string;
  rfid: string;
  patient: {
    name: string;
    age: number;
    // ... other fields
  };
}
```

**API Service:** `client/src/services/api.ts`
```typescript
export async function fetchPatientByRfid(rfid: string) {
  const response = await fetch(`http://localhost:5000/api/patients/rfid/${rfid}`);
  return response.json();
}
```

### Backend (`server/`)

**Entry Point:** `server/src/index.js`
```javascript
const app = express();
const PORT = process.env.PORT || 5000;

// Connect to MongoDB
mongoose.connect(process.env.MONGODB_URI);

// Start auto-sync service
startRfidTxtAutoSync();

// Listen on port
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
```

**Routes:** `server/src/routes/patients.js`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/patients` | List all patients from MongoDB |
| `GET` | `/api/patients/rfid/:rfid` | Find patient by RFID |
| `POST` | `/api/patients/txt` | Create patient txt file + save to MongoDB |
| `POST` | `/api/patients/sync-txt` | Manually trigger txt sync |

**MongoDB Schema:** `server/src/models/Patient.js`
```javascript
const patientSchema = new Schema({
  id: String,
  rfid: { type: String, unique: true, sparse: true, uppercase: true, trim: true },
  patient: {
    name: String,
    age: Number,
    sex: String,
    dob: String,
    mrn: String,
    allergies: [{ name: String, severity: Number }],
    medications: [String],
    history: String
  },
  conversationSummary: String,
  previousDoctorNotes: String
});
```

**Auto-Sync Service:** `server/src/services/rfidTxtSync.js`

On backend startup, this service:
1. Scans `RFID Code/` and `RFID Code/patients/` folders for `.txt` files
2. Parses each `.txt` file (key-value format: `name:John`, `rfid:1042`, etc.)
3. Converts to MongoDB document schema
4. Upserts into `patients` collection (updates if exists, creates if new)
5. Watches for file changes and auto-syncs every 30 seconds

**Txt File Format** (ESP32-friendly):
```
id:1042
name:Jane Doe
dob:19900315
visit:20260328
gender:F
allergy:Penicillin,4
symptom:Hives
symptom:Swelling
```

---

## Code Explanations

### How Patient Lookup Works

**Flow:**
1. User enters RFID in frontend → `LookupPage.tsx`
2. Input triggers API call → `client/src/services/api.ts` → `GET /api/patients/rfid/1042`
3. Backend route receives request → `server/src/routes/patients.js`
4. Route queries MongoDB → `Patient.findOne({ rfid: '1042' })`
5. Returns patient data as JSON
6. Frontend displays in `InfoField` component

**Example Code:**
```typescript
// Frontend: LookupPage.tsx
const handleRfidSearch = async (rfid: string) => {
  const data = await fetchPatientByRfid(rfid);
  setPatient(data);
};
```

```javascript
// Backend: server/src/routes/patients.js
app.get('/api/patients/rfid/:rfid', async (req, res) => {
  const patient = await Patient.findOne({ rfid: req.params.rfid.toUpperCase() });
  res.json(patient);
});
```

### How Patient TXT Writer Works

**Flow:**
1. User fills form → `PatientTxtWriterPage.tsx`
2. Clicks submit → Form data sent to backend
3. Backend receives → `POST /api/patients/txt`
4. Two things happen:
   - **A:** Generates `.txt` file → saved to `RFID Code/patients/`
   - **B:** Upserts to MongoDB → `patients.collection`
5. Auto-sync service detects new txt file (optional redundancy)
6. Frontend gets success response

**Example Code:**
```typescript
// Frontend: Submit form
const handleSubmit = async (formData: PatientTxtPayload) => {
  await createPatientTxt(formData);
};

// API call
export async function createPatientTxt(data: PatientTxtPayload) {
  const response = await fetch('http://localhost:5000/api/patients/txt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return response.json();
}
```

```javascript
// Backend: POST /api/patients/txt
app.post('/api/patients/txt', async (req, res) => {
  // 1. Build txt content
  const txtContent = buildTxtFormat(req.body);
  
  // 2. Write to file
  fs.writeFileSync(`RFID Code/patients/${rfid}.txt`, txtContent);
  
  // 3. Upsert to MongoDB
  await Patient.updateOne(
    { $or: [{ rfid }, { id }] },
    buildPatientDocument(req.body),
    { upsert: true }
  );
  
  res.json({ success: true });
});
```

### How TXT Auto-Sync Works

On server startup:

```javascript
// server/src/services/rfidTxtSync.js
const startRfidTxtAutoSync = async () => {
  // 1. Initial sync of all existing txt files
  await syncTxtPatientsToMongo();
  
  // 2. Watch folders for changes
  fs.watch('RFID Code/', { recursive: true }, async () => {
    await syncTxtPatientsToMongo();
  });
  
  // 3. Fallback: sync every 30 seconds
  setInterval(syncTxtPatientsToMongo, 30000);
};
```

---

## Available Commands

### Root Level Commands

```bash
npm run dev          # Start frontend + backend concurrently
npm run dev:client  # Start frontend only (Vite, port 5173)
npm run dev:server  # Start backend only (Express, port 5000)
npm run sync:txt    # Import all RFID txt files to MongoDB (one-shot)
npm run build       # Build frontend for production
npm run start       # Run production frontend build
```

### What Each Command Does

| Command | What It Runs | When to Use |
|---------|----------|-----------|
| `npm run dev` | Both servers + hot reload | **Development (Recommended)** |
| `npm run dev:client` | Vite dev server (port 5173) | When backend already running |
| `npm run dev:server` | Express server (port 5000) | When frontend already running |
| `npm run sync:txt` | Node script importing txt files to MongoDB | After adding new txt files to RFID Code/ |
| `npm run build` | Vite build for production | Prepare frontend for deployment |

### Under-the-Hood: What `npm run dev` Does

The root `package.json` contains:
```json
{
  "scripts": {
    "dev": "concurrently \"npm run dev:client\" \"npm run dev:server\"",
    "dev:client": "cd client && npm run dev",
    "dev:server": "cd server && npm run dev",
    "sync:txt": "cd server && npm run sync:txt"
  }
}
```

**Breakdown:**
- `concurrently` = Run both commands at the same time
- `npm run dev:client` = Enters `client/` folder and runs its `dev` script (Vite)
- `npm run dev:server` = Enters `server/` folder and runs its `dev` script (Nodemon + Express)

---

## Features

✅ **RFID Patient Lookup** - Find patients by RFID number, view allergies, medications, conditions  
✅ **Patient TXT Writer** - Create new patient records with allergies/symptoms array management  
✅ **MongoDB Integration** - All patient data persists to MongoDB Atlas or local MongoDB  
✅ **Auto-Sync Service** - Txt files in `RFID Code/` automatically import to MongoDB on startup  
✅ **TypeScript** - Full type safety for React components and backend utilities  
✅ **ESP32-Compatible Format** - Txt files use key-value format readable by embedded systems  
✅ **React Router** - Multi-page navigation between lookup and writer pages  
✅ **Vite Bundler** - Fast frontend build and hot reload  
✅ **Express REST API** - Clean API endpoints for all operations  

---

## Troubleshooting

### Problem: "npm: command not found"
**Solution:** Install Node.js from https://nodejs.org/  
Verify: `node --version`

### Problem: "PORT 5173 already in use"
**Solution:** Kill the process using that port or specify a different port:
```bash
# Mac/Linux
lsof -ti:5173 | xargs kill -9

# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

### Problem: "Cannot connect to MongoDB"
**Solution:** 
1. Verify `MONGODB_URI` in `server/.env` is correct
2. If using MongoDB Atlas, ensure:
   - IP address is whitelisted (0.0.0.0/0 for testing)
   - Username/password are correct
   - Database name is specified in URI
3. Test connection: `npm run sync:txt`

### Problem: "Patients not visible in MongoDB Atlas"
**Solution:**
- Verify `MONGODB_URI` points to correct database name (e.g., `/heart_tag`)
- Run: `npm run sync:txt` to force import
- Restart backend: `npm run dev`

### Problem: "Blank page in browser"
**Solution:**
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Verify frontend is running on `http://localhost:5173`
4. Verify backend is running on `http://localhost:5000`
5. Restart with: `npm run dev`

---

## Summary

**To get started:**

```bash
# 1. Clone
git clone https://github.com/WannaBeCoolPizza/Healthcare-Guiding-Badge.git
cd Healthcare-Guiding-Badge

# 2. Install
npm install
npm install --prefix server
npm install --prefix client

# 3. Configure
cp server/.env.example server/.env
# Edit server/.env with your MongoDB connection string

# 4. Run
npm run dev

# 5. Open
# Browser: http://localhost:5173
```

That's it! Your full-stack MERN application is now running.