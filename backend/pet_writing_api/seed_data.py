"""Seed data for PET Writing MVP."""

from __future__ import annotations

PET_WRITING_PROMPTS = [
    {
        "id": "wp_pet_email_001",
        "prompt_code": "wp_pet_email_001",
        "task_type": "email",
        "title": "Write an email to your English friend",
        "instructions": (
            "You have received an email from your English friend Sam. "
            "Sam asks you about an after-school club at your school. "
            "Write an email to Sam. In your email, say which club you joined, "
            "why you like it, and invite Sam to visit or join you one day."
        ),
        "target_word_count_min": 100,
        "target_word_count_max": 140,
        "recommended_time_sec": 1200,
        "rubric_version": "pet-writing-v1",
        "metadata": {
            "content_points": [
                ["club", "music", "art", "sports", "science", "drama"],
                ["because", "enjoy", "like", "love", "interesting", "fun"],
                ["join", "come", "visit", "invite", "with me", "next week"],
            ]
        },
    },
    {
        "id": "wp_pet_article_001",
        "prompt_code": "wp_pet_article_001",
        "task_type": "article",
        "title": "Write an article for your school magazine",
        "instructions": (
            "Your school magazine wants articles about memorable school days. "
            "Write an article about your best day at school. "
            "Describe what happened, explain why it was special, and say what "
            "you learned from the experience."
        ),
        "target_word_count_min": 100,
        "target_word_count_max": 140,
        "recommended_time_sec": 1200,
        "rubric_version": "pet-writing-v1",
        "metadata": {
            "content_points": [
                ["day", "school", "class", "trip", "match", "festival"],
                ["because", "special", "memorable", "important", "best"],
                ["learned", "learnt", "realised", "understood", "experience"],
            ]
        },
    },
]
