
from openai import OpenAI

client = OpenAI(
    api_key="8TcilqiSoUXtWGQMWsTRkop5Z8JXp0eME0Ey8albHXPG6kTH6HIfJQQJ99CBACHYHv6XJ3w3AAAAACOGMeo8",
    base_url="https://ai-vondudio9925ai384200949027.openai.azure.com/openai/v1/"
)

response = client.responses.create(
    model="gpt-5.3-codex",
    input="create python code to generate the first 25 prime numbers"
)

print(response.output[0].content[0].text)
