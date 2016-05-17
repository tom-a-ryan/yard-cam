
# private entries for gae flask main app

# allowed users when authenticated by google
# TBD should be moved to data store

white_list = [your_email@gmail.com
              ]

# used by Flask session
flask_secret = 'My Flask Application Secret'

# admin internal to main app, not GAE admin
# admin righta can clear images, etc. and someday edit white_list...

admin_name = 'admin'
admin_password = 'change_me'

