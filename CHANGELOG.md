Release 2025.02.01
- Merge branch 'feature/n-species'
- Update to version 0.4: Add new features and update documentation
- cleanup: removed temporary database, script and log files
- Remove .artefacts from Git tracking and add to .gitignore
- Update cfr-example.md
- Implement asynchronous response logging and improve error handling
- Remove backup file for model consortium implementation
- feat: Integrate consortium model capabilities with logging and documentation updates

Release 2025.02.02
- Update to version 0.5:
  - Introduced the `model:count` syntax for specifying the number of instances for each model in the consortium (primarily for the Python API; the CLI uses `-m model -n count`).
  - Improved consortium configuration management to support instance counts.
  - Enhanced logging to track model instances and their responses more effectively.
  - **Performance Enhancement:** Implemented parallel processing for improved consortium execution speed.
