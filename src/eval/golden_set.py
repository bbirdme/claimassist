"""
Golden question/answer set for evaluating retrieval quality in Phase 1.

Every question's correct answer is derived directly from facts.py, not from
generated document prose, so grading retrieval/answer quality never depends
on trusting the LLM that wrote the documents. `source_docs` lists exactly
which document(s) contain the answer - single-doc questions test basic
retrieval, multi-doc questions test whether retrieval pulls together facts
that live in genuinely separate documents (e.g. a claim + the policy it's
filed against).
"""

GOLDEN_SET = [
    # --- Single-document: policy facts ---
    {
        "id": "Q01",
        "question": "What is the wind/hail deductible on policy HO-88213-4?",
        "answer": "$2,500",
        "source_docs": ["HO-88213-4"],
    },
    {
        "id": "Q02",
        "question": "What is the dwelling coverage limit on David Chen's homeowners policy?",
        "answer": "$500,000 (policy HO-4471-9)",
        "source_docs": ["HO-4471-9"],
    },
    {
        "id": "Q03",
        "question": "Does Angela Torres's homeowners policy (HO-1120-7) cover flood damage?",
        "answer": "No, flood damage is explicitly excluded.",
        "source_docs": ["HO-1120-7"],
    },
    {
        "id": "Q04",
        "question": "What is the collision deductible on James Whitfield's auto policy?",
        "answer": "$500 (policy AU-3387-1)",
        "source_docs": ["AU-3387-1"],
    },
    {
        "id": "Q05",
        "question": "What rental reimbursement benefit does Priya Nair's auto policy include?",
        "answer": "$30/day, maximum 30 days",
        "source_docs": ["AU-7742-5"],
    },
    {
        "id": "Q06",
        "question": "What is the liability limit on Marcus Webb's auto policy?",
        "answer": "$50,000/$100,000 (policy AU-2298-3)",
        "source_docs": ["AU-2298-3"],
    },
    {
        "id": "Q07",
        "question": "What is Sofia Ramirez's individual health plan deductible and out-of-pocket max?",
        "answer": "$2,000 deductible, $6,500 out-of-pocket max (policy HI-5502-8)",
        "source_docs": ["HI-5502-8"],
    },
    {
        "id": "Q08",
        "question": "What is the embedded individual deductible within the Okafor family health plan?",
        "answer": "$2,000 (policy HI-6614-2)",
        "source_docs": ["HI-6614-2"],
    },
    {
        "id": "Q09",
        "question": "What is Robert Kim's coinsurance rate after meeting his deductible?",
        "answer": "10% (policy HI-3309-6, HSA-eligible high-deductible plan)",
        "source_docs": ["HI-3309-6"],
    },
    {
        "id": "Q10",
        "question": "Is cosmetic surgery covered under any of the health policies in this corpus?",
        "answer": "No, cosmetic procedures are excluded on all three health policies (HI-5502-8, HI-6614-2, HI-3309-6).",
        "source_docs": ["HI-5502-8", "HI-6614-2", "HI-3309-6"],
    },
    # --- Single-document: claim facts ---
    {
        "id": "Q11",
        "question": "What was the total estimated repair cost for Maria Gutierrez's storm damage claim?",
        "answer": "$9,650 (roof/skylight $8,450 + fence $1,200)",
        "source_docs": ["CLM-2026-0301"],
    },
    {
        "id": "Q12",
        "question": "What caused the water damage in Angela Torres's claim?",
        "answer": "A burst supply line pipe in the upstairs bathroom.",
        "source_docs": ["CLM-2026-0214"],
    },
    {
        "id": "Q13",
        "question": "What was the repair estimate for Priya Nair's windshield/hail claim?",
        "answer": "$2,100",
        "source_docs": ["CLM-2026-0601"],
    },
    # --- Single-document: medical notes ---
    {
        "id": "Q14",
        "question": "What diagnosis did Sofia Ramirez receive at the emergency room?",
        "answer": "Distal radius fracture (right wrist)",
        "source_docs": ["MED-0520-A"],
    },
    {
        "id": "Q15",
        "question": "What was James Whitfield's urgent care visit billed at?",
        "answer": "$450",
        "source_docs": ["MED-0412-A"],
    },
    {
        "id": "Q16",
        "question": "What is the treatment plan from Sofia Ramirez's orthopedic follow-up visit?",
        "answer": "Continue cast 3 more weeks, then physical therapy referral after cast removal.",
        "source_docs": ["MED-0603-A"],
    },
    # --- Multi-document: requires connecting claim + policy (or + medical note) ---
    {
        "id": "Q17",
        "question": (
            "For claim CLM-2026-0412, what deductible applies to the repair "
            "estimate, and was there an associated injury?"
        ),
        "answer": (
            "Collision deductible of $500 (policy AU-3387-1) applies to the "
            "$6,200 repair estimate; yes, James Whitfield was treated for a "
            "cervical strain (see medical note MED-0412-A)."
        ),
        "source_docs": ["CLM-2026-0412", "AU-3387-1", "MED-0412-A"],
    },
    {
        "id": "Q18",
        "question": (
            "For Sofia Ramirez's injury claim, what is the total billed across "
            "both medical visits, and what is her health plan's out-of-pocket "
            "maximum?"
        ),
        "answer": (
            "$4,800 (ER) + $320 (orthopedic follow-up) = $5,120 total billed; "
            "out-of-pocket max is $6,500 (policy HI-5502-8)."
        ),
        "source_docs": ["CLM-2026-0520", "MED-0520-A", "MED-0603-A", "HI-5502-8"],
    },
    {
        "id": "Q19",
        "question": (
            "Which deductible applies to Angela Torres's water damage claim, "
            "and why not the wind/hail deductible?"
        ),
        "answer": (
            "The standard deductible ($500 on policy HO-1120-7) applies, "
            "because the loss was a burst pipe, not a wind/hail event."
        ),
        "source_docs": ["CLM-2026-0214", "HO-1120-7"],
    },
]
