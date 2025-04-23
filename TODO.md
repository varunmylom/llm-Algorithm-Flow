
- [ ] I beleive this is no longer extracting the final synthesis and saving to its own record in the llm logs.db responses table, like it used to. Either that or the last attempt to do so was not successful.
- [ ] Investigate more robust arbiter response handling. Explore options like:
    - Simplifying the required XML structure.
    - Implementing and testing JSON schema mode for the arbiter prompt.
    - Potentially comparing XML vs JSON schema mode quality/reliability using a meta-consortium.
