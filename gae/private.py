# private entries imported by gae flask main.py app
# these need to be changed before deployment
# this file is in .gitignore`
# but to be extra sure to avoid accidentally sending changes back to a repository
# execute something like
#    git update-index --assume-unchanged gae/private.py
# after an edit

# used by Flask session, replace with a different secret
flask_secret = 'Flask Application Secret'

# allowed users, authenticated by google
white_list = ['some_user@gmail.com'
             ]

# Administration internal to application, not GAE admin
# admin can clear images, etc.
admin_name = 'admin'
admin_password = 'password'
