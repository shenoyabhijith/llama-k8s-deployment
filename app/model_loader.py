from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch
import os

def load_model():
    model_name = os.getenv("MODEL_NAME", "meta-llama/Llama-3.2-3B")
    
    # Configure 4-bit quantization for memory efficiency
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    return model, tokenizer
