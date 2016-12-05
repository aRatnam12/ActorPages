#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, redirect, url_for, flash
# from flask.ext.sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os
import MySQLdb
import urllib
import urllib2
import json
from collections import OrderedDict

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

tmdb_api_key = "1eaa83e12e6aba3348d97b7f51753059"

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

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_name = form.name.data
        cur = db.cursor()
        cur.execute('SELECT userID,name FROM User WHERE name LIKE \'' + str(user_name) + '\';')
	user_id,u_name = cur.fetchone()
        if user_id:
            return redirect('/home/' + str(user_id))
        else:
            flash('No user exists with that name.')
    return render_template('pages/login.html', form=form)

@app.route('/register', methods=('GET', 'POST'))
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user_name = form.name.data
        cur = db.cursor()
        cur.execute('SELECT userID,name FROM User WHERE name LIKE \'' + str(user_name) + '\';')
        if cur.fetchone():
            flash('User with that name already exists.')
        else:
            cur = db.cursor()
            cur.execute('INSERT INTO User(name) VALUES (\'' + str(user_name) + '\');')
            db.commit()
            cur = db.cursor()
            cur.execute('SELECT userID,name FROM User WHERE name LIKE \'' + str(user_name) + '\';')
            user_id,u_name = cur.fetchone()
            return redirect('/home/' + str(user_id))
    return render_template('pages/registration.html', form=form)

@app.route('/logout')
def logout():
    return redirect('pages/login')

@app.route('/home/<user_id>', methods=['GET', 'POST'])
def home(user_id):
    cur = db.cursor()
    cur.execute('SELECT Actor.name,Actor.actorID FROM Actor, Favorites WHERE Favorites.userID = ' + user_id + ' AND Actor.actorID = Favorites.actorID AND Favorites.rank < 11 ORDER BY Favorites.rank;')
    favorites = [ (name,urllib.quote(str(actor_id))) for (name,actor_id) in cur.fetchall() ]
    i = 0
    recommended = []
    while i<4 and i<len(favorites):
        fav = favorites[i][1]
        if fav:
            amount = 11
            query = 'SELECT A2.name, A2.actorID FROM Actor A2, ActsIn AI2, Movies M2 WHERE AI2.movieID = M2.MovieId AND AI2.actorID = A2.actorID AND A2.actorID NOT IN (SELECT Favorites.actorID FROM Favorites WHERE 1) and M2.MovieId IN (SELECT AI1.movieId from ActsIn AI1 where AI1.actorID=' + str(fav) + ') GROUP BY A2.actorID ORDER BY count(*) DESC LIMIT ' + str(amount) + ';' 
            #query = 'SELECT A3.name, A3.actorID FROM Actor A3 WHERE A3.actorID IN (SELECT A2.actorID FROM Actor A2, ActsIn AI2, Movies M2 WHERE AI2.movieID = M2.MovieId AND AI2.actorID = A2.actorID AND A2.actorID NOT IN (SELECT Favorites.actorID FROM Favorites WHERE 1) and M2.MovieId IN (SELECT AI1.movieId from ActsIn AI1 where AI1.actorID=' + str(fav) + ') GROUP BY A2.actorID) GROUP BY A3.actorID, A3.name ORDER BY count(*) DESC LIMIT ' + str(amount) + ';'
            cur = db.cursor()
            cur.execute(query)
            
            new_recs = [ (name,urllib.quote(str(actor_id))) for (name,actor_id) in cur.fetchall() ]
            count = 4 - i
            while count > 0:
                if new_recs[0] not in recommended:
                    recommended.append(new_recs[0])
                    count -= 1
                new_recs = new_recs[1:]
        i += 1
    return render_template('pages/home.html', res=favorites, rec=recommended, userid=user_id)

'''
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
    movies = [ (movieID, unicode(str(title), 'latin-1'), urllib.quote(str(rating)), urllib.quote(str(year))) for (movieID, title, rating, year) in cur.fetchall() ]
    movie_genres = {}

    for movieID,title,rating,year in movies:
        i = 0
        recommended = []
        while i<3 and i<len(favorites):
            fav = favorites[i][1]
            if fav:
                query = 'SELECT A3.name, A3.actorID FROM Actor A3 WHERE A3.actorID IN (SELECT A2.actorID FROM Actor A2, ActsIn AI2, Movies M2 WHERE AI2.movieID = M2.MovieId AND AI2.actorID = A2.actorID AND A2.actorID NOT IN (SELECT Favorites.actorID FROM Favorites WHERE 1) and M2.MovieId IN (SELECT AI1.movieId from ActsIn AI1 where AI1.actorID=' + str(fav) + ') GROUP BY A2.actorID)  GROUP BY A3.name ORDER BY count(*) DESC LIMIT 3;'
                cur = db.cursor()
                cur.execute(query)
                recommended = recommended + [ (name,urllib.quote(str(actor_id))) for (name,actor_id) in cur.fetchall() ]
            i += 1
    return render_template('pages/home.html', res=favorites, rec=recommended, userid=user_id)
'''

