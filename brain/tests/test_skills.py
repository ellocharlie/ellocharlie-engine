"""
Tests for brain.skills — create_skill, get_skill, list_skills, improve_skill,
match_skill, increment_usage, delete_skill, and markdown file writing.
"""

from __future__ import annotations

import pytest

from brain.skills import (
    create_skill,
    delete_skill,
    get_skill,
    improve_skill,
    increment_usage,
    list_skills,
    match_skill,
)


# ---------------------------------------------------------------------------
# create_skill
# ---------------------------------------------------------------------------


def test_create_skill_returns_complete_row():
    """create_skill() must return a dict with all expected fields."""
    skill = create_skill(
        name="customer-onboarding",
        description="Standard procedure for onboarding a new customer",
        trigger_pattern="new customer onboarding setup",
        content="1. Welcome email\n2. Schedule kickoff call\n3. Set up workspace",
    )
    assert skill["id"] is not None
    assert skill["name"] == "customer-onboarding"
    assert skill["description"] == "Standard procedure for onboarding a new customer"
    assert skill["trigger_pattern"] == "new customer onboarding setup"
    assert "Welcome email" in skill["skill_content"]
    assert skill["usage_count"] == 0


def test_create_skill_writes_markdown_file(tmp_path, monkeypatch):
    """create_skill() must write a .md file with the skill's content."""
    import brain.skills as skills_mod

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(skills_mod, "SKILLS_DIR", skills_dir)

    create_skill(
        name="content-review",
        description="Review and approve blog content",
        trigger_pattern="review content approve blog post",
        content="## Steps\n1. Check frontmatter\n2. Verify word count\n3. Approve",
    )

    md_file = skills_dir / "content-review.md"
    assert md_file.exists(), "Markdown file was not created"
    text = md_file.read_text()
    assert "content-review" in text
    assert "Review and approve blog content" in text
    assert "Check frontmatter" in text


def test_create_skill_markdown_has_yaml_frontmatter(tmp_path, monkeypatch):
    """The written .md file must have YAML front-matter with name, trigger, usage_count."""
    import brain.skills as skills_mod

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(skills_mod, "SKILLS_DIR", skills_dir)

    create_skill(
        name="deploy-checklist",
        description="Checklist for production deployments",
        trigger_pattern="deploy production checklist",
        content="- Run tests\n- Check monitoring\n- Deploy",
    )
    text = (skills_dir / "deploy-checklist.md").read_text()
    assert text.startswith("---")
    assert "name: deploy-checklist" in text
    assert "usage_count: 0" in text


def test_create_skill_upserts_existing():
    """Creating a skill with an existing name must update it, not duplicate it."""
    create_skill(
        name="pricing-strategy",
        description="Initial pricing doc",
        trigger_pattern="pricing strategy",
        content="Original content",
    )
    updated = create_skill(
        name="pricing-strategy",
        description="Updated pricing doc",
        trigger_pattern="pricing strategy",
        content="Revised content with more detail",
    )
    all_skills = list_skills()
    matching = [s for s in all_skills if s["name"] == "pricing-strategy"]
    assert len(matching) == 1, "Upsert created a duplicate"
    assert matching[0]["description"] == "Updated pricing doc"


def test_create_skill_slug_with_special_chars():
    """Skill names with spaces and special chars must generate a clean slug file."""
    import brain.skills as skills_mod

    create_skill(
        name="seo & content workflow",
        description="SEO workflow for blog posts",
        trigger_pattern="seo content workflow",
        content="Research keywords, write, review, publish",
    )
    # _slug should convert to: seo-content-workflow
    expected_path = skills_mod.SKILLS_DIR / "seo-content-workflow.md"
    assert expected_path.exists()


# ---------------------------------------------------------------------------
# get_skill
# ---------------------------------------------------------------------------


def test_get_skill_returns_row_with_markdown_path():
    """get_skill() must return the row dict including 'markdown_path'."""
    create_skill(
        name="incident-response",
        description="Protocol for handling production incidents",
        trigger_pattern="incident production outage response",
        content="1. Page on-call\n2. Create incident channel\n3. Post updates every 15 min",
    )
    skill = get_skill("incident-response")
    assert skill is not None
    assert skill["name"] == "incident-response"
    assert "markdown_path" in skill
    assert skill["markdown_path"].endswith("incident-response.md")


def test_get_skill_returns_none_for_missing():
    """get_skill() must return None for a name that doesn't exist."""
    result = get_skill("this-skill-does-not-exist")
    assert result is None


# ---------------------------------------------------------------------------
# list_skills
# ---------------------------------------------------------------------------


def test_list_skills_returns_all():
    """list_skills() must return all created skills."""
    create_skill("skill-a", "Skill A", "trigger a", "content a")
    create_skill("skill-b", "Skill B", "trigger b", "content b")
    create_skill("skill-c", "Skill C", "trigger c", "content c")
    skills = list_skills()
    names = {s["name"] for s in skills}
    assert {"skill-a", "skill-b", "skill-c"}.issubset(names)


def test_list_skills_includes_markdown_path():
    """Every row from list_skills() must include 'markdown_path'."""
    create_skill("path-test", "test", "test trigger", "test content")
    skills = list_skills()
    assert all("markdown_path" in s for s in skills)


def test_list_skills_ordered_by_usage_count_desc():
    """list_skills() must return skills ordered by usage_count descending."""
    create_skill("low-usage", "Low usage skill", "low usage trigger", "content")
    create_skill("high-usage", "High usage skill", "high usage trigger", "content")

    increment_usage("high-usage")
    increment_usage("high-usage")
    increment_usage("high-usage")

    skills = list_skills()
    counts = [s["usage_count"] for s in skills]
    assert counts == sorted(counts, reverse=True)


