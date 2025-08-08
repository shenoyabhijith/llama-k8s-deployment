from fastapi import FastAPI, HTTPException
from model_loader import load_model
from pydantic import BaseModel
import os
import torch
from concurrent.futures import ThreadPoolExecutor
import time

app = FastAPI()
model, tokenizer = load_model()

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=4)

class Prompt(BaseModel):
    text: str
    max_tokens: int = 100
    temperature: float = 0.7

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": os.getenv("MODEL_NAME", "unknown")}

@app.post("/generate")
async def generate(prompt: Prompt):
    try:
        # Process in thread pool for parallel execution
        future = executor.submit(process_request, prompt)
        return await future
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def process_request(prompt):
    start_time = time.time()
    
    # Tokenize input
    inputs = tokenizer(prompt.text, return_tensors="pt").to(model.device)
    
    # Generate response
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_length=prompt.max_tokens,
            temperature=prompt.temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Decode response
    response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    return {
        "response": response_text,
        "processing_time_ms": round(processing_time * 1000, 2),
        "model": os.getenv("MODEL_NAME", "unknown")
    }
