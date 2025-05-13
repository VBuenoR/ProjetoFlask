from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'segredo-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

 # MODELS
class User(db.Model, UserMixin):
   id = db.Column(db.Integer, primary_key=True)
   username = db.Column(db.String(150), unique=True, nullable=False)
   email = db.Column(db.String(150), unique=True, nullable=False)
   password = db.Column(db.String(150), nullable=False)
   contacts = db.relationship('Contact', backref='owner', lazy=True)
   messages = db.relationship('Message', backref='sender', lazy=True)
class Contact(db.Model):
   id = db.Column(db.Integer, primary_key=True)
   name = db.Column(db.String(100), nullable=False)
   email = db.Column(db.String(150), nullable=False)
   phone = db.Column(db.String(20), nullable=False)
   user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
   messages = db.relationship('Message', backref='contact', lazy=True)
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    sent_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
 # FORMS
class RegisterForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirme a senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Cadastrar')
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Nome de usuário já existe.')
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email já cadastrado.')
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')
class ContactForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Celular', validators=[DataRequired(), Length(min=8, max=20)])
    submit = SubmitField('Salvar')
class MessageForm(FlaskForm):
    contact = SelectField('Contato', coerce=int, validators=[DataRequired()])
    title = StringField('Título', validators=[DataRequired(), Length(max=100)])
    text = TextAreaField('Mensagem', validators=[DataRequired()])
    submit = SubmitField('Enviar')
# ROTAS
@app.route('/contacts/delete/<int:contact_id>', methods=['POST'])
@login_required
def delete_contact(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
    if contact:
        db.session.delete(contact)
        db.session.commit()
        flash('Contato excluído!', 'success')
    else:
        flash('Contato não encontrado.', 'danger')
    return redirect(url_for('contacts'))

@app.route('/chat/<int:contact_id>')
@login_required
def chat(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
    if not contact:
        flash('Contato não encontrado.', 'danger')
        return redirect(url_for('contacts'))
    # Busque as mensagens trocadas com esse contato
    messages = Message.query.filter_by(user_id=current_user.id, contact_id=contact_id).order_by(Message.sent_date).all()
    return render_template('chat.html', contact=contact, messages=messages)

@app.route('/chat/<int:contact_id>', methods=['POST'])
@login_required
def send_message(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
    if not contact:
        flash('Contato não encontrado.', 'danger')
        return redirect(url_for('contacts'))
    text = request.form.get('text')
    if text:
        msg = Message(
            title="Chat",
            text=text,
            user_id=current_user.id,
            contact_id=contact_id,
            sender=current_user  # ajuste conforme seu modelo
        )
        db.session.add(msg)
        db.session.commit()
    return redirect(url_for('chat', contact_id=contact_id))

from flask import render_template, redirect, url_for, flash, request

@app.route('/contacts/edit/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
    if not contact:
        flash('Contato não encontrado.', 'danger')
        return redirect(url_for('contacts'))
    form = ContactForm(obj=contact)
    if form.validate_on_submit():
        contact.name = form.name.data
        contact.email = form.email.data
        contact.phone = form.phone.data
        db.session.commit()
        flash('Contato atualizado com sucesso!', 'success')
        return redirect(url_for('contacts'))
    return render_template('edit_contact.html', form=form, contact=contact)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login inválido. Verifique email e senha.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu com sucesso.', 'info')
    return redirect(url_for('login'))
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
@app.route('/contacts', methods=['GET', 'POST'])
@login_required
def contacts():
    form = ContactForm()
    if form.validate_on_submit():
        contact = Contact(name=form.name.data, email=form.email.data, phone=form.phone.data, user_id=current_user.id)
        db.session.add(contact)
        db.session.commit()
        flash('Contato cadastrado!', 'success')
        return redirect(url_for('contacts'))
    contacts = Contact.query.filter_by(user_id=current_user.id).all()
    return render_template('contacts.html', form=form, contacts=contacts)
@app.route('/messages', methods=['GET'])
@login_required
def messages():
    form = MessageForm()
    form.contact.choices = [(c.id, c.name) for c in Contact.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        msg = Message(
            title=form.title.data,
            text=form.text.data,
            sender=current_user,
            contact_id=form.contact.data
        )
        db.session.add(msg)
        db.session.commit()
        flash('Mensagem enviada!', 'success')
        return redirect(url_for('messages'))
    messages = Message.query.filter_by(user_id=current_user.id).order_by(Message.sent_date.desc()).all()
    return render_template('messages.html', form=form, messages=messages)
 # TEMPLATES (em arquivos separados na pasta templates)
 # Veja exemplos abaixo
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)