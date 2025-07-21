<h1 align="center">🚀 JanSetu – Your Bridge to Sansad</h1>
<p align="center"><strong>Transparency. Accountability. Empowerment.</strong></p>

<p align="center">
<img width="800" height="auto" alt="Screenshot 2025-07-20 at 10 50 16 PM" src="https://github.com/user-attachments/assets/6682061a-3932-4e8d-89b2-87a0b7e46434" />
</p>
<p align="center">
<img width="800" height="auto" alt="Screenshot 2025-07-20 at 10 50 32 PM" src="https://github.com/user-attachments/assets/5bac8b15-5fc8-41cb-9e1e-26126e4e32fa" />
</p>
<p align="center">
<img width="800" height="auto" alt="Screenshot 2025-07-20 at 10 50 44 PM" src="https://github.com/user-attachments/assets/e9a426d6-4c83-4ff5-8f8a-38e5d91d3e80" />
</p>

## 📌 Overview

**JanSetu** is an AI-powered civic-tech platform that empowers citizens to:
- 🔍 Search any topic using natural or regional language  
- 🎥 Directly view timestamped Sansad TV debates  
- 🧠 Understand policies via AI-driven summaries  

It simplifies complex policy information and fosters **trust through transparency**.

---

## ✨ Features

- 🔎 **Multilingual Natural Language Search** (`e.g. “Delhi water crisis”, “जल समस्या”`)
- 🎬 **YouTube Links with Timestamps** (Verified via Sansad TV)
- 🧑‍⚖️ **Speaker, Ministry & Session Metadata**
- 🧭 **Vector-based Semantic Search**
- 🖥️ **User-friendly Web Interface**

---

## 🧰 Tech Stack

| Layer         | Technology                          |
|---------------|-------------------------------------|
| **Backend**   | Python, FastAPI, MongoDB, LLMs      |
| **AI/NLP**    | Google Gemini / OpenAI, Sentence Transformers |
| **Data**      | YouTube Data API v3, Sansad TV      |
| **Frontend**  | HTML, TailwindCSS, JavaScript       |

---

## ⚙️ Getting Started

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-org/jansetu.git
   cd jansetu

2. Install dependencies:
   ```bash
   pip install -r requirements.txt

4. Setup .env file with API keys:
   - YOUTUBE_API_KEY [Google Cloud API - Enable the youtube data api v3]
   - MONGO_URI [Create a mongodb cluster]
   - GEMINI_API_KEY [ Google Cloud API - Enable Gemini api]

5. Run this to upload the youtube transcript data to your mongodb.
   ```bash
   python script/bulk_youtube_mongo.py new_data/
Output : raw_video is uploaded in your mongodb cluster

6. Run to process the raw_video in your mongodb to generate videos.
   ```bash
   python script/mongodb_transcript_processor.py --database youtube_data
Output : videos is created in your mongodb cluster 

7. Run to process the videos in your mongodb to generate ttl file.
   ```bash
   python script/mongodb_ttl_generator.py --database youtube_data
Output : ttl and json-ld section are created within every videos collection in your mongodb cluster

8. Run to store the data in form of knowledge graph[nodes,edges,statements].
   ```bash
   python script/mongodb_graph_loader.py --database youtube_data
Output : nodes, edges, statements are created in your mongodb youtube_data cluster

9. Run the backend server:
   ```bash
   python jansetu.py

10. open the index.html page and go live

---

### 👥 Team

| Name                | Role                   | Responsibilities                                  |
|---------------------|------------------------|---------------------------------------------------|
| **Dev Priya Gupta** | Backend & AI Developer | LLM integration, knowledge graph, search engine   |
| **Vaidehi Gupta**   | Frontend & Database    | UI/UX, TailwindCSS, MongoDB schema & APIs         |


### 📬 Contact

- 📧 **Email**: [devpriyagupta8765@gmail.com](mailto:devpriyagupta8765@gmail.com)   
- 📽️ **Demo Video**: [YouTube Link](https://www.youtube.com/watch?v=Hfraw21HvIs) 
- 📂 **Project Repository**: [GitHub Repo](https://github.com/JanSetu/JanSetu/tree/main) 

