#!/usr/bin/env python3
"""Fill the remaining pages in batch 04221021 without calling the external API."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


BATCH_ID = "04221021"
ROOT = Path("/Users/xzhan/vibcoding/EnglishTest")
PIPELINE_PATH = ROOT / "scripts" / "pet_reading_pipeline.py"
VOCAB_JSON = ROOT / "output" / "test_vocab.json"
RAW_DIR = ROOT / "output" / f"raw_{BATCH_ID}"


DRAFTS: dict[int, dict] = {
    16: {
        "passage": "Last month, Riverside School started a comedy production for the spring festival. Mia, whose nationality is Spanish, wanted to compete for one of the main parts, but she was nearly too nervous to stand on the stage. Mr Cole, the honest drama teacher, wrote the rehearsal times on the blackboard every morning so nobody forgot them. During the first practice, a local cameraman visited the hall to film a short report about the club. He asked the students to repeat one funny scene several times. Mia was terrified when she forgot her line, but her classmates laughed kindly and clapped. After that, she relaxed and spoke more clearly. Although Mia did not get the lead role, she helped the club finish a lively show and learned that taking part was sometimes more important than winning.",
        "questions": [
            {"number": 1, "question": "What is the passage mainly about?", "options": {"A": "A school comedy production", "B": "A hockey final", "C": "A television news studio", "D": "A nationality lesson"}, "answer": "A"},
            {"number": 2, "question": "Why did Mr Cole write on the blackboard?", "options": {"A": "To test the students", "B": "To show the cameraman a script", "C": "So nobody forgot rehearsal times", "D": "To choose the main actor"}, "answer": "C"},
            {"number": 3, "question": "Why did the cameraman come to the hall?", "options": {"A": "To offer Mia a paid job", "B": "To film a report about the club", "C": "To teach hockey to the students", "D": "To repair the stage lights"}, "answer": "B"},
            {"number": 4, "question": "How did the class react when Mia forgot her line?", "options": {"A": "They laughed kindly and clapped", "B": "They became annoyed with her", "C": "They left the hall at once", "D": "They asked the teacher to stop"}, "answer": "A"},
            {"number": 5, "question": "What did Mia learn by the end?", "options": {"A": "Winning is the only important thing", "B": "The lead role is always the easiest", "C": "Being filmed is better than acting", "D": "Taking part can matter more than winning"}, "answer": "D"},
        ],
        "difficulty_notes": "A clear school story with simple emotions and familiar performance vocabulary.",
    },
    17: {
        "passage": "Hi Ben, Thanks for your message about Saturday. I spent the day in the city with my cousin Ella, who has real musical talent. First, we went to a short lecture at the arts centre about classical music. The speaker explained why some young people think it is old-fashioned, but he also showed how exciting it can be. After that, we did some shopping for sunglasses and a new phone battery because Ella had lost both during a night out. The only disadvantage of the trip was the crowd. There were so many people in the streets because the weekend nightlife festival had already started. Still, we enjoyed the atmosphere and even heard a student orchestra playing outside the station. On the way home, Ella said she might join the school music club again.",
        "questions": [
            {"number": 1, "question": "Why did the writer go to the city?", "options": {"A": "To work at a festival", "B": "To enjoy music activities and shop", "C": "To return a receipt", "D": "To meet a head teacher"}, "answer": "B"},
            {"number": 2, "question": "What did Ella need to buy?", "options": {"A": "A dress and shoes", "B": "Books about classical music", "C": "Sunglasses and a phone battery", "D": "Tickets for a dance class"}, "answer": "C"},
            {"number": 3, "question": "What was the disadvantage of the trip?", "options": {"A": "The lecture was cancelled", "B": "There were too many people", "C": "The shops were closed", "D": "Ella forgot her bag"}, "answer": "B"},
            {"number": 4, "question": "What can we understand about Ella?", "options": {"A": "She may rejoin the music club", "B": "She dislikes classical music", "C": "She hates shopping trips", "D": "She wants to leave school"}, "answer": "A"},
            {"number": 5, "question": "What does the word talent mean in the email?", "options": {"A": "A natural ability", "B": "A difficult exam", "C": "A noisy instrument", "D": "A type of concert"}, "answer": "A"},
        ],
        "difficulty_notes": "An everyday email that mixes a city outing with simple meaning and inference questions.",
    },
    18: {
        "passage": "On the thirtieth day of our summer project, our class visited a cultural museum in Bristol. An experienced guide called Mrs Green led us through the building and showed us a new documentary about the history of local science. After the film, she asked us to describe the object that interested us most. I chose an old suitcase that had belonged to a young chemist who travelled around Europe. Mrs Green said his career began when he was still at school and he loved chemistry experiments. She also explained that students should keep notes whenever they visit a museum, because small details are easy to forget. Before we left, we were allowed to look into a narrow closet where workers store costumes and posters from past exhibitions. The trip was much more interesting than I had expected.",
        "questions": [
            {"number": 1, "question": "What did the class watch at the museum?", "options": {"A": "A comedy play", "B": "A documentary about local science", "C": "A live chemistry lesson", "D": "A sports film"}, "answer": "B"},
            {"number": 2, "question": "Which object did the writer choose to describe?", "options": {"A": "An old suitcase", "B": "A silver medal", "C": "A camera", "D": "A school uniform"}, "answer": "A"},
            {"number": 3, "question": "Why did Mrs Green say students should keep notes?", "options": {"A": "The museum was noisy", "B": "Teachers would collect them", "C": "Details are easy to forget", "D": "The guide wanted homework"}, "answer": "C"},
            {"number": 4, "question": "What was kept in the closet?", "options": {"A": "Snacks for visitors", "B": "Costumes and posters", "C": "Chemistry equipment", "D": "Travel bags"}, "answer": "B"},
            {"number": 5, "question": "How did the writer feel about the visit?", "options": {"A": "It was more interesting than expected", "B": "It was too long and boring", "C": "It was only useful for scientists", "D": "It was less helpful than school"}, "answer": "A"},
        ],
        "difficulty_notes": "A museum report with straightforward detail questions and a clear final opinion.",
    },
    19: {
        "passage": "Dear Students, If you intend to improve your English speaking, our language centre has a simple solution. From next Monday, a qualified teacher will offer evening classes twice a week. The course includes pronunciation training, short conversations and games. We use colourful cards and picture stories so the lessons feel lively rather than difficult. Several students have already asked questions regarding homework. The answer is easy: bring a notebook and a pen, and the rest of the material is ours. If you miss a class, do not borrow another student's notes and pretend they are theirs. Instead, speak to the teacher after the lesson and ask what to revise. The centre believes that regular practice matters more than speed, so students should feel calmer and more confident by the end of the month.",
        "questions": [
            {"number": 1, "question": "What is the purpose of the text?", "options": {"A": "To advertise a speaking course", "B": "To describe a school trip", "C": "To explain a library rule", "D": "To report exam results"}, "answer": "A"},
            {"number": 2, "question": "Who will teach the classes?", "options": {"A": "A student helper", "B": "A qualified teacher", "C": "A visiting actor", "D": "A science coach"}, "answer": "B"},
            {"number": 3, "question": "What should students bring to class?", "options": {"A": "A dictionary and cards", "B": "Their own textbooks", "C": "A notebook and a pen", "D": "A laptop and headphones"}, "answer": "C"},
            {"number": 4, "question": "What should a student do after missing a class?", "options": {"A": "Stop attending the course", "B": "Copy someone else's notes", "C": "Ask a friend for all the answers", "D": "Speak to the teacher after class"}, "answer": "D"},
            {"number": 5, "question": "What does the centre believe?", "options": {"A": "Speed is more important than practice", "B": "Regular practice matters most", "C": "Homework should be avoided", "D": "Evening classes are too hard"}, "answer": "B"},
        ],
        "difficulty_notes": "A simple course notice using familiar classroom situations and clear advice.",
    },
    20: {
        "passage": "Every Friday at lunchtime, the square near our school turns into a busy market. Last week, our class helped to assist the organisers because they wanted to attract more young visitors. One stall sold old-fashioned toys, while another offered half-price books and maps from every continent. I was nervous at first because I had to answer questions from strangers, but the stall owners were friendly and patient. My job was to check which bags were marked for the art club and to carry them less than a kilometre from the bus stop to the square. By midday, the smell of fresh bread and soup filled the air, and the whole place felt cheerful. The event taught me that a simple local market can be both useful and fun when students are willing to help.",
        "questions": [
            {"number": 1, "question": "What happens near the school every Friday?", "options": {"A": "A music lesson", "B": "A film club", "C": "A market in the square", "D": "A sports meeting"}, "answer": "C"},
            {"number": 2, "question": "Why did the class help the organisers?", "options": {"A": "To attract more young visitors", "B": "To earn money for a holiday", "C": "To practise cooking", "D": "To sell school uniforms"}, "answer": "A"},
            {"number": 3, "question": "What was the writer's job?", "options": {"A": "To play music for visitors", "B": "To move marked bags from the bus stop", "C": "To paint signs for the square", "D": "To sell soup and bread"}, "answer": "B"},
            {"number": 4, "question": "Why was the writer nervous at first?", "options": {"A": "The square was too far away", "B": "The market was closing early", "C": "The bags were too heavy", "D": "Strangers were asking questions"}, "answer": "D"},
            {"number": 5, "question": "What did the writer learn from the event?", "options": {"A": "Markets are only for adults", "B": "Old-fashioned toys are expensive", "C": "Local events can be useful and enjoyable", "D": "Students should not help in public"}, "answer": "C"},
        ],
        "difficulty_notes": "An easy market story with practical tasks and a clear final lesson.",
    },
    21: {
        "passage": "Last weekend, my family stayed at a well-known guest-house on the coast. The place was run by a friendly woman who used to work as a theatre director, so every room had a different style. Ours had a blue wall, a small fridge and posters in the background showing old plays. On Saturday evening, a young guitar player came to the dining room to perform for the guests. We wanted to stay until the end, but my little brother was already exhausted after a day of surfing lessons. The owner said we could listen from our room unless the rain became too loud on the roof. Luckily, the weather stayed calm. The guest-house was comfortable without trying too hard to be fashionable, and that made it feel warm and honest.",
        "questions": [
            {"number": 1, "question": "What is the passage mainly about?", "options": {"A": "A school drama lesson", "B": "A family stay at a coastal guest-house", "C": "A music competition", "D": "A job in a hotel kitchen"}, "answer": "B"},
            {"number": 2, "question": "What was special about the rooms?", "options": {"A": "Each one had a different style", "B": "They were all painted black", "C": "They had no windows", "D": "They were only for actors"}, "answer": "A"},
            {"number": 3, "question": "Why did the family leave the dining room early?", "options": {"A": "The music was too loud", "B": "The player stopped performing", "C": "The little brother was exhausted", "D": "The rain came inside"}, "answer": "C"},
            {"number": 4, "question": "When could the family keep listening from their room?", "options": {"A": "After the director arrived", "B": "Unless the rain became too loud", "C": "Only if the fridge was moved", "D": "When the guests had gone home"}, "answer": "B"},
            {"number": 5, "question": "How did the writer feel about the guest-house?", "options": {"A": "It was cold and disappointing", "B": "It was too modern to relax in", "C": "It was expensive but beautiful", "D": "It felt comfortable and welcoming"}, "answer": "D"},
        ],
        "difficulty_notes": "A short travel review with familiar accommodation details and simple inference.",
    },
    22: {
        "passage": "At the town museum, visitors are invited to take part in a new nature trail. When you enter, turn right at the main stairs and pick up the green sheet from the right-hand desk. It asks each group to answer a question about plants, animals and local history. If you are unsure about anything, a guide will inform you where to look next. At the end of the trail, children can create a simple paper bird and take home a small souvenir. The most exciting stop is the room about a recent discovery in the nearby hills, where workers found ancient tools under the ground. The display explains how these objects may influence what we know about early life in the area. Tickets are cheap, and the walk around the museum takes less than an hour.",
        "questions": [
            {"number": 1, "question": "What should visitors do first?", "options": {"A": "Pick up a green sheet", "B": "Buy a souvenir", "C": "Watch a film", "D": "Meet the butcher"}, "answer": "A"},
            {"number": 2, "question": "What can children do at the end of the trail?", "options": {"A": "Paint the museum wall", "B": "Feed animals outside", "C": "Make a paper bird", "D": "Take tools home"}, "answer": "C"},
            {"number": 3, "question": "What is the most exciting stop on the trail?", "options": {"A": "The ticket office", "B": "The room about a recent discovery", "C": "The café near the exit", "D": "The shop by the door"}, "answer": "B"},
            {"number": 4, "question": "What should you do if you are not sure where to go?", "options": {"A": "Ask a guide", "B": "Leave the museum", "C": "Wait for another family", "D": "Read the answer sheet"}, "answer": "A"},
            {"number": 5, "question": "Why is the museum trail good for families?", "options": {"A": "It is cheap and does not take long", "B": "It includes free lunch", "C": "It only needs one adult", "D": "It finishes at the park"}, "answer": "A"},
        ],
        "difficulty_notes": "An information text with clear instructions and a simple museum setting.",
    },
    23: {
        "passage": "For our school health week, Tom and I worked on a project about safe cycling. We did online research in my bedroom and read several reports about why walking and riding bikes are good exercise. Tom drew a poster showing the most important parts of a bicycle, including the handlebars and the lights. He is usually well-dressed and careful, so I was surprised when he turned up in paint-covered trousers after art club. We laughed about it and decided that appearance did not matter as much as clear information. One report said many accidents happen because riders make stupid choices, such as using their phones on the road. We added that point to our poster and also included a drawing of a helmet. By Friday, the finished display looked bright, useful and healthy enough to hang in the hall.",
        "questions": [
            {"number": 1, "question": "What was the project about?", "options": {"A": "How to repair bicycles", "B": "Healthy and safe cycling", "C": "How to decorate a bedroom", "D": "Why walking is boring"}, "answer": "B"},
            {"number": 2, "question": "What did Tom show on the poster?", "options": {"A": "Different school uniforms", "B": "Results from an exam", "C": "Pictures of internet pages", "D": "Important bicycle parts"}, "answer": "D"},
            {"number": 3, "question": "Why was the writer surprised by Tom?", "options": {"A": "He was usually well-dressed", "B": "He refused to do research", "C": "He could not draw", "D": "He disliked healthy food"}, "answer": "A"},
            {"number": 4, "question": "What unsafe action did the report mention?", "options": {"A": "Walking too slowly", "B": "Wearing bright clothes", "C": "Using phones while riding", "D": "Keeping a bike in a bedroom"}, "answer": "C"},
            {"number": 5, "question": "Why was the display put in the hall?", "options": {"A": "It was too large for the bedroom", "B": "It looked useful and healthy", "C": "The art teacher needed the space", "D": "Tom wanted to take it home"}, "answer": "B"},
        ],
        "difficulty_notes": "A school project text with direct links between the passage and each question.",
    },
    24: {
        "passage": "Just before the school show began, Anna realised that one orange scarf was missing from the costume box. She checked her locker, looked behind the curtain and asked everyone if they could identify the item. At first, she forgot to search the photography room, where students had been taking pictures of the actors. A boy called Leo, whose initial was also A, said he had seen something colourful near the window. Anna ran there and found the scarf hanging beside a paper butterfly from the art class. She felt relieved at once, because the scarf was needed for the opening dance. Leo joked that the main actor looked too handsome to worry about a small problem, but Anna knew that one missing object could spoil the first scene. When the music started, everything was finally ready.",
        "questions": [
            {"number": 1, "question": "What was missing before the show?", "options": {"A": "A camera", "B": "A script", "C": "An orange scarf", "D": "A pair of shoes"}, "answer": "C"},
            {"number": 2, "question": "Where did Anna finally find the scarf?", "options": {"A": "Inside her locker", "B": "Under the stage", "C": "In the school office", "D": "Near the window in the photography room"}, "answer": "D"},
            {"number": 3, "question": "Why did Anna feel relieved?", "options": {"A": "The scarf was needed for the dance", "B": "Leo offered her a new costume", "C": "The show was cancelled", "D": "The actor found his shoes"}, "answer": "A"},
            {"number": 4, "question": "What mistake did Anna make at first?", "options": {"A": "She blamed Leo", "B": "She forgot to search one room", "C": "She put the scarf in a bag", "D": "She left the theatre early"}, "answer": "B"},
            {"number": 5, "question": "What does the story show?", "options": {"A": "Actors never worry", "B": "Butterflies are useful in plays", "C": "Small problems can affect a show", "D": "Photography rooms should stay closed"}, "answer": "C"},
        ],
        "difficulty_notes": "A backstage school story with clear cause-and-effect questions.",
    },
    25: {
        "passage": "On the twenty-third of June, our town will hold its summer sports day. Every runner will go through the park before finishing in the main square. I finished sixteenth last year, which made me proud because I had only started training in spring. This time, I am helping the organisers as well, because I have a part-time job at the stadium on Saturdays. Near the finish line, volunteers will sell drinks, fruit and warm mushroom pies. Visitors love the route because it passes the lake and the old tower, the town's most famous attraction. A local news team may film the race for the evening programme, so the square is likely to be busier than usual. Although I want to run faster, I like the event most because it raises money for the children's hospital.",
        "questions": [
            {"number": 1, "question": "When will the sports day take place?", "options": {"A": "On the twenty-third of June", "B": "At the end of July", "C": "On the sixteenth of May", "D": "Next Saturday morning"}, "answer": "A"},
            {"number": 2, "question": "Where do the runners go before the finish?", "options": {"A": "Across the beach", "B": "Through the park", "C": "Around the school hall", "D": "Past the hospital"}, "answer": "B"},
            {"number": 3, "question": "How did the writer do last year?", "options": {"A": "He won the race", "B": "He stopped halfway", "C": "He worked at the stadium", "D": "He finished sixteenth"}, "answer": "D"},
            {"number": 4, "question": "What food will volunteers sell?", "options": {"A": "Fish sandwiches", "B": "Chocolate cakes", "C": "Mushroom pies", "D": "Sausage rolls"}, "answer": "C"},
            {"number": 5, "question": "Why does the writer like the event most?", "options": {"A": "It raises money for the hospital", "B": "It is shown on television", "C": "It gives him a paid job", "D": "It is easy to win"}, "answer": "A"},
        ],
        "difficulty_notes": "A community sports text with direct factual questions and one opinion item.",
    },
    26: {
        "passage": "Hi Emma, I still cannot believe how good our autumn trip was. In October, my best friend Lily and I travelled to a small town in the northwest of France. At first, the destination sounded dull because almost nobody in class had heard of it, and our teacher said there was nowhere exciting to shop. However, the place turned out to be perfect for a quiet weekend. Lily is easygoing, so she never complained when our train was late or when it rained on the first morning. We stayed in a family hotel where breakfast included fresh bread, fruit and local cheese. My favourite part was walking along the harbour and watching fishing boats return at sunset. It was not a glamorous holiday, but it was absolutely relaxing. If the school offers the same trip next year, I will join again.",
        "questions": [
            {"number": 1, "question": "Where did the writer travel in October?", "options": {"A": "A village in southern England", "B": "A town in northwest France", "C": "A city in eastern Spain", "D": "A port in northern Italy"}, "answer": "B"},
            {"number": 2, "question": "Why did the destination sound dull at first?", "options": {"A": "It was too expensive", "B": "The hotel was old", "C": "The weather was cold", "D": "It sounded like there was nowhere exciting to shop"}, "answer": "D"},
            {"number": 3, "question": "What is Lily like?", "options": {"A": "Easygoing", "B": "Very impatient", "C": "Rather shy", "D": "Quite rude"}, "answer": "A"},
            {"number": 4, "question": "What did they have for breakfast?", "options": {"A": "Soup and salad", "B": "Eggs and bacon", "C": "Bread, fruit and cheese", "D": "Fish and rice"}, "answer": "C"},
            {"number": 5, "question": "How does the writer feel about the trip now?", "options": {"A": "It was too quiet", "B": "It was absolutely relaxing", "C": "It was not worth the journey", "D": "It should be shorter next time"}, "answer": "B"},
        ],
        "difficulty_notes": "An email-style travel reflection with simple character and attitude questions.",
    },
    46: {
        "passage": "Our school camping club will hold a winter sleepover on Friday evening, and I am writing to announce a few details. Everyone is welcome to arrive in ordinary clothes or in a funny costume. The teachers say either choice is OK/okay, as long as it is safe and warm. Because the hall can get cold after midnight, please do not forget your pyjamas and a small heater if your parents allow it. The oldest student helper is nineteen, and he is an expert at organising indoor games. He believes that people are more likely to enjoy the night if they bring snacks and join in. Last year, a few students made negative comments about the food, but most of us still had a great time. Remember to hand in your permission form by Wednesday so we know how many beds to prepare.",
        "questions": [
            {"number": 1, "question": "Why is the writer sending this message?", "options": {"A": "To complain about last year", "B": "To invite parents to a meeting", "C": "To announce details of a sleepover", "D": "To ask for a new costume"}, "answer": "C"},
            {"number": 2, "question": "What may students wear?", "options": {"A": "Ordinary clothes or a costume", "B": "Only pyjamas", "C": "School uniform only", "D": "Sports clothes only"}, "answer": "A"},
            {"number": 3, "question": "Why should students bring pyjamas and maybe a heater?", "options": {"A": "The games room is outside", "B": "The club wants a fashion show", "C": "Beds are not ready", "D": "The hall can be cold at night"}, "answer": "D"},
            {"number": 4, "question": "What is special about the oldest student helper?", "options": {"A": "He cooks all the meals", "B": "He is nineteen and good at organising games", "C": "He works at the school office", "D": "He dislikes the sleepover"}, "answer": "B"},
            {"number": 5, "question": "What must students do by Wednesday?", "options": {"A": "Choose a teacher", "B": "Pay for a heater", "C": "Hand in a permission form", "D": "Write about last year"}, "answer": "C"},
        ],
        "difficulty_notes": "A practical school notice with clear rules and a simple deadline.",
    },
    56: {
        "passage": "On Saturday, our school will host the twenty-first youth speaking day. Students from several local schools are coming to take part in a short speech competition and a music workshop. If you have an inquiry about times or tickets, please send it to the office by Thursday afternoon. The morning programme begins with a pleasant face-to-face meeting for all competitors, so they can relax before speaking in public. After lunch, a young musician will lead a session on using voice and rhythm in presentations. Teachers will also give short advice after each round, which many students find useful. My sister entered the contest when she was in eighteenth place on the reserve list, but another student became ill and she was invited at the last minute. She has practised every evening and now feels much more confident about the day.",
        "questions": [
            {"number": 1, "question": "What event will happen on Saturday?", "options": {"A": "A youth speaking day", "B": "A sports final", "C": "A school trip", "D": "A parents meeting"}, "answer": "A"},
            {"number": 2, "question": "How should someone ask about times or tickets?", "options": {"A": "Speak to the musician", "B": "Wait until the day", "C": "Ask a classmate", "D": "Send an inquiry to the office"}, "answer": "D"},
            {"number": 3, "question": "Why is there a face-to-face meeting in the morning?", "options": {"A": "To choose the winners", "B": "To help competitors relax", "C": "To sell tickets", "D": "To move furniture"}, "answer": "B"},
            {"number": 4, "question": "What will the young musician do?", "options": {"A": "Judge every speech", "B": "Play during lunch", "C": "Lead a workshop session", "D": "Drive students home"}, "answer": "C"},
            {"number": 5, "question": "How did the writer's sister get a place?", "options": {"A": "Another student became ill", "B": "She was the first to apply", "C": "Her teacher paid for it", "D": "She won a school prize"}, "answer": "A"},
        ],
        "difficulty_notes": "An event notice with simple sequencing and one small inference about the sister.",
    },
    57: {
        "passage": "We were meant to take a charter bus to the sports centre for a squash tournament last Sunday, but the weather changed everything. Heavy rain began before breakfast, and by the time we reached the crossroads near school, the driver said the roads were unsafe. Our coach checked his contract with the bus company and decided to cancel the trip. It was a real disappointment because we had trained for weeks. Some players were even wearing their new team fashion jackets for the first time. While we waited for parents to collect us, my friend Zara used her handkerchief to dry the windows so we could watch the storm outside. Later, the teacher promised that the competition would happen next month if the hall was free. We were unhappy at first, but at least nobody was put in danger.",
        "questions": [
            {"number": 1, "question": "How were the players meant to travel?", "options": {"A": "By train", "B": "By charter bus", "C": "By bicycle", "D": "On foot"}, "answer": "B"},
            {"number": 2, "question": "Why was the trip cancelled?", "options": {"A": "The sports centre closed early", "B": "Not enough players arrived", "C": "The weather made the roads unsafe", "D": "The bus company lost the contract"}, "answer": "C"},
            {"number": 3, "question": "What did the coach check before cancelling?", "options": {"A": "The contract with the company", "B": "The players' tickets", "C": "The school timetable", "D": "The cost of lunch"}, "answer": "A"},
            {"number": 4, "question": "Why did Zara use her handkerchief?", "options": {"A": "To clean her shoes", "B": "To wrap a present", "C": "To dry the team shirts", "D": "To wipe the windows"}, "answer": "D"},
            {"number": 5, "question": "How did the players feel in the end?", "options": {"A": "Glad the match was finished", "B": "Angry with the driver", "C": "Still sad but pleased nobody was hurt", "D": "Excited to play outdoors"}, "answer": "C"},
        ],
        "difficulty_notes": "A cancelled trip story with clear reasons and a simple emotional ending.",
    },
    58: {
        "passage": "Last night, the science club put on an entertainment show about space travel. The hall was full of families, and nearly a hundred people came to watch. At the centre of the stage stood a yellow model rocket that the older students had been working on for weeks. Their aim was to achieve two things: explain how rockets move and prove that science can be fun. During the programme, visitors guessed the quantity of air needed to push the model upward. When the countdown ended, a button was pressed and the rocket flew high enough to make everyone cheer. One boy almost dropped his drink in surprise, but luckily no liquid touched the equipment. The evening was lovely from start to finish, and by the end the club felt complete because every member had helped in some way.",
        "questions": [
            {"number": 1, "question": "What kind of event did the science club organise?", "options": {"A": "A space entertainment show", "B": "A school dance", "C": "A football match", "D": "A cooking lesson"}, "answer": "A"},
            {"number": 2, "question": "How many people came to watch?", "options": {"A": "About twenty", "B": "More than two hundred", "C": "Exactly fifty", "D": "Nearly a hundred"}, "answer": "D"},
            {"number": 3, "question": "Why did the students build the rocket?", "options": {"A": "To win money", "B": "To explain science in a fun way", "C": "To travel outside", "D": "To decorate the stage"}, "answer": "B"},
            {"number": 4, "question": "What did visitors guess during the show?", "options": {"A": "The speed of the bus", "B": "The colour of the rocket", "C": "The quantity of air needed", "D": "The number of teachers there"}, "answer": "C"},
            {"number": 5, "question": "How does the writer describe the evening?", "options": {"A": "Lovely and successful", "B": "Too noisy and long", "C": "Useful but dull", "D": "Confusing and unsafe"}, "answer": "A"},
        ],
        "difficulty_notes": "A lively club report with simple science vocabulary and clear outcomes.",
    },
    59: {
        "passage": "Last month, our class visited a wildlife park in the western part of the county. The bus driver asked to see the teacher's licence before we set off, and everyone laughed because Mr Hayes had almost forgotten it. At the park gate, the bird keeper gave us a short talk about animals from southern Africa and Australia. Unfortunately, the weather turned wet, so we spent more time indoors than we had planned. In the reptile house, I bought a small purple notebook because I wanted to write a composition about the trip later. There was also a curved mirror near the exit, which made us all look taller and stranger than usual. Even with the rain, the day was alright in the end. The best present was being able to watch the baby penguins being fed at close range.",
        "questions": [
            {"number": 1, "question": "Where did the class go?", "options": {"A": "A museum in the city centre", "B": "A park in the south of France", "C": "A wildlife park in the western county", "D": "A beach near school"}, "answer": "C"},
            {"number": 2, "question": "What did the driver ask to see?", "options": {"A": "The map", "B": "The teacher's licence", "C": "A present for the keeper", "D": "The lunch tickets"}, "answer": "B"},
            {"number": 3, "question": "What did the keeper talk about?", "options": {"A": "Birds from southern places", "B": "How to draw a composition", "C": "Why the mirror was broken", "D": "The school timetable"}, "answer": "A"},
            {"number": 4, "question": "Why did the class stay indoors more than planned?", "options": {"A": "The guide was late", "B": "The reptiles were hungry", "C": "The notebook shop was crowded", "D": "The weather became wet"}, "answer": "D"},
            {"number": 5, "question": "Why did the writer buy the purple notebook?", "options": {"A": "To show the driver", "B": "To give it to the keeper", "C": "To write a composition later", "D": "To hide the licence inside"}, "answer": "C"},
        ],
        "difficulty_notes": "A class trip report with simple details and an easy vocabulary question in context.",
    },
    60: {
        "passage": "On Sunday, our running club met in the park at fourteen minutes past nine for a charity morning. Some members preferred jogging around the lake, while others helped set up tables for snacks and hot drinks. I arrived early with my camera because the organiser wanted a photograph of everyone before the race began. We covered one table with a bright table-cloth and placed cups in a straight line so the picture would look tidy. The weather was cold enough to freeze the grass in the shaded areas, but the sun soon warmed us up. Later, one parent asked if I was looking for employment as a sports photographer, which made me laugh. I am still a student, but it was nice to hear. The event was friendly, well organised and very reasonable for a small local club.",
        "questions": [
            {"number": 1, "question": "Why did the writer arrive early?", "options": {"A": "To start jogging first", "B": "To take a photograph", "C": "To sell hot drinks", "D": "To clean the park"}, "answer": "B"},
            {"number": 2, "question": "What did the group put on the table?", "options": {"A": "A table-cloth and cups", "B": "A heater and coats", "C": "Medals and books", "D": "A television and food"}, "answer": "A"},
            {"number": 3, "question": "What does the passage say about the weather?", "options": {"A": "It was hot all morning", "B": "It stayed dark until midday", "C": "The rain stopped the event", "D": "The grass could freeze in the shade"}, "answer": "D"},
            {"number": 4, "question": "Why did a parent mention employment?", "options": {"A": "The writer was taking photos well", "B": "The club needed a new coach", "C": "The event cost too much", "D": "The organiser was late"}, "answer": "A"},
            {"number": 5, "question": "How does the writer describe the event?", "options": {"A": "Friendly and reasonable", "B": "Large and difficult", "C": "Cold but boring", "D": "Short and disappointing"}, "answer": "A"},
        ],
        "difficulty_notes": "A simple community event text with clear physical details and one mild inference.",
    },
    61: {
        "passage": "Our gymnastics team had an early flight on Monday, so we met at the airport before sunrise. Mrs Khan stood by the entrance and asked anyone who had not checked in online to come straight to her. One boy arrived with an untidy bag full of clothes, snacks and even an eraser from his maths lesson. He said he had packed in a hurry and was already tired. Another student felt disappointed because the warm breeze outside made her wish we were going to the beach instead of to a sports hall. Before we went through security, the coach read out every surname to make sure the team list was correct. The group would consist of twelve gymnasts and two teachers. Once everyone was together, even the nervous students began to smile and talk about the competition ahead.",
        "questions": [
            {"number": 1, "question": "Where did the team meet?", "options": {"A": "At the airport", "B": "In the gym", "C": "At the beach", "D": "Outside the hotel"}, "answer": "A"},
            {"number": 2, "question": "What unusual thing was in the boy's bag?", "options": {"A": "A football shirt", "B": "A silver cup", "C": "A camera battery", "D": "An eraser"}, "answer": "D"},
            {"number": 3, "question": "Why was one student disappointed?", "options": {"A": "She lost her ticket", "B": "The warm breeze made her want a beach trip", "C": "Her surname was missing", "D": "She forgot her bag"}, "answer": "B"},
            {"number": 4, "question": "What did the coach read out before security?", "options": {"A": "The weather report", "B": "The hotel address", "C": "Every surname", "D": "The flight price"}, "answer": "C"},
            {"number": 5, "question": "What would the group consist of?", "options": {"A": "Twelve gymnasts and two teachers", "B": "Ten parents and two teachers", "C": "Twelve coaches and one student", "D": "Fourteen teachers"}, "answer": "A"},
        ],
        "difficulty_notes": "An airport departure story with clear factual questions and light emotional detail.",
    },
    62: {
        "passage": "Our class trip to England began on the twenty-fourth of March, and the hardest part was the airport check-in. Because our flight left early, we travelled overnight by coach and arrived before dawn. The teacher told us to keep a phone number for emergency contact in our pockets and to request help at once if anything went wrong. One student's suitcase was too heavy, so the airline worker showed him how to remove a silver photo frame and pack it in hand luggage instead. A banker standing behind us smiled and said school trips were always more exciting than business travel. After security, we sat near the gate and watched planes connect with flights to other cities. Although everyone looked tired, the mood was cheerful because our long journey was finally beginning.",
        "questions": [
            {"number": 1, "question": "When did the trip to England begin?", "options": {"A": "On the first of March", "B": "On the twenty-fourth of March", "C": "At the end of April", "D": "On a Saturday in May"}, "answer": "B"},
            {"number": 2, "question": "What was the hardest part of the journey?", "options": {"A": "The airport check-in", "B": "The overnight coach", "C": "The flight to England", "D": "The walk to the gate"}, "answer": "A"},
            {"number": 3, "question": "Why did the class travel overnight?", "options": {"A": "The teacher preferred it", "B": "The airport was very far away", "C": "Hotels were too expensive", "D": "Their flight left early"}, "answer": "D"},
            {"number": 4, "question": "What did the airline worker ask one student to do?", "options": {"A": "Call an emergency contact", "B": "Give a bag to the banker", "C": "Move a silver photo frame into hand luggage", "D": "Buy another suitcase"}, "answer": "C"},
            {"number": 5, "question": "How did the class feel after security?", "options": {"A": "Tired but cheerful", "B": "Angry and confused", "C": "Bored and hungry", "D": "Scared of flying"}, "answer": "A"},
        ],
        "difficulty_notes": "A travel passage with a clear timeline and simple airport vocabulary.",
    },
    63: {
        "passage": "Everyone at school has received an invitation to the spring talent evening next month. The event will be led by a former student who now works as a television presenter. He has agreed to introduce each act and interview the most talented performers after the show. Because the hall is open to the public, extra security will be in place at the doors. Students are asked to keep large bags in the wardrobe room behind the stage and to arrive at least thirty minutes early. My band is practising a new song, and our music teacher is doing us a favour by lending extra speakers. She says that performing live helps create a stronger connection with the audience than posting videos online. If the night goes well, we may even raise money for the local youth club.",
        "questions": [
            {"number": 1, "question": "What event are students invited to?", "options": {"A": "The spring talent evening", "B": "A science exhibition", "C": "A sports prizegiving", "D": "A film afternoon"}, "answer": "A"},
            {"number": 2, "question": "Who will lead the evening?", "options": {"A": "The head teacher", "B": "A famous singer", "C": "A security guard", "D": "A former student who is now a presenter"}, "answer": "D"},
            {"number": 3, "question": "Why will there be extra security?", "options": {"A": "The band is very popular", "B": "The wardrobe room is full", "C": "The hall is open to the public", "D": "Students are bringing money"}, "answer": "C"},
            {"number": 4, "question": "Where should students leave large bags?", "options": {"A": "In the music room", "B": "In the wardrobe room", "C": "Beside the stage lights", "D": "At the front door"}, "answer": "B"},
            {"number": 5, "question": "What favour is the music teacher doing?", "options": {"A": "Lending extra speakers", "B": "Buying the tickets", "C": "Writing a new song", "D": "Driving students home"}, "answer": "A"},
        ],
        "difficulty_notes": "A performance notice with familiar school details and very clear key information.",
    },
    64: {
        "passage": "When Mr Lewis took retirement from teaching, he did not want to spend every day sitting at home. Instead, he opened a small second-hand bookshop near the station. At first, some people were surprised by the idea, but the shop soon became a happy part of the town's culture. Mr Lewis keeps a shelf of travel writing, a corner for young readers and a table for revision guides before exams. He says his greatest happiness comes from helping a child discover a story they love. Last week, I asked whether he ever misses the classroom. He smiled and said he sometimes thinks about his old students, especially when one of them is absent from the shop for a long time. Still, he feels totally sure that he made the right decision.",
        "questions": [
            {"number": 1, "question": "What did Mr Lewis do after retirement?", "options": {"A": "He travelled abroad", "B": "He started teaching online", "C": "He opened a second-hand bookshop", "D": "He worked at the station"}, "answer": "C"},
            {"number": 2, "question": "Why were some people surprised at first?", "options": {"A": "The shop sold food", "B": "A teacher opened a bookshop", "C": "The prices were too low", "D": "The building was very large"}, "answer": "B"},
            {"number": 3, "question": "What does Mr Lewis put on the table before exams?", "options": {"A": "Travel books", "B": "Children's stories", "C": "Free magazines", "D": "Revision guides"}, "answer": "D"},
            {"number": 4, "question": "What gives Mr Lewis the most happiness?", "options": {"A": "Selling expensive books", "B": "Meeting famous writers", "C": "Helping a child find a story they love", "D": "Closing the shop early"}, "answer": "C"},
            {"number": 5, "question": "How does Mr Lewis feel about his decision?", "options": {"A": "Totally sure it was right", "B": "Still uncertain", "C": "A little disappointed", "D": "Too busy to decide"}, "answer": "A"},
        ],
        "difficulty_notes": "A warm human-interest text with a clear opinion at the end.",
    },
    65: {
        "passage": "My cheerful grandparent came to stay with us on the twenty-second of August while my parents were away. On the first morning, Grandpa took me to the city centre because he had to visit the passport department at the embassy. Afterwards, we bought bread, fruit and a spicy sausage for lunch. He also chose a bag of peanut biscuits for the train journey home. Grandpa likes looking at old buildings and always tells stories about every street. When we returned to our flat, he asked where he could put the food. I showed him the freezer, but he laughed and said the biscuits would be better in the cupboard. Later, he helped me write a postcard and reminded me that caring for other people's property is part of being a good guest. By the end of the week, I did not want him to leave.",
        "questions": [
            {"number": 1, "question": "Why did Grandpa go to the city centre?", "options": {"A": "To buy new clothes", "B": "To visit the passport department at the embassy", "C": "To meet an old friend", "D": "To see a football match"}, "answer": "B"},
            {"number": 2, "question": "What did they buy for lunch?", "options": {"A": "Peanut soup", "B": "Frozen fish", "C": "A spicy sausage", "D": "Cheese sandwiches"}, "answer": "C"},
            {"number": 3, "question": "Where did the writer first suggest putting the food?", "options": {"A": "In the freezer", "B": "On the balcony", "C": "In the wardrobe", "D": "Under the bed"}, "answer": "A"},
            {"number": 4, "question": "What lesson did Grandpa give later?", "options": {"A": "Postcards should be short", "B": "Stations are always busy", "C": "Embassies can be confusing", "D": "A good guest respects other people's property"}, "answer": "D"},
            {"number": 5, "question": "How did the writer feel at the end of the visit?", "options": {"A": "Glad the flat was quiet again", "B": "Sorry Grandpa was leaving", "C": "Eager to visit the embassy", "D": "Tired of city walks"}, "answer": "B"},
        ],
        "difficulty_notes": "A family visit story with clear sequence and a gentle message about behaviour.",
    },
    66: {
        "passage": "A bright new vegetarian cafe has opened beside the library, and the owner is looking to employ one weekend helper. The lady who runs the place says she wants a student who can smile at customers, clear tables quickly and learn simple tasks in the kitchen. I visited yesterday with my sister, and the room felt sunny and welcoming, with plants on every shelf. The menu was short but delicious: soup, salad, sandwiches and fruit drinks. Although I am not vegetarian, I enjoyed the food and the calm atmosphere. The owner explained that the job is only for Saturday mornings, so it would not affect schoolwork. She also said experience is useful but not necessary if the person is polite and reliable. It sounds like a good first job for someone who likes working with people.",
        "questions": [
            {"number": 1, "question": "Where is the new cafe?", "options": {"A": "Beside the library", "B": "Next to the station", "C": "Inside the school", "D": "Near the beach"}, "answer": "A"},
            {"number": 2, "question": "What kind of helper does the lady want?", "options": {"A": "Someone who can cook full meals", "B": "A person with years of experience", "C": "A polite student who can help customers", "D": "A musician for Saturday evenings"}, "answer": "C"},
            {"number": 3, "question": "Why is the job suitable for a student?", "options": {"A": "It includes free books", "B": "It is only on Saturday mornings", "C": "It is close to the beach", "D": "It pays for all school costs"}, "answer": "B"},
            {"number": 4, "question": "What did the writer think of the cafe?", "options": {"A": "Too small and dark", "B": "Expensive but quiet", "C": "Only good for vegetarians", "D": "Sunny, welcoming and tasty"}, "answer": "D"},
            {"number": 5, "question": "Who runs the cafe?", "options": {"A": "A lady owner", "B": "The local library", "C": "Two school students", "D": "A sports coach"}, "answer": "A"},
        ],
        "difficulty_notes": "A simple job and café text with very direct factual questions.",
    },
}


def load_pipeline():
    spec = importlib.util.spec_from_file_location("pet_pipeline_fill", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_pipeline()
    data = json.loads(VOCAB_JSON.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for page_number, draft in sorted(DRAFTS.items()):
        page_data = data["pages"][page_number - 1]
        page = module.VocabPage(
            page_number=page_data["page_number"],
            lesson_number=page_data["lesson_number"],
            words=[module.VocabEntry(**item) for item in page_data["words"]],
        )
        errors, normalized = module.validate_reading(draft, page)
        if errors:
            raise RuntimeError(f"Validation failed for page {page_number}: {errors}")
        normalized.update(
            {
                "title": module.build_title(page.page_number, BATCH_ID),
                "page_number": page.page_number,
                "lesson_number": page.lesson_number,
                "focus_words": [
                    {"term": entry.term, "gloss": entry.gloss}
                    for entry in module.select_focus_words(page.words)
                ],
                "source_words": [
                    {"term": entry.term, "gloss": entry.gloss}
                    for entry in page.words
                ],
            }
        )
        output_path = RAW_DIR / f"page_{page_number:03d}.json"
        output_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[filled] {output_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
