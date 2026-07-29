import google.generativeai as genai

genai.configure(
    api_key="gemini_api_key"
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)
def get_ai_response(message):

    response = model.generate_content(message)

    return response.text
