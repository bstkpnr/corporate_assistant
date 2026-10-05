"""Prompt dosyalarının testleri."""
import pytest

from src.prompts import PROMPTS_DIR, load_prompt


@pytest.mark.parametrize("name", [p.stem for p in PROMPTS_DIR.glob("*.md")])
def test_every_prompt_loads(name):
    """Her prompt dosyası hatasız yüklenmeli (eksik değişken = KeyError)."""
    load_prompt(name, context="x", question="y")


def test_system_prompt_has_no_unfilled_placeholders():
    text = load_prompt("system_prompt", employee_name="Muhammet Boğa", employee_id="E001")
    assert "Muhammet Boğa" in text and "E001" in text
    assert "{" not in text and "}" not in text