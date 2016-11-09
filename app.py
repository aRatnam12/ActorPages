#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request
# from flask.ext.sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os
import MySQLdb
import urllib

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.config.from_object('config')

Session = scoped_session( sessionmaker() )
engine = create_engine('mysql+mysqldb://root:cs411fa2016@localhost/actor_pages')

app.config['SQLALCHEMY_POOL_SIZE'] = 100
app.config['SQLALCHEMY_POOL_RECYCLE'] = 280

#db = SQLAlchemy(app)
db = MySQLdb.connect(host='localhost', user='root', passwd='cs411fa2016', db='actor_pages')
# Automatically tear down SQLAlchemy.

'''
@app.teardown_request
def shutdown_session(exception=None):
    db.close() 
'''

# Login required decorator.
'''
def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return test(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap
'''
#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def home():
    cur = db.cursor()
    cur.execute('SELECT Actor.name,Actor.actorID FROM Actor, Favorites WHERE Favorites.userID = 1 AND Actor.actorID = Favorites.actorID ORDER BY Favorites.rank;')
    results = [ (name,urllib.quote(str(actor_id))) for (name,actor_id) in cur.fetchall() ]
    return render_template('pages/home.html', res=results)

@app.route('/actors', methods=['GET', 'POST'])
def actors():
    form = SearchForm()
    if form.validate_on_submit():
        # Split name at commas and spaces
        comma_split = form.search_term.data.split(',')
        search_terms = []
        for term in comma_split:
		search_terms = search_terms + [x.strip() for x in term.split(' ')]
 
        # Build query from each part of name
        query = 'SELECT actorID, name FROM Actor WHERE name LIKE \'%' + search_terms[0] + '%\''
        for i in range(1,len(search_terms)):
            query += 'AND name LIKE \'%' + search_terms[i] + '%\''
        query += ';'

        cur = db.cursor()
        cur.execute(query)
        actor_list = [ (urllib.quote(str(actor_id)), name) for (actor_id, name) in cur.fetchall()[0:20] ]

        return render_template('pages/actors.html', form=form, actor_list=actor_list)
    return render_template('pages/actors.html', form=form, actor_list=[])

@app.route('/actor/<actor_id>', methods=['GET', 'POST'])
def actor(actor_id):
    form = FavoriteForm()
    query = 'SELECT name FROM Actor WHERE actorID=' + actor_id + ';'
    cur = db.cursor()
    cur.execute(query)
    actor_name = cur.fetchone()
    movie_query = 'SELECT m.MovieID, m.title, m.rating, m.year FROM Movies m, ActsIn a WHERE m.MovieID=a.MovieID AND a.ActorID=' + actor_id + ';'
    cur = db.cursor()
    cur.execute(movie_query)
    movies = [ (movieID, urllib.quote(str(title)), urllib.quote(str(rating)), urllib.quote(str(year))) for (movieID, title, rating, year) in cur.fetchall() ]
    movie_genres = {}
    for movieID,title,rating,year in movies:
        genre_query = 'SELECT g.genreName FROM Genre g, HasGenre hg WHERE g.genreID=hg.genreID AND hg.MovieID=' + str(movieID) +';'
        cur = db.cursor()
        cur.execute(genre_query)
        movie_genres[(title,rating,year)] = [urllib.quote(str(genre)) for genre in cur.fetchall()]
    if form.validate_on_submit():
        user_id=1
        favorite_query = 'DELETE FROM Favorites WHERE userID=' + str(user_id) + ' AND (rank=10 OR actorID=' + str(actor_id) + ');'
        cur = db.cursor()
        cur.execute(favorite_query)
        update_query = 'UPDATE Favorites SET rank=rank+1 WHERE 1;'
        cur = db.cursor()
        cur.execute(update_query)
        add_favorite_query = 'INSERT INTO Favorites VALUES(' + str(user_id) + ',' + actor_id + ',1);'
        cur = db.cursor()
        cur.execute(add_favorite_query) 
        return render_template('pages/actor.html', add_favorite_form=form, actor_id=actor_id, actor_name=actor_name, movies=movie_genres)
    return render_template('pages/actor.html', add_favorite_form=form, actor_id=actor_id, actor_name=actor_name, movies=movie_genres)

@app.route('/about')
def about():
    return render_template('pages/about.html')


@app.route('/login')
def login():
    form = LoginForm(request.form)
    return render_template('forms/login.html', form=form)


@app.route('/register')
def register():
    form = RegisterForm(request.form)
    return render_template('forms/register.html', form=form)


@app.route('/forgot')
def forgot():
    form = ForgotForm(request.form)
    return render_template('forms/forgot.html', form=form)

# Error handlers.


@app.errorhandler(500)
def internal_error(error):
    #db_session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
'''
if __name__ == '__main__':
    app.run()
'''
# Or specify port manually:

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

