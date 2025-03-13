from llm_consortium import create_consortium

# Create a consortium with multiple models, showing the new features
orchestrator = create_consortium(
    models=["claude-3-haiku", "gpt-4o", "gemini-pro"],  # 1 instance of each model
    confidence_threshold=0.8,
    max_iterations=3,
    min_iterations=1,
    arbiter="claude-3-haiku",
    show_arbiter=True,  # Show arbiter analysis (can be set to False to hide)
    raw=True  # Show individual model responses for demonstration
)

# Run the consortium with a sample prompt
result = orchestrator.orchestrate("What are the key considerations when designing a multi-model LLM agent?")

# Display results - these will now include the consortium_id
print(f"\nSynthesized Response: {result['synthesis']['synthesis']}")
print(f"Confidence: {result['synthesis']['confidence']}")
print(f"Analysis: {result['synthesis']['analysis']}")
print(f"Consortium ID: {result['metadata']['consortium_id']}")  # New: Display the consortium_id
