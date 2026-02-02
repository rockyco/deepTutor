"""GL Assessment English prompt templates.

Covers comprehension (with passages), vocabulary, grammar, spelling, and punctuation.
"""

ENGLISH_SYSTEM = """You are an expert 11+ exam question writer specializing in GL Assessment English.
You write questions for Year 5 students (age 10-11) preparing for selective school entrance exams.

CRITICAL RULES:
1. Comprehension passages must require INFERENCE, not just literal recall.
2. Use vocabulary at Year 5-6 level: endearing, adorned, magnificent, proclaimed, reluctant,
   peculiar, astonished, resemble, conspicuous, prominent.
3. Include 'No mistake' or 'No error' as one option where appropriate (characteristic GL format).
4. Grammar questions must test precise grammatical terminology (determiner, subordinate clause,
   relative pronoun, etc.).
5. Vary the position of the correct answer across A-E.
6. Return ONLY a JSON array. No markdown, no commentary."""


ENGLISH_TYPES = {
    "comprehension": {
        "description": "Reading passage + inference/analysis questions",
        "examples": [
            {
                "passage": "The old lighthouse keeper peered through the rain-streaked window. For forty years, he had watched ships navigate the treacherous rocks below. Tonight, however, something was different. The usual rhythm of the waves had changed to an angry, relentless pounding, and the beam of his lighthouse seemed to be swallowed by the darkness before it could reach the water.",
                "text": "What does the phrase 'swallowed by the darkness' suggest?",
                "options": [
                    "The lighthouse had broken down",
                    "The storm was extremely severe",
                    "It was very late at night",
                    "The keeper needed new light bulbs",
                    "The rocks were blocking the light",
                ],
                "answer": "The storm was extremely severe",
            },
        ],
        "guidance": """Generate a passage of 80-150 words, then 1 question about it.
Passages should be age-appropriate fiction or non-fiction with rich vocabulary.
Questions should test: inference (what does this suggest/imply?), vocabulary in context
(what does the word X mean here?), author's purpose, character analysis, or theme.
Do NOT ask simple fact-retrieval questions that can be answered by copying from the text.
Use sophisticated but accessible vocabulary in the passage.""",
    },
    "vocabulary": {
        "description": "Word meanings, synonyms, antonyms, word-in-context, odd word out",
        "examples": [
            {
                "text": "Which word is closest in meaning to 'reluctant'?",
                "options": ["eager", "hesitant", "confused", "angry", "satisfied"],
                "answer": "hesitant",
            },
            {
                "text": "Which word is most opposite in meaning to 'magnificent'?",
                "options": ["ordinary", "terrible", "ugly", "pathetic", "dreadful"],
                "answer": "ordinary",
                "note": "Opposite of magnificent (grand/impressive) is ordinary (plain/unremarkable), not terrible or ugly which are different dimensions.",
            },
        ],
        "guidance": """Mix question types: synonyms, antonyms, word-in-context, odd-word-out.
Use Year 5-6 vocabulary: conspicuous, abundant, cautious, diligent, feeble,
ingenious, jubilant, luminous, meander, obscure, tranquil, vivid.
For antonyms, the correct answer should be the TRUE opposite (not just a negative word).
Distractors should be real words from similar semantic fields.""",
    },
    "grammar": {
        "description": "Word classes, sentence structure, tenses, grammatical terminology",
        "examples": [
            {
                "text": "Which word is a determiner in the sentence below?\n\n'Several children from the school were playing happily in the park.'",
                "options": ["Several", "children", "happily", "playing", "park"],
                "answer": "Several",
                "note": "'Several' is a determiner (specifies quantity of the noun). GL tests precise grammatical terminology.",
            },
            {
                "text": "Which sentence uses the correct form of the verb?",
                "options": [
                    "The team has played their best game yet.",
                    "The team have played their best game yet.",
                    "The team has played its best game yet.",
                    "The team have played its best game yet.",
                    "No mistake",
                ],
                "answer": "The team has played its best game yet.",
                "note": "'Team' is a collective noun treated as singular in standard British English.",
            },
        ],
        "guidance": """Test: determiners, prepositions, conjunctions, relative pronouns, subordinate clauses,
active vs passive voice, subject-verb agreement, correct tense usage.
Use complex sentences with semicolons, embedded clauses, and sophisticated punctuation.
Questions should test PRECISE grammatical knowledge, not vague 'which sounds right'.""",
    },
    "spelling": {
        "description": "Identify correctly/incorrectly spelled words, homophones in context",
        "examples": [
            {
                "text": "Which sentence contains a spelling mistake?",
                "options": [
                    "The children received their certificates at assembly.",
                    "The whether forecast predicted heavy rain.",
                    "She carefully measured the ingredients.",
                    "The ancient castle had a mysterious atmosphere.",
                    "No mistake",
                ],
                "answer": "The whether forecast predicted heavy rain.",
                "note": "'whether' should be 'weather'. Homophone error.",
            },
        ],
        "guidance": """Focus on: commonly confused homophones (their/there/they're, weather/whether,
affect/effect, practise/practice, stationary/stationery), silent letters,
double consonants, and -tion/-sion/-cian endings.
Include 'No mistake' as an option. The errors should be PLAUSIBLE mistakes
that a student might actually make (not obvious typos).""",
    },
    "punctuation": {
        "description": "Spot punctuation errors, correct usage of apostrophes, commas, colons, semicolons",
        "examples": [
            {
                "text": "Which sentence has a punctuation error?",
                "options": [
                    "The dog's bone was buried in the garden.",
                    "Its a beautiful day for a picnic.",
                    "She couldn't believe what she saw.",
                    "\"Come quickly!\" shouted the teacher.",
                    "No mistake",
                ],
                "answer": "Its a beautiful day for a picnic.",
                "note": "'Its' should be 'It's' (contraction of 'it is'). Common error: confusing possessive 'its' with contraction 'it's'.",
            },
        ],
        "guidance": """Test: apostrophes for contraction vs possession, its/it's, commas in lists
and subordinate clauses, colons and semicolons, speech marks, capital letters
after speech marks. Include 'No mistake' option. Errors should be common mistakes
(not missing full stops or obvious errors).""",
    },
}


