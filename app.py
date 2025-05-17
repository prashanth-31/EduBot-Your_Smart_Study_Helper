import streamlit as st
import google.generativeai as genai
import os
import re
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

DEFAULT_API_KEY = "GOOGLE_API_KEY"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", DEFAULT_API_KEY)

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    st.error("No API key found. Please enter your API key in the sidebar.")

if 'messages' not in st.session_state:
    st.session_state['messages'] = [
        {"role": "assistant", "content": "Hi there! I'm EduBot, your smart study helper. I can generate quizzes, summarize text, solve math problems, create flashcards, and answer your study questions. How can I help you today?"}
    ]

if 'quiz_active' not in st.session_state:
    st.session_state['quiz_active'] = False

if 'debug_mode' not in st.session_state:
    st.session_state['debug_mode'] = False
    
if 'study_history' not in st.session_state:
    st.session_state['study_history'] = []
    
if 'flashcards' not in st.session_state:
    st.session_state['flashcards'] = []
    
if 'flashcard_index' not in st.session_state:
    st.session_state['flashcard_index'] = 0
    
if 'flashcard_active' not in st.session_state:
    st.session_state['flashcard_active'] = False
    
if 'current_card_flipped' not in st.session_state:
    st.session_state['current_card_flipped'] = False
    
if 'pomodoro_active' not in st.session_state:
    st.session_state['pomodoro_active'] = False
    
if 'pomodoro_start_time' not in st.session_state:
    st.session_state['pomodoro_start_time'] = None
    
if 'pomodoro_duration' not in st.session_state:
    st.session_state['pomodoro_duration'] = 25
    
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'

def save_study_session(session_type, topic, duration=None, score=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_data = {
        "timestamp": timestamp,
        "type": session_type,
        "topic": topic,
        "duration": duration,
        "score": score
    }
    st.session_state['study_history'].append(session_data)

def get_model():
    if 'current_api_key' in st.session_state:
        genai.configure(api_key=st.session_state['current_api_key'])
    elif GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        st.session_state['current_api_key'] = GOOGLE_API_KEY
    
    try:
        DEFAULT_MODEL = 'gemini-2.0-flash'
        
        try:
            available_models = [model.name for model in genai.list_models()]
            st.session_state['available_models'] = available_models
            
            model_to_use = None
            for available in available_models:
                if DEFAULT_MODEL in available:
                    model_to_use = available
                    break
            
            if not model_to_use:
                gemini_model_candidates = [
                    'gemini-1.5-pro',
                    'gemini-pro',
                    'gemini-1.0-pro',
                    'models/gemini-1.5-flash',
                    'models/gemini-1.5-pro',
                    'models/gemini-pro',
                    'models/gemini-1.0-pro'
                ]
                
                for candidate in gemini_model_candidates:
                    for available in available_models:
                        if candidate in available:
                            model_to_use = available
                            break
                    if model_to_use:
                        break
            
            if not model_to_use and available_models:
                model_to_use = available_models[0]
                
            if model_to_use:
                if st.session_state['debug_mode']:
                    st.sidebar.success(f"Using model: {model_to_use}")
                return genai.GenerativeModel(model_to_use)
            else:
                st.error("No compatible models found")
                return None
                
        except Exception as e:
            if st.session_state['debug_mode']:
                st.sidebar.warning(f"Error listing models: {str(e)}")
            return genai.GenerativeModel(DEFAULT_MODEL)
            
    except Exception as e:
        st.error(f"Error setting up the model: {str(e)}")
        st.info("Please check your API key in the sidebar.")
        
        if 'available_models' in st.session_state:
            st.info(f"Available models: {', '.join(st.session_state['available_models'])}")
        return None

def generate_quiz(topic, num_questions=3):
    model = get_model()
    if not model:
        return "Error: Could not initialize the AI model. Please check your API key."
        
    prompt = f"""
    Create a quiz about {topic} with {num_questions} multiple-choice questions.
    For each question:
    1. Provide a clear question related to {topic}
    2. Give 4 possible answers labeled A, B, C, and D
    3. Indicate the correct answer
    
    Format the output as follows for each question:
    Q1: [Question text]
    A: [Option A]
    B: [Option B]
    C: [Option C]
    D: [Option D]
    Answer: [Correct option letter]
    Explanation: [Brief explanation of why this is correct]
    
    Separate each question with a blank line.
    """
    
    try:
        response = model.generate_content(prompt)
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'parts'):
            return ''.join([part.text for part in response.parts])
        else:
            return str(response)
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return f"Failed to generate quiz: {str(e)}"

