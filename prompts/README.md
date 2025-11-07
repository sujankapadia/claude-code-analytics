# Analysis Prompts

This directory contains prompt templates for different types of conversation analysis.

## Structure

- `*.md` files: Jinja2 prompt templates
- `metadata.yaml`: Metadata about each analysis type (names, descriptions)
- `README.md`: This file

## Adding a New Analysis Type

1. **Create a prompt file**: `prompts/your-analysis.md`
   ```jinja2
   {#
   PROMPT: Your Analysis Name
   PURPOSE: What this analysis does
   AUTHOR: Your name
   CREATED: YYYY-MM-DD
   LAST_UPDATED: YYYY-MM-DD

   Required Variables:
     - transcript (str): The full conversation text

   Optional Variables:
     - (list any optional variables)

   Output Format:
     - (describe expected output structure)

   Notes:
     - (any important notes about this prompt)
   #}

   Your prompt text here...

   {{ transcript }}
   ```

2. **Add metadata**: Edit `metadata.yaml`
   ```yaml
   your-analysis:
     name: "Your Analysis Display Name"
     description: "Short description"
     file: "your-analysis.md"
   ```

3. **Update script**: Add to `choices` in `scripts/analyze_session.py`
   ```python
   parser.add_argument(
       '--type',
       choices=['decisions', 'errors', 'your-analysis'],
       ...
   )
   ```

## Prompt Template Syntax

Prompts use Jinja2 syntax:

- **Variables**: `{{ variable_name }}`
- **Comments**: `{# This is a comment #}`
- **Multi-line comments**:
  ```jinja2
  {#
  Multi-line
  comment
  #}
  ```
- **Conditionals** (if needed):
  ```jinja2
  {% if variable %}
    Content here
  {% endif %}
  ```

## Current Analysis Types

### decisions
- **Purpose**: Extract technical decisions and reasoning
- **Output**: Executive summary, key decisions, revised decisions

### errors
- **Purpose**: Identify error patterns and resolutions
- **Output**: Error breakdown, error pattern summary

## Best Practices

1. **Document thoroughly**: Use Jinja2 comments to explain the prompt
2. **Version tracking**: Update LAST_UPDATED when changing prompts
3. **Test iteratively**: Test prompt changes on sample conversations
4. **Keep focused**: Each prompt should have a single clear purpose
5. **Structure output**: Specify clear output format expectations
