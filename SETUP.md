# QA Team Dashboard — Setup Guide

## Prerequisites
- Python 3.9 or higher
- Git
- A terminal (Command Prompt / PowerShell on Windows, Terminal on Mac/Linux)

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/HimanshuManchanda78/Teamstatus.git
cd Teamstatus
```

---

## Step 2 — Create a Virtual Environment

**Mac / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Mac / Linux
cp .env .env.bak   # optional backup, skip if .env doesn't exist yet
```

Open (or create) `.env` and fill in your values:

```
AZURE_DEVOPS_PAT=your_personal_access_token_here
AZURE_DEVOPS_ORG=aononedevops
AZURE_DEVOPS_PROJECT=ACIA_Health_Solutions_App
AZURE_DEVOPS_QUERY=your_saved_query_name_here
```

> **How to create an Azure DevOps PAT:**
> 1. Go to https://dev.azure.com → click your profile icon (top right) → **Personal access tokens**
> 2. Click **New Token**
> 3. Give it a name, set expiry, and grant **Work Items → Read** scope
> 4. Copy the token and paste it as the value for `AZURE_DEVOPS_PAT`

> **Note:** The `.env` file is listed in `.gitignore` and will never be pushed to GitHub.

---

## Step 5 — (Optional) Update Team Member Roles

Open `app.py` and find the `MEMBER_ROLES` dictionary (search for `MEMBER_ROLES`).  
Add your team members' names exactly as they appear in Azure DevOps:

```python
MEMBER_ROLES: dict[str, str] = {
    "Alice Johnson": "Senior QA Engineer",
    "Bob Smith":     "QA Engineer",
    # add more as needed
}
```

---

## Step 6 — Run the Application

```bash
streamlit run app.py
```

The app will open automatically in your browser at:
```
http://localhost:8501
```

---

## Step 7 — Fetch Live Data from Azure DevOps

Once the app is running:
1. Click the **🔄 Refresh Data** button (top right of the dashboard)
2. The app will connect to Azure DevOps, run your saved query, fetch all tasks, and update the dashboard automatically

> If the button shows an error, double-check that `AZURE_DEVOPS_PAT` and `AZURE_DEVOPS_QUERY` are correctly set in your `.env` file.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure your virtual environment is activated and you ran `pip install -r requirements.txt` |
| `AZURE_DEVOPS_PAT is not set` | Check your `.env` file exists in the project root and has the correct variable name |
| `Query '...' not found` | Verify the query name in `.env` exactly matches the saved query name in Azure DevOps |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8502` to use a different port |
