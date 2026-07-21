CLAIM_NARRATIVE = """
Claimant: Maria Gutierrez, Policy #HO-88213-4
Date of Loss: March 3, 2026
Loss Location: 214 Birchwood Lane, Springfield

On the morning of March 3rd, a severe wind and hail storm passed through the
Springfield area, with gusts recorded up to 65 mph by the regional weather
station. The claimant reports returning home from an overnight trip at
approximately 7:45 AM to find several roof shingles missing from the
south-facing slope of the roof, a cracked skylight in the upstairs bathroom,
and water staining on the ceiling directly below the skylight, consistent with
active leaking during the storm. The claimant also reports that a wooden
fence panel on the east side of the property was blown down, and a large oak
branch fell onto the detached garage, denting the roof panel but not
penetrating it. No injuries were reported. The claimant states that the roof
was replaced approximately 6 years ago and has no prior history of leaks or
storm damage claims. A neighbor, John Alvarez, has provided a written
statement corroborating the storm timing and the fence damage. The claimant
has submitted photos of the roof, skylight, ceiling stain, fence, and garage
dent, along with a contractor estimate for roof and skylight repair totaling
$8,450 and a separate fence repair estimate of $1,200. The policy has a wind/
hail deductible of $2,500 and dwelling coverage limit of $350,000.
""".strip()

PROMPTS = [
    {
        "id": "factual_short",
        "category": "short_factual",
        "text": "What is subrogation in insurance?",
    },
    {
        "id": "claim_summary",
        "category": "long_context_summary",
        "text": (
            "Summarize the following insurance claim narrative in 3 sentences "
            "for a case worker who has not read it yet:\n\n" + CLAIM_NARRATIVE
        ),
    },
    {
        "id": "claim_extraction",
        "category": "structured_output",
        "text": (
            "Extract the following fields from this claim narrative and return "
            "ONLY a JSON object with these exact keys: claimant_name, policy_number, "
            "date_of_loss, deductible_usd, total_estimated_repair_cost_usd.\n\n"
            + CLAIM_NARRATIVE
        ),
    },
]
