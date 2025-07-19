# JanSetu - ## "Your bridge to Sansad"
**Transparency. Accountability. Empowerment.**

JanSetu is an AI-powered civic-tech platform that enables citizens to search, explore, and verify real parliamentary discussions. 
By linking session transcripts with timestamped YouTube debates, it breaks down policy complexities into simple, accessible insights.


###Features:
- 🔍 Natural language + multilingual search (e.g., “Delhi water crisis”, “जल समस्या”)
- 🎥 Direct links to official Sansad TV videos with timestamps
- 🗣️ Speaker info, ministries, session date & bill metadata
- 📚 AI-powered summarization of policy discussions
- 🧠 Vector embeddings for semantic understanding
- 🌐 Simple web interface for the general public


###Tech Stack used:
- Backend: Python, FastAPI, MongoDB , LLM
- AI: Google Gemini / OpenAI, Youtube data api v3
- Data Sources: Sansad TV (YouTube channel)
- Frontend: HTML , TailwindCSS , javascript

###Getting Started (Setup Instructions)
1. Clone the repository:
   git clone https://github.com/your-org/jansetu.git

2. Install dependencies:
   pip install -r requirements.txt

3. Setup .env file with API keys:
   - YOUTUBE_API_KEY
   - MONGO_URI
   - GEMINI_API_KEY

4. Run the backend server:
   python app.py

5. Launch frontend (if separate):
   cd frontend && npm install && npm run dev


###Demo:
![Search UI Screenshot](images/demo_search.png)
🎥 [Watch Demo](https://youtu.be/demo-link)


###Team
- Dev Priya Gupta (Backend , AI)
- Vaidehi Gupta (Frontend , Database)


Contact:
Reach out via Issues or email: devpriyagupta8765@gmail.com
