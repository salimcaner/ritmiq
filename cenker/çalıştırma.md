```bash
cd ritmiq

python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000
```

`.env` içeriği  
`GEMINI_API_KEY`
`REDIS_URL`.

Hangi link: http://localhost:8000
