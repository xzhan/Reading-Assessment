"""Seed reading passages for local tests and the MVP demo."""

from __future__ import annotations


READING_PASSAGES = [
    {
        "id": "rp_b1_garden_notice",
        "passage_code": "B1_GARDEN_NOTICE",
        "title": "A New Garden at School",
        "body_text": (
            "Our school has a small new garden behind the library. Last month, the science teacher asked students "
            "to help plant vegetables and flowers there. At first, only ten students joined the garden club, but now "
            "more than thirty students come every Friday afternoon. Some students water the plants, some clean the paths, "
            "and others write short notes about how the plants change. The club will sell some vegetables at the school fair "
            "next month. The money will help buy more seeds and simple tools. Many students say the garden makes the school "
            "feel quieter and friendlier."
        ),
        "band_label": "Band 1",
        "anchor_lexile": 600,
        "cefr_level": "A2-",
        "genre": "functional",
        "word_count": 130,
        "topic": "school garden",
        "items": [
            {
                "id": "ri_b1_garden_main",
                "item_order": 1,
                "skill": "main_idea",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 600,
                "question_text": "What is the passage mainly about?",
                "choices": {
                    "A": "A teacher who leaves school",
                    "B": "A new school club and its garden",
                    "C": "A library that sells books",
                    "D": "A fair for parents only",
                },
                "correct_choice": "B",
                "rationales": {
                    "A": "No teacher leaves school.",
                    "B": "The passage explains the garden club and its work.",
                    "C": "The library is only a location clue.",
                    "D": "The fair is a future event, not the main idea.",
                },
            },
            {
                "id": "ri_b1_garden_detail",
                "item_order": 2,
                "skill": "detail",
                "difficulty_label": "easy",
                "difficulty_offset": -75,
                "estimated_item_lexile": 525,
                "question_text": "When do students come to the garden club?",
                "choices": {
                    "A": "Every Friday afternoon",
                    "B": "Every Monday morning",
                    "C": "Only during summer",
                    "D": "Before the library opens",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The passage states they come every Friday afternoon.",
                    "B": "Monday is not mentioned.",
                    "C": "Summer is not mentioned.",
                    "D": "The library is not part of the schedule.",
                },
            },
            {
                "id": "ri_b1_garden_inference",
                "item_order": 3,
                "skill": "inference",
                "difficulty_label": "hard",
                "difficulty_offset": 75,
                "estimated_item_lexile": 675,
                "question_text": "Why will the club sell vegetables at the fair?",
                "choices": {
                    "A": "To pay for a school trip",
                    "B": "To buy more seeds and tools",
                    "C": "To close the garden",
                    "D": "To help the library move",
                },
                "correct_choice": "B",
                "rationales": {
                    "A": "No trip is mentioned.",
                    "B": "The passage says the money will buy seeds and tools.",
                    "C": "The garden is growing, not closing.",
                    "D": "The library does not move.",
                },
            },
            {
                "id": "ri_b1_garden_vocab",
                "item_order": 4,
                "skill": "vocabulary_context",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 600,
                "question_text": "In the passage, what does tools mean?",
                "choices": {
                    "A": "Things used to do a job",
                    "B": "Stories about plants",
                    "C": "Places to study",
                    "D": "People in a club",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "Seeds and garden work show tools are useful objects.",
                    "B": "Stories do not fit the context.",
                    "C": "Places do not fit the sentence.",
                    "D": "People are students, not tools.",
                },
            },
            {
                "id": "ri_b1_garden_structure",
                "item_order": 5,
                "skill": "structure_author_purpose",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 600,
                "question_text": "Why does the writer include different jobs students do?",
                "choices": {
                    "A": "To show how the club works",
                    "B": "To compare two schools",
                    "C": "To explain a library rule",
                    "D": "To describe a difficult exam",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The jobs explain club activities.",
                    "B": "Only one school is discussed.",
                    "C": "No library rule appears.",
                    "D": "No exam is described.",
                },
            },
        ],
    },
    {
        "id": "rp_b2_volunteer_farm",
        "passage_code": "B2_VOLUNTEER_FARM",
        "title": "Alex on a French Farm",
        "body_text": (
            "Last summer, Alex, a 16-year-old student from London, joined a volunteer program in France. The program was "
            "part of a school project to experience life abroad. Alex lived on a small farm with basic facilities, such as "
            "a shared kitchen and outdoor toilets, which was a change from the luxury of home. The farm had several animals, "
            "including a donkey named Pierre, who became Alex's favourite. One important job was to measure the height of "
            "Pierre every week for a display at an agricultural show. At first, Alex considered this an unimportant task, "
            "but the farmer said that the display helped teach children about animal growth. Alex used a special tool to "
            "measure accurately and wrote down the figures in a notebook. The work was tiring, but Alex enjoyed being "
            "outdoors and learning new skills. Other volunteers came from different countries, and they worked together to "
            "keep the farm running. By the end of the program, Alex felt that the experience was valuable, not just for the "
            "farm but for personal growth."
        ),
        "band_label": "Band 2",
        "anchor_lexile": 750,
        "cefr_level": "A2",
        "genre": "narrative",
        "word_count": 197,
        "topic": "volunteering abroad",
        "items": [
            {
                "id": "ri_b2_farm_main",
                "item_order": 1,
                "skill": "main_idea",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 750,
                "question_text": "What is the passage mainly about?",
                "choices": {
                    "A": "Alex's trip to France for a holiday",
                    "B": "Alex's experience volunteering on a farm in France",
                    "C": "The life of a donkey named Pierre",
                    "D": "The facilities at a French farm",
                },
                "correct_choice": "B",
                "rationales": {
                    "A": "The trip was a volunteer program, not a holiday.",
                    "B": "The whole passage follows Alex's farm volunteer experience.",
                    "C": "Pierre is only one part of the experience.",
                    "D": "The facilities are background detail.",
                },
            },
            {
                "id": "ri_b2_farm_detail",
                "item_order": 2,
                "skill": "detail",
                "difficulty_label": "easy",
                "difficulty_offset": -75,
                "estimated_item_lexile": 675,
                "question_text": "How often did Alex measure Pierre's height?",
                "choices": {
                    "A": "Every day",
                    "B": "Once a week",
                    "C": "Every month",
                    "D": "Only at the end of the program",
                },
                "correct_choice": "B",
                "rationales": {
                    "A": "The passage says every week, not every day.",
                    "B": "Every week means once a week.",
                    "C": "Every month is not stated.",
                    "D": "The measuring happened throughout the program.",
                },
            },
            {
                "id": "ri_b2_farm_structure",
                "item_order": 3,
                "skill": "structure_author_purpose",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 750,
                "question_text": "Why does the writer explain the purpose of the display?",
                "choices": {
                    "A": "To show why Alex's task mattered",
                    "B": "To show off the farm's luxury facilities",
                    "C": "To explain how to sell the donkey",
                    "D": "To attract more volunteers",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The display taught children about animal growth.",
                    "B": "The farm is described as basic, not luxurious.",
                    "C": "The donkey is not for sale.",
                    "D": "The display is not described as advertising.",
                },
            },
            {
                "id": "ri_b2_farm_inference",
                "item_order": 4,
                "skill": "inference",
                "difficulty_label": "hard",
                "difficulty_offset": 75,
                "estimated_item_lexile": 825,
                "question_text": "What can be inferred about Alex's feelings at the end of the program?",
                "choices": {
                    "A": "Alex was disappointed with the experience.",
                    "B": "Alex felt the work was too difficult to finish.",
                    "C": "Alex valued the personal growth from the experience.",
                    "D": "Alex preferred city life to farm life.",
                },
                "correct_choice": "C",
                "rationales": {
                    "A": "The final sentence says the experience was valuable.",
                    "B": "The work was tiring, but Alex completed it.",
                    "C": "The final sentence directly supports this inference.",
                    "D": "The passage does not say Alex preferred city life.",
                },
            },
            {
                "id": "ri_b2_farm_vocab",
                "item_order": 5,
                "skill": "vocabulary_context",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 750,
                "question_text": "What does unimportant mean in the passage?",
                "choices": {
                    "A": "Very important",
                    "B": "Not important",
                    "C": "Somewhat important",
                    "D": "Extremely important",
                },
                "correct_choice": "B",
                "rationales": {
                    "A": "This is the opposite meaning.",
                    "B": "Alex first thought the task did not matter.",
                    "C": "Somewhat important is weaker than the context suggests.",
                    "D": "This repeats the opposite meaning.",
                },
            },
        ],
    },
    {
        "id": "rp_b3_robot_club",
        "passage_code": "B3_ROBOT_CLUB",
        "title": "A Robot That Carries Books",
        "body_text": (
            "The students in Class Seven wanted to build a robot for the school technology fair, but they did not want to make another toy car. "
            "Their teacher suggested watching younger students in the library. After two afternoons, the class noticed that many children carried "
            "heavy books from one table to another while looking for information. The team designed a small robot with a flat top and slow wheels. "
            "It followed a black line on the floor and stopped when someone pressed a red button. The robot was not fast, but that was part of the plan. "
            "In a crowded library, a quick robot would be unsafe. At the fair, the judges praised the team because they had solved a real school problem."
        ),
        "band_label": "Band 3",
        "anchor_lexile": 875,
        "cefr_level": "A2+/B1-",
        "genre": "informational",
        "word_count": 130,
        "topic": "school technology",
        "items": [
            {
                "id": "ri_b3_robot_main",
                "item_order": 1,
                "skill": "main_idea",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 875,
                "question_text": "What is the passage mainly about?",
                "choices": {
                    "A": "Students designing a useful robot for school",
                    "B": "A library replacing all its books",
                    "C": "Judges teaching students to drive cars",
                    "D": "A toy car race at a technology fair",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The team builds a book-carrying robot.",
                    "B": "The library keeps its books.",
                    "C": "Judges evaluate the project.",
                    "D": "They avoid making another toy car.",
                },
            },
            {
                "id": "ri_b3_robot_detail",
                "item_order": 2,
                "skill": "detail",
                "difficulty_label": "easy",
                "difficulty_offset": -75,
                "estimated_item_lexile": 800,
                "question_text": "What did the robot follow on the floor?",
                "choices": {
                    "A": "A black line",
                    "B": "A blue light",
                    "C": "A library card",
                    "D": "A teacher's voice",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The passage states it followed a black line.",
                    "B": "No blue light is mentioned.",
                    "C": "Cards are not part of the robot.",
                    "D": "Voice control is not described.",
                },
            },
            {
                "id": "ri_b3_robot_inference",
                "item_order": 3,
                "skill": "inference",
                "difficulty_label": "hard",
                "difficulty_offset": 75,
                "estimated_item_lexile": 950,
                "question_text": "Why was being slow a good feature for the robot?",
                "choices": {
                    "A": "It made the robot cheaper to paint",
                    "B": "It made the robot safer in a busy place",
                    "C": "It helped the robot win races",
                    "D": "It allowed the robot to read books",
                },
                "correct_choice": "B",
                "rationales": {
                    "A": "Painting is not discussed.",
                    "B": "A quick robot would be unsafe in a crowded library.",
                    "C": "The robot is not for racing.",
                    "D": "It carries books but does not read.",
                },
            },
            {
                "id": "ri_b3_robot_vocab",
                "item_order": 4,
                "skill": "vocabulary_context",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 875,
                "question_text": "What does praised mean in the passage?",
                "choices": {
                    "A": "Spoke well of",
                    "B": "Disagreed with",
                    "C": "Copied from",
                    "D": "Waited for",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The judges liked the useful solution.",
                    "B": "They did not disagree.",
                    "C": "No copying is described.",
                    "D": "Waiting is not the meaning.",
                },
            },
            {
                "id": "ri_b3_robot_structure",
                "item_order": 5,
                "skill": "structure_author_purpose",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 875,
                "question_text": "Why does the writer describe the students watching younger children?",
                "choices": {
                    "A": "To show how they found a real problem",
                    "B": "To explain why libraries are noisy",
                    "C": "To introduce a new reading contest",
                    "D": "To show that the fair was cancelled",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "Observation led to the robot idea.",
                    "B": "Noise is not the issue.",
                    "C": "There is no reading contest.",
                    "D": "The fair takes place.",
                },
            },
        ],
    },
    {
        "id": "rp_b4_sleep_article",
        "passage_code": "B4_SLEEP_ARTICLE",
        "title": "Why One School Started Later",
        "body_text": (
            "For many years, Green Hill School began lessons at 7:30 each morning. Teachers believed the early start gave students more time for clubs "
            "and homework in the afternoon. However, a survey showed that many older students were sleeping less than seven hours on school nights. "
            "Some arrived late, and others said they could not concentrate during the first two lessons. The school tested a later start time for one term. "
            "Lessons began at 8:20, while clubs moved slightly later in the day. The change did not solve every problem, but attendance improved and fewer "
            "students reported feeling sleepy before lunch. The head teacher said the result was not a simple victory for sleeping longer. It showed that "
            "school schedules should be checked when students' habits and health change."
        ),
        "band_label": "Band 4",
        "anchor_lexile": 1025,
        "cefr_level": "B1",
        "genre": "opinion",
        "word_count": 139,
        "topic": "school schedule",
        "items": [
            {
                "id": "ri_b4_sleep_main",
                "item_order": 1,
                "skill": "main_idea",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 1025,
                "question_text": "What is the main idea of the article?",
                "choices": {
                    "A": "A school tested a later start time after noticing student tiredness",
                    "B": "Students at one school stopped doing homework",
                    "C": "A head teacher cancelled all afternoon clubs",
                    "D": "Teachers wanted every lesson to be shorter",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The article explains the reason and result of the later start.",
                    "B": "Homework is not stopped.",
                    "C": "Clubs moved later, not cancelled.",
                    "D": "Lesson length is not discussed.",
                },
            },
            {
                "id": "ri_b4_sleep_detail",
                "item_order": 2,
                "skill": "detail",
                "difficulty_label": "easy",
                "difficulty_offset": -75,
                "estimated_item_lexile": 950,
                "question_text": "What problem did the survey find?",
                "choices": {
                    "A": "Many older students slept less than seven hours",
                    "B": "Most students disliked all clubs",
                    "C": "Teachers arrived after lunch",
                    "D": "The school had no homework",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The survey showed this directly.",
                    "B": "Club dislike is not stated.",
                    "C": "Teacher arrival is not mentioned.",
                    "D": "Homework still exists.",
                },
            },
            {
                "id": "ri_b4_sleep_inference",
                "item_order": 3,
                "skill": "inference",
                "difficulty_label": "hard",
                "difficulty_offset": 75,
                "estimated_item_lexile": 1100,
                "question_text": "What does the head teacher probably believe?",
                "choices": {
                    "A": "Schedules should respond to evidence about students",
                    "B": "Students should choose every lesson time",
                    "C": "Clubs are more important than health",
                    "D": "Starting earlier always improves learning",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The final sentence says schedules should be checked as habits and health change.",
                    "B": "Students do not choose every time.",
                    "C": "Health is central to the decision.",
                    "D": "The school moved away from an early start.",
                },
            },
            {
                "id": "ri_b4_sleep_vocab",
                "item_order": 4,
                "skill": "vocabulary_context",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 1025,
                "question_text": "In the article, what does concentrate mean?",
                "choices": {
                    "A": "Pay attention",
                    "B": "Leave quickly",
                    "C": "Feel hungry",
                    "D": "Write more slowly",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "Sleepy students struggled during lessons.",
                    "B": "Leaving is not implied.",
                    "C": "Hunger is not discussed.",
                    "D": "Writing speed is not the issue.",
                },
            },
            {
                "id": "ri_b4_sleep_structure",
                "item_order": 5,
                "skill": "structure_author_purpose",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 1025,
                "question_text": "Why does the writer mention both benefits and limits of the change?",
                "choices": {
                    "A": "To give a balanced explanation",
                    "B": "To make the school sound careless",
                    "C": "To show that surveys are useless",
                    "D": "To argue clubs should disappear",
                },
                "correct_choice": "A",
                "rationales": {
                    "A": "The article says the change helped but did not solve everything.",
                    "B": "The school is shown as testing evidence.",
                    "C": "The survey helps identify the issue.",
                    "D": "Clubs are moved, not removed.",
                },
            },
        ],
    },
]
