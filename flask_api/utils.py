import re

def detect_language(text):
    # This is a simplified language detection function
    # In a real-world scenario, you would use a more sophisticated library or API
    
    # Define some common words for each language
    language_words = {
        'en': ['the', 'be', 'to', 'of', 'and', 'in', 'that', 'have', 'it', 'for'],
        'es': ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'ser', 'se', 'no'],
        'fr': ['le', 'la', 'de', 'et', 'est', 'pas', 'un', 'vous', 'que', 'qui'],
        # Add more languages as needed
    }

    text = text.lower()
    words = re.findall(r'\b\w+\b', text)
    
    language_scores = {lang: sum(1 for word in words if word in lang_words) for lang, lang_words in language_words.items()}
    
    detected_language = max(language_scores, key=language_scores.get)
    
    # For simplicity, we'll assume the dialect is always the first option
    dialect_map = {'en': 'US', 'es': 'ES', 'fr': 'FR'}
    
    return detected_language, dialect_map.get(detected_language, 'Unknown')
