import unittest
from unittest.mock import MagicMock
import re
import llm_consortium
from llm_consortium import ConsortiumOrchestrator

class TestConfidenceParsing(unittest.TestCase):
    def setUp(self):
        self.orchestrator = ConsortiumOrchestrator(
            models=["model1", "model2"],
            confidence_threshold=0.8,
            max_iterations=3,
            arbiter="arbiter_model"
        )
    
    def test_extract_confidence_with_tag(self):
        # Test with <confidence> tag
        text = "Some text <confidence>0.85</confidence> more text"
        result = self.orchestrator._extract_confidence(text)
        self.assertEqual(result, 0.85)
    
    def test_extract_confidence_with_percentage(self):
        # Test with percentage format
        text = "Confidence: 75%"
        result = self.orchestrator._extract_confidence(text)
        self.assertEqual(result, 0.75)
    
    def test_extract_confidence_with_decimal(self):
        # Test with decimal format
        text = "Confidence is 0.92"
        result = self.orchestrator._extract_confidence(text)
        self.assertEqual(result, 0.92)
    
    def test_extract_confidence_no_value(self):
        # Test with no confidence value
        text = "No confidence value present"
        result = self.orchestrator._extract_confidence(text)
        self.assertEqual(result, 0.5)  # Default value
    
    def test_parse_confidence_value_with_tag(self):
        # Test parsing with tag
        text = "<confidence>0.85</confidence>"
        result = self.orchestrator._parse_confidence_value(text, 0.5)
        self.assertEqual(result, 0.85)
    
    def test_parse_confidence_value_with_percentage(self):
        # Test parsing with percentage
        text = "Confidence: 75%"
        result = self.orchestrator._parse_confidence_value(text, 0.5)
        self.assertEqual(result, 0.75)
    
    def test_parse_confidence_value_with_decimal(self):
        # Test parsing with decimal
        text = "Confidence is 0.92"
        result = self.orchestrator._parse_confidence_value(text, 0.5)
        self.assertEqual(result, 0.92)
    
    def test_parse_confidence_value_no_value(self):
        # Test parsing with no confidence value
        text = "No confidence value present"
        result = self.orchestrator._parse_confidence_value(text, 0.4)
        self.assertEqual(result, 0.4)  # Should use provided default
    
    def test_parse_confidence_value_multiple_matches(self):
        # Test with multiple confidence values, should take the first one
        text = "<confidence>0.85</confidence> and later <confidence>0.75</confidence>"
        result = self.orchestrator._parse_confidence_value(text, 0.5)
        self.assertEqual(result, 0.85)
    
    def test_parse_confidence_value_invalid_value(self):
        # Test with invalid confidence value
        text = "<confidence>invalid</confidence>"
        result = self.orchestrator._parse_confidence_value(text, 0.5)
        self.assertEqual(result, 0.5)  # Should use provided default

if __name__ == '__main__':
    unittest.main()
