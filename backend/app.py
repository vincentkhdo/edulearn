import os
import openai
import logging
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import Session
import random

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student_progress.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

# Set the OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

logging.basicConfig(level=logging.INFO)

class StudentProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)
    user_answer = db.Column(db.String(100), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    questions = db.Column(db.JSON, nullable=False)
    responses = db.Column(db.JSON, nullable=True)
    score = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Not Started')
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)

class StudentProgress(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)
    user_answer = db.Column(db.String(100), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)

async def generate_questions_async(subject, grade_level, num_questions):
    client = openai.AsyncOpenAI(api_key=openai.api_key)

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Generate {num_questions} multiple-choice questions for {subject} for grade level {grade_level} based on the California curriculum. Each question should have exactly 4 options, each option enclosed in double quotation marks. The correct answer should be indicated clearly at the end of each question. The format should be:\nQuestion: <question text>\nOptions: \"<option1>\", \"<option2>\", \"<option3>\", \"<option4>\"\nCorrect answer: \"<correct_option>\"\nEnsure the options are listed without any prefixes like A), B), etc."}
        ]
    )

    logging.info(f"OpenAI response: {response}")

    questions_text = response.choices[0].message.content.strip()
    questions = []
    current_question = None

    for line in questions_text.split('\n'):
        line = line.strip()
        if line.startswith("Correct answer:"):
            if current_question:
                current_question['correct_answer'] = line.replace("Correct answer:", "").strip().strip('"')
                questions.append(current_question)
            current_question = None
        elif line.startswith("Options:"):
            if current_question:
                options = line.replace("Options:", "").split('", "')
                current_question['options'] = [opt.strip().strip('"') for opt in options]
                random.shuffle(current_question['options'])
        elif line and not line.startswith("Options:") and not line.startswith("Correct answer:"):
            if current_question is None:
                current_question = {'question': line.replace("Question: ", ""), 'options': [], 'correct_answer': None}
            else:
                questions.append(current_question)
                current_question = {'question': line.replace("Question: ", ""), 'options': [], 'correct_answer': None}

    return questions