def generate_flashcards(topic, num_cards=5):
    model = get_model()
    if not model:
        return "Error: Could not initialize the AI model. Please check your API key."
        
    prompt = f"""
    Create {num_cards} flashcards about {topic}.
    For each flashcard:
    1. Provide a clear term, concept, or question on the front
    2. Provide a concise definition, explanation, or answer on the back
    
    Format the output as follows for each flashcard:
    Front: [Term/Concept/Question]
    Back: [Definition/Explanation/Answer]
    
    Separate each flashcard with a blank line.
    """
    
    try:
        response = model.generate_content(prompt)
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'parts'):
            return ''.join([part.text for part in response.parts])
        else:
            return str(response)
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return f"Failed to generate flashcards: {str(e)}"

def parse_flashcards(flashcards_text):
    try:
        cards_raw = re.split(r'\n\s*\n', flashcards_text)
        
        cards = []
        for card_raw in cards_raw:
            if not card_raw.strip():
                continue
                
            card_dict = {}
            lines = card_raw.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Front:'):
                    card_dict["front"] = line.split(':', 1)[1].strip()
                elif line.startswith('Back:'):
                    card_dict["back"] = line.split(':', 1)[1].strip()
            
            if "front" in card_dict and "back" in card_dict:
                cards.append(card_dict)
        
        return cards
    except Exception as e:
        if st.session_state['debug_mode']:
            st.error(f"Error parsing flashcards: {str(e)}")
        return []

def parse_quiz(quiz_text):
    try:
        questions_raw = re.split(r'\n\s*\n', quiz_text)
        
        questions = []
        for q_raw in questions_raw:
            if not q_raw.strip():
                continue
                
            q_dict = {"options": {}}
            
            lines = q_raw.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Q') and ':' in line:
                    q_dict["question"] = line.split(':', 1)[1].strip()
                elif line.startswith('A:'):
                    q_dict["options"]["A"] = line[2:].strip()
                elif line.startswith('B:'):
                    q_dict["options"]["B"] = line[2:].strip()
                elif line.startswith('C:'):
                    q_dict["options"]["C"] = line[2:].strip()
                elif line.startswith('D:'):
                    q_dict["options"]["D"] = line[2:].strip()
                elif line.startswith('Answer:'):
                    q_dict["answer"] = line.split(':', 1)[1].strip()
                elif line.startswith('Explanation:'):
                    q_dict["explanation"] = line.split(':', 1)[1].strip()
            
            if "question" in q_dict and len(q_dict["options"]) == 4 and "answer" in q_dict:
                if q_dict["answer"].strip() in ["A", "B", "C", "D"]:
                    questions.append(q_dict)
        
        return questions
    except Exception as e:
        if 'debug_mode' in st.session_state and st.session_state['debug_mode']:
            st.error(f"Error parsing quiz: {str(e)}")
        return []

def summarize_text(text):
    model = get_model()
    if not model:
        return "Error: Could not initialize the AI model. Please check your API key."
        
    prompt = f"""
    Please summarize the following text into 1-2 concise sentences that capture the key points.
    Make the summary simple, clear, and easy to understand.
    
    TEXT TO SUMMARIZE:
    {text}
    """
    
    try:
        response = model.generate_content(prompt)
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'parts'):
            return ''.join([part.text for part in response.parts])
        else:
            return str(response)
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return f"Failed to summarize text: {str(e)}"

def create_study_plan(topic, days=7):
    model = get_model()
    if not model:
        return "Error: Could not initialize the AI model. Please check your API key."
        
    prompt = f"""
    Create a {days}-day study plan for learning about {topic}.
    For each day, include:
    1. Main focus/objective for the day
    2. Key concepts to study
    3. Suggested activities or exercises
    4. Estimated time needed
    
    Format the output as follows for each day:
    Day 1:
    Focus: [Main objective]
    Concepts: [Key concepts]
    Activities: [Suggested activities]
    Time: [Estimated time in hours]
    
    Separate each day with a blank line.
    """
    
    try:
        response = model.generate_content(prompt)
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'parts'):
            return ''.join([part.text for part in response.parts])
        else:
            return str(response)
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return f"Failed to create study plan: {str(e)}"

