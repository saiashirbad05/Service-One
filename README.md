# Service-One — Home Appliance Repair Quote Auditor

**Know the fair price before you pay.**

Service-One is a serverless web platform designed to help consumers evaluate if their home appliance repair or installation quotes are fair before paying. By analyzing location, appliance, service type, and price, Service-One compares quotes against regional market benchmarks, active provider directories, historical community invoice reports, and trust signals to return a clear pricing verdict.

---

## 🚀 Live Services

* **Frontend Web Application (Firebase Hosting)**: [https://service-one-platform.web.app](https://service-one-platform.web.app)

## ✨ Features & Capabilities

* **AI Quote Verdict System**: Classifies submitted invoice quotes into **Fair**, **High**, **Suspicious**, or **Low** pricing categories.
* **Dynamic User Dashboard**:
  * **Total Savings Counter**: Large financial counter monitoring total money saved against regional averages.
  * **Interactive Verdict Chart**: Custom breakdown visualization filtering historical logs with one click.
  * **Competitor Tracker List**: Save and monitor competitor listing links and rates dynamically.
  * **Community Reports**: Submit local invoice details with proof photo attachments for regional index indexing.
* **Theme-Aware Aesthetic**: Fully integrated theme toggler syncing all screens and dashboard components between Light Mode and Aubergine Dark Mode.
* **Verification Certificates**: Auto-generated PDF reports of invoice audits for easy sharing and technician negotiation.
* **Geo-Lookup Resilience**: Fallback system querying the Indian Postal API when local pincode databases are missed.

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | React, Next.js / Vite, Tailwind (global) & Custom HSL CSS Variables | Single-page layout featuring modular component styling |
| **Backend** | FastAPI (Python) | High-performance API endpoints |
| **Database** | Google Cloud Firestore (NoSQL) | Serverless primary datastore |
| **Caching** | Redis (Upstash) | Level-1 caching for pricing queries |
| **AI / Agents** | Google ADK, Vertex AI (Gemini Flash & Gemini Flash-Lite) | Multi-agent analysis pipeline |
| **Auth** | Google OAuth 2.0 / JWT | Federated user registration |
| **Hosting** | Firebase Hosting & Google Cloud Run | Serverless server & static frontend hosting |

---

## 📁 Project Structure

```
service-one/
├── frontend/                       # React App
│   ├── src/
│   │   ├── app/
│   │   │   └── dashboard/          # User Quote History Dashboard (dynamic cards, SVG charts, trackers)
│   │   │   └── services/           # Diagnostic quote checkers
│   │   ├── components/
│   │   │   └── layout-next/        # Header, Footer components (theme switching and layout)
│   │   ├── index.css               # Global theme variable stylesheet
│   │   └── App.jsx                 # Routing entry point
│   ├── .env                        # Local developer environment variables
│   └── package.json
│
├── backend/                        # FastAPI Application
│   ├── agents/                     # Multi-agent orchestrators (GSTIN agent, voice-bots, Lifespan analyzers)
│   ├── db/
│   │   ├── database.py             # Firestore client connection manager and data endpoints
│   │   └── storage.py              # Cloud Storage signed URL utilities
│   ├── tests/                      # Pytest suite (agent logic and endpoint validation)
│   ├── Dockerfile                  # Container definition for Cloud Run
│   ├── requirements.txt            # Python environment packages
│   └── main.py                     # API entry point & routers
```

---

## ⚙️ Local Setup

### 1. Backend Setup

```bash
cd backend

# Create and activate environment
python -m venv venv
venv\Scripts\activate       # On Windows
source venv/bin/activate    # On Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Start local server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install package dependencies
npm install

# Start local dev server
npm run dev
```

---

## 📡 Core API Routes

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Live service health check status |
| `GET` | `/healthz` | Detailed database (Firestore) connectivity status |
| `POST` | `/api/check-quote` | Evaluates a repair quote with multi-agent models |
| `GET` | `/api/geo/states` | Fetch list of Indian states |
| `POST` | `/api/custom-search` | Save tracking listing URL |
| `POST` | `/api/community-report` | Submit invoice proof and price details |

---

## 🔄 Recent Changes & Migrations

1. **Firestore DB Switch**: Legacy PostgreSQL code and PostgreSQL client dependencies (`psycopg2`) have been removed from the backend database layer. The application now uses Google Cloud Firestore natively for robust, low-maintenance serverless scalability.
2. **Dependency Resolution**: Added missing packages (including `redis` client) in `requirements.txt` to resolve deployment container startup crashes.
3. **Theme Variables Integration**: Refactored the dashboard component markup in the frontend to bind fully to CSS custom variables (`var(--bg)`, `var(--text)`, etc.), making theme changes instantaneous.
4. **Header Enhancements**: Relocated the **Dashboard** shortcut button to sit right next to the user profile avatar, styled as a premium action pill. Added corresponding mobile menu drawer support.
