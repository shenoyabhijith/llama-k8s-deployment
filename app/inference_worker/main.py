import asyncio
import json
import os
import time
from typing import Dict, Any

from redis.asyncio import Redis
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch


def get_env(name: str, default: str) -> str:
    return os.getenv(name, default)


REDIS_URL = get_env("REDIS_URL", "redis://redis:6379/0")
MODEL_NAME = get_env("MODEL_NAME", "meta-llama/Llama-3.2-3B")
RESULT_TTL_SECONDS = int(get_env("RESULT_TTL_SECONDS", "86400"))
CACHE_TTL_SECONDS = int(get_env("CACHE_TTL_SECONDS", "86400"))


async def load_model():
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        quantization_config=bnb_config,
        device_map="auto",
    )
    return model, tokenizer


async def process_jobs():
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    model, tokenizer = await load_model()

    try:
        while True:
            job = await redis.blpop("jobs", timeout=5)
            if job is None:
                await asyncio.sleep(0.2)
                continue
            _, data = job
            payload = json.loads(data)

            request_id = payload["request_id"]
            text = payload["text"]
            max_tokens = int(payload.get("max_tokens", 256))
            temperature = float(payload.get("temperature", 0.7))
            cache_key = payload.get("cache_key")

            channel = f"tokens:{request_id}"
            result_key = f"result:{request_id}"

            # Run generation
            start = time.time()
            inputs = tokenizer(text, return_tensors="pt").to(model.device)

            # Greedy-ish generation with sampling
            with torch.no_grad():
                outputs = model.generate(
                    inputs.input_ids,
                    max_length=min(inputs.input_ids.shape[1] + max_tokens, 2048),
                    temperature=temperature,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

            response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Publish token stream (approximate by whitespace tokens)
            for token in response_text.split():
                await redis.publish(channel, token)
            await redis.publish(channel, "__DONE__")

            # Store final result
            result: Dict[str, Any] = {
                "response": response_text,
                "processing_time_ms": round((time.time() - start) * 1000, 2),
                "model": MODEL_NAME,
            }
            await redis.set(result_key, json.dumps(result), ex=RESULT_TTL_SECONDS)

            # Cache by content
            if cache_key:
                await redis.set(f"cache:{cache_key}", json.dumps(result), ex=CACHE_TTL_SECONDS)

    finally:
        await redis.close()


if __name__ == "__main__":
    asyncio.run(process_jobs())


