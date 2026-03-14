from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Optional
import base64
import logging
import httpx
from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

@router.post("/analyze")
async def analyze_image(
    image: UploadFile = File(...),
    prompt: Optional[str] = "What do you see in this image? Provide a premium, smart analysis as Callista.",
    user_id: str = "default_user"
):
    """
    Analyzes an uploaded image using Llama 3.2 Vision via Groq.
    """
    try:
        # Read and encode image content
        contents = await image.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        # Prepare Groq API request
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.5,
            "max_tokens": 1024
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            
        if response.status_code != 200:
            logger.error(f"Groq Vision API error: {response.text}")
            raise HTTPException(status_code=500, detail="Vision AI failed to respond.")
            
        result = response.json()
        analysis = result["choices"][0]["message"]["content"]
        
        return {"analysis": analysis}

    except Exception as e:
        logger.error(f"Error in vision analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
