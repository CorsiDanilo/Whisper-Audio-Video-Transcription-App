import logging
from config import load_default_values, get_gemini_api_key
import google.generativeai as genai

default_values = load_default_values()

def initialize_model(gemini_model):
    """Initialize the Gemini model with the specified configurations."""
    def gemini_configurations():
        gemini_config = default_values['gemini']
        generation_config = {
            "temperature": gemini_config["temperature"],
            "top_p": gemini_config["top_p"],
            "top_k": gemini_config["top_k"],
            "max_output_tokens": gemini_config["max_output_tokens"],
            "response_mime_type": gemini_config["response_mime_type"],
        }

        safety_settings = [
            {
                "category": gemini_config['safety_settings']["harm_category_harassment"]['name'],
                "threshold": gemini_config['safety_settings']["harm_category_harassment"]['threshold'],
            },
            {
                "category": gemini_config['safety_settings']["harm_category_hate_speech"]['name'],
                "threshold": gemini_config['safety_settings']["harm_category_hate_speech"]['threshold'],
            },
            {
                "category": gemini_config['safety_settings']["harm_category_sexually_explicit"]['name'],
                "threshold": gemini_config['safety_settings']["harm_category_sexually_explicit"]['threshold'],
            },
            {
                "category": gemini_config['safety_settings']["harm_category_dangerous_content"]['name'],
                "threshold": gemini_config['safety_settings']["harm_category_dangerous_content"]['threshold']
            },
        ]
        return generation_config, safety_settings

    GEMINI_API_KEY = get_gemini_api_key()
    genai.configure(api_key=GEMINI_API_KEY)
    generation_config, safety_settings = gemini_configurations()
    model = genai.GenerativeModel(
        model_name=gemini_model,
        safety_settings=safety_settings,
        generation_config=generation_config,
    )
    return model

def query_gemini(user_input, transcription, gemini_model):
    """Executes a query to the Gemini API using the transcribed text and user input."""
    try:
        model = initialize_model(gemini_model)
        query = f"Transcription: {transcription}\n\nUser Input: {user_input}"
        response = model.generate_content(query).text
        return response
    except Exception as e:
        logging.error(f"Error querying Gemini: {e}")
        return f"Error querying Gemini: {e}"
