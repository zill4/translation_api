import random

class MockTranslationService:
    @staticmethod
    def translate(text, source_lang, source_dialect, target_lang, target_dialect):
        # This is a mock translation service that simulates Llama 3 8b responses
        # In a real implementation, this would call the Llama 3 8b API
        
        # Simulate translation by adding some random characters to the original text
        translated_text = text + ' ' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=5))
        
        return {
            'original_text': text,
            'translated_text': translated_text,
            'source_lang': source_lang,
            'source_dialect': source_dialect,
            'target_lang': target_lang,
            'target_dialect': target_dialect
        }

translation_service = MockTranslationService()
