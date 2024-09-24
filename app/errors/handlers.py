from flask import render_template
from app import db
from app.errors import bp
from app.main.forms import SearchForm



@bp.app_errorhandler(404)
def not_found_error(error):
    form = SearchForm()
    return render_template('errors/404.html', form=form), 404

@bp.app_errorhandler(500)
def internal_error(error):
    form = SearchForm()
    db.session.rollback()
    return render_template('errors/500.html', form=form), 500