def solve_math_problem(problem):
    model = get_model()
    if not model:
        return "Error: Could not initialize the AI model. Please check your API key."
        
    prompt = f"""
    Please solve this math problem step by step:
    {problem}
    
    Provide a clear, detailed solution showing each step of your work.
    If this involves calculus, algebra, or other mathematical concepts, explain the key principles involved.
    Make your explanation understandable to a student learning this topic.
    """
    
    try:
        response = model.generate_content(prompt)
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'parts'):
            return ''.join([part.text for part in response.parts])
        else:
            return str(response)
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return f"Failed to solve math problem: {str(e)}"

def answer_general_question(question):
    model = get_model()
    if not model:
        return "Error: Could not initialize the AI model. Please check your API key."
        
    prompt = f"""
    You are EduBot, a friendly and helpful educational assistant. Answer the following question
    in a conversational, helpful manner. If the question is outside the educational domain,
    politely steer the conversation back to education.
    
    Question: {question}
    """
    
    try:
        response = model.generate_content(prompt)
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'parts'):
            return ''.join([part.text for part in response.parts])
        else:
            return str(response)
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return f"Failed to answer question: {str(e)}"

def detect_intent(user_input):
    user_input_lower = user_input.lower()
    
    # Check for flashcards intent
    flashcard_keywords = ['flashcard', 'flash card', 'flash cards', 'flashcards', 'create flashcards']
    if any(keyword in user_input_lower for keyword in flashcard_keywords):
        topic_match = re.search(r'(?:about|on) ([^?.,!]*)(?:\?|$|,|\.)', user_input_lower)
        if topic_match:
            topic = topic_match.group(1).strip()
            return 'flashcards', {'topic': topic}
        else:
            return 'flashcards_prompt', {}
    
    # Check for study plan intent
    study_plan_keywords = ['study plan', 'learning plan', 'study schedule', 'create a plan', 'learning schedule']
    if any(keyword in user_input_lower for keyword in study_plan_keywords):
        topic_match = re.search(r'(?:about|on|for|studying) ([^?.,!]*)(?:\?|$|,|\.)', user_input_lower)
        if topic_match:
            topic = topic_match.group(1).strip()
            return 'study_plan', {'topic': topic}
        else:
            return 'study_plan_prompt', {}
    
    # Check for pomodoro intent
    pomodoro_keywords = ['pomodoro', 'timer', 'study timer', 'focus timer', 'start timer']
    if any(keyword in user_input_lower for keyword in pomodoro_keywords):
        duration_match = re.search(r'(\d+) minutes', user_input_lower)
        if duration_match:
            duration = int(duration_match.group(1))
            return 'pomodoro', {'duration': duration}
        else:
            return 'pomodoro_prompt', {}
    
    # Check for quiz intent
    quiz_keywords = ['quiz', 'test', 'questions', 'make a quiz', 'create a quiz', 'generate a quiz']
    if any(keyword in user_input_lower for keyword in quiz_keywords):
        topic_match = re.search(r'(?:about|on) ([^?.,!]*)(?:\?|$|,|\.)', user_input_lower)
        if topic_match:
            topic = topic_match.group(1).strip()
            return 'quiz', {'topic': topic}
        else:
            return 'quiz_prompt', {}
    
    # Check for summarize intent
    summarize_keywords = ['summarize', 'summary', 'summarize this', 'condense', 'shorten']
    if any(keyword in user_input_lower for keyword in summarize_keywords):
        if len(user_input.split()) > 30:
            return 'summarize', {'text': user_input}
        else:
            return 'summarize_prompt', {}
    
    # Check for math problem intent
    math_keywords = ['solve', 'math', 'problem', 'equation', 'calculate', 'find', '=', '+', '-', '*', '/', 'algebra', 'calculus']
    if any(keyword in user_input_lower for keyword in math_keywords) and any(c.isdigit() for c in user_input):
        return 'math', {'problem': user_input}
    
    # Default to general question
    return 'general', {'question': user_input}

