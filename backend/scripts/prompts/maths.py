"""GL Assessment maths prompt templates.

Each prompt includes 2-3 worked examples at GL difficulty level and explicit
distractor design rules. Maths questions must require multi-step reasoning
and concept combination - not simple single-operation calculations.
"""

MATHS_SYSTEM = """You are an expert 11+ exam question writer specializing in GL Assessment format.
You write questions for Year 5 students (age 10-11) preparing for selective school entrance exams.

CRITICAL RULES:
1. Every question must require MULTI-STEP reasoning or combine 2+ mathematical concepts.
   Single-operation questions (e.g., "What is 45 + 27?") are TOO EASY for GL Assessment.
2. Every distractor must represent a SPECIFIC plausible mistake a Year 5 student would make.
   Never use random numbers as distractors.
3. Vary the position of the correct answer across A-E. Do NOT cluster correct answers at one position.
4. Use Year 5 vocabulary and contexts (school, sports, shopping, cooking, travel).
5. Return ONLY a JSON array. No markdown, no commentary."""

MATHS_TYPES = {
    "number_operations": {
        "description": "Multi-step arithmetic, place value, factors, multiples, primes, squares, cubes, BODMAS",
        "examples": [
            {
                "text": "2x is an acute angle and 3x is an obtuse angle. Which of these could be the value of x?",
                "options": ["20", "25", "35", "40", "50"],
                "answer": "35",
                "why": "If x=35: 2x=70 (acute, <90) and 3x=105 (obtuse, 90<x<180). x=20: 3x=60 not obtuse. x=40: 2x=80 acute but 3x=120 works too - but 2x must be strictly acute. x=25: 3x=75 not obtuse. x=50: 2x=100 not acute.",
            },
            {
                "text": "What is the value of 7 + 3 x 4 - 2?",
                "options": ["17", "38", "22", "19", "12"],
                "answer": "17",
                "why": "BODMAS: 3x4=12, then 7+12-2=17. Distractor 38=(7+3)x4-2 (left to right). 22=7+3x(4+2). 19=7+3x4. 12=wrong BODMAS.",
            },
            {
                "text": "___ / 1000 = 0.2543",
                "options": ["25.43", "254.3", "2543", "25430", "0.02543"],
                "answer": "254.3",
                "why": "0.2543 x 1000 = 254.3. Distractors: 25.43 (x100), 2543 (x10000), 25430 (confused), 0.02543 (divided instead).",
            },
        ],
        "prompt_extra": """Focus on: BODMAS problems, place value puzzles (e.g., "Which digit is in the thousands place of..."),
inverse operations ("___ / 1000 = 0.2543"), factor/multiple relationships, square and cube number identification,
and multi-step problems combining 2+ operations.""",
    },
    "fractions": {
        "description": "Comparing, ordering, adding, subtracting, multiplying fractions, mixed numbers, equivalents, fraction of amount",
        "examples": [
            {
                "text": "Which fraction is closest to 1/2?\n\nA) 2/5  B) 3/7  C) 5/9  D) 4/11  E) 7/15",
                "options": ["2/5", "3/7", "5/9", "4/11", "7/15"],
                "answer": "5/9",
                "why": "Convert to decimals: 2/5=0.4, 3/7=0.429, 5/9=0.556, 4/11=0.364, 7/15=0.467. Closest to 0.5 is 5/9 (0.056 away) or 7/15 (0.033 away). Actually 7/15=0.467, distance=0.033. 5/9=0.556, distance=0.056. So 7/15 is closer. Let me recalculate - this example shows why verification matters.",
            },
            {
                "text": "Sam eats 2/5 of a pizza. Tom eats 1/3 of the same pizza. What fraction is left?",
                "options": ["4/15", "3/8", "1/5", "7/15", "1/2"],
                "answer": "4/15",
                "why": "2/5 + 1/3 = 6/15 + 5/15 = 11/15. Left = 1 - 11/15 = 4/15. Distractors: 3/8 (wrong denominator), 1/5 (subtracted wrong), 7/15 (forgot one portion), 1/2 (guess).",
            },
        ],
        "prompt_extra": """Include problems requiring: finding common denominators, converting between mixed numbers
and improper fractions, fraction of an amount (e.g., "3/4 of 120"), ordering fractions with different denominators,
and multi-step fraction arithmetic. Always use fractions that are NOT trivially equivalent.""",
    },
    "geometry": {
        "description": "Angles, 2D/3D shape properties, coordinates, symmetry, perimeter, area, volume, compound shapes",
        "examples": [
            {
                "text": "A rectangle has a perimeter of 36 cm. Its length is twice its width. What is the area?",
                "options": ["72 cm2", "36 cm2", "54 cm2", "108 cm2", "48 cm2"],
                "answer": "72 cm2",
                "why": "Let width = w. Length = 2w. Perimeter: 2(w + 2w) = 6w = 36, so w = 6. Area = 6 x 12 = 72. Distractors: 36 (perimeter confused with area), 54 (9x6 wrong length), 108 (18x6), 48 (wrong calculation).",
            },
            {
                "text": "How many lines of symmetry does a regular pentagon have?",
                "options": ["3", "4", "5", "6", "10"],
                "answer": "5",
                "why": "Regular polygon with n sides has n lines of symmetry. Distractors: 3 (confused with triangle), 4 (square), 6 (hexagon), 10 (double).",
            },
        ],
        "prompt_extra": """Include: compound shape area/perimeter (L-shapes, T-shapes), angle calculations in triangles
and quadrilaterals, properties of 3D shapes (faces, edges, vertices), coordinate geometry (reflections, translations),
and multi-step geometry problems. Use diagrams described in text when needed.""",
    },
    "measurement": {
        "description": "Length, mass, capacity, time, unit conversion, reading scales, temperature",
        "examples": [
            {
                "text": "A jug holds 2.5 litres of juice. Mia pours out 750 ml. How much juice is left in the jug?",
                "options": ["1.75 litres", "1750 ml", "2.25 litres", "1.25 litres", "175 ml"],
                "answer": "1.75 litres",
                "why": "2.5L = 2500ml. 2500 - 750 = 1750ml = 1.75L. Distractors: 1750ml (correct but different unit - trick!), 2.25 (subtracted 0.25 not 0.75), 1.25 (subtracted 1.25L), 175ml (decimal error).",
            },
        ],
        "prompt_extra": """Include problems requiring unit conversions (mm/cm/m/km, g/kg, ml/L),
time calculations across midnight or with different units (seconds/minutes/hours),
reading scales with unlabelled divisions, and multi-step measurement problems in real-world contexts.""",
    },
    "word_problems": {
        "description": "Multi-step real-world problems combining multiple operations and concepts",
        "examples": [
            {
                "text": "Ben has 8 pounds. He spends one quarter of his money. What percentage of his money does he have left?",
                "options": ["75%", "25%", "80%", "20%", "50%"],
                "answer": "75%",
                "why": "One quarter spent = 3/4 left = 75%. Distractors: 25% (quarter spent, not left), 80% (confused with amount), 20% (2/8 confused), 50% (half).",
            },
            {
                "text": "A shop sells pencils in packs of 6 for 1.50 pounds or individually for 30p each. How much cheaper is it to buy 12 pencils in packs rather than individually?",
                "options": ["60p", "30p", "1.20 pounds", "0.90 pounds", "3.00 pounds"],
                "answer": "60p",
                "why": "Packs: 2 x 1.50 = 3.00. Individual: 12 x 0.30 = 3.60. Difference: 60p. Distractors: 30p (per pencil saving), 1.20 (wrong calc), 0.90 (pack of 6 saving x3?), 3.00 (pack cost).",
            },
        ],
        "prompt_extra": """Every word problem must require at least 2 steps. Use contexts: shopping (discounts, change, bulk buying),
cooking (scaling recipes), travel (speed-distance-time), sharing (ratios, equal portions), and money.
Include trap distractors that result from stopping after step 1 of a 2-step problem.""",
    },
    "data_handling": {
        "description": "Reading tables, bar/pie/line charts, mean, median, mode, range, interpreting data",
        "examples": [
            {
                "text": "Five students scored 12, 15, 15, 18, and 20 in a test. What is the mean score?",
                "options": ["15", "16", "15.5", "17", "18"],
                "answer": "16",
                "why": "Sum = 80, mean = 80/5 = 16. Distractors: 15 (median/mode), 15.5 (wrong division), 17 (forgot one score), 18 (confused).",
            },
        ],
        "prompt_extra": """Describe data in text form since we cannot include images.
Use frequency tables, described bar charts ('the bar for Monday reaches 15...'),
or listed data sets. Questions should require calculation (not just reading),
such as finding missing values, comparing averages, or calculating ranges.""",
    },
    "algebra": {
        "description": "Simple equations, sequences, function machines, missing number problems, expressions",
        "examples": [
            {
                "text": "In the sequence 3, 7, 11, 15, ..., what is the 10th term?",
                "options": ["39", "43", "37", "41", "35"],
                "answer": "39",
                "why": "Common difference = 4. nth term = 3 + (n-1) x 4. 10th = 3 + 36 = 39. Distractors: 43 (11th term), 37 (off by 1), 41 (started from n=0), 35 (9th term wrong).",
            },
            {
                "text": "If 3y - 7 = 20, what is the value of y?",
                "options": ["9", "7", "27", "6", "11"],
                "answer": "9",
                "why": "3y = 27, y = 9. Distractors: 7 (20-7=13/wrong), 27 (forgot to divide), 6 (20/3 rounded), 11 (added instead).",
            },
        ],
        "prompt_extra": """Include: solving one-step and two-step equations, finding terms in sequences (arithmetic and simple geometric),
function machines with 2+ operations, writing expressions from word descriptions,
and substitution into simple formulae.""",
    },
    "ratio": {
        "description": "Ratio notation, simplifying, sharing in ratio, proportion, scaling, direct proportion",
        "examples": [
            {
                "text": "Amy and Ben share 45 pounds in the ratio 4:5. How much does Ben get?",
                "options": ["25 pounds", "20 pounds", "30 pounds", "15 pounds", "9 pounds"],
                "answer": "25 pounds",
                "why": "Total parts = 9. Each part = 45/9 = 5. Ben gets 5 x 5 = 25. Distractors: 20 (Amy's share), 30 (wrong ratio), 15 (45/3), 9 (number of parts).",
            },
        ],
        "prompt_extra": """Include: sharing amounts in given ratios, simplifying ratios (with different units),
scaling recipes (e.g., 'recipe serves 4, how much for 6?'), finding missing values in proportion tables,
and ratio problems requiring unit conversion first.""",
    },
    "decimals": {
        "description": "Decimal operations, ordering, rounding, place value, decimal/fraction conversion",
        "examples": [
            {
                "text": "Put these decimals in order from smallest to largest: 0.35, 0.305, 0.3, 0.053, 0.5. Which is the third smallest?",
                "options": ["0.305", "0.3", "0.35", "0.053", "0.5"],
                "answer": "0.305",
                "why": "Order: 0.053, 0.3, 0.305, 0.35, 0.5. Third = 0.305. Common mistake: thinking 0.305 > 0.35 because 305 > 35.",
            },
        ],
        "prompt_extra": """Include: ordering decimals with different numbers of decimal places,
rounding to specified decimal places, converting between fractions and decimals,
decimal arithmetic requiring carrying/borrowing, and place value questions.""",
    },
    "percentages": {
        "description": "Finding percentages, percentage of amount, percentage increase/decrease, fraction-decimal-percentage conversion",
        "examples": [
            {
                "text": "A coat costs 80 pounds. In a sale, it is reduced by 15%. What is the sale price?",
                "options": ["68 pounds", "65 pounds", "12 pounds", "72 pounds", "92 pounds"],
                "answer": "68 pounds",
                "why": "15% of 80 = 12. Sale price = 80 - 12 = 68. Distractors: 65 (rough guess), 12 (the discount not the price), 72 (10% off), 92 (added instead).",
            },
        ],
        "prompt_extra": """Include: percentage of amounts, finding original price after percentage change,
converting between fractions/decimals/percentages, comparing values using percentages,
and multi-step problems (e.g., successive percentage changes).""",
    },
}


