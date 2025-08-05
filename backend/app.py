from fastapi import FastAPI

# Create the FastAPI app
app = FastAPI(title="Document RAG System")

# A simple endpoint to test everything works
@app.get("/")
def read_root():
    return {"message": "Hello! The API is working!"}
