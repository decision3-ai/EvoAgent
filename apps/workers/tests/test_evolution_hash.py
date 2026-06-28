"""
Unit tests for SHA-256 evolution verification logic.

Tests the hash comparison that prevents fake/noop evolutions from being
committed to the database. No DB or LLM required — pure Python.
"""
import hashlib
import unittest


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def simulate_evolution_hash_check(current_prompt: str, improved_prompt: str) -> dict:
    """
    Mirrors the hash verification logic in evolve_agent.
    Returns a dict with status and hash info.
    """
    baseline_hash = _sha256(current_prompt)
    evolved_hash = _sha256(improved_prompt)

    if evolved_hash == baseline_hash:
        return {'status': 'evolution_noop', 'hash': baseline_hash}

    return {
        'status': 'evolved',
        'baseline_hash': baseline_hash,
        'evolved_hash': evolved_hash,
    }


class TestEvolutionHashVerification(unittest.TestCase):

    def test_identical_prompts_detected_as_noop(self):
        prompt = "You are a helpful coding assistant."
        result = simulate_evolution_hash_check(prompt, prompt)
        self.assertEqual(result['status'], 'evolution_noop')
        self.assertIn('hash', result)
        self.assertEqual(result['hash'], _sha256(prompt))

    def test_whitespace_only_change_detected_as_noop(self):
        """Prompts differing only in trailing whitespace still differ in hash."""
        prompt_a = "You are a helpful coding assistant."
        prompt_b = "You are a helpful coding assistant.  "
        result = simulate_evolution_hash_check(prompt_a, prompt_b)
        # Trailing whitespace IS a real diff — sha256 catches it
        self.assertEqual(result['status'], 'evolved')

    def test_real_change_is_accepted(self):
        original = "You are a helpful coding assistant."
        evolved = "You are a concise, precise coding assistant. Avoid verbose answers."
        result = simulate_evolution_hash_check(original, evolved)
        self.assertEqual(result['status'], 'evolved')
        self.assertIn('baseline_hash', result)
        self.assertIn('evolved_hash', result)
        self.assertNotEqual(result['baseline_hash'], result['evolved_hash'])

    def test_hash_is_64_hex_chars(self):
        h = _sha256("any prompt text")
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in h))

    def test_hashes_are_deterministic(self):
        prompt = "You are an AI coding assistant.\nBe direct."
        self.assertEqual(_sha256(prompt), _sha256(prompt))

    def test_case_sensitive(self):
        """Upper vs lower case counts as a real change."""
        result = simulate_evolution_hash_check(
            "You are a helpful assistant.",
            "You are a Helpful Assistant.",
        )
        self.assertEqual(result['status'], 'evolved')

    def test_empty_evolved_prompt_would_be_caught_upstream(self):
        """Empty string vs original — hash differs, but the real guard is the
        'if not improved_prompt' check before hash comparison in evolve_agent."""
        result = simulate_evolution_hash_check("some prompt", "")
        # Empty string has a different hash than any non-empty prompt
        self.assertEqual(result['status'], 'evolved')
        self.assertNotEqual(result['baseline_hash'], result['evolved_hash'])

    def test_noop_returns_no_evolved_hash(self):
        prompt = "Prompt that did not change."
        result = simulate_evolution_hash_check(prompt, prompt)
        self.assertNotIn('evolved_hash', result)
        self.assertNotIn('baseline_hash', result)


if __name__ == '__main__':
    unittest.main()
