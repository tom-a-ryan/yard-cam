# private entries for gae flask main app

# used by Flask session, replace with a different secret
flask_secret = 'Flask Application Secret'


# These should probably be moved to a data store

# allowed users, authenticated by google
white_list = ['tom.a.ryan@gmail.com'
              ]

# internal to main app, not GAE admin
# admin can clear images, etc.
admin_name = 'admin'
admin_password = 'password'
