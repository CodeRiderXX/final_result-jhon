from app import db
import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    papers = db.relationship('QuestionPaper', backref='owner', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"

class QuestionPaper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False, default="Untitled Paper")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    questions = db.relationship('Question', backref='paper', cascade="all, delete-orphan", lazy=True)

    def __repr__(self):
        return f"<QuestionPaper {self.title}>"

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    question_paper_id = db.Column(db.Integer, db.ForeignKey('question_paper.id'), nullable=False)

    def __repr__(self):
        return f"<Question {self.id}>"