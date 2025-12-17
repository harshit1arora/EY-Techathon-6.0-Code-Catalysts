from groq import Groq
import os

client = Groq(api_key=os.getenv("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"))

resp = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello"}]
)

print(resp.choices[0].message.content)