@app.route('/actors/<user_id>', methods=['GET', 'POST'])
def actors(user_id):
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

        return render_template('pages/actors.html', form=form, actor_list=actor_list, userid=user_id)
    return render_template('pages/actors.html', form=form, actor_list=[], userid=user_id)

@app.route('/actor/<user_id>/<actor_id>', methods=['GET', 'POST'])
def actor(user_id, actor_id):
    form = FavoriteForm()
    query = 'SELECT name,score,picture FROM Actor WHERE actorID=' + str(actor_id) + ';'
    cur = db.cursor()
    cur.execute(query)
    actor_name,actor_score,actor_picture = cur.fetchone()
    if not actor_score:
        score_query = 'UPDATE Actor set score=(SELECT avg(rating) FROM Movies, ActsIn WHERE Movies.MovieID=ActsIn.MovieID AND ActsIn.ActorID=' + str(actor_id) + ') WHERE actorID=' + str(actor_id) + ';'
        cur = db.cursor()
        cur.execute(score_query)
        db.commit()
        get_score_query = 'SELECT score FROM Actor WHERE actorID=' + str(actor_id) + ';'
        cur = db.cursor()
        cur.execute(get_score_query)
        actor_score = cur.fetchone()
        if actor_score[0]:
            actor_score = "%.2f" % float(actor_score[0])
        else:
            actor_score = '0.0'
    else:
	actor_score = "%.2f" % float(actor_score)

    if not actor_picture:
        img_url = ""
        config_request = "https://api.themoviedb.org/3/configuration?api_key=" + tmdb_api_key
        req = urllib2.urlopen(config_request)
        if req.getcode() == 200:
            data = json.loads(req.read())
            img_url += data['images']['base_url'] + data['images']['profile_sizes'][1]

            find_request = "https://api.themoviedb.org/3/search/person?api_key=" + tmdb_api_key + "&language=en-US&query=" + urllib.quote(actor_name) + "&page=1&include_adult=false"
            req = urllib2.urlopen(find_request)
            if req.getcode() == 200:
                data = json.loads(req.read())
                img_url += data['results'][0]['profile_path']

                picture_query = "UPDATE Actor SET picture='" + img_url + "' WHERE actorID=" + actor_id
                cur = db.cursor()
                cur.execute(picture_query)
                actor_picture = img_url

    movie_query = 'SELECT m.MovieID, m.title, m.rating, m.year FROM Movies m, ActsIn a WHERE m.MovieID=a.MovieID AND a.ActorID=' + str(actor_id) + ';'
    cur = db.cursor()
    cur.execute(movie_query)
    movies = [ (movieID, unicode(str(title), 'latin-1'), urllib.quote(str(rating)), urllib.quote(str(year))) for (movieID, title, rating, year) in cur.fetchall() ]
    movie_genres = {}
    genre_scores = {}
    for movieID,title,rating,year in movies:
        genre_query = 'SELECT g.genreName FROM Genre g, HasGenre hg WHERE g.genreID=hg.genreID AND hg.MovieID=' + str(movieID) +';'
        cur = db.cursor()
        cur.execute(genre_query)
        genres = [str(genre).strip('(').strip('),').strip('\'') for genre in cur.fetchall()]
        movie_genres[(title,rating,year)] = genres
        for genre in genres:
            if genre in genre_scores:
                cumulative,num = genre_scores[genre]
                genre_scores[genre] = (cumulative + float(rating), num+1)
            else:
                genre_scores[genre] = (float(rating), 1)
    for key,(val1,val2) in genre_scores.iteritems():
        rounded_score = float("%.2f" % (val1/val2))
        genre_scores[key] = (rounded_score, val2)
    genre_scores = OrderedDict(sorted(genre_scores.items(), key=lambda kv: kv[1][0], reverse=True))
    movie_genres = OrderedDict(sorted(movie_genres.items(), key=lambda kv: kv[0][2], reverse=True))
    if form.validate_on_submit():
        rank = form.rank.data
        if rank < 1:
            rank = 1
        if rank > 10 or not rank:
            rank = 10
        favorite_query = 'DELETE FROM Favorites WHERE userID=' + str(user_id) + ' AND (rank=10 OR actorID=' + str(actor_id) + ');'
        cur = db.cursor()
        cur.execute(favorite_query)
        update_query = 'UPDATE Favorites SET rank=rank+1 WHERE userID=' + str(user_id) + ' AND rank>=' + str(rank) + ';'
        cur = db.cursor()
        cur.execute(update_query)
        add_favorite_query = 'INSERT INTO Favorites VALUES(' + str(user_id) + ',' + actor_id + ',' + str(rank) + ');'
        cur = db.cursor()
        cur.execute(add_favorite_query)
        db.commit()
        return redirect(url_for('actor',user_id=user_id,actor_id=actor_id))
    return render_template('pages/actor.html', add_favorite_form=form, actor_id=actor_id, actor_name=actor_name, actor_score=actor_score, actor_picture=actor_picture, movies=movie_genres, scores=genre_scores, userid=user_id)

@app.route('/about/<user_id>', methods=['GET'])
def about(user_id):
    return render_template('pages/about.html', userid=user_id)


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
