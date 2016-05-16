
# private entries for gae flask main app

# allowed users, authenticated by google
# not very scalable and should be moved to data store

white_list = ['email@gmail.com'
              ]

# ised by Flask session
flask_secret = 'Flask Application Secret'

# internal to main app, not GAE admin
# admin can clear images, etc.

admin_name = 'admin'
admin_password = 'change_me'

