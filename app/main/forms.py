from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
import sqlalchemy as sa
from app import db
from app.models import User
from flask_ckeditor import CKEditorField

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=180)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(User.username == username.data))
            if user is not None:
                raise ValidationError('Please use a different username.')
            

class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=100)])
    post = CKEditorField('Description', validators=[DataRequired()])
    image_url = StringField('Image URL (optional)')
    image_file = FileField('Upload Image (optional)', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Submit')

class CommentForm(FlaskForm):
    comment = TextAreaField('Add a comment', validators=[DataRequired(), Length(min=1, max=70)])
    submit = SubmitField('Submit')

class EditPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=100)])
    post = CKEditorField('Description', validators=[DataRequired()], render_kw={'rows': 10})
    image_url = StringField('Image URL (optional)')
    image_file = FileField('Upload Image (optional)', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Save Changes')

class SearchForm(FlaskForm):
    searched = StringField('Searched', validators=[DataRequired()])
    submit = SubmitField('Submit')