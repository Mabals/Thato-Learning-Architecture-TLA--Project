Markdown
# 🤖 The Thato Learning Architecture (TLA)

The Thato Learning Architecture (TLA) is an enterprise-grade, data-driven corporate talent development and adaptive learning ecosystem. It replaces static, "one-size-fits-all" learning management systems with an intelligent Python-driven data engine, a responsive Flask administrative portal, an automated **AI Assessment Matrix Generator**, and live Power BI executive dashboards.

The architecture continuously tracks individual employee technical competencies, algorithmically injects prerequisite remediation paths for skill gaps, and provides real-time visibility into an organization's overall capabilities while remaining strictly compliant with South African data privacy legislation (**POPIA**).

---

## 🚀 Key Architecture Features

* **Employee UpSkilling Hub:** A responsive interface where users consume custom curriculum tracks, run live time-bounded evaluations, and navigate dynamically adapting learning paths.
* **🤖 AI Assessment Matrix Generator:** Integrates with the **Gemini API** to automatically parse text-based curriculum documents and instantly generate structured multiple-choice question repositories.
* **Configure Evaluation Parameters Panel:** A central administrative workspace allowing L&D managers to dynamically control assessment rules, duration limits, active date windows, and baseline placement parameters.
* **Algorithmic Remediation Engine:** Real-time evaluation rules that automatically manage progress pipelines:
    * **Remediation Loop:** Scoring **< 60%** automatically appends a foundational prerequisite module to the employee's active queue.
    * **Exemption Fast-Track:** Scoring **≥ 85%** on placement assessments grants immediate downstream exemptions.
* **Executive Talent Cockpit (Power BI):** Deep relational reporting utilizing a hybrid operational strategy (**DirectQuery** for live quiz telemetry streams and **In-Memory Import** for historical structural dimensions).

---

## 🛠️ Technical Stack Inventory

| Layer | Component | Specification / Version |
| :--- | :--- | :--- |
| **Backend Runtime** | Python | v3.11.x |
| **Web Framework** | Flask | v3.0.x (WSGI Compliant) |
| **Generative AI SDK** | Google GenAI | Integrated with Gemini API |
| **Database Connector** | pyodbc | Native MS ODBC Layer |
| **Enterprise Database**| Microsoft SQL Server | 2022 Express / Developer Edition |
| **UI Styling Engine** | Semantic HTML5 / CSS3 | Modern Enterprise Minimalist Variable Sheet |
| **Business Intelligence**| Power BI Desktop | Hybrid DirectQuery & Import Model |

---

## 🗄️ Relational Database Schema Design

The data storage layer is explicitly designed in Microsoft SQL Server using a performance-optimized **Star Schema** architecture splitting system write-operations from heavy analytical reads.

### 🔹 Dimension Tables
* `Dim_Employees`: Centralizes profile attributes, departments, and system security clearance roles (**Admin, Facilitator, Employee**).
* `Dim_Modules`: Catalogs internal training modules, baseline competencies, and metadata configurations.
* `Dim_Questions`: Holds multiple-choice question pools mapped to modules, generated automatically via the AI Matrix engine.
* `Dim_Materials`: Tracks auxiliary training guides, streaming walkthrough URLs, and archived lecture recordings.

### 🔸 Fact Tables
* `Fact_Quiz_Attempts`: Captures raw evaluation tracking metrics, including calculated durations (`DurationSeconds`), marks scored, and remediation outcomes.
* `Fact_Skills_Matrix`: Maps live competency rankings (Scale 1–5) across business units for real-time gap charting.

---

## 💻 Getting Started & Installation

Follow these directives to set up a localized instance of the TLA environment on your system:

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/thato-learning-architecture.git](https://github.com/YOUR_USERNAME/thato-learning-architecture.git)
cd thato-learning-architecture
2. Configure Your Virtual Environment
Bash
# Create the environment
python -m venv env

# Activate the environment (Windows)
.\env\Scripts\activate

# Activate the environment (Linux/macOS)
source env/bin/activate
3. Install System Dependencies
Bash
pip install -r requirements.txt
4. Inject Environmental Runtime Variables
Create a secure .env file in the root project folder (this is kept hidden from GitHub using .gitignore for POPIA compliance):

Code snippet
FLASK_SECRET_KEY=YourSuperSecretSystemMasterKey
GEMINI_API_KEY=YourValidGoogleGenAIApiKey
DB_DRIVER={ODBC Driver 17 for SQL Server}
DB_SERVER=YOUR_SERVER_NAME
DB_NAME=TLA_Database
5. Initialize the Database Schema
Open SQL Server Management Studio (SSMS), connect to your database instance, and execute the structural DDL setup scripts provided within the database directory to instantiate the tables (Dim_* and Fact_*).

6. Run the Application Localy
Bash
python app.py
Navigate to http://127.0.0.1:5000 inside your web browser to access the portal dashboard workspace.

🔒 Data Privacy & Regulatory Compliance (POPIA)
TLA is explicitly built around South African data protection principles:

Purpose Specification: Employee tracking and evaluation metrics are captured solely for career development, training optimizations, and upskilling tracks.

Access Limitation & Minimization: Personal Identifiable Information (PII) is securely isolated within structured SQL dimensions, protected behind application role-based security layers, and encrypted before processing.

✍️ Author & Project Maintenance
Lead Architect/Developer: Thato Khonkhe

Version: 1.0.0

Development Cycle Update: June 2026


### 💡 Quick Tips Before Pushing:
1. Make sure you have a `.gitignore` file in your root folder containing `env/`, `__pycache__/`, `.env`, and `.vscode/` so you don't accidentally push your virtual environment or api keys to public GitHub.
2. Replace `YOUR_USERNAME` in the clone command path with your exact GitHub profile handle.