@app.route('/api/generate_questions', methods=['POST'])
def generate_questions():
    try:
        data = request.get_json()
        subject = data['subject']
        grade_level = data['grade_level']
        num_questions = data['num_questions']

        logging.info(f"Received request: {data}")

        questions = asyncio.run(generate_questions_async(subject, grade_level, num_questions))
        
        logging.info(f"Generated questions: {questions}")

        return jsonify({"questions": questions})

    except Exception as e:
        logging.error(f"Error in /api/generate_questions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/save_response', methods=['POST'])
def save_response():
    try:
        data = request.get_json()
        subject = data['subject']
        grade_level = data['grade_level']
        responses = data['responses']

        for response in responses:
            question = response['question']
            correct_answer = response['correct_answer']
            user_answer = response['userAnswer']
            is_correct = response['isCorrect']

            new_response = StudentProgress(
                subject=subject,
                grade_level=grade_level,
                question=question,
                correct_answer=correct_answer,
                user_answer=user_answer,
                is_correct=is_correct
            )
            db.session.add(new_response)
        db.session.commit()

        return jsonify({"message": "Responses saved successfully"})

    except Exception as e:
        logging.error(f"Error in /api/save_response: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear_data', methods=['POST'])
def clear_data():
    try:
        db.session.query(StudentProgress).delete()
        db.session.commit()
        return jsonify({"message": "Student data cleared successfully"})
    except Exception as e:
        logging.error(f"Error in /api/clear_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/save_assignment', methods=['POST'])
def save_assignment():
    try:
        data = request.get_json()
        subject = data['subject']
        grade_level = data['grade_level']
        questions = data['questions']

        new_assignment = Assignment(
            subject=subject,
            grade_level=grade_level,
            questions=questions
        )
        db.session.add(new_assignment)
        db.session.commit()

        return jsonify({"message": "Assignment saved successfully"})

    except Exception as e:
        logging.error(f"Error in /api/save_assignment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_assignments', methods=['GET'])
def get_assignments():
    try:
        assignments = Assignment.query.all()
        return jsonify([{
            'id': assignment.id,
            'subject': assignment.subject,
            'grade_level': assignment.grade_level,
            'questions': assignment.questions
        } for assignment in assignments])

    except Exception as e:
        logging.error(f"Error in /api/get_assignments: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_assignment/<int:assignment_id>', methods=['GET'])
def get_assignment(assignment_id):
    try:
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return jsonify({"error": "Assignment not found"}), 404

        return jsonify({
            'id': assignment.id,
            'title': assignment.title,
            'subject': assignment.subject,
            'grade_level': assignment.grade_level,
            'questions': assignment.questions,
            'responses': assignment.responses,
            'status': assignment.status,
            'student_id': assignment.student_id
        })
    except Exception as e:
        logging.error(f"Error in /api/get_assignment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/progress_report', methods=['GET'])
def progress_report():
    try:
        summary = asyncio.run(generate_summary_analysis())
        return jsonify(summary)
    except Exception as e:
        logging.error(f"Error in /api/progress_report: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete_assignment', methods=['POST'])
def delete_assignment():
    try:
        data = request.get_json()
        assignment_id = data['id']
        
        with db.session() as session:
            assignment = session.get(Assignment, assignment_id)
            if assignment:
                session.delete(assignment)
                session.commit()
                return jsonify({"message": "Assignment deleted successfully"})
            else:
                return jsonify({"error": "Assignment not found"}), 404
    except Exception as e:
        logging.error(f"Error in /api/delete_assignment: {str(e)}")
        return jsonify({"error": str(e)}), 500


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    assignments = db.relationship('StudentAssignment', backref='student', lazy=True)

class StudentAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Not Started')

@app.route('/api/add_student', methods=['POST'])
def add_student():
    try:
        data = request.get_json()
        new_student = Student(name=data['name'])
        db.session.add(new_student)
        db.session.commit()
        return jsonify({"message": "Student added successfully"})
    except Exception as e:
        logging.error(f"Error in /api/add_student: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_students', methods=['GET'])
def get_students():
    try:
        students = Student.query.all()
        return jsonify([{
            'id': student.id,
            'name': student.name
        } for student in students])
    except Exception as e:
        logging.error(f"Error in /api/get_students: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/assign_to_student', methods=['POST'])
def assign_to_student():
    try:
        data = request.get_json()
        assignment_id = data.get('assignment_id')
        student_ids = data.get('student_ids')

        if not assignment_id or not student_ids:
            return jsonify({"error": "Assignment ID and student IDs are required"}), 400

        with db.session() as session:
            assignment = session.get(Assignment, assignment_id)
            if not assignment:
                return jsonify({"error": "Assignment not found"}), 404

            for student_id in student_ids:
                student = session.get(Student, student_id)
                if not student:
                    logging.error(f"Student with ID {student_id} not found")
                    continue

                existing_assignment = session.query(StudentAssignment).filter_by(student_id=student_id, assignment_id=assignment_id).first()
                if existing_assignment:
                    logging.info(f"Assignment {assignment_id} already assigned to student {student_id}")
                    continue

                new_student_assignment = StudentAssignment(
                    student_id=student_id,
                    assignment_id=assignment_id,
                    status='Not Started'
                )
                session.add(new_student_assignment)

            session.commit()
        return jsonify({"message": "Assignment assigned to students successfully"})
    except Exception as e:
        logging.error(f"Error in /api/assign_to_student: {str(e)}")
        return jsonify({"error": str(e)}), 500




@app.route('/api/get_student_assignments/<int:student_id>', methods=['GET'])
def get_student_assignments(student_id):
    try:
        student_assignments = Assignment.query.filter_by(student_id=student_id).all()
        assignments = []
        for assignment in student_assignments:
            assignments.append({
                'id': assignment.id,
                'title': assignment.title,
                'subject': assignment.subject,
                'grade_level': assignment.grade_level,
                'questions': assignment.questions,
                'status': assignment.status
            })
        
        # Log the retrieved assignments
        logging.info(f"Retrieved assignments for student {student_id}: {assignments}")
        
        return jsonify(assignments)
    except Exception as e:
        logging.error(f"Error in /api/get_student_assignments: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/submit_assignment', methods=['POST'])
def submit_assignment():
    try:
        data = request.get_json()
        assignment_id = data['assignment_id']
        student_id = data['student_id']
        responses = data['responses']

        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return jsonify({"error": "Assignment not found"}), 404

        logging.info(f"Assignment ID: {assignment_id}, Student ID: {student_id}, Responses: {responses}")

        correct_answers = 0
        total_questions = len(responses)

        for response in responses:
            question = response['question']
            correct_answer = response['correct_answer']
            user_answer = response['user_answer']
            is_correct = user_answer == correct_answer
            if is_correct:
                correct_answers += 1

        score = (correct_answers / total_questions) * 100
        assignment.responses = responses
        assignment.score = score
        assignment.status = 'Completed'
        
        # Log before commit
        logging.info(f"Before commit - Assignment status: {assignment.status}")

        db.session.commit()
        
        # Log after commit
        logging.info(f"After commit - Assignment status: {assignment.status}")
        logging.info(f"Updated assignment: {assignment}")

        return jsonify({"message": "Assignment submitted successfully", "score": score})
    except Exception as e:
        logging.error(f"Error in /api/submit_assignment: {str(e)}")
        return jsonify({"error": str(e)}), 500





@app.route('/api/get_student_progress/<int:student_id>', methods=['GET'])
def get_student_progress(student_id):
    try:
        summary = asyncio.run(generate_summary_analysis(student_id))
        return jsonify(summary)
    except Exception as e:
        logging.error(f"Error in /api/get_student_progress: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear_all_assignments', methods=['POST'])
def clear_all_assignments():
    try:
        db.session.query(StudentAssignment).delete()
        db.session.query(Assignment).delete()
        db.session.commit()
        return jsonify({"message": "All assignments cleared successfully"})
    except Exception as e:
        logging.error(f"Error in /api/clear_all_assignments: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/create_assignment', methods=['POST'])
def create_assignment():
    try:
        data = request.get_json()
        title = data['title']
        subject = data['subject']
        grade_level = data['grade_level']
        questions = data['questions']
        student_ids = data['student_ids']  # List of student IDs to assign the assignment

        assignments = []
        for student_id in student_ids:
            new_assignment = Assignment(
                title=title,
                subject=subject,
                grade_level=grade_level,
                questions=questions,
                student_id=student_id,
                status='Not Started'
            )
            db.session.add(new_assignment)
            assignments.append(new_assignment)
        
        db.session.commit()

        return jsonify({"message": "Assignments created and assigned to students successfully", "assignments": [a.id for a in assignments]})
    except Exception as e:
        logging.error(f"Error in /api/create_assignment: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/get_student_scores/<int:student_id>', methods=['GET'])
def get_student_scores(student_id):
    try:
        with db.session() as session:
            student = session.get(Student, student_id)
            if not student:
                return jsonify({"error": "Student not found"}), 404

            student_assignments = session.query(Assignment).filter_by(student_id=student.id).all()
            assignments = []
            for assignment in student_assignments:
                assignments.append({
                    'assignment_id': assignment.id,
                    'title': assignment.title,
                    'subject': assignment.subject,
                    'grade_level': assignment.grade_level,
                    'status': assignment.status,
                    'score': assignment.score,
                    'responses': assignment.responses
                })

        return jsonify({
            'id': student.id,
            'name': student.name,
            'assignments': assignments
        })
    except Exception as e:
        logging.error(f"Error in /api/get_student_scores: {str(e)}")
        return jsonify({"error": str(e)}), 500

async def generate_summary_analysis(student_id):
    assignments = Assignment.query.filter_by(student_id=student_id).all()
    logging.info(f"Fetched {len(assignments)} assignments for student ID {student_id}")

    if not assignments:
        return {"summary": "No assignments found."}

    subject_responses = {}

    for assignment in assignments:
        for response in assignment.responses:
            subject = assignment.subject
            if subject not in subject_responses:
                subject_responses[subject] = {
                    "correct_answers": 0,
                    "incorrect_answers": 0,
                    "responses": []
                }

            subject_responses[subject]["responses"].append({
                "question": response["question"],
                "correct_answer": response["correct_answer"],
                "user_answer": response["user_answer"],
                "is_correct": response["is_correct"]
            })

            if response["is_correct"]:
                subject_responses[subject]["correct_answers"] += 1
            else:
                subject_responses[subject]["incorrect_answers"] += 1

    summary_input = "Summarize the following student responses and provide areas of improvement based on the incorrect answers. Only include suggestions for improvement.\n"

    for subject, data in subject_responses.items():
        summary_input += f"Subject: {subject}\n"
        for resp in data["responses"]:
            summary_input += f"Question: {resp['question']}, Correct Answer: {resp['correct_answer']}, User Answer: {resp['user_answer']}, Correct: {resp['is_correct']}\n"

    logging.info(f"Generated summary input for OpenAI:\n{summary_input}")

    client = openai.AsyncOpenAI(api_key=openai.api_key)

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": summary_input + "\nFor each subject, provide bullet points of strengths and areas of improvement in the following format:\n\nStrengths:\n[Strength #1]\n[Strength #2]\n[etc.]\n\nAreas of Improvement:\n[Area of Improvement #1]\n[Area of Improvement #2]\n[etc.]\n"}
        ]
    )

    response_message = response.choices[0].message.content
    logging.info(f"OpenAI response: {response_message}")

    return {"summary": response_message}

@app.route('/api/get_student_progress_report/<int:student_id>', methods=['GET'])
def get_student_progress_report(student_id):
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404

        summary = asyncio.run(generate_summary_analysis(student_id))
        return jsonify({
            'id': student.id,
            'name': student.name,
            'progress_report': summary['summary']
        })
    except Exception as e:
        logging.error(f"Error in /api/get_student_progress_report: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Ensure to create the tables in the database
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5001)
