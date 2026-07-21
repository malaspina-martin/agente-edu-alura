import google.generativeai as genai

api_key = input("API Key: ")

genai.configure(api_key=api_key)

print("Modelos disponibles:\n")

for m in genai.list_models():
    print(m.name)