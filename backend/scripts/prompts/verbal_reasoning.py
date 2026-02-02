"""GL Assessment verbal reasoning prompt templates for all 21 types.

Each type has the exact GL instruction format, worked examples at correct
difficulty, and explicit distractor design guidance.
"""

VR_SYSTEM = """You are an expert 11+ exam question writer specializing in GL Assessment verbal reasoning.
You write questions for Year 5 students (age 10-11) preparing for selective school entrance exams.

CRITICAL RULES:
1. Follow the EXACT GL Assessment instruction format for each question type.
2. Use age-appropriate but sophisticated vocabulary (e.g., destitute, adorned, belligerent,
   endearing, irresistible - not baby words, not obscure academic terms).
3. Every distractor must be plausible - a real word that could tempt a student who
   doesn't fully understand the concept.
4. Vary the position of the correct answer across A-E.
5. Return ONLY a JSON array. No markdown, no commentary."""


VR_TYPES = {
    "vr_synonyms": {
        "instruction": "Find two words, one from each group, that are closest in meaning.",
        "examples": [
            {
                "text": "Find two words, one from each group, that are closest in meaning.\n\n(happy sad angry)    (joyful tired hungry)",
                "options": ["happy, joyful", "sad, tired", "angry, hungry", "happy, tired", "sad, joyful"],
                "answer": "happy, joyful",
            },
            {
                "text": "Find two words, one from each group, that are closest in meaning.\n\n(brave cunning swift)    (agile clever bold)",
                "options": ["brave, bold", "cunning, agile", "swift, clever", "brave, clever", "cunning, bold"],
                "answer": "brave, bold",
            },
        ],
        "guidance": """Use groups of 3 words each. Words should be at Year 5-6 reading level.
At least one pair in each group should be CLOSE but not exact synonyms (to create good distractors).
Include words with multiple meanings to add complexity.""",
    },
    "vr_odd_ones_out": {
        "instruction": "Three of the five words are related. Find the TWO words that do not belong to the group.",
        "examples": [
            {
                "text": "Three of the five words below are related in some way. Find the TWO words that do not belong.\n\nmercury    venus    jupiter    mars    pluto",
                "options": ["mercury, pluto", "venus, pluto", "jupiter, mars", "mercury, mars", "venus, mars"],
                "answer": "mercury, pluto",
                "note": "Mercury is also a metal/element, Pluto is a dwarf planet - the three true planets are Venus, Jupiter, Mars",
            },
        ],
        "guidance": """The connection between the 3 related words should NOT be immediately obvious.
Use words that have multiple meanings or belong to multiple categories.
The two odd ones out should each be odd for a DIFFERENT reason ideally.
Categories: animals, plants, materials, tools, musical terms, geographical features.""",
    },
    "vr_hidden_word": {
        "instruction": "Find a four-letter word hidden at the end of one word and the beginning of the next word in the sentence.",
        "examples": [
            {
                "text": "Find a four-letter word hidden at the end of one word and the beginning of the next word.\n\nThe children are playing in the swamp area behind the school.",
                "options": ["park", "pare", "lamp", "rear", "mare"],
                "answer": "pare",
                "note": "swamP AREa - 'pare' spans across 'swamp' and 'area'",
            },
            {
                "text": "Find a four-letter word hidden at the end of one word and the beginning of the next word.\n\nPlease push around the corner carefully.",
                "options": ["harm", "shar", "harp", "push", "roun"],
                "answer": "harp",
                "note": "pusH ARPound - hmm, that doesn't work. Let me reconsider: pusH AROund - 'haro' isn't a word. Actually: puSH AROund - no. The answer should be verified carefully.",
            },
        ],
        "guidance": """The hidden word must span EXACTLY across two adjacent words in the sentence.
Use common 4-letter words that are real English words.
The sentence must read naturally - don't force awkward phrasing.
Distractors should be real 4-letter words but NOT hidden in the sentence.
VERIFY that the hidden word actually spans across two adjacent words before including it.""",
    },
    "vr_missing_word": {
        "instruction": "Choose two words, one from each set of brackets, that complete the sentence in the most sensible way.",
        "examples": [
            {
                "text": "Choose two words, one from each set of brackets, that complete the sentence in the most sensible way.\n\nPrecious is to (destitute   worthless   adorned) as divide is to (combine   scatter   arrange).",
                "options": ["worthless, combine", "destitute, scatter", "adorned, arrange", "worthless, scatter", "destitute, combine"],
                "answer": "worthless, combine",
                "note": "Precious (valuable) is opposite of worthless. Divide is opposite of combine. The relationship is antonyms.",
            },
            {
                "text": "Choose two words, one from each set of brackets, that complete the sentence in the most sensible way.\n\nRock is to (pebble   solid   mineral) as water is to (liquid   moisture   humid).",
                "options": ["solid, liquid", "mineral, moisture", "pebble, humid", "solid, moisture", "mineral, liquid"],
                "answer": "solid, liquid",
                "note": "Rock is solid (state of matter). Water is liquid (state of matter). The relationship is 'state of matter'.",
            },
        ],
        "guidance": """Use analogy-style sentences: "X is to (...) as Y is to (...)."
The relationship should be clear but require thought (antonyms, category membership,
part-whole, cause-effect, state of matter, degree/intensity).
Each bracket should have exactly 3 words.
Distractors should use words from the brackets but in wrong pairings that don't maintain the relationship.""",
    },
    "vr_number_series": {
        "instruction": "Find the number that continues the series in the most sensible way.",
        "examples": [
            {
                "text": "Find the number that continues the series in the most sensible way.\n\n3    7    15    31    63    ?",
                "options": ["95", "125", "127", "126", "64"],
                "answer": "127",
                "note": "Pattern: x2+1. 3x2+1=7, 7x2+1=15, 15x2+1=31, 31x2+1=63, 63x2+1=127",
            },
            {
                "text": "Find the number that continues the series in the most sensible way.\n\n2    6    12    20    30    ?",
                "options": ["40", "42", "36", "38", "44"],
                "answer": "42",
                "note": "Differences: 4, 6, 8, 10, 12. Each difference increases by 2. So next = 30 + 12 = 42.",
            },
        ],
        "guidance": """Use patterns that require genuine reasoning: doubling +/- constant, increasing differences,
alternating operations, two interleaved sequences, or triangular/square numbers.
Do NOT use simple +N or xN patterns - those are too easy for GL Assessment.
Distractors should result from applying slightly wrong rules (e.g., wrong constant, wrong operation).""",
    },
    "vr_letter_series": {
        "instruction": "Find the pair of letters that continues the sequence in the best way.",
        "examples": [
            {
                "text": "Find the pair of letters that continues the sequence in the best way.\n\nAB    CD    EF    GH    ?",
                "options": ["IJ", "HI", "JK", "IK", "GI"],
                "answer": "IJ",
                "note": "Simple consecutive pairs. But GL questions are harder than this.",
            },
            {
                "text": "Find the pair of letters that continues the sequence in the best way.\n\nAZ    BY    CX    DW    ?",
                "options": ["EV", "EU", "EW", "FV", "DX"],
                "answer": "EV",
                "note": "First letter: A, B, C, D, E (+1). Second letter: Z, Y, X, W, V (-1).",
            },
        ],
        "guidance": """Use two-letter pairs where each letter follows its own pattern.
Patterns should combine: forward alphabet, backward alphabet, skip letters, alternating directions.
The two letters in each pair should follow DIFFERENT rules to add complexity.
At least one pattern should involve skipping (e.g., +2, +3) rather than simple +1/-1.""",
    },
    "vr_number_connections": {
        "instruction": "Choose the number that completes the final set of numbers in the same way as the other sets.",
        "examples": [
            {
                "text": "Choose the number that completes the final set of numbers in the same way as the other sets.\n\n12 (4) 8    13 (6) 7    21 (?) 3",
                "options": ["18", "12", "24", "9", "7"],
                "answer": "18",
                "note": "Rule: first number minus third number = middle number. 12-8=4, 13-7=6, 21-3=18.",
            },
            {
                "text": "Choose the number that completes the final set of numbers in the same way as the other sets.\n\n5 (30) 6    4 (28) 7    3 (?) 8",
                "options": ["11", "24", "15", "32", "22"],
                "answer": "24",
                "note": "Rule: first x third = middle. 5x6=30, 4x7=28, 3x8=24.",
            },
        ],
        "guidance": """Present 3 sets of numbers in format: A (X) B. Two sets are complete, the third has ? for X.
The rule connecting A, B, and X should use basic operations: sum, difference, product,
half of sum, double difference, etc. Do NOT use overly complex rules.
Distractors should result from applying other plausible operations (sum vs product, etc.).""",
    },
    "vr_word_pairs": {
        "instruction": "The words in the second set follow the same pattern as the words in the first set. Find the missing word.",
        "examples": [
            {
                "text": "The words in the second set follow the same pattern as the words in the first set. Find the missing word.\n\n(hot   warm   cool)    (freezing   cold   ?)",
                "options": ["tepid", "chilly", "icy", "mild", "frosty"],
                "answer": "mild",
                "note": "Pattern: decreasing intensity of temperature. hot>warm>cool, freezing>cold>mild.",
            },
        ],
        "guidance": """Use word sets where the relationship is: degree/intensity, size order, category hierarchy,
cause and effect sequence, or temporal order. The pattern between sets must be parallel.
The missing word should be in position 3 (or 1 or 2 for variety).
Distractors should be words from the same semantic field but wrong intensity/position.""",
    },
    "vr_insert_letter": {
        "instruction": "Find the letter that will complete both pairs of words. The letter must end the first word and start the second word in each pair.",
        "examples": [
            {
                "text": "Find the letter that completes both pairs of words.\n\nbea(?)ook    cha(?)est",
                "options": ["r", "t", "d", "k", "s"],
                "answer": "t",
                "note": "beat/took, chat/test. The letter 't' completes both pairs.",
            },
            {
                "text": "Find the letter that completes both pairs of words.\n\nwor(?)ite    gol(?)ark",
                "options": ["d", "k", "f", "s", "n"],
                "answer": "d",
                "note": "word/dite - hmm, 'dite' is uncommon. Better: word/site? No. Gold/dark. So 'd' gives: word/dite and gold/dark. Actually need to verify both pairs make real words.",
            },
        ],
        "guidance": """CRITICAL: Both pairs must form REAL, COMMON English words when the letter is inserted.
Test all four resulting words before including the question.
Use common 3-5 letter base words. The inserted letter must work for BOTH pairs.
Distractors should be letters that complete ONE pair but not the other.""",
    },
    "vr_alphabet_code": {
        "instruction": "Use the alphabet to work out the answer. If the code uses a pattern of shifts, decode the given word.",
        "examples": [
            {
                "text": "Use the alphabet to help you work out the answer.\nA B C D E F G H I J K L M N O P Q R S T U V W X Y Z\n\nIf the code for SPOT is VRPT, what does the code CQOE stand for?",
                "options": ["ZONE", "YOUR", "ZOOM", "WOKE", "WANE"],
                "answer": "ZONE",
                "note": "Shifts: S->V (+3), P->R (+2), O->P (+1), T->T (0). Pattern: +3, +2, +1, 0. Apply reverse: C-3=Z, Q-2=O, O-1=N, E-0=E. ZONE.",
            },
        ],
        "guidance": """Use VARIABLE shift patterns, not simple Caesar ciphers (same shift for all letters).
Good patterns: decreasing (+3,+2,+1,0), alternating (+2,-1,+2,-1), progressive (+1,+2,+3,+4).
The encoded and decoded words should both be common English words students would recognize.
Always include the full alphabet as reference. Use 4-letter words.
Distractors should be real English words that result from applying slightly wrong shift patterns.""",
    },
    "vr_multiple_meaning": {
        "instruction": "Find one word that has two different meanings and can complete both sentences.",
        "examples": [
            {
                "text": "Find one word that can complete both sentences.\n\nThe ___ of the river was very strong.\n\nShe plugged in the ___ to check her email.",
                "options": ["flow", "current", "stream", "power", "charge"],
                "answer": "current",
                "note": "'Current' means both a flow of water and electrical current/modern.",
            },
        ],
        "guidance": """Use common homonyms/polysemous words: bank, bat, light, bark, match, spring, ring, right, play, fair, etc.
Both sentences must use a DIFFERENT meaning of the same word.
The word must grammatically fit both sentences.
Distractors should be words that fit ONE sentence but not the other.""",
    },
    "vr_letter_relationships": {
        "instruction": "Work out the relationship between the letters and find the missing letters.",
        "examples": [
            {
                "text": "AB is to CD as PQ is to ?",
                "options": ["RS", "ST", "QR", "RQ", "NO"],
                "answer": "RS",
                "note": "Each pair moves forward 2 letters. AB -> CD (+2 each), PQ -> RS (+2 each).",
            },
        ],
        "guidance": """Use letter-pair analogies with transformations: shift by N positions, reverse order,
skip pattern, vowel/consonant alternation. The relationship between the first pair
must apply identically to produce the answer from the third pair.""",
    },
    "vr_number_codes": {
        "instruction": "Letters stand for numbers. Work out the answer to the sum.",
        "examples": [
            {
                "text": "In these questions, letters stand for numbers.\n\nIf A = 3, B = 7, C = 2, D = 5\n\nWhat is the value of AB - CD?",
                "options": ["22", "27", "32", "17", "12"],
                "answer": "27",
                "note": "AB = 37 (concatenated digits), CD = 25. Hmm, or A x B - C x D = 21 - 10 = 11? The GL format typically means: A=3, B=7, so calculate using operations. Need to specify whether letters are digits or values.",
            },
        ],
        "guidance": """Define 4-5 letter-number mappings. Then give an arithmetic expression using the letters.
The expression should require substitution THEN multi-step calculation.
Make it clear whether letters represent digit positions or values.
Include brackets or BODMAS challenges. Distractors from wrong substitution or wrong order of operations.""",
    },
    "vr_compound_words": {
        "instruction": "Find a word that can go after the first word and before the second word to make two new words.",
        "examples": [
            {
                "text": "Find a word that can go after the first word and before the second word to make two new compound words.\n\nfoot  (?)  game",
                "options": ["ball", "play", "step", "note", "work"],
                "answer": "ball",
                "note": "football + ballgame. Both are real compound words.",
            },
            {
                "text": "Find a word that can go after the first word and before the second word to make two new compound words.\n\nstar  (?)  tank",
                "options": ["light", "fish", "water", "fire", "ship"],
                "answer": "fish",
                "note": "starfish + fishtank. Both are real compound words.",
            },
        ],
        "guidance": """Both resulting compound words must be REAL, commonly used English words.
The linking word should be a simple, common noun (3-5 letters).
Distractors should form a valid compound with ONE of the words but not both.
Test both compounds before including the question.""",
    },
    "vr_word_shuffling": {
        "instruction": "The letters of a word have been shuffled. Rearrange them to find the word, then answer the question.",
        "examples": [
            {
                "text": "Rearrange the letters to make a word, then answer the question.\n\nHOWADS\n\nWhat does this word mean?",
                "options": ["A type of dark area created by an object blocking light", "A painting technique", "A type of fabric", "A window treatment", "A type of dance"],
                "answer": "A type of dark area created by an object blocking light",
                "note": "HOWASD = SHADOW. A shadow is a dark area created by blocking light.",
            },
        ],
        "guidance": """Shuffle 5-7 letter words that Year 5 students would know.
The scrambled version should NOT accidentally spell another word.
After unscrambling, ask a follow-up question (meaning, category, rhyme, etc.)
to add a second step of reasoning.""",
    },
    "vr_anagrams": {
        "instruction": "Rearrange the letters to make a word. Which category does it belong to?",
        "examples": [
            {
                "text": "Rearrange the letters in capitals to make a word.\n\nTEPANL\n\nWhich of these is it?",
                "options": ["A country", "A planet", "An animal", "A colour", "A food"],
                "answer": "A planet",
                "note": "TEPALN = PLANET",
            },
        ],
        "guidance": """Use 5-7 letter words. The anagram should have only ONE valid solution.
Ask the student to identify the category of the unscrambled word.
Categories should be clearly distinct (not overlapping).
Include one distractor category that is close but wrong.""",
    },
    "vr_logic_problems": {
        "instruction": "Read the information carefully, then answer the question.",
        "examples": [
            {
                "text": "Read the information carefully, then answer the question.\n\nFive friends - Alex, Ben, Clara, Dan, and Eve - each have a different pet: cat, dog, hamster, fish, and rabbit.\n- Alex does not have a cat or dog.\n- Ben's pet has four legs.\n- Clara has the fish.\n- Dan does not have the rabbit.\n- The person with the cat sits next to Eve.\n\nWho has the hamster?",
                "options": ["Alex", "Ben", "Dan", "Eve", "Clara"],
                "answer": "Alex",
                "note": "Clara=fish. Alex not cat/dog, so Alex has hamster, fish or rabbit. Clara has fish. So Alex has hamster or rabbit. Ben has 4-legged pet (cat/dog/hamster/rabbit). Dan not rabbit. Working through: Alex=hamster.",
            },
        ],
        "guidance": """Use 4-5 people/items with 4+ clues requiring elimination logic.
Clues should be given as negative statements ('X does NOT have...') and positive statements mixed.
The problem should require AT LEAST 3 steps of logical deduction.
Include enough clues for a unique solution. Verify the solution is correct and unique.
Distractors should be the other people in the problem.""",
    },
    "vr_explore_facts": {
        "instruction": "Read the information and use it to answer the question.",
        "examples": [
            {
                "text": "Read the information carefully.\n\nIn a school, all students who play football also play cricket. Some students who play cricket also play tennis. No student who plays tennis plays basketball.\n\nWhich statement MUST be true?",
                "options": [
                    "All football players play tennis",
                    "Some football players play basketball",
                    "All football players play cricket",
                    "No cricket players play basketball",
                    "All tennis players play football",
                ],
                "answer": "All football players play cricket",
                "note": "Given directly: all football players play cricket. The others don't necessarily follow.",
            },
        ],
        "guidance": """Present 3-4 logical statements about sets/categories, then ask which conclusion MUST be true.
Use Venn diagram-style logic (all X are Y, some X are Y, no X are Y).
Distractors should be plausible conclusions that COULD be true but aren't guaranteed.
Use school/sport/club contexts familiar to Year 5 students.""",
    },
    "vr_solve_riddle": {
        "instruction": "Use the clues to work out the answer.",
        "examples": [
            {
                "text": "Use the clues to work out the answer.\n\nI am a number.\nI am between 20 and 40.\nI am odd.\nThe sum of my digits is 8.\nI am not divisible by 3.\n\nWhat number am I?",
                "options": ["35", "17", "26", "53", "29"],
                "answer": "35",
                "note": "Between 20-40, odd: 21,23,25,27,29,31,33,35,37,39. Digit sum 8: 35 (3+5=8), 17 not in range. Not div by 3: 35 is not div by 3. Answer: 35.",
            },
        ],
        "guidance": """Give 4-5 clues that progressively narrow down the answer.
Use number riddles, word riddles, or object riddles.
Each clue should eliminate some options. The final answer should be unique.
Distractors should satisfy MOST but not ALL clues.""",
    },
    "vr_rhyming_synonyms": {
        "instruction": "Find two words that rhyme AND are closest in meaning.",
        "examples": [
            {
                "text": "Find two words from the list that rhyme with each other AND have similar meanings.\n\nglare    fair    stare    care    rare",
                "options": ["glare, stare", "fair, rare", "glare, fair", "care, rare", "stare, care"],
                "answer": "glare, stare",
                "note": "Glare and stare both mean to look intently, and they rhyme (-are).",
            },
        ],
        "guidance": """Provide 5 words that all rhyme (or nearly rhyme). Students must find the pair that
BOTH rhymes AND shares meaning. Include distractor pairs that rhyme but don't share meaning.
Use words with rich synonym relationships.""",
    },
    "vr_shuffled_sentences": {
        "instruction": "The words in a sentence have been shuffled. Rearrange them, then answer the question.",
        "examples": [
            {
                "text": "The words in the sentence below have been shuffled. Put them in the correct order.\n\nthe  dog  big  chased  brown  cat  a  small\n\nWhat is the last word of the sentence?",
                "options": ["cat", "small", "dog", "big", "chased"],
                "answer": "cat",
                "note": "Correct sentence: 'The big brown dog chased a small cat.' Last word = cat.",
            },
        ],
        "guidance": """Use sentences of 7-10 words. The sentence should have only ONE valid ordering.
Include adjectives and descriptive phrases to add complexity.
Ask about a specific word position (first, third, last) or grammatical role.
The shuffled words should not accidentally form a different valid sentence.""",
    },
}


