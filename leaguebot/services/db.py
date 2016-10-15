from leaguebot import app
import sqlite3
from flask import g

if 'SQLLITE_PATH' not in app.config:
    app.config['SQLLITE_PATH'] = '/tmp/leaguebot/sqlite'


def get_conn():
    conn = getattr(g, '_database', None)
    if conn is None:
        g._database = sqlite3.connect(app.config['SQLLITE_PATH'])
        create_table_sql = '''
        create table if not exists ALERTS (
            id TEXT PRIMARY KEY,
            tick INTEGER NOT NULL
        )
        '''
        g._database.cursor().execute(create_table_sql)

    return g._database


@app.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def runQuery(query, params=None):
    conn = get_conn()
    cursor = conn.cursor()
    if (params is not None):
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    conn.commit()
    return cursor

def find_one(query, params=None):
    return runQuery(query, params).fetchone()


def find_all(query, params=None):
    return runQuery(query, params).fetchall()

def execute(query, params=None):
    runQuery(query, params)
