from datetime import datetime, timezone
from flask import render_template, flash, redirect, url_for, request, current_app, g
from flask_login import current_user, login_required
import sqlalchemy as sa
from app import db, mail
from app.main.forms import EditProfileForm, EmptyForm, PostForm, CommentForm, EditPostForm, SearchForm
from app.models import User, Post, Comment, followers
from app.main import bp
from flask_mail import Message
from werkzeug.utils import secure_filename
import os
import bleach
from sqlalchemy import or_

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!', 'success')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(current_user.following_posts(), page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Home', posts=posts.items, form=form, next_url=next_url, prev_url=prev_url)

@bp.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', title='User Profile', user=user, posts=posts.items, form=form, next_url=next_url, prev_url=prev_url)

@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.', 'success')
        return redirect(url_for('main.user', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('new_edit_profile.html', title='Update Profile', form=form)


@bp.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = db.session.scalar(sa.select(Post).where(Post.id == post_id))
    if post is None:
        flash('Post not found.', 'error')
        return redirect(url_for('main.index'))
    
    form = EditPostForm(obj=post)
    
    if form.validate_on_submit():
        if post.author != current_user:
            flash('You do not have permission to edit this post.', 'error')
            return redirect(url_for('main.post_page', post_id=post_id))

        post.title = form.title.data
        post.body = form.post.data
        post.image_url = form.image_url.data
        image_file = form.image_file.data
        image_path = None

        if image_file:
            filename = secure_filename(image_file.filename)

            # Ensure the directory exists
            image_folder = os.path.join(current_app.root_path, 'static', 'images')
            if not os.path.exists(image_folder):
                os.makedirs(image_folder)

            image_path = os.path.join(image_folder, filename)
            image_file.save(image_path)

            # Construct URL using `url_for()` to ensure slashes are correct for URLs
            image_url = url_for('static', filename=f'images/{filename}', _external=True)

            post.image_url = image_url

        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('main.post_page', post_id=post_id))
    
    elif request.method == 'GET':
        form.title.data = post.title
        form.post.data = post.body
    return render_template('new_edit_post.html', form=form, post=post)



@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.', 'error')
            return redirect(url_for('main.index'))
        if user == current_user:
            flash('You cannot follow yourself!', 'error')
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'You are following {username}!', 'success')
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))
    

@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.', 'error')
            return redirect(url_for('main.index'))
        if user == current_user:
            flash('You cannot unfollow yourself!', 'error')
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f'You have unfollowed {username}.', 'success')
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))
    
@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Explore', posts=posts.items, next_url=next_url, prev_url=prev_url)

@bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_page(post_id):
    form = CommentForm()
    hiddenform = EmptyForm()
    post = db.session.scalar(sa.select(Post).where(Post.id == post_id))
    if form.validate_on_submit():
        if post:
            comment = Comment(body=form.comment.data, post=post, author=current_user)
            db.session.add(comment)
            db.session.commit()
            flash('Your comment has been posted!', 'success')
            post_url = url_for('main.post_page', post_id=post_id, _external=True)
            msg = Message(
                'New Comment',
                recipients=[post.author.email],
                body=f"{form.comment.data}\nBy: {current_user.username}\n\nPost URL: {post_url}"
            )
            mail.send(msg)
            print('successful')
        else:
            flash('Post not found.', 'error')
        return redirect(url_for('main.post_page', post_id=post_id))
    comments = post.get_comments()
    return render_template('new_post.html', post=post, form=form, comments=comments, hiddenform=hiddenform)

@bp.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = db.session.scalar(sa.select(Post).where(Post.id == post_id))

    if post is None:
        flash('Post not found.', 'error')
        return redirect(url_for('main.index'))
    
    if post.author != current_user:
        flash('You do not have permission to delete this post.', 'error')
        return redirect(url_for('main.post_page', post_id=post_id))
    
    db.session.execute(sa.delete(Comment).where(Comment.post_id == post.id))
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('main.index'))

@bp.route('/delete_user/<username>', methods=['GET','POST'])
@login_required
def delete_user(username):
    user = db.session.scalar(sa.select(User).where(User.username == username))

    if user is None:
        flash('No user found', 'error')
        return redirect(url_for('main.index'))
    
    if user != current_user:
        flash('You do not have the permission to delete a user.', 'error')
        return redirect(url_for('main.user', username=username))
    
    db.session.execute(sa.delete(Comment).where(Comment.author == user))
    db.session.execute(sa.delete(Post).where(Post.author == user))
    db.session.execute(sa.delete(followers).where(followers.c.follower_id == user.id))
    db.session.execute(sa.delete(followers).where(followers.c.followed_id == user.id))
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/followers_list/<username>')
@login_required
def followers_list(username):
    user = db.session.scalar(sa.select(User).where(User.username == username))
    list = user.get_followers_users()

    return render_template('followers.html', user=user, list=list)

@bp.route('/following_list/<username>')
@login_required
def following_list(username):
    user = db.session.scalar(sa.select(User).where(User.username == username))
    list = user.get_following_users()

    return render_template('following.html', user=user, list=list)

@bp.context_processor
def inject_search_form():
    return dict(form=SearchForm())

@bp.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    
    if form.validate_on_submit():
        searched = form.searched.data
    else:
        searched = request.args.get('searched', '')

    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).where(
        or_(
            Post.title.ilike(f'%{searched}%'),
            Post.body.ilike(f'%{searched}%')
        )
    ).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.search', page=posts.next_num, searched=searched) if posts.has_next else None
    prev_url = url_for('main.search', page=posts.prev_num, searched=searched) if posts.has_prev else None

    return render_template('search.html', title='Search Results', form=form, posts=posts.items, next_url=next_url, prev_url=prev_url, searched=searched)

@bp.route('/add_blog', methods=['GET', 'POST'])
def add_blog():
        form = PostForm()
        if form.validate_on_submit():
            image_url = form.image_url.data
            image_file = form.image_file.data
            image_path = None

            if image_file:
                filename = secure_filename(image_file.filename)

                # Ensure the directory exists
                image_folder = os.path.join(current_app.root_path, 'static', 'images')
                if not os.path.exists(image_folder):
                    os.makedirs(image_folder)

                image_path = os.path.join(image_folder, filename)
                image_file.save(image_path)

                # Construct URL using `url_for()` to ensure slashes are correct for URLs
                image_url = url_for('static', filename=f'images/{filename}', _external=True)

            post = Post(title=form.title.data, body=form.post.data, author=current_user, image_url=image_url)
            db.session.add(post)
            db.session.commit()

            flash('Your post is now live!', category='success')
            return redirect(url_for('main.index'))
        
        return render_template('add_blog.html', title='Add Blog', form=form)

# @bp.template_filter('truncate_html')
# def truncate_html(content, length=200):
#     return bleach.clean(content, tags=[], strip=True)[:length]