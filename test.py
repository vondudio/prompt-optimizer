
from openai import OpenAI

client = OpenAI(
    api_key="",
    base_url=""
)

response = client.responses.create(
    model="gpt-5.3-codex",
    input="create python code to generate the first 25 prime numbers"
)

print(response.output[0].content[0].text)
