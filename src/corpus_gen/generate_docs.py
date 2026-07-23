import json

from src.integrations.llm_providers import call_ollama
from src.corpus_gen.facts import POLICIES, CLAIMS, MEDICAL_NOTES

POLICY_PROMPT = """You are drafting a formal insurance policy document for an \
internal system. Write realistic, formal policy-document prose (not a \
summary) covering ONLY the facts below, organized under these exact section \
headers, each on its own line in ALL CAPS:

DECLARATIONS
COVERAGE SUMMARY
DEDUCTIBLES AND LIMITS
EXCLUSIONS
DEFINITIONS

Do not invent coverage amounts, dates, or facts beyond what is given below. \
Under DEDUCTIBLES AND LIMITS, present each figure as its own line so it reads \
like a schedule, not a paragraph. Under DEFINITIONS, write 3-4 short \
definitions of insurance terms relevant to this policy type (e.g. \
"deductible", "dwelling coverage", "collision", "coinsurance" as applicable) \
in your own words.

Facts:
{facts}

Write the full document text now, starting with DECLARATIONS.
"""

CLAIM_PROMPT = """Write a formal claim intake narrative for a case worker, in \
prose paragraphs, based ONLY on the facts below. Do not invent facts beyond \
what is given. Mention the claim ID and policy number naturally in the text.

Facts:
{facts}

Write the narrative now.
"""

MEDICAL_NOTE_PROMPT = """Write a clinical visit note in the style used by a \
{facility_type}, based ONLY on the facts below. Do not invent facts beyond \
what is given. Use a standard clinical note structure (chief complaint, \
assessment, plan, etc.) as appropriate for this facility type.

Facts:
{facts}

Write the note now.
"""


def generate_policy_document(policy: dict) -> str:
    prompt = POLICY_PROMPT.format(facts=json.dumps(policy, indent=2))
    return call_ollama(prompt, model="llama3.2:3b")["response_text"]


def generate_claim_narrative(claim: dict) -> str:
    prompt = CLAIM_PROMPT.format(
        facts=f"Claim ID: {claim['claim_id']}\n"
        f"Policy number: {claim['policy_number']}\n"
        f"Date of loss: {claim['date_of_loss']}\n"
        f"{claim['facts']}"
    )
    return call_ollama(prompt, model="llama3.2:3b")["response_text"]


def generate_medical_note(note: dict) -> str:
    prompt = MEDICAL_NOTE_PROMPT.format(
        facility_type=note["facility_type"],
        facts=f"Patient: {note['patient_name']}\n"
        f"Visit date: {note['visit_date']}\n"
        f"{note['facts']}",
    )
    return call_ollama(prompt, model="llama3.2:3b")["response_text"]


if __name__ == "__main__":
    sample = POLICIES[0]
    print(f"=== Generating sample policy doc: {sample['policy_number']} ===\n")
    print(generate_policy_document(sample))