def process_user_message(user_input):
    try:
        intent, params = detect_intent(user_input)
        
        if intent == 'flashcards':
            topic = params.get('topic')
            response = f"I'd be happy to create flashcards about {topic}! How many flashcards would you like (1-10)?"
            st.session_state['pending_flashcards_topic'] = topic
            st.session_state['waiting_for_flashcards_count'] = True
        
        elif intent == 'flashcards_prompt':
            response = "I'd be happy to create flashcards for you! What topic would you like the flashcards to be about?"
            st.session_state['waiting_for_flashcards_topic'] = True
        
        elif intent == 'study_plan':
            topic = params.get('topic')
            response = f"I'd be happy to create a study plan for learning about {topic}! How many days would you like the plan to cover (1-14)?"
            st.session_state['pending_study_plan_topic'] = topic
            st.session_state['waiting_for_study_plan_days'] = True
        
        elif intent == 'study_plan_prompt':
            response = "I'd be happy to create a study plan for you! What topic would you like to study?"
            st.session_state['waiting_for_study_plan_topic'] = True
        
        elif intent == 'pomodoro':
            duration = params.get('duration', 25)
            if duration < 1:
                duration = 25
            elif duration > 60:
                duration = 60
                
            st.session_state['pomodoro_duration'] = duration
            st.session_state['pomodoro_active'] = True
            st.session_state['pomodoro_start_time'] = datetime.datetime.now()
            
            response = f"I've started a {duration}-minute Pomodoro timer for you! Focus on your work, and I'll let you know when time is up."
        
        elif intent == 'pomodoro_prompt':
            response = "I'd be happy to set a Pomodoro timer for you! How many minutes would you like to focus for (1-60)?"
            st.session_state['waiting_for_pomodoro_duration'] = True
        
        elif intent == 'quiz':
            topic = params.get('topic')
            response = f"I'd be happy to create a quiz about {topic}! How many questions would you like (1-5)?"
            st.session_state['pending_quiz_topic'] = topic
            st.session_state['waiting_for_quiz_count'] = True
        
        elif intent == 'quiz_prompt':
            response = "I'd be happy to create a quiz for you! What topic would you like the quiz to be about?"
            st.session_state['waiting_for_quiz_topic'] = True
        
        elif intent == 'summarize':
            text = params.get('text')
            summary = summarize_text(text)
            response = f"Here's a summary of what you shared:\n\n{summary}\n\nIs there anything else you'd like me to explain or summarize?"
        
        elif intent == 'summarize_prompt':
            response = "I'd be happy to summarize some text for you! Please share the passage you'd like me to summarize."
            st.session_state['waiting_for_summarize_text'] = True
        
        elif intent == 'math':
            problem = params.get('problem')
            solution = solve_math_problem(problem)
            response = f"Here's the solution to your math problem:\n\n{solution}\n\nDo you have any other problems you'd like me to solve?"
        
        else:  # general question
            question = params.get('question')
            response = answer_general_question(question)
        
        return response
    except Exception as e:
        if st.session_state['debug_mode']:
            return f"I'm sorry, I encountered an error processing your message. Error: {str(e)}"
        else:
            return "I'm sorry, I encountered an error processing your message. Could you try rephrasing or asking something else?"

def handle_flashcards_flow(user_input):
    if 'waiting_for_flashcards_topic' in st.session_state and st.session_state['waiting_for_flashcards_topic']:
        topic = user_input
        st.session_state['pending_flashcards_topic'] = topic
        st.session_state['waiting_for_flashcards_topic'] = False
        st.session_state['waiting_for_flashcards_count'] = True
        return f"Great! I'll create flashcards about {topic}. How many flashcards would you like (1-10)?"
    
    elif 'waiting_for_flashcards_count' in st.session_state and st.session_state['waiting_for_flashcards_count']:
        try:
            num_cards = int(user_input.strip())
            if 1 <= num_cards <= 10:
                topic = st.session_state['pending_flashcards_topic']
                st.session_state['waiting_for_flashcards_count'] = False
                
                with st.spinner("Generating your flashcards..."):
                    flashcards_text = generate_flashcards(topic, num_cards)
                    st.session_state['flashcards'] = parse_flashcards(flashcards_text)
                    
                    if not st.session_state['flashcards'] or len(st.session_state['flashcards']) == 0:
                        return f"I'm sorry, I couldn't generate flashcards about {topic} at the moment. Could you try another topic or try again later?"
                    
                    st.session_state['flashcard_active'] = True
                    st.session_state['flashcard_index'] = 0
                    st.session_state['current_card_flipped'] = False
                
                card = st.session_state['flashcards'][0]
                save_study_session("flashcards", topic)
                return f"Here are your flashcards on {topic}!\n\n**Card 1 (Front):** {card['front']}\n\nType 'flip' to see the back of the card, 'next' for the next card, or 'exit' to finish studying."
            else:
                return "Please choose a number between 1 and 10."
        except ValueError:
            return "Sorry, I didn't get that. Please enter a number between 1 and 10."
        except Exception as e:
            if st.session_state['debug_mode']:
                st.error(f"Flashcard generation error: {str(e)}")
            return f"I'm having trouble generating your flashcards about {topic}. Could you try another topic or try again later?"
    
    return None

