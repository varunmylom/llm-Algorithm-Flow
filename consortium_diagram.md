# LLM Consortium Algorithm Diagram

```mermaid
graph TB
    subgraph Initialization
        A[Start] --> B[Initialize Consortium]
        B --> C[Load Configuration]
        C --> D[Set System Prompt]
    end

    subgraph Orchestration
        D --> E[Receive User Prompt]
        E --> F[Start Iteration Loop]
        F --> G{Max Iterations Reached?}
        G -- No --> H[Get Model Responses]
        H --> I[Synthesize Responses]
        I --> J[Evaluate Confidence]
        J --> K{Confidence Threshold Met?}
        K -- No --> L[Prepare Next Iteration]
        L --> F
        K -- Yes --> M[Generate Final Answer]
        G -- Yes --> M
    end

    subgraph Model_Responses
        H --> N1[Model 1]
        H --> N2[Model 2]
        H --> N3[Model 3]
        N1 --> O[Collect Responses]
        N2 --> O
        N3 --> O
    end

    subgraph Synthesis
        O --> P[Arbiter Model]
        P --> Q[Parse XML Response]
        Q --> R[Extract Synthesis]
        Q --> S[Extract Confidence]
        Q --> T[Extract Analysis]
    end

    subgraph Output
        M --> U[Format Final Result]
        U --> V[Save to JSON if requested]
        U --> W[Display Result]
    end

    classDef blue fill:#3498db,stroke:#333,stroke-width:2px;
    classDef green fill:#2ecc71,stroke:#333,stroke-width:2px;
    classDef orange fill:#e67e22,stroke:#333,stroke-width:2px;
    classDef red fill:#e74c3c,stroke:#333,stroke-width:2px;
    classDef purple fill:#9b59b6,stroke:#333,stroke-width:2px;

    class A,B,C,D blue;
    class E,F,G,K,M green;
    class H,N1,N2,N3,O orange;
    class I,J,P,Q,R,S,T purple;
    class U,V,W red;
```

This diagram illustrates the LLM Consortium algorithm, highlighting the following key components:

1. **Initialization** (Blue): The process starts by initializing the consortium, loading the configuration, and setting the system prompt.

2. **Orchestration** (Green): This section shows the main iteration loop, including checking for max iterations and confidence thresholds.

3. **Model Responses** (Orange): Multiple models generate responses in parallel.

4. **Synthesis** (Purple): The arbiter model synthesizes the responses, extracting key information through XML parsing.

5. **Output** (Red): The final result is formatted, optionally saved to a JSON file, and displayed to the user.

The color-coding helps to differentiate the various stages of the process, making it easier to understand the flow of the algorithm.
