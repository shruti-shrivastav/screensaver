# Screensaver

An AI-powered application that seamlessly captures your screen, analyzes code or problems using the Gemini API, and automatically solves them for you in real-time. 

## Features
- **Live Screen Capture:** Automatically captures the relevant portion of your screen.
- **AI Analysis:** Uses Gemini to parse captured problems into structured data.
- **Autonomous Solver:** Generates solutions and runs local tests in a continuous loop until they pass.
- **Real-time Streaming UI:** Watch the LLM's thought process and coding live in your browser.
- **History & Gallery:** Keep track of all your past sessions and original screen captures.

---

## Setup Instructions

### 1. Backend Dependencies
Ensure you have Python 3.10+ installed. 
```bash
# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate

# Install the Python dependencies
pip install -r requirements.txt
```

### 2. Frontend Dependencies (Optional, needed only if frontend changes are made)
The user interface is built with React and Vite. You need Node.js and npm installed.
```bash
cd frontend-react
npm install
npm run build
cd ..
```

### 3. Environment Configuration
Copy the sample environment file to create your local config.
```bash
cp .env.example .env
```
Open `.env` in a text editor and fill in the required fields:
- `JWT_SECRET`: A long, random string for securing your sessions.
- `GEMINI_API_KEY`: Your Google Gemini API Key. 
- *(Optional)* `NGROK_URL` or `CF_TUNNEL_NAME` if you want to expose the app to the internet.

### 4. Create an Account
Because the app grants local code-execution and screen-capture capabilities, it requires a secure login. Create your initial user account by running:
```bash
python setup_user.py
```
*(Follow the interactive prompt to set your username and password).*

---

## Usage

1. **Start the Server**
   Run the main entry point:
   ```bash
   python run.py
   ```
   The server will start by default on `http://localhost:9090` (unless configured otherwise via tunneling).

2. **Access the Web UI**
   Open your browser and navigate to `http://localhost:9090`. Log in using the credentials you created during setup.

3. **Analyze & Solve**
   - Click **Analyze Screen** to capture your current screen. The AI will extract the problem details.
   - Click **Solve** to start the autonomous solver. You can watch the AI stream its code directly in the UI.
   - You can also manually submit instructions via the text box if you want the AI to modify its approach (e.g. "Optimize this for space complexity").

4. **Review History**
   Every frame you capture is saved locally. You can review past captures and problem statements in the right-hand **History** panel.