def handle_study_plan_flow(user_input):
    if 'waiting_for_study_plan_topic' in st.session_state and st.session_state['waiting_for_study_plan_topic']:
        topic = user_input
        st.session_state['pending_study_plan_topic'] = topic
        st.session_state['waiting_for_study_plan_topic'] = False
        st.session_state['waiting_for_study_plan_days'] = True
        return f"Great! I'll create a study plan for {topic}. How many days would you like the plan to cover (1-14)?"
    
    elif 'waiting_for_study_plan_days' in st.session_state and st.session_state['waiting_for_study_plan_days']:
        try:
            days = int(user_input.strip())
            if 1 <= days <= 14:
                topic = st.session_state['pending_study_plan_topic']
                st.session_state['waiting_for_study_plan_days'] = False
                
                with st.spinner("Creating your study plan..."):
                    study_plan = create_study_plan(topic, days)
                
                save_study_session("study_plan", topic)
                return f"Here's your {days}-day study plan for learning about {topic}:\n\n{study_plan}\n\nIs there anything you'd like me to explain or adjust about this plan?"
            else:
                return "Please choose a number between 1 and 14 days."
        except ValueError:
            return "Sorry, I didn't get that. Please enter a number between 1 and 14."
        except Exception as e:
            if st.session_state['debug_mode']:
                st.error(f"Study plan creation error: {str(e)}")
            return f"I'm having trouble creating your study plan for {topic}. Could you try another topic or try again later?"
    
    return None

def handle_pomodoro_flow(user_input):
    if 'waiting_for_pomodoro_duration' in st.session_state and st.session_state['waiting_for_pomodoro_duration']:
        try:
            duration = int(user_input.strip())
            if 1 <= duration <= 60:
                st.session_state['waiting_for_pomodoro_duration'] = False
                st.session_state['pomodoro_duration'] = duration
                st.session_state['pomodoro_active'] = True
                st.session_state['pomodoro_start_time'] = datetime.datetime.now()
                
                return f"I've started a {duration}-minute Pomodoro timer for you! Focus on your work, and I'll let you know when time is up."
            else:
                return "Please choose a duration between 1 and 60 minutes."
        except ValueError:
            return "Sorry, I didn't get that. Please enter a duration between 1 and 60 minutes."
    
    return None

def handle_flashcard_interaction(user_input):
    if 'flashcard_active' in st.session_state and st.session_state['flashcard_active']:
        if not st.session_state['flashcards']:
            st.session_state['flashcard_active'] = False
            return "I'm sorry, there seems to be an issue with the flashcards. Let's try again with a different topic."
        
        current_index = st.session_state['flashcard_index']
        total_cards = len(st.session_state['flashcards'])
        
        if current_index >= total_cards:
            st.session_state['flashcard_active'] = False
            return "You've gone through all the flashcards! Would you like to create another set on a different topic?"
        
        current_card = st.session_state['flashcards'][current_index]
        user_command = user_input.strip().lower()
        
        if user_command == 'flip':
            st.session_state['current_card_flipped'] = not st.session_state['current_card_flipped']
            side = "Back" if st.session_state['current_card_flipped'] else "Front"
            content = current_card['back'] if st.session_state['current_card_flipped'] else current_card['front']
            
            return f"**Card {current_index + 1} ({side}):** {content}\n\nType 'flip' to see the other side, 'next' for the next card, or 'exit' to finish studying."
        
        elif user_command == 'next':
            st.session_state['flashcard_index'] += 1
            st.session_state['current_card_flipped'] = False
            
            if st.session_state['flashcard_index'] >= total_cards:
                st.session_state['flashcard_active'] = False
                return "You've gone through all the flashcards! Would you like to create another set on a different topic?"
            
            next_card = st.session_state['flashcards'][st.session_state['flashcard_index']]
            return f"**Card {st.session_state['flashcard_index'] + 1} (Front):** {next_card['front']}\n\nType 'flip' to see the back of the card, 'next' for the next card, or 'exit' to finish studying."
        
        elif user_command == 'exit':
            st.session_state['flashcard_active'] = False
            return "Flashcard study session ended. What would you like to do next?"
        
        else:
            return "Please type 'flip', 'next', or 'exit'."
    
    return None

