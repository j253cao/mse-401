# UW Course Recommendation System

A course recommendation system for University of Waterloo students. Features text-based search, resume analysis, and transcript parsing to suggest relevant courses.

## Project Structure

```
mse-401/
├── backend/                    # Python backend (FastAPI)
│   ├── api/                    # API endpoints
│   │   └── main.py            # FastAPI application
│   ├── parsers/               # Document parsers
│   │   ├── resume_parser.py   # Resume PDF parsing + LLM analysis
│   │   ├── resume_llm_client.py # Google Gemini LLM client
│   │   └── transcript_parser.py # UW transcript parsing
│   └── recommender/           # Course recommendation engine
│       ├── main.py            # Main recommendation logic
│       ├── data_loader.py     # Data loading utilities
│       ├── embedding_generators.py # TF-IDF, SVD, BERT embeddings
│       ├── recommenders.py    # Various recommendation algorithms
│       └── utils.py           # Helper utilities
│
├── frontend/                   # React + TypeScript frontend (Vite)
│   ├── src/
│   │   ├── App.tsx            # Main app component
│   │   ├── HomePage.tsx       # Landing page
│   │   ├── RecommendationPage.tsx # Course recommendations
│   │   ├── CalendarPage.tsx   # Calendar view
│   │   ├── ProfilePage.tsx    # User profile
│   │   └── components/        # Reusable UI components
│   ├── .env.example           # Frontend environment variables template
│   ├── package.json
│   └── vite.config.ts
│
├── data/                       # All data files
│   ├── courses/               # Course catalog data
│   │   ├── waterloo-open-api-data.json # Main course data
│   │   ├── courses.json       # Course list with PIDs
│   │   ├── departments.json   # Department list
│   │   ├── undergrad-courses.json
│   │   └── grad-courses.json
│   ├── embeddings/            # ML model embeddings
│   │   ├── course_embeddings.npy
│   │   ├── course_bert_embeddings.npy
│   │   ├── tfidf_vectorizer.pkl
│   │   └── svd_model.pkl
│   ├── dependencies/          # Course prerequisites data
│   │   └── course_dependencies.json
│   └── degree_requirements/   # Degree requirement data
│
├── notebooks/                  # Jupyter notebooks for exploration
│
├── tests/                      # Test files
│   └── test_data/
│       ├── resumes/           # Sample resume PDFs
│       └── transcripts/       # Sample transcript PDFs
│
├── .env.example               # Environment variables template (copy to .env)
├── backend/requirements.txt   # Python dependencies
└── README.md
```

## Setup

### Environment Variables

Before running the application, you need to set up environment variables:

1. **Backend environment variables** (project root):
   - Copy `.env.example` to `.env` in the project root:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your `GEMINI_API_KEY`:
     - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
     - Replace `your-gemini-api-key-here` with your actual API key

2. **Frontend environment variables** (optional):
   - Copy `frontend/.env.example` to `frontend/.env`:
     ```bash
     cp frontend/.env.example frontend/.env
     ```
   - Edit `frontend/.env` if your backend runs on a different URL (defaults to `http://localhost:8000`)

**Note:** `.env` files are gitignored and should not be committed to the repository. The `.env.example` files serve as templates showing what variables are needed.

### Backend Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

2. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Ensure your `.env` file is set up in the project root with `GEMINI_API_KEY` (see Environment Variables section above)

4. Run the backend server:
   ```bash
   cd backend
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at http://localhost:8000

### Frontend Setup

1. Install Node.js dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at http://localhost:5173

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/recommend` | POST | Get course recommendations from text queries |
| `/resume-recommend` | POST | Get recommendations from uploaded resume PDF |
| `/transcript-parse` | POST | Parse uploaded transcript PDF |
| `/random-course` | GET | Get a random course |

### Example Request

```bash
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["machine learning and data science"],
    "filters": {
      "include_undergrad": true,
      "include_grad": false
    }
  }'
```

## Features

- **Text-based Search**: Find courses using natural language queries
- **Resume Analysis**: Upload a resume to get personalized course recommendations
- **Transcript Parsing**: Parse UW transcripts to track completed courses
- **Multiple Algorithms**: Cosine similarity, FAISS, BERT, and ensemble methods
- **Filtering**: Filter by undergraduate/graduate level, department, prerequisites

## Tech Stack

### Backend
- Python 3.10+
- FastAPI
- scikit-learn (TF-IDF, SVD)
- sentence-transformers (BERT embeddings)
- FAISS (similarity search)
- pdfplumber (PDF parsing)
- Google Gemini (resume analysis)

### Frontend
- React 19
- TypeScript
- Vite
- Tailwind CSS
- Radix UI
