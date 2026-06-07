from google import genai
client = client.genai(api_key = "AIzaSyA5Frabwr7DBJDmNR6a_15P-4PB22dcoOA")

response = client.models.generate_key(
    model = "gemini-2.5-flash",
    contents = "block amount money of germany of student visa in 2026"
)

print(response.contents)


get_model(
    nullable = False,
    unique = True,
    setattr = map,
    contents = "contents",
    config = "config",  
)