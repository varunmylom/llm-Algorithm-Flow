from llm_consortium import create_consortium

orchestrator = create_consortium(
    models=["o3-mini:1", "gpt-4o:2", "gemini-2:3"],  # 3 instances of o3-mini, 2 of gpt-4o, and 1 of gemini-2
    confidence_threshold=1,
    max_iterations=6,
    min_iterations=4,
    arbiter="gemini-2",
    raw=True
)

result = orchestrator.orchestrate("151206 152204 082512 062202")

print(f"Synthesized Response: {result['synthesis']['synthesis']}")
print(f"Confidence: {result['synthesis']['confidence']}")
print(f"Analysis: {result['synthesis']['analysis']}")