def get_english_prompt(qtype: str, count: int) -> str:
    """Build a GL-calibrated English generation prompt."""
    type_info = ENGLISH_TYPES.get(qtype, ENGLISH_TYPES["comprehension"])

    examples_text = ""
    for i, ex in enumerate(type_info["examples"], 1):
        passage = ex.get("passage", "")
        passage_str = f'\nPassage: "{passage}"' if passage else ""
        note = ex.get("note", "")
        examples_text += f"""
EXAMPLE {i}:{passage_str}
Question: {ex['text']}
Options: {ex['options']}
Answer: {ex['answer']}
{"Note: " + note if note else ""}
"""

    passage_format = ""
    if qtype == "comprehension":
        passage_format = """
Each question object must include a "passage" field in the content:
    "content": {
      "text": "[Question about the passage]",
      "passage": "[The full reading passage, 80-150 words]",
      "options": [...]
    }"""

    return f"""Generate {count} GL Assessment English "{qtype}" questions for Year 5 (age 10-11).

TOPIC: {qtype} - {type_info['description']}

{type_info['guidance']}

{examples_text}

Return a JSON array of exactly {count} objects:
[
  {{
    "subject": "english",
    "question_type": "{qtype}",
    "format": "multiple_choice",
    "difficulty": 3,
    "content": {{
      "text": "[Question text]",{passage_format}
      "options": ["Option A", "Option B", "Option C", "Option D", "Option E"]
    }},
    "answer": {{ "value": "[Exact text of correct option]" }},
    "explanation": "[Why this answer is correct]",
    "hints": [],
    "tags": ["{qtype}"],
    "source": "LLM Generated"
  }}
]

CRITICAL: Every answer must be correct. For spelling/punctuation, verify the identified error is real.
Include 'No mistake' as an option where the question type calls for it.
Vary the correct answer position across A-E."""