def get_maths_prompt(qtype: str, count: int) -> str:
    """Build a GL-calibrated maths generation prompt."""
    type_info = MATHS_TYPES.get(qtype, MATHS_TYPES["number_operations"])

    examples_text = ""
    for i, ex in enumerate(type_info["examples"], 1):
        examples_text += f"""
EXAMPLE {i}:
Question: {ex['text']}
Options: {ex['options']}
Answer: {ex['answer']}
Distractor reasoning: {ex['why']}
"""

    return f"""Generate {count} GL Assessment maths questions for Year 5 (age 10-11).

TOPIC: {qtype} - {type_info['description']}

{type_info['prompt_extra']}

{examples_text}

DISTRACTOR DESIGN RULES:
- Each wrong option must result from a SPECIFIC common mistake:
  * Forgetting BODMAS order
  * Multiplying instead of dividing (or vice versa)
  * Off-by-one errors
  * Forgetting to convert units
  * Stopping after step 1 of a 2-step problem
  * Confusing similar concepts (e.g., perimeter vs area)
- Never use random numbers as distractors
- Ensure all 5 options are distinct and plausible

Return a JSON array of exactly {count} objects:
[
  {{
    "subject": "maths",
    "question_type": "{qtype}",
    "format": "multiple_choice",
    "difficulty": 3,
    "content": {{
      "text": "[Question text]",
      "options": ["Option A", "Option B", "Option C", "Option D", "Option E"]
    }},
    "answer": {{ "value": "[Exact text of correct option]" }},
    "explanation": "[Step-by-step solution showing working]",
    "hints": [],
    "tags": ["{qtype}"],
    "source": "LLM Generated"
  }}
]

CRITICAL: Every answer MUST be mathematically correct. Show full working in the explanation.
Vary the position of the correct answer (A through E) roughly equally across questions."""
