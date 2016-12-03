from flask_wtf import Form
from wtforms import TextField, PasswordField, IntegerField
from wtforms.validators import DataRequired, EqualTo, Length

# Set your classes here.

class SearchForm(Form):
    search_term = TextField('Search', validators=[DataRequired(), Length(min=3, max=50)])

class RegistrationForm(Form):
    name = TextField(
        'Username', validators=[DataRequired(), Length(min=6, max=25)]
    )

class LoginForm(Form):
    name = TextField('Username', validators=[DataRequired()])

class FavoriteForm(Form):
    rank = IntegerField('rank', validators=[DataRequired()])
