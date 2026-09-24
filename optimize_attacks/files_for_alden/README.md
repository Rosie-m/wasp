### 1. OpenAI API Key

```
OPENAI_API_KEY=...
```

Please use `gpt-5-mini` to get started, and do not use `*-pro` models (they are very expensive).

### 2. File `instantiated_prompt_injections_config.json`

This file contains a list of JSON objects, each object contains a `instantiated_instruction` field, which is the attack string, i.e., description of GitLab issue.
So it looks like this in a webpage (one example of an attack I adapted from the WASP attacks): 

<img src="/Users/luoxim/Desktop/Screenshot 2025-11-10 at 11.50.55 PM.png" alt="Screenshot 2025-11-10 at 11.50.55 PM" style="zoom:50%;" />

### 3. Dir `prompts`

It includes `system_prompt.txt` and `user_prompt.txt`. The system prompt is the same across all the tasks. The user prompt is instantiated with one WASP attack (create a deploy token). See elements 1659 and arounds. I put `{attack_before_link_text}` and `{after_action_text}` around the attack goal, but feel free to change whatever.

The input to the model will be a concatenation of system prompt and user prompt.