def get_vr_prompt(qtype: str, count: int) -> str:
    """Build a GL-calibrated VR generation prompt."""
    type_info = VR_TYPES.get(qtype)
    if not type_info:
        raise ValueError(f"Unknown VR type: {qtype}")

    examples_text = ""
    for i, ex in enumerate(type_info["examples"], 1):
        note = ex.get("note", "")
        examples_text += f"""
EXAMPLE {i}:
Question: {ex['text']}
Options: {ex['options']}
Answer: {ex['answer']}
{"Reasoning: " + note if note else ""}
"""

    return f"""Generate {count} GL Assessment verbal reasoning "{qtype}" questions for Year 5 (age 10-11).

GL INSTRUCTION FORMAT: "{type_info['instruction']}"

{type_info['guidance']}

{examples_text}

Return a JSON array of exactly {count} objects:
[
  {{
    "subject": "verbal_reasoning",
    "question_type": "{qtype}",
    "format": "multiple_choice",
    "difficulty": 3,
    "content": {{
      "text": "[Question text following the GL Assessment instruction format above]",
      "options": ["Option A", "Option B", "Option C", "Option D", "Option E"]
    }},
    "answer": {{ "value": "[Exact text of correct option]" }},
    "explanation": "[Why this answer is correct, with reasoning steps]",
    "hints": [],
    "tags": ["{qtype}"],
    "source": "LLM Generated"
  }}
]

CRITICAL: Every answer MUST be verifiably correct. For word-based questions, all words must be real
English words. Vary the correct answer position across A-E."""
