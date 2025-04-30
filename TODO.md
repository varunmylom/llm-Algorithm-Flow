- [ ] when using llm consortium save -m model1 -n 2 -m model2 --arbiter arbiter_model 
- [ ] fix the problem when model name includes ':free'
- [ ]  llm consortium save free-qwen -m qwen/qwen3-235b-a22b:free:2 -m qwen/qwen3-32b:free:2 -m tngtech/deepseek-r1t-chimera:free --arbite
r deepseek/deepseek-r1-zero:free --max-iterations 1
Error: Invalid count for model qwen/qwen3-235b-a22b: free:2
 llm consortium save free-qwen -m qwen/qwen3-235b-a22b:free -n 1 -m qwen/qwen3-32b:free -n 2 -m tngtech/deepseek-r1t-chimera:free -n 1 --arbiter deepseek/deepseek-r1-zero:free --max-iterations 1
Error: Invalid count for model qwen/qwen3-235b-a22b: free