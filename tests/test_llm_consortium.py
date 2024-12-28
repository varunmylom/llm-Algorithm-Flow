import unittest
from unittest.mock import patch, MagicMock
import asyncio
from llm_consortium import ConsortiumOrchestrator, DatabaseConnection

class TestConsortiumOrchestrator(unittest.TestCase):
    def setUp(self):
        self.orchestrator = ConsortiumOrchestrator(
            models=["model1", "model2"],
            confidence_threshold=0.8,
            max_iterations=3,
            arbiter="arbiter_model"
        )

    @patch('llm_consortium.llm.get_model')
    @patch('llm_consortium.DatabaseConnection.get_connection')
    def test_get_model_response(self, mock_db_connection, mock_get_model):
        mock_model = MagicMock()
        mock_model.prompt.return_value.text.return_value = "<confidence>0.75</confidence>Test response"
        mock_get_model.return_value = mock_model

        async def run_test():
            result = await self.orchestrator._get_model_response("model1", "Test prompt")
            self.assertEqual(result["model"], "model1")
            self.assertEqual(result["response"], "<confidence>0.75</confidence>Test response")
            self.assertEqual(result["confidence"], 0.75)

        asyncio.run(run_test())

    def test_parse_confidence_value(self):
        self.assertEqual(self.orchestrator._parse_confidence_value("<confidence>0.75</confidence>"), 0.75)
        self.assertEqual(self.orchestrator._parse_confidence_value("Confidence: 80%"), 0.8)
        self.assertEqual(self.orchestrator._parse_confidence_value("No confidence value"), 0.5)

    @patch('llm_consortium.llm.get_model')
    @patch('llm_consortium.DatabaseConnection.get_connection')
    def test_synthesize_responses(self, mock_db_connection, mock_get_model):
        mock_arbiter = MagicMock()
        mock_arbiter.prompt.return_value.text.return_value = """
        <synthesis_output>
            <synthesis>Synthesized response</synthesis>
            <confidence>0.85</confidence>
            <analysis>Analysis of responses</analysis>
            <dissent>Dissenting views</dissent>
            <needs_iteration>false</needs_iteration>
            <refinement_areas>
                Area 1
                Area 2
            </refinement_areas>
        </synthesis_output>
        """
        mock_get_model.return_value = mock_arbiter

        async def run_test():
            responses = [
                {"model": "model1", "response": "Response 1", "confidence": 0.7},
                {"model": "model2", "response": "Response 2", "confidence": 0.8}
            ]

            result = await self.orchestrator._synthesize_responses("Original prompt", responses)

            self.assertEqual(result["synthesis"], "Synthesized response")
            self.assertEqual(result["confidence"], 0.85)
            self.assertEqual(result["analysis"], "Analysis of responses")
            self.assertEqual(result["dissent"], "Dissenting views")
            self.assertFalse(result["needs_iteration"])
            self.assertEqual(result["refinement_areas"], ["Area 1", "Area 2"])

        asyncio.run(run_test())

    @patch.object(ConsortiumOrchestrator, '_get_model_responses')
    @patch.object(ConsortiumOrchestrator, '_synthesize_responses')
    def test_orchestrate(self, mock_synthesize, mock_get_responses):
        mock_get_responses.return_value = [
            {"model": "model1", "response": "Response 1", "confidence": 0.7},
            {"model": "model2", "response": "Response 2", "confidence": 0.8}
        ]
        mock_synthesize.return_value = {
            "synthesis": "Final synthesis",
            "confidence": 0.9,
            "analysis": "Final analysis",
            "dissent": "Final dissent",
            "needs_iteration": False,
            "refinement_areas": []
        }

        async def run_test():
            result = await self.orchestrator.orchestrate("Test prompt")

            self.assertEqual(result["original_prompt"], "Test prompt")
            self.assertEqual(len(result["model_responses"]), 2)
            self.assertEqual(result["synthesis"]["synthesis"], "Final synthesis")
            self.assertEqual(result["synthesis"]["confidence"], 0.9)
            self.assertEqual(result["metadata"]["models_used"], ["model1", "model2"])
            self.assertEqual(result["metadata"]["arbiter"], "arbiter_model")
            self.assertEqual(result["metadata"]["iteration_count"], 1)

        asyncio.run(run_test())

class TestDatabaseConnection(unittest.TestCase):
    @patch('llm_consortium.sqlite_utils.Database')
    def test_get_connection(self, mock_database):
        connection1 = DatabaseConnection.get_connection()
        connection2 = DatabaseConnection.get_connection()

        self.assertIs(connection1, connection2)
        mock_database.assert_called_once()

if __name__ == '__main__':
    unittest.main()
