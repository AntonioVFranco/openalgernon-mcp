"""Teaching discipline profiles for the OpenAlgernon MCP server.

These are embedded here to keep the MCP server self-contained.
The canonical versions live in open-algernon/prompts/teaching-profiles/.
"""

from __future__ import annotations

TEACHING_PROFILES: dict[str, str] = {
    "math": """\
# Mathematics Teaching Profile

## Pedagogical approach
- Geometric/visual intuition first, algebraic formalization second.
- Sequence: intuition → worked example → near transfer → far transfer → proof.
- Every rule must be derived or shown, not presented as a given.
- Concrete examples before abstract statements.

## Understanding signals
- Can the student generate their own examples of the concept?
- Can they explain *why* a rule works, not just apply it?
- Can they identify when a rule does and does not apply?
- Can they produce a counterexample when challenged?

## Technique triggers
- Student sees a new concept → Analogy (anchor to geometric/physical reality)
- First exposure to a procedure → Worked examples (model fully before asking)
- Student applies formula without understanding → Socratic interrogation
- Student stuck → Scaffolding (reduce to simpler case)
- Student too comfortable → Desirable difficulty (increase interleaving)
- Wrong answer → Error analysis (diagnose the specific misconception)

## Misconceptions catalog

### Algebra
- Sign errors: confusing -(-a) with a; dropping negatives when distributing.
- Fraction addition: a/b + c/d is not (a+c)/(b+d).
- Exponent errors: (a+b)^2 is not a^2 + b^2; a^m * a^n = a^(m+n) not a^(mn).

### Calculus
- Product rule: (fg)' is not f'g'.
- Chain rule omission: forgetting the inner derivative multiplier.
- Integration constant: omitting +C for indefinite integrals.

### Linear algebra
- Matrix multiplication: AB is not always equal to BA.
- Confusing eigenvalues with diagonal entries (only true for diagonal matrices).

### Statistics
- Confusing correlation with causation.
- p < 0.05 does not mean the effect is large or important.
""",

    "cs": """\
# Computer Science Teaching Profile

## Pedagogical approach
- Mental model before syntax: understand the mechanism before writing code.
- CRA model: Concrete → Representational → Abstract.
- Cycle: pseudocode → working code → execution trace → debugging.
- Build-break-fix as the primary learning loop.

## Understanding signals
- Can the student predict the output of code without running it?
- Can they debug an error without print-driven discovery alone?
- Can they state the time and space complexity of their solution?
- Can they recognize the pattern in a new, unfamiliar problem?

## Technique triggers
- New data structure → CRA progression (draw before coding)
- New algorithm → Worked examples with full execution trace
- Student can execute but not explain → Elaborative interrogation
- Student copies pattern without understanding → Feynman
- Runtime error → Error analysis (trace the specific failure site)

## Misconceptions catalog

### Arrays and memory
- Off-by-one: loop bounds i <= n vs i < n; last valid index is length-1.
- Reference vs value semantics: a = b does not copy a mutable object.

### Recursion
- Missing base case → infinite recursion.
- Not returning the recursive result → function returns None.

### Algorithms
- Greedy correctness: greedy does not always produce an optimal solution.
- O(n log n) comparison-based sort lower bound is tight.
""",

    "ai-engineering": """\
# AI Engineering Teaching Profile

## Pedagogical approach
- Mathematical foundations when required, implementation-first when practical.
- Cycle: paper → minimal implementation → trade-off critique.
- Systems thinking: every component has inputs, outputs, failure modes, and cost.
- Real benchmarks over theoretical claims; reproduce results when possible.

## Understanding signals
- Can the student identify the failure modes of a system?
- Can they choose the right tool for a task and defend the choice?
- Can they read a paper abstract and state what problem it solves?
- Can they estimate cost: tokens, FLOPS, latency, memory?

## Technique triggers
- New model architecture → Analogy to simpler model + worked implementation
- New technique → Worked example with code
- Student accepts benchmark claims uncritically → Socratic
- Abstract concept (attention, embeddings) → CRA progression

## Misconceptions catalog

### Transformers and LLMs
- Attention is O(n^2) in sequence length — limits context.
- RLHF optimizes for human preference ratings, not ground truth.
- Bigger model is not always better.
- Temperature controls sampling randomness, not reasoning quality.

### RAG and retrieval
- Retrieval finds semantically similar text, not necessarily correct answers.
- Chunk size affects precision/recall trade-off significantly.
- Vector databases do not replace keyword search in all cases.

### Fine-tuning
- Fine-tuning does not always beat prompting for reasoning.
- LoRA does not modify base model weights.
- Eval data contamination is the most common benchmarking error.

### Agents
- Tool calling is pattern matching, not general reasoning.
- Errors compound in multi-step agents.
- Context window exhaustion is the most common production failure.
""",

    "english": """\
# English (L2) Teaching Profile

## Pedagogical approach
- Comprehensible input at i+1 (Krashen): always slightly above current level.
- Meaning before form: grammar emerges from exposure.
- Forced output with feedback: speaking and writing, not passive reading alone.
- Vocabulary through context, not isolated word lists.

## Understanding signals
- Can the student communicate their intent clearly, even with some errors?
- Has processing time decreased on familiar patterns?
- Can the student produce new sentences using the target structure?

## Technique triggers
- New vocabulary → Context-rich examples (3+ sentences showing usage)
- Grammar confusion → Error analysis (show the pattern via examples)
- Hesitation on familiar patterns → Retrieval practice
- Communication breakdown → Scaffolding

## Misconceptions catalog (Portuguese-speaker specific)
- Word-for-word translation from Portuguese produces unnatural English.
- 'Make' vs 'do' collocations are idiomatic (no universal rule).
- False cognates: 'eventually' in English ≠ 'eventualmente' in Portuguese.
- Present perfect vs simple past (both map to 'pretérito perfeito' for Portuguese speakers).
- Gerund vs infinitive after verbs: 'enjoy doing' vs 'want to do'.
""",
}

VALID_DISCIPLINES = frozenset(TEACHING_PROFILES.keys())


def get_profile(discipline: str) -> str:
    """Return the teaching profile for a discipline.

    Args:
        discipline: One of 'math', 'cs', 'ai-engineering', 'english'.

    Returns:
        The profile markdown text.

    Raises:
        ValueError: If the discipline is not recognized.
    """
    if discipline not in TEACHING_PROFILES:
        raise ValueError(
            f"Unknown discipline '{discipline}'. "
            f"Valid options: {sorted(VALID_DISCIPLINES)}"
        )
    return TEACHING_PROFILES[discipline]