def handle_quiz_flow(user_input):
    if 'waiting_for_quiz_topic' in st.session_state and st.session_state['waiting_for_quiz_topic']:
        topic = user_input
        st.session_state['pending_quiz_topic'] = topic
        st.session_state['waiting_for_quiz_topic'] = False
        st.session_state['waiting_for_quiz_count'] = True
        return f"Great! I'll create a quiz about {topic}. How many questions would you like (1-5)?"
    
    elif 'waiting_for_quiz_count' in st.session_state and st.session_state['waiting_for_quiz_count']:
        try:
            num_questions = int(user_input.strip())
            if 1 <= num_questions <= 5:
                topic = st.session_state['pending_quiz_topic']
                st.session_state['waiting_for_quiz_count'] = False
                
                with st.spinner("Generating your quiz..."):
                    quiz_text = generate_quiz(topic, num_questions)
                    st.session_state.quiz_questions = parse_quiz(quiz_text)
                    
                    if not st.session_state.quiz_questions or len(st.session_state.quiz_questions) == 0:
                        return f"I'm sorry, I couldn't generate a quiz about {topic} at the moment. Could you try another topic or try again later?"
                    
                    st.session_state.quiz_active = True
                    st.session_state.current_question = 0
                    st.session_state.score = 0
                    st.session_state.answered = [False] * len(st.session_state.quiz_questions)
                
                current_q = st.session_state.quiz_questions[0]
                options_text = "\n".join([f"{k}: {v}" for k, v in current_q['options'].items()])
                
                save_study_session("quiz", topic)
                return f"Here's your quiz on {topic}!\n\n**Question 1:** {current_q['question']}\n\n{options_text}\n\nReply with just the letter of your answer (A, B, C, or D)."
            else:
                return "Please choose a number between 1 and 5."
        except ValueError:
            return "Sorry, I didn't get that. Please enter a number between 1 and 5."
        except Exception as e:
            if st.session_state['debug_mode']:
                st.error(f"Quiz generation error: {str(e)}")
            return f"I'm having trouble generating your quiz about {topic}. Could you try another topic or try again later?"
    
    return None

def handle_summarize_flow(user_input):
    if 'waiting_for_summarize_text' in st.session_state and st.session_state['waiting_for_summarize_text']:
        text = user_input
        st.session_state['waiting_for_summarize_text'] = False
        
        summary = summarize_text(text)
        return f"Here's a summary of what you shared:\n\n{summary}\n\nIs there anything else you'd like me to explain or summarize?"
    
    return None

def handle_quiz_answer(user_input):
    if 'quiz_active' in st.session_state and st.session_state.quiz_active:
        if not hasattr(st.session_state, 'quiz_questions') or not st.session_state.quiz_questions:
            st.session_state.quiz_active = False
            return "I'm sorry, there seems to be an issue with the quiz. Let's try again with a different topic."
        
        if st.session_state.current_question >= len(st.session_state.quiz_questions):
            st.session_state.quiz_active = False
            return "The quiz is already completed. Would you like to try another quiz on a different topic?"
        
        user_answer = user_input.strip().upper()
        
        if len(user_answer) == 1 and user_answer in "ABCD":
            current_q = st.session_state.quiz_questions[st.session_state.current_question]
            correct_answer = current_q['answer']
            
            if user_answer == correct_answer:
                st.session_state.score += 1
                response = f"✅ Correct! {current_q.get('explanation', '')}"
            else:
                response = f"❌ Not quite. The correct answer is {correct_answer}. {current_q.get('explanation', '')}"
                
            st.session_state.answered[st.session_state.current_question] = True
            st.session_state.current_question += 1
            
            if st.session_state.current_question >= len(st.session_state.quiz_questions):
                percentage = (st.session_state.score / len(st.session_state.quiz_questions)) * 100
                response += f"\n\n🎉 Quiz complete! Your final score is {st.session_state.score}/{len(st.session_state.quiz_questions)} ({percentage:.1f}%)."
                
                if percentage >= 80:
                    response += "\n\nExcellent work! You really know this subject well."
                elif percentage >= 60:
                    response += "\n\nGood job! You have a solid understanding of this topic."
                else:
                    response += "\n\nKeep studying! You're making progress, but could use more practice with this topic."
                
                response += "\n\nWould you like to try another quiz on a different topic?"
                st.session_state.quiz_active = False
                
                topic = st.session_state.get('pending_quiz_topic', 'unknown')
                save_study_session("quiz", topic, score=f"{st.session_state.score}/{len(st.session_state.quiz_questions)}")
            else:
                next_q = st.session_state.quiz_questions[st.session_state.current_question]
                options_text = "\n".join([f"{k}: {v}" for k, v in next_q['options'].items()])
                response += f"\n\n**Question {st.session_state.current_question + 1}:** {next_q['question']}\n\n{options_text}\n\nReply with just the letter of your answer (A, B, C, or D)."
            
            return response
        else:
            return "Please reply with just the letter of your answer (A, B, C, or D)."
    
    return None

