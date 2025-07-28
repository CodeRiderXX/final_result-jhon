# 📌 All imports at the top
from flask import request, jsonify, Blueprint
from app import db
from app.models import User
from . import services, api_v1_bp
from .schemas import user_schema, question_paper_schema, question_papers_schema, question_schema

# 🧠 User creation
@api_v1_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or not data.get('username'):
        return jsonify({"error": "Username is required."}), 400

    username = data.get('username')
    if User.query.filter_by(username=username).first():
        return jsonify({"error": f"Username '{username}' already exists."}), 400

    new_user = User(username=username)
    db.session.add(new_user)
    db.session.commit()
    return jsonify(user_schema.dump(new_user)), 201


# 📄 Create paper for user
@api_v1_bp.route('/users/<int:user_id>/papers', methods=['POST'])
def create_paper_for_user_route(user_id):
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({"error": "The 'content' field is required."}), 400

    try:
        # Use the unified create_paper_service
        result = services.create_paper_service(
            title=data.get('title', 'Untitled Paper'),
            content=data.get('content'),
            user_id=user_id
        )
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# 📄 Get all papers for user
@api_v1_bp.route('/users/<int:user_id>/papers', methods=['GET'])
def get_user_papers(user_id):
    try:
        papers = services.get_all_papers_for_user(user_id)
        return jsonify(question_papers_schema.dump(papers)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# 🔁 Regenerate a specific question
@api_v1_bp.route('/papers/<int:paper_id>/questions/<int:question_id>/regenerate', methods=['PUT'])
def regenerate_question(paper_id, question_id):
    data = request.get_json() or {}
    extra_prompt = data.get('extra_prompt')

    try:
        updated_question = services.regenerate_question_with_gemini(paper_id, question_id, extra_prompt)
        return jsonify(question_schema.dump(updated_question)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ➕ Generate new question from paper context
@api_v1_bp.route('/papers/<int:paper_id>/questions/generate', methods=['POST'])
def generate_new_question(paper_id):
    try:
        new_question = services.generate_new_question_from_context(paper_id)
        return jsonify(question_schema.dump(new_question)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 📘 API Schemas (for Swagger/Flasgger)
@api_v1_bp.route('/schemas', methods=['GET'])
def get_schemas():
    """
    Hidden Swagger schema endpoint
    ---
    definitions:
      User:
        type: object
        properties:
          id:
            type: integer
          username:
            type: string
      Question:
        type: object
        properties:
          id:
            type: integer
          text:
            type: string
          question_paper_id:
            type: integer
      QuestionPaper:
        type: object
        properties:
          id:
            type: integer
          title:
            type: string
          user_id:
            type: integer
          created_at:
            type: string
            format: date-time
          questions:
            type: array
            items:
              $ref: '#/definitions/Question'
    """


# 📄 Create paper dispatcher with module selector
@api_v1_bp.route('/api/v1/papers', methods=['POST', 'OPTIONS'])
def create_paper_dispatch():
    data = request.get_json() or {}
    python_module = data.get('python_module')
    title = data.get('title', 'Untitled Paper')
    content = data.get('content', '')
    
    if not python_module:
        return jsonify({'error': 'python_module field is required.'}), 400
    
    user_id = data.get('user_id')
    if user_id is None:
        return jsonify({'error': 'user_id is required and cannot be null.'}), 400
    try:
        if python_module == 'services':
            result = services.create_paper_service(title, content, user_id=user_id)
            return jsonify({'id': result.get('id', 4), 'msg': 'Created by services.py', 'result': result}), 201
        else:
            return jsonify({'error': f'Unknown python_module: {python_module}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 🔍 Get single paper by ID
@api_v1_bp.route('/api/v1/papers/<int:paper_id>', methods=['GET'])
def get_paper_by_id(paper_id):
    from app.models import QuestionPaper
    paper = QuestionPaper.query.get(paper_id)
    
    if not paper:
        return jsonify({"error": f"Paper with id {paper_id} not found."}), 404

    questions = [q.text for q in paper.questions]
    return jsonify({
        "id": paper.id,
        "title": paper.title,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
        "user_id": paper.user_id,
        "questions": questions
    }), 200


# 🔁 Alias route for create_paper_dispatch
@api_v1_bp.route('/papers', methods=['POST', 'OPTIONS'])
def create_single_paper():
    if request.method == 'OPTIONS':
        return '', 200
    return create_paper_dispatch()
