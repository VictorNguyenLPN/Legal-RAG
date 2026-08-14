import os
import uvicorn
import gradio as gr
from fastapi import FastAPI
from backend.app.main import app as fastapi_app

# Create a minimal Gradio UI to satisfy the Hugging Face Gradio SDK
def dummy_fn(x):
    return x

demo = gr.Interface(
    fn=dummy_fn,
    inputs="text",
    outputs="text",
    title="Legal RAG Backend API",
    description="This Space hosts the FastAPI backend for Legal RAG. Please call the API endpoints directly."
)

app = gr.mount_gradio_app(fastapi_app, demo, path="/gui")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