def check_pomodoro_timer():
    if st.session_state['pomodoro_active'] and st.session_state['pomodoro_start_time']:
        current_time = datetime.datetime.now()
        elapsed_time = current_time - st.session_state['pomodoro_start_time']
        elapsed_minutes = elapsed_time.total_seconds() / 60
        
        if elapsed_minutes >= st.session_state['pomodoro_duration']:
            st.session_state['pomodoro_active'] = False
            st.session_state['pomodoro_start_time'] = None
            
            save_study_session("pomodoro", "Focus Session", duration=f"{st.session_state['pomodoro_duration']} minutes")
            return f"⏰ Your {st.session_state['pomodoro_duration']}-minute Pomodoro timer is complete! Time to take a 5-minute break. Would you like to start another timer after your break?"
    
    return None

def main():
    st.set_page_config(
        page_title="EduBot - Your Smart Study Helper",
        page_icon="📚",
        layout="wide"
    )
    
    # Check if dark theme is enabled
    if st.session_state['theme'] == 'dark':
        st.markdown("""
        <style>
        body {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }
        .stApp {
            background-color: #1E1E1E;
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Change base layout based on theme
    primary_color = "#1E88E5" if st.session_state['theme'] == 'light' else "#90CAF9"
    
    st.markdown(f"""
    <style>
    .main-header {{
        font-size: 2.5rem;
        color: {primary_color};
        text-align: center;
    }}
    .stButton button {{
        background-color: {primary_color};
        color: {'#FFFFFF' if st.session_state['theme'] == 'light' else '#000000'};
    }}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 class='main-header'>📚 EduBot - Your Smart Study Helper</h1>", unsafe_allow_html=True)
    st.markdown("Chat with your AI study buddy! Ask questions, generate quizzes, summarize text, create flashcards, and more.")
    
    # Check if a Pomodoro timer has completed
    pomodoro_notification = check_pomodoro_timer()
    if pomodoro_notification:
        st.info(pomodoro_notification)
        st.session_state.messages.append({"role": "assistant", "content": pomodoro_notification})
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            value=GOOGLE_API_KEY if GOOGLE_API_KEY else "",
            help="Enter your Google Gemini API key. You can get one from https://makersuite.google.com/app/apikey"
        )
        
        if api_key:
            if api_key != os.getenv("GOOGLE_API_KEY"):
                genai.configure(api_key=api_key)
                st.success("API key updated!")
                st.session_state['current_api_key'] = api_key
        else:
            st.warning("Please enter your Google Gemini API key to use EduBot.")
        
        # Theme toggle
        theme = st.selectbox("Theme", ["Light", "Dark"], index=0 if st.session_state['theme'] == 'light' else 1)
        if (theme == "Light" and st.session_state['theme'] == 'dark') or (theme == "Dark" and st.session_state['theme'] == 'light'):
            st.session_state['theme'] = theme.lower()
            st.experimental_rerun()
        
        # Add a debug mode toggle
        debug_mode = st.checkbox("Debug Mode", value=st.session_state['debug_mode'])
        if debug_mode != st.session_state['debug_mode']:
            st.session_state['debug_mode'] = debug_mode
            st.experimental_rerun()
        
        # Display available models when in debug mode
        if st.session_state['debug_mode']:
            st.subheader("Debug Information")
            if st.button("Check Available Models"):
                try:
                    available_models = [model.name for model in genai.list_models()]
                    st.session_state['available_models'] = available_models
                    st.write("Available models:")
                    for model in available_models:
                        st.write(f"- {model}")
                except Exception as e:
                    st.error(f"Error listing models: {str(e)}")
        
        # Study history section
        st.markdown("---")
        st.subheader("📊 Study History")
        
        if st.session_state['study_history']:
            if st.button("View Study History"):
                history_text = "Your recent study sessions:\n\n"
                for i, session in enumerate(st.session_state['study_history'][-5:]):
                    history_text += f"{i+1}. {session['type'].title()} on '{session['topic']}' ({session['timestamp']})"
                    if session.get('score'):
                        history_text += f" - Score: {session['score']}"
                    if session.get('duration'):
                        history_text += f" - Duration: {session['duration']}"
                    history_text += "\n"
                st.info(history_text)
        else:
            st.info("No study history yet. Start learning to track your progress!")
        
        if st.button("Clear Study History"):
            st.session_state['study_history'] = []
            st.success("Study history cleared!")
        
        st.markdown("---")
        st.markdown("### About EduBot")
        st.markdown("""
        EduBot is a smart study helper that uses AI to help you learn more effectively.
        
        **Features:**
        - Chat about any educational topic
        - Generate quizzes on any subject
        - Create and study flashcards
        - Create personalized study plans
        - Set Pomodoro timers for focused study
        - Summarize lengthy texts
        - Solve math problems step-by-step
        
        Powered by Google Gemini API
        """)
        
        # Quick prompt suggestions
        st.markdown("### Quick Prompts")
        
        suggested_prompts = [
            "Create a quiz about photosynthesis",
            "Make flashcards on world capitals",
            "Create a study plan for calculus",
            "Start a 25-minute Pomodoro timer",
            "Summarize the key events of World War II",
            "Solve 2x + 5 = 15",
            "What's the difference between mitosis and meiosis?"
        ]
        
        for prompt in suggested_prompts:
            if st.button(prompt):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.experimental_rerun()

    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Display Pomodoro timer if active
    if st.session_state['pomodoro_active'] and st.session_state['pomodoro_start_time']:
        current_time = datetime.datetime.now()
        elapsed_time = current_time - st.session_state['pomodoro_start_time']
        elapsed_seconds = elapsed_time.total_seconds()
        remaining_seconds = max(0, st.session_state['pomodoro_duration'] * 60 - elapsed_seconds)
        
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)
        
        st.sidebar.subheader("⏱️ Pomodoro Timer")
        st.sidebar.markdown(f"**Time Remaining:** {minutes:02d}:{seconds:02d}")
        
        progress = 1 - (remaining_seconds / (st.session_state['pomodoro_duration'] * 60))
        st.sidebar.progress(min(1.0, max(0.0, progress)))
        
        if st.sidebar.button("Cancel Timer"):
            st.session_state['pomodoro_active'] = False
            st.session_state['pomodoro_start_time'] = None
            st.experimental_rerun()

    # Get user input
    user_input = st.chat_input("Ask me anything about your studies...")

    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Process user message and generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Check if user is interacting with flashcards
                    flashcard_response = handle_flashcard_interaction(user_input)
                    
                    if flashcard_response:
                        response = flashcard_response
                    else:
                        # Check if we're in the middle of a quiz
                        quiz_response = handle_quiz_answer(user_input)
                        
                        if quiz_response:
                            response = quiz_response
                        else:
                            # Check if we're in the middle of a flow
                            flow_response = (
                                handle_flashcards_flow(user_input) or 
                                handle_study_plan_flow(user_input) or 
                                handle_pomodoro_flow(user_input) or 
                                handle_quiz_flow(user_input) or 
                                handle_summarize_flow(user_input)
                            )
                            
                            if flow_response:
                                response = flow_response
                            else:
                                # Process as a new message
                                response = process_user_message(user_input)
                    
                    st.markdown(response)
                except Exception as e:
                    error_msg = f"I'm sorry, I encountered an error while processing your request. Please try again."
                    if st.session_state['debug_mode']:
                        error_msg += f"\n\nError details: {str(e)}"
                    st.markdown(error_msg)
                    response = error_msg
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()