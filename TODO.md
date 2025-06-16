Need to fix the following errors in the arbiter response parsing:

llm -m CON_gemini-2.5-flash-preview-04-17x3JR "Quickly, which is greater 101.9 or 101.11?"
2025-06-16 17:58:03,113 - llm_consortium - ERROR - Error parsing arbiter response: Top-ranked response ID 2 not found.
2025-06-16 17:58:03,113 - llm_consortium - ERROR - Error parsing arbiter response: Top-ranked response ID 2 not found.
<ranking>
    <rank position="1">2</rank>
    <rank position="2">1</rank>
    <rank position="3">3</rank>
</ranking>
    ~/Projects/llm/pl/Utilities/llm-consortium/llm-consortium-fix    feature/judging-methods *6 !3 ?9  llm -m CON_gemini-2.5-flash-preview-04-17x3Jp1 "Quickly, which is greater 101.9 or 101.11?"
2025-06-16 17:58:27,897 - llm_consortium - ERROR - Error parsing arbiter response: Arbiter chose response ID 2, but this ID was not found.
2025-06-16 17:58:27,897 - llm_consortium - ERROR - Error parsing arbiter response: Arbiter chose response ID 2, but this ID was not found.
<winner>
    <response_id>2</response_id>
</winner>
    ~/Projects/llm/pl/Utilities/llm-consortium/llm-consortium-fix    feature/judging-methods *6 !3 ?9  llm -m CON_gemini-2.5-flash-preview-04-17x3Jp1 "Quickly, which is greater 101.9 or 101.11?"
2025-06-16 17:58:52,235 - llm_consortium - ERROR - Error parsing arbiter response: Arbiter chose response ID 3, but this ID was not found.
2025-06-16 17:58:52,235 - llm_consortium - ERROR - Error parsing arbiter response: Arbiter chose response ID 3, but this ID was not found.
<winner>
    <response_id>3</response_id>
</winner>
    ~/Projects/llm/pl/Utilities/llm-consortium/llm-consortium-fix    feature/judging-methods *6 !3 ?9  llm -m CON_gemini-2.5-flash-preview-04-17x3JR "Quickly, which is greater 101.9 or 101.11?" 
2025-06-16 17:59:03,783 - llm_consortium - ERROR - Error parsing arbiter response: Top-ranked response ID 1 not found.
2025-06-16 17:59:03,783 - llm_consortium - ERROR - Error parsing arbiter response: Top-ranked response ID 1 not found.
<ranking>
    <rank position="1">1</rank>
    <rank position="2">2</rank>
    <rank position="3">3</rank>
</ranking>


And as well as fixing the above errors, or as a way of fixing the above errors, we need to track llm response IDs better and be able to output the llm response for response.id of the chosen answer. We also need to improve logging and tracking so that we can better evaluate model performance and arbiter decisions.

Interactively interview me using zenity, after you have researched the issue and the codebase of the relevant packages. The llm project is at /home/thomas/Projects/llm/my-llm and the docs are in /home/thomas/Projects/llm/my-llm/docs. 
the database is at /home/thomas/.config/io.datasette.llm/logs.db