def test_list_skills_empty_when_none_created():
    """list_skills() must return an empty list if no skills exist."""
    assert list_skills() == []


# ---------------------------------------------------------------------------
# improve_skill
# ---------------------------------------------------------------------------


def test_improve_skill_appends_feedback_to_content():
    """improve_skill() must append feedback as a note to skill_content."""
    create_skill(
        name="email-campaign",
        description="Email campaign workflow",
        trigger_pattern="email campaign send newsletter",
        content="1. Draft\n2. Review\n3. Send",
    )
    improved = improve_skill(
        "email-campaign",
        "Add A/B testing step before sending",
    )
    assert "Add A/B testing step before sending" in improved["skill_content"]
    assert "Improvement Note" in improved["skill_content"]


def test_improve_skill_updates_markdown_file():
    """improve_skill() must rewrite the .md file with the updated content."""
    import brain.skills as skills_mod

    create_skill(
        name="support-triage",
        description="Customer support triage",
        trigger_pattern="support ticket triage escalate",
        content="1. Categorise\n2. Route\n3. Respond",
    )
    improve_skill("support-triage", "Add SLA tracking step")
    text = (skills_mod.SKILLS_DIR / "support-triage.md").read_text()
    assert "SLA tracking" in text


def test_improve_skill_raises_for_missing():
    """improve_skill() must raise ValueError for a non-existent skill."""
    with pytest.raises(ValueError, match="not found"):
        improve_skill("ghost-skill", "some feedback")


# ---------------------------------------------------------------------------
# match_skill
# ---------------------------------------------------------------------------


def test_match_skill_exact_phrase():
    """match_skill() must return a skill when its trigger phrase is the context."""
    create_skill(
        name="weekly-metrics-review",
        description="Weekly metrics review process",
        trigger_pattern="weekly metrics review dashboard",
        content="Pull data, analyse, post to Slack",
    )
    result = match_skill("weekly metrics review dashboard")
    assert result is not None
    assert result["name"] == "weekly-metrics-review"


def test_match_skill_word_overlap():
    """match_skill() should find a skill via word-overlap scoring."""
    create_skill(
        name="content-publishing",
        description="Content publishing procedure for the blog",
        trigger_pattern="publish blog content review approve",
        content="1. Validate frontmatter\n2. Review\n3. Publish to CDN",
    )
    result = match_skill("how do we publish blog content")
    assert result is not None
    assert result["name"] == "content-publishing"


def test_match_skill_returns_none_when_no_match():
    """match_skill() must return None when there are no skills at all."""
    result = match_skill("xyzzy frob blort unknown topic")
    assert result is None


def test_match_skill_returns_markdown_path():
    """match_skill() result must include 'markdown_path'."""
    create_skill(
        name="renewal-playbook",
        description="Customer renewal playbook",
        trigger_pattern="renewal playbook customer retention",
        content="60 days out: review health score. 30 days: exec sponsor. Close.",
    )
    result = match_skill("renewal playbook retention")
    assert result is not None
    assert "markdown_path" in result


# ---------------------------------------------------------------------------
# increment_usage
# ---------------------------------------------------------------------------


def test_increment_usage_increases_count():
    """increment_usage() must increment usage_count by 1 each call."""
    create_skill(
        name="api-design",
        description="API design standards",
        trigger_pattern="api design rest standards",
        content="Use noun-based routes, version with /v1/, return JSON",
    )
    s1 = increment_usage("api-design")
    assert s1["usage_count"] == 1

    s2 = increment_usage("api-design")
    assert s2["usage_count"] == 2


def test_increment_usage_sets_last_used():
    """increment_usage() must update the last_used timestamp."""
    create_skill(
        name="sprint-retro",
        description="Sprint retrospective procedure",
        trigger_pattern="sprint retro retrospective agile",
        content="What went well, what to improve, action items",
    )
    original = get_skill("sprint-retro")
    assert original["last_used"] is None

    updated = increment_usage("sprint-retro")
    assert updated["last_used"] is not None


def test_increment_usage_updates_markdown_file():
    """increment_usage() must rewrite the .md file with the new usage count."""
    import brain.skills as skills_mod

    create_skill(
        name="code-review",
        description="Code review checklist",
        trigger_pattern="code review pull request check",
        content="- Tests pass\n- Docs updated\n- No lint errors",
    )
    increment_usage("code-review")
    text = (skills_mod.SKILLS_DIR / "code-review.md").read_text()
    assert "usage_count: 1" in text


def test_increment_usage_raises_for_missing():
    """increment_usage() must raise ValueError for a non-existent skill."""
    with pytest.raises(ValueError, match="not found"):
        increment_usage("nonexistent-skill")


# ---------------------------------------------------------------------------
# delete_skill
# ---------------------------------------------------------------------------


def test_delete_skill_removes_from_db_and_fs():
    """delete_skill() must remove the DB row and the .md file."""
    import brain.skills as skills_mod

    create_skill(
        name="temp-skill",
        description="Temporary skill to be deleted",
        trigger_pattern="temp skill delete",
        content="This will be deleted",
    )
    md_path = skills_mod.SKILLS_DIR / "temp-skill.md"
    assert md_path.exists()

    result = delete_skill("temp-skill")
    assert result is True
    assert not md_path.exists()
    assert get_skill("temp-skill") is None


def test_delete_skill_returns_false_for_missing():
    """delete_skill() must return False when the skill doesn't exist."""
    assert delete_skill("never-created-skill